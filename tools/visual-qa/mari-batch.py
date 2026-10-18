"""Sequential third-screen capture; existing accepted frames are immutable."""
import json,time,os,sys,shutil
from pathlib import Path
from runtime import ROOT,RUN,BASE,APP,GAME,sha,save,processes,check_saves,check_desktop,launch,stop,resource_baseline
from batch import apply,restore
from mari_route import MariRoute
OUTPUT=ROOT/'dist/screenshots/20261017-native'
def protected_frames():
 baseline=json.loads((ROOT/'runtime/visual-qa/20261017-mari-manual-01/accepted-54.json').read_text())
 fix_path=ROOT/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json'
 if fix_path.exists():
  fix=json.loads(fix_path.read_text())
  if fix['status']=='verified':
   assert baseline['ru-02-load-game.png']==fix['oldImageSha256']
   assert sha(Path(fix['preservedOldImage']))==fix['oldImageSha256']
   baseline['ru-02-load-game.png']=fix['newImageSha256']
 return baseline
def await_review(code):
 path=RUN/code/'visual-review.json';end=time.monotonic()+1800;print('AWAITING_MARI_REVIEW',code,flush=True)
 while not path.exists():assert time.monotonic()<end,'Review gate timeout';time.sleep(1)
 review=json.loads(path.read_text());cap=json.loads((RUN/code/'mari-capture.json').read_text())
 assert review['status']=='pass' and review['file']==cap['file'] and review['sha256']==cap['sha256'],'Third-screen review rejected or mismatched'
def main():
 assert os.environ.get('OMORI_QA_BACKGROUND')=='1','Background-only route required'
 assert (RUN/'templates').is_dir(),'Pin every recognition template before launching a batch'
 selected=sys.argv[1:];assert selected and len(selected)==len(set(selected))
 baseline54=protected_frames()
 try:
  for code in selected:
   assert code!='ru';dest=OUTPUT/(code+'-03-mari-quests.png');assert not dest.exists(),'Preserve existing third-screen evidence'
   assert all(sha(OUTPUT/n)==h for n,h in baseline54.items())
   check_desktop();check_saves();apply(code);pid=launch(code);route=None
   try:
    route=MariRoute(pid,RUN/code);receipt=route.run();source=Path(receipt['frame']);shutil.copyfile(source,dest)
    receipt.update(locale=code,runtimeChannel='en',file=dest.name,sha256=sha(dest),dimensions=[1280,960],automatedResult='pass',visualReview='pending',captureMethod='Oculix 4.0.0 Finder and native macOS game content without resizing or annotations')
    save(RUN/code/'mari-capture.json',receipt);print('MARI_CAPTURED',code,flush=True)
   except BaseException as e:
    if route:
     try:frame,_,_=route.frame('failure');save(RUN/code/'mari-failure.json',{'error':repr(e),'frame':str(frame)})
     except Exception:pass
    raise
   finally:
    if route:route.close()
    stop()
   await_review(code)
  save(RUN/'mari-status.json',{'status':'complete','locales':selected,'allVisualReviewsPassed':True})
 except BaseException as e:save(RUN/'mari-status.json',{'status':'stopped','error':repr(e)});raise
 finally:
  if (RUN/'owned-game.json').exists():
   own=json.loads((RUN/'owned-game.json').read_text());rows=processes()
   if own['pid'] in rows and not rows[own['pid']]['state'].startswith('Z'):stop()
  restore()
  restored=json.loads((RUN/'restoration.json').read_text())
  verified=[];unknown=[]
  for code in selected:
   directory=RUN/code;cap=directory/'mari-capture.json';proof=directory/'load-first-save-semantic-result.json';legacy=directory/'load-first-save-after.json'
   if cap.exists() and json.loads(cap.read_text()).get('saveSlotLoaded')==1:verified.append(code)
   elif proof.exists() or legacy.exists():
    state=json.loads((proof if proof.exists() else legacy).read_text())
    if state.get('scene')=='Scene_Map' and state.get('map',{}).get('id')==92:verified.append(code)
    else:unknown.append(code)
   elif (directory/'load-first-save-before.json').exists():unknown.append(code)
  restored.update(saveSlotsLoaded=True if verified else (None if unknown else False),saveSlotLoadedPerLocale=1 if len(verified)==len(selected) else None,verifiedLoadedLocales=verified,loadEvidenceUnknownLocales=unknown,saveSlotsWritten=False,resourceProfile=resource_baseline()[1])
  save(RUN/'restoration.json',restored)
  assert all(sha(OUTPUT/n)==h for n,h in baseline54.items())
  for p in RUN.glob('*/package-before.json'):assert (GAME/'package.json').read_bytes()==p.read_bytes()
if __name__=='__main__':main()
