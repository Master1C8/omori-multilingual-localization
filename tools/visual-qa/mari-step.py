"""One supervised native action with fresh state and before/after evidence."""
import argparse,json,sys,subprocess,time,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--scene',required=True);p.add_argument('--key',type=int);p.add_argument('--marker');a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime import RUN,state,save,check_saves,check_desktop
from vision import Vision
owned=json.loads((RUN/'owned-game.json').read_text());pid=owned['pid'];directory=RUN/'steps'/a.label;directory.mkdir(parents=True,exist_ok=False)
v=Vision(directory)
try:
 check_desktop();check_saves();s=state();assert s['scene']==a.scene,s
 native=json.loads(subprocess.check_output([str(RUN/'native-control'),str(pid),'state']))
 if os.environ.get('OMORI_QA_BACKGROUND')!='1':assert native['targetActive'] and native['frontmostPid']==pid
 before,rgb,w=v.capture(pid,'before');save(directory/'before.json',s)
 if a.marker:assert v.match(rgb,a.marker+'.png')['matched']
 if a.key is not None:
  assert (s['focused'] or os.environ.get('OMORI_QA_BACKGROUND')=='1') and not s['visibleError']
  import importlib.util
  spec=importlib.util.spec_from_file_location('ack_input',Path(__file__).with_name('ack-input.py'));ack=importlib.util.module_from_spec(spec);spec.loader.exec_module(ack)
  ack.pulse(pid,a.key,directory/'input.json');time.sleep(2)
 after,_,_=v.capture(pid,'after');save(directory/'after.json',state())
 probe=Path(owned['statePath']+'.mari.json');save(directory/'gameplay.json',json.loads(probe.read_text()))
 game=json.loads(probe.read_text());print(after);print(json.dumps({'scene':game['scene'],'file':game['file'],'player':game['player'],'message':game['message'],'openWindows':[w for w in game['windows'] if w.get('openness',0)>0 and ('Quest' in w['type'] or w['type']=='Window_Message')]}))
except BaseException as error:
 save(directory/'failure.json',{'error':repr(error),'lastFrame':str(before) if 'before' in locals() else None})
 raise
finally:v.close()
