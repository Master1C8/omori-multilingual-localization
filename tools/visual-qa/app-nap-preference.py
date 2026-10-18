"""Temporary app-scoped App Nap diagnostic with exact prior-key restoration."""
import argparse,json,plistlib,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
APP=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app')
DOMAIN=plistlib.loads((APP/'Contents/Info.plist').read_bytes())['CFBundleIdentifier']
KEY='NSAppSleepDisabled'
def value():
 t=subprocess.run(['/usr/bin/defaults','read-type',DOMAIN,KEY],capture_output=True,text=True)
 if t.returncode:
  assert ('does not exist' in t.stderr or "Could not find key '"+KEY+"' in domain '"+DOMAIN+"'." in t.stderr),t.stderr
  return {'exists':False}
 assert 'boolean' in t.stdout,t.stdout
 r=subprocess.run(['/usr/bin/defaults','read',DOMAIN,KEY],capture_output=True,text=True,check=True)
 assert r.stdout.strip() in ['0','1']
 return {'exists':True,'type':'boolean','value':r.stdout.strip()=='1'}
def stopped():
 native=str(APP/'Contents/MacOS/nwjs')+' '
 assert not any(l.strip().startswith(native) for l in subprocess.check_output(['ps','-axo','command='],text=True).splitlines()),'Game must be stopped before preference change'
def save(p,d,new=False):
 if new:
  with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
 else:
  q=p.with_suffix('.json.new');assert not q.exists();q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p)
p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','restore']);p.add_argument('receipt',type=Path);a=p.parse_args();receipt=a.receipt.resolve()
assert receipt.is_relative_to(ROOT/'runtime/visual-qa');assert DOMAIN=='io.nwjs.nwjs';stopped()
if a.action=='apply':
 before=value();d={'status':'prepared','domain':DOMAIN,'key':KEY,'before':before,'preparedAt':time.time(),'scope':'Temporary native game background screenshot diagnostic; no global preference changes','source':'https://developer.apple.com/library/archive/releasenotes/MacOSX/WhatsNewInOSX/Articles/MacOSX10_9.html'}
 save(receipt,d,True)
 subprocess.check_call(['/usr/bin/defaults','write',DOMAIN,KEY,'-bool','YES'])
 assert value()=={'exists':True,'type':'boolean','value':True}
 d.update(status='active',appliedAt=time.time());save(receipt,d)
else:
 d=json.loads(receipt.read_text());assert d['domain']==DOMAIN and d['key']==KEY and d['status']=='active'
 assert value()=={'exists':True,'type':'boolean','value':True},'Preference changed externally; preserve it'
 before=d['before']
 if before['exists']:subprocess.check_call(['/usr/bin/defaults','write',DOMAIN,KEY,'-bool','YES' if before['value'] else 'NO'])
 else:subprocess.check_call(['/usr/bin/defaults','delete',DOMAIN,KEY])
 assert value()==before
 d.update(status='restored',restoredAt=time.time());save(receipt,d)
print(json.dumps({'status':d['status'],'domain':DOMAIN,'original':d['before']}))
