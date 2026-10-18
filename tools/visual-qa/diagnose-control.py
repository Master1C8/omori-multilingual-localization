import json,subprocess,time
from runtime import ROOT,RUN,state,save
from vision import Vision
owned=json.loads((RUN/'owned-game.json').read_text());pid=owned['pid'];directory=Path(owned['directory']) if False else RUN/'ru-observer';v=Vision(directory);receipts=[]
try:
 subprocess.check_call([str(RUN/'native-control'),str(pid),'focus']);time.sleep(3)
 path,s,m,w=v.require(pid,'title-logo','Title');assert s.get('active') and s.get('index')==1,s
 receipts.append({'stage':'before','state':s})
 subprocess.check_call([str(ROOT/'runtime/visual-qa/20261017-native/native-input'),'key','6']);time.sleep(2);s=state();receipts.append({'stage':'after-old-global-input','state':s});v.capture(pid,'old-input-result');save(directory/'diagnosis.json',receipts)
 if 'Title' in s.get('scene',''):
  path,s,m,w=v.require(pid,'title-logo','Title',3);assert s['index']==1 and s.get('active'),s
  subprocess.check_call([str(RUN/'native-control'),str(pid),'key','6']);time.sleep(2);s=state();receipts.append({'stage':'after-fixed-targeted-input','state':s});v.capture(pid,'fixed-input-result');save(directory/'diagnosis.json',receipts)
 print(json.dumps(receipts,indent=2),flush=True)
finally:v.close()
