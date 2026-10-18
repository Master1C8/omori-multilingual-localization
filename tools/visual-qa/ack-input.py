"""Hold one native key until a fresh observer proves engine frames consumed it."""
import json,subprocess,time,os
from pathlib import Path
from runtime import RUN,state,save
KEYS={6:(90,'ok'),7:(88,'escape'),123:(37,'left'),124:(39,'right'),125:(40,'down'),126:(38,'up')}
def assert_background_focus(native):
 if native.get('targetActive') is not False or native.get('frontmostPid')==native.get('targetPid'):
  raise ValueError('Background capture refuses foreground game input')
def pulse(pid,key,evidence):
 if os.environ.get('OMORI_QA_INPUT_MODE')=='bridge':
  import importlib.util
  spec=importlib.util.spec_from_file_location('bridge_input',Path(__file__).with_name('bridge-input.py'))
  bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
  assert os.environ.get('OMORI_QA_BACKGROUND')=='1'
  return bridge.pulse(pid,key,evidence,KEYS,assert_background_focus)
 native=RUN/'native-control';before=state();code,name=KEYS[key]
 focus=json.loads(subprocess.check_output([str(native),str(pid),'state']))
 if os.environ.get('OMORI_QA_BACKGROUND')=='1':assert_background_focus(focus)
 if os.environ.get('OMORI_QA_BACKGROUND')!='1':assert focus['targetActive'] and focus['frontmostPid']==pid and before['focused']
 owned=json.loads((RUN/'owned-game.json').read_text())
 command=[str(native),str(pid),'ackkey',str(key),owned['statePath']]
 process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:result=json.loads(process.stdout)
 except ValueError:
  save(evidence,{'key':key,'before':before,'returncode':process.returncode,'stdout':process.stdout,'stderr':process.stderr})
  raise
 save(evidence,{'key':key,'before':before,'native':result,'returncode':process.returncode,'stderr':process.stderr})
 assert process.returncode==0 and result['acknowledged'],result
 time.sleep(.3);after=state();save(evidence,{'key':key,'before':before,'native':result,'returncode':process.returncode,'afterRelease':after,'mode':'One native process holds down until observed engine-frame consumption, then releases without another helper launch'})
 return after
