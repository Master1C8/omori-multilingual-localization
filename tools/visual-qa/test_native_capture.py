"""WindowServer/native image capture is replaced; exercise bounded recovery only."""
import json,tempfile,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import vision as v

def window(number,pid=101):
 return dict(kCGWindowNumber=number,kCGWindowOwnerPID=pid,kCGWindowBounds={'Width':640,'Height':508})
transient='could not create image from window\n'
for errors in [[],[transient],['permission denied'],[transient,transient]]:
 with tempfile.TemporaryDirectory() as folder:
  directory=Path(folder);windows=[];requests=[];desktop=[]
  def metadata(args):
   windows.append(args);return json.dumps([window(11+len(windows))])
  def capture(args,**kw):
   assert args[0]=='/usr/sbin/screencapture' and kw==dict(capture_output=True,text=True,timeout=10)
   requests.append(args);error=errors[len(requests)-1] if len(requests)<=len(errors) else ''
   if not error:Path(args[-1]).write_bytes(b'native-frame-fixture')
   return subprocess.CompletedProcess(args,1 if error else 0,'',error)
  with patch.dict(v.os.environ,OMORI_QA_BACKGROUND='1'),patch.object(v,'check_desktop',side_effect=lambda:desktop.append(True)),patch.object(v.subprocess,'check_output',side_effect=metadata),patch.object(v.subprocess,'run',side_effect=capture),patch.object(v.time,'sleep'):
   try:raw,w=v.native_capture(101,directory,'fixture',18)
   except subprocess.CalledProcessError as error:
    assert errors in [['permission denied'],[transient,transient]] and error.returncode==1
   else:
    assert errors in [[],[transient]] and raw.read_bytes()==b'native-frame-fixture'
    assert w['kCGWindowNumber']==11+len(requests)
   expected=2 if errors and errors[0]==transient else 1
   assert len(requests)==len(windows)==expected
   assert [a[a.index('-l')+1] for a in requests]==[str(12+i) for i in range(expected)]
   if expected==2:assert requests[0][-1]!=requests[1][-1] and 'retry-1' in requests[1][-1]
   rows=json.loads((directory/'0018-fixture-native-capture-attempts.json').read_text())
   assert len(rows)==expected and [r['returncode'] for r in rows]==[1 if i<len(errors) else 0 for i in range(expected)]
# Reject ambiguous ownership before invoking the image API at all.
with tempfile.TemporaryDirectory() as folder:
 ticks=iter([0,10]);directory=Path(folder)
 def bad_metadata(args):return json.dumps([window(12),window(13)]) if args[-1]!='state' else '{}'
 with patch.dict(v.os.environ,OMORI_QA_BACKGROUND='1'),patch.object(v,'check_desktop'),patch.object(v.subprocess,'check_output',side_effect=bad_metadata),patch.object(v.subprocess,'run') as image_api,patch.object(v.time,'monotonic',side_effect=lambda:next(ticks)):
  try:v.native_capture(101,directory,'fixture',1)
  except RuntimeError as error:assert 'did not settle' in str(error)
  else:raise AssertionError('Ambiguous native ownership passed')
  image_api.assert_not_called();assert (directory/'window-boundary.json').exists()
print('PASS native capture unchanged success, one exact-error retry with fresh window identity/unique raw path, immediate permission failure, persistent-failure bound and ambiguous-owner rejection. No native WindowServer or pixel-capture correctness is claimed by these mocks.')
# A timeout is an unknown command result. Reconcile the exact unique file first.
from PIL import Image
for mode in ['complete','absent-then-success','invalid-then-success','wrong-size-then-success','persistent-timeout']:
 with tempfile.TemporaryDirectory() as folder:
  directory=Path(folder);requests=[];windows=[]
  def metadata(args):windows.append(args);return json.dumps([window(40+len(windows))])
  def capture(args,**kw):
   requests.append(args);path=Path(args[-1])
   if len(requests)>1 and mode!='persistent-timeout':path.write_bytes(b'success-fixture');return subprocess.CompletedProcess(args,0,'','')
   if mode=='complete':Image.new('RGB',(1280,1016)).save(path)
   elif mode=='invalid-then-success':path.write_bytes(b'broken PNG')
   elif mode=='wrong-size-then-success':Image.new('RGB',(1280,960)).save(path)
   raise subprocess.TimeoutExpired(args,10)
  with patch.dict(v.os.environ,OMORI_QA_BACKGROUND='1'),patch.object(v,'check_desktop'),patch.object(v.subprocess,'check_output',side_effect=metadata),patch.object(v.subprocess,'run',side_effect=capture),patch.object(v.time,'sleep'):
   try:raw,w=v.native_capture(101,directory,'timeout',22)
   except subprocess.TimeoutExpired:assert mode=='persistent-timeout'
   else:assert mode!='persistent-timeout' and raw.exists()
   assert len(requests)==len(windows)==(1 if mode=='complete' else 2)
   rows=json.loads((directory/'0022-timeout-native-capture-attempts.json').read_text());assert rows[0]['returncode'] is None and rows[0]['timedOut']
   assert rows[0]['completeNativePngValidated']==(mode=='complete')
   if len(requests)==2:assert requests[0][-1]!=requests[1][-1]
print('PASS timeout outcome reconciliation: complete native PNG accepted without false exit zero or replay; absent/corrupt/wrong-size outputs require one fresh read; repeated timeout stops.')
