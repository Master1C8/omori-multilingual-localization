"""Dispatch immutable one-locale sessions sequentially; never issue review gates."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--route',choices=['mari','equipment','wave','shop'],default='mari');a=p.parse_args();root=Path(__file__).resolve().parents[2]
plan=a.plan.resolve();data=json.loads(plan.read_text());folder=plan.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert data['status']=='ready' and len(data['entries'])==len({e['locale'] for e in data['entries']})
assert data.get('route',a.route)==a.route,'Plan/worker route mismatch'
assert not (folder/'active.json').exists()
for name in ['tools/visual-qa/mari-series.py','tools/visual-qa/storage_retention.py','tools/visual-qa/retained_series.py']:
 assert name in data['driverInputs'] and sha(root/name)==data['driverInputs'][name], 'Fresh plans must pin the complete retention recipe: '+name
from retained_series import register_plan,storage_lock,collect,finish_plan
from storage_retention import load,atomic_save
control=root/'runtime/storage-retention';control.mkdir(parents=True,exist_ok=True)
policy_path=control/'policy.json'
with storage_lock(control):
 policy=register_plan(root,load(policy_path),plan);atomic_save(policy_path,policy)
for entry in data['entries']:
 for name,h in data['driverInputs'].items():assert sha(root/name)==h,'Dispatch dependency changed: '+name
 run=Path(entry['run']);catalog=Path(entry['catalog']);assert sha(catalog/'catalog.json')==entry['catalogSha256']
 assert not (run/'adoption.json').exists(),'Reconcile the existing session instead of resubmitting it'
 with (run/'batch.log').open('xb') as log:
  child=subprocess.Popen([sys.executable,'-B',str(root/'tools/visual-qa/mari-session.py'),'--run',str(run),'--catalog',str(catalog),'--route',a.route,entry['locale']],cwd=root,stdout=log,stderr=subprocess.STDOUT)
  (folder/'active.json').write_text(json.dumps(dict(entry,pid=child.pid,startedAt=time.time()),indent=2)+'\n')
  print('STARTED',entry['locale'],child.pid,flush=True);result=child.wait()
 assert result==0,'Session failed; preserve its process identity and reconcile cleanup: '+str(run)
 assert json.loads((run/'russian-level-restoration.json').read_text())['levelRepairRestored']
 print('COMPLETED',entry['locale'],flush=True)
 (folder/'active.json').unlink()
 # Every route evicts verified closed caches. Unlinking active.json happens only
 # after the worker exits and restoration passes; queued inputs stay registered.
 with storage_lock(control):
  collect(root,plan,control)
(folder/'complete.json').write_text(json.dumps({'status':'complete','locales':[e['locale'] for e in data['entries']],'planSha256':sha(plan)},indent=2)+'\n')
finish_plan(root,policy_path,plan,control)
