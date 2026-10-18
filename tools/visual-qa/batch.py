"""Sequential native OMORI/Oculix capture with byte-bound installer switching.
A global keyboard pulse can reach DOM down/up inside one engine tick. The
private-source PID-targeted pulse is regression-checked by both Oculix and the
read-only runtime observer before any further action. Never load a save slot.
"""
from runtime import ROOT,RUN,BASE,APP,GAME,CATALOG,sha,save,processes,check_saves,check_desktop,launch,state,stop,resource_baseline
from vision import Vision
from pathlib import Path
import json,subprocess,time,shutil,sys,signal,os
OUTPUT=Path(os.environ.get('OMORI_QA_OUTPUT',str(ROOT/'dist/screenshots/20261017-native')));catalog=json.loads((CATALOG/'catalog.json').read_text());baseline=json.loads((BASE/'baseline.json').read_text());HASH=sha(CATALOG/'catalog.json');ADAPTER=BASE/'locale-adapter'
baseline['assets'],baseline['resourceProfile']=resource_baseline(catalog)
def apply(code):
 check_saves();assert not any(v['command'].startswith(str(APP)+'/') and not v['state'].startswith('Z') for v in processes().values())
 subprocess.check_call([str(ADAPTER),str(CATALOG),HASH,str(APP),code])
 s=json.loads((GAME/'.vnrevival-omori/state.json').read_text());l=next(l for l in catalog['locales'] if l['code']==code);assert s['locale']==code and s['runtimeCode']=='en' and s['catalog']==HASH
 assert s['owned']=={k:f['sha256'] for k,f in l['files'].items()}
 assert all(sha(GAME/k)==f['sha256'] for k,f in l['files'].items()),'Installed bytes differ from package'
 save(RUN/(code+'-installation.json'),{'locale':code,'runtimeChannel':'en','catalogSha256':HASH,'packageArchiveSha256':l['archiveSha256'],'verifiedFiles':len(l['files']),'fileHashes':s['owned']})
def restore():
 # The same adapter restores original-only paths; no raw unguarded asset writes.
 if (GAME/'.vnrevival-omori/state.json').exists():
  apply('ru');assert not (GAME/'.vnrevival-omori/journal.json').exists()
  assert all((sha(GAME/k) if (GAME/k).exists() else None)==h for k,h in baseline['assets'].items()),'Baseline resource restoration mismatch'
  check_saves();meta=GAME/'.vnrevival-omori';dest=RUN/'installer-metadata-final';assert not dest.exists();shutil.move(str(meta),str(dest))
 save(RUN/'restoration.json',{'status':'verified','locale':'ru','runtimeChannel':'en','assetsByteIdentical':len(baseline['assets']),'protectedSaveAndSettingsFilesByteIdentical':len(check_saves()),'saveSlotsLoaded':False,'saveSlotsWritten':False,'temporaryObserverRemoved':True,'installerMetadataArchived':str(RUN/'installer-metadata-final')})
