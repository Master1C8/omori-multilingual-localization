"""Consolidate proven duplicate objects in one restored, closed QA archive.

All paths and bytes survive. Archived backup objects must remain immutable.
Unique objects, live installer metadata, and game resources are never selected.
"""
import argparse,sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from cleanup_localization_storage import signature,digest,link_identical
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);a=p.parse_args();run=a.run.resolve()
assert run.is_relative_to(ROOT/'runtime/visual-qa') and not (run/'archive-deduplication.json').exists()
assert json.loads((run/'restoration.json').read_text())['status']=='verified'
assert json.loads((run/'russian-level-restoration.json').read_text())['levelRepairRestored']
own=json.loads((run/'owned-game.json').read_text());directory=Path(own['directory'])
assert directory.is_relative_to(run) and json.loads((directory/'stopped.json').read_text())['stopped']
base=run/'installer-metadata-final/backups';assert base.is_dir()
proof=ROOT/'diagnostics/cleanup-20261018-01/plan.json';index={}
for x in json.loads(proof.read_text())['links']:
 k=x['keeper'];name=k['path'];assert name.startswith('runtime/visual-qa/20261017-') and '/installer-metadata-final/backups/' in name
 index[(k['sha256'],*k['signature'][4:])]=ROOT/name
selected=[];kept=0
for target in sorted(base.iterdir()):
 s=signature(target);h=target.name;assert len(h)==64 and all(c in '0123456789abcdef' for c in h)
 assert digest(target)==h and signature(target)==s
 keeper=index.get((h,*s[4:]))
 if keeper is None:kept+=1;continue
 ks=signature(keeper)
 assert digest(keeper)==h and signature(keeper)==ks
 if s[:2]==ks[:2]:kept+=1;continue
 selected.append((target,keeper,s,ks,h))
receipt={'status':'verified','run':str(run),'keeperInventorySha256':digest(proof),'linked':[],
 'retainedUniqueOrAlreadySharedObjects':kept,'policy':'Only immutable, restored, stopped QA backup objects; all bytes and paths retained.'}
with (run/'archive-deduplication.journal.jsonl').open('x') as log:
 for target,keeper,s,ks,h in selected:
  link_identical(target,keeper,s,ks,h)
  row={'path':str(target.relative_to(ROOT)),'keeper':str(keeper.relative_to(ROOT)),'sha256':h}
  log.write(json.dumps(row)+'\n');log.flush();receipt['linked'].append(row)
for target,keeper,_,_,h in selected:assert digest(target)==h and target.stat().st_ino==keeper.stat().st_ino
with (run/'archive-deduplication.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'run':str(run),'status':'verified','linkedDuplicateObjects':len(selected),'retainedObjects':kept}))
