"""Three independent locale builds; defer source edits until all recorded children exit."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2];q=root/'runtime/visual-qa/20261018-wave';spec=json.loads((q/'contextual-build-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=json.loads((root/'build/multilingual-delivery/ar/native-wave-20261018-01/manifest.json').read_text());pins={n:sha(root/n) for n in parent['recipeDependencies']}
target=q/'contextual-build-jobs.json';assert not target.exists()
def write(value):
 p=target.with_suffix('.json.new');p.write_text(json.dumps(value,indent=2)+'\n');p.replace(target)
state=dict(status='running',sourceEditPolicy='No delivery/helper/source-closure edits until all children exit',sourcePins=pins,jobs={})
children=[]
for code,s in spec.items():
 output=root/'build/multilingual-delivery'/code/'native-wave-20261018-01';assert not output.exists()
 log=(q/(code+'-wave-build.log')).open('xb')
 args=[sys.executable,'-B',str(root/'tools/multilingual/delivery/native_delivery.py'),'--root',str(root),'--locale',code,'build','--plaintext',s['plaintext'],'--output',str(output),'--reuse-font-build',s['reuseFontBuild']]
 p=subprocess.Popen(args,cwd=root,stdout=log,stderr=subprocess.STDOUT);children.append((code,p,log));state['jobs'][code]=dict(pid=p.pid,output=str(output),log=str(q/(code+'-wave-build.log')),returncode=None);write(state)
 print('STARTED_BUILD',code,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in children):
 changed=False
 for code,p,_ in children:
  result=p.poll()
  if result is not None and state['jobs'][code]['returncode'] is None:
   state['jobs'][code]['returncode']=result;changed=True;print('FINISHED_BUILD',code,result,flush=True)
 if changed:write(state)
 time.sleep(1)
for code,p,log in children:state['jobs'][code]['returncode']=p.wait();log.close()
assert all(sha(root/n)==h for n,h in pins.items()),'Source closure changed while builds were live'
state['status']='complete' if all(v['returncode']==0 for v in state['jobs'].values()) else 'failed';write(state)
if state['status']!='complete':raise SystemExit(1)