def capture(code,pid):
 directory=RUN/code;v=Vision(directory)
 try:
  check_desktop()
  focus=json.loads(subprocess.check_output([str(RUN/'native-control'),str(pid),'focus']))
  save(directory/'focus.json',focus)
  assert focus['targetActive'] and focus['frontmostPid']==pid,'Native game focus unavailable; no input sent'
  time.sleep(3)
  title,s,tm,w=v.require(pid,'title-logo','Title',100)
  end=time.monotonic()+15
  while not s.get('active'):
   assert time.monotonic()<end,'Title never became interactive';time.sleep(.5);title,s,tm,w=v.require(pid,'title-logo','Title',3)
  if not s.get('focused'):
   subprocess.check_call([str(RUN/'native-control'),str(pid),'focus']);time.sleep(1)
   title,s,tm,w=v.require(pid,'title-logo','Title',5)
   assert s.get('focused'),'Native game did not receive focus; no input sent'
  if s.get('index')!=1:
   assert s.get('index') in (0,2),s;key=124 if s['index']==0 else 123
   subprocess.check_call([str(RUN/'native-control'),str(pid),'key',str(key)]);time.sleep(.7);title,s,tm,w=v.require(pid,'title-logo','Title',3)
  assert s['index']==1 and s.get('active') and s.get('focused') and s.get('canContinue'),s
  time.sleep(2);title,s,tm,w=v.require(pid,'title-logo','Title',3);assert s['index']==1 and s.get('active') and s.get('focused')
  main=OUTPUT/(code+'-01-main-menu.png');assert not main.exists();shutil.copyfile(title,main)
  # Fresh independent runtime and visual guards before Confirm.
  guard,s,_,_=v.require(pid,'title-logo','Title',3);assert s['index']==1 and s.get('active') and s.get('focused')
  subprocess.check_call([str(RUN/'native-control'),str(pid),'key','6'])
  load,ls,lm,lw=v.require(pid,'load-portrait','File',20);time.sleep(2);load,ls,lm,lw=v.require(pid,'load-portrait','File',3)
  assert ls['scene']=='Scene_OmoriFile',ls
  from PIL import Image
  text_pixels=sum(max(v)>60 for v in Image.open(load).convert('RGB').crop((420,70,1170,112)).getdata())
  assert text_pixels>300,'Save header text not yet visible'
  dest=OUTPUT/(code+'-02-load-game.png');assert not dest.exists();shutil.copyfile(load,dest)
  save(directory/'capture.json',{'locale':code,'runtimeChannel':'en','mainMenu':{'file':main.name,'sha256':sha(main),'marker':tm,'state':s},'loadGame':{'file':dest.name,'sha256':sha(dest),'marker':lm,'state':ls},'dimensions':[1280,960],'window':w,'captureMethod':'Oculix 4.0.0 Finder engine, native macOS window content without resizing or annotations','input':'Private-source PID-targeted native Z pulse; no slot confirmation','automatedResult':'pass','visualReview':'pending','saveSlotsLoaded':False,'saveSlotsWritten':False})
  print('CAPTURED',code,flush=True)
 except BaseException:
  try:
   p,_,_=v.capture(pid,'failure');save(directory/'failure.json',{'frame':str(p),'state':state()})
  except Exception:pass
  raise
 finally:v.close()
def await_review(code):
 if os.environ.get('OMORI_QA_REVIEW_GATE')!='1':return
 receipt=RUN/code/'visual-review.json';end=time.monotonic()+1800
 print('AWAITING_VISUAL_REVIEW',code,flush=True)
 while not receipt.exists():
  assert time.monotonic()<end,'Visual review gate timed out; restore before another locale'
  time.sleep(1)
 review=json.loads(receipt.read_text());capture_receipt=json.loads((RUN/code/'capture.json').read_text())
 assert review['status']=='pass','Visual review rejected '+code
 assert review['files']=={capture_receipt[k]['file']:capture_receipt[k]['sha256'] for k in ['mainMenu','loadGame']},'Review is bound to different frames'
def main():
 selected=sys.argv[1:] or [l['code'] for l in catalog['locales'] if l['code']!='ru'];active=False
 try:
  for code in selected:
   assert code in baseline['requiredLocales'] and code!='ru'
   receipt=RUN/code/'capture.json'
   if receipt.exists():
    r=json.loads(receipt.read_text());assert all(sha(OUTPUT/r[k]['file'])==r[k]['sha256'] for k in ['mainMenu','loadGame']);print('REUSED',code,flush=True);continue
   check_desktop();assert os.access(RUN/'native-control',os.X_OK),'Native controller is not executable'
   apply(code);pid=launch(code);active=True
   try:capture(code,pid)
   finally:stop();active=False
   await_review(code)
  save(RUN/'batch-status.json',{'status':'capture-complete-review-pending','locales':selected})
 except BaseException as e:
  save(RUN/'batch-status.json',{'status':'stopped','error':repr(e)});raise
 finally:
  if (RUN/'owned-game.json').exists():
   owned=json.loads((RUN/'owned-game.json').read_text());rows=processes();pid=owned['pid']
   if pid in rows and rows[pid]['command'].startswith(owned['executable']+' ') and not rows[pid]['state'].startswith('Z'):stop()
  restore()
if __name__=='__main__':main()
