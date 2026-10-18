"""Pin all fifth-frame dependencies and preserve every previously accepted image."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('locale');a=p.parse_args()
root=Path(__file__).resolve().parents[2];tools=root/'tools/visual-qa';run=a.run.resolve()
subprocess.check_call([sys.executable,str(tools/'prepare-equipment-run.py'),'--run',str(run),'--catalog',str(a.catalog),a.locale])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((root/'runtime/visual-qa/20261018-equipment/completion.json').read_text())['nativePngHashesAfterEncoding']
assert len(base)==108 and all(sha(root/'dist/screenshots/20261017-native'/n)==h for n,h in base.items())
(run/'protected-108.json').write_text(json.dumps(base,indent=2)+'\n')
inputs=json.loads((run/'source-inputs.json').read_text())
for n in ['wave_route.py','wave-batch.py','wave-observer.js','file-assets.js']:
 inputs[str((tools/n).relative_to(root))]=sha(tools/n)
 if n.endswith('.py'):shutil.copy2(tools/n,run/'snapshot'/n)
p=run/'snapshot/runtime-observer.js';p.write_text(p.read_text()+'\n'+(tools/'wave-observer.js').read_text())
p=run/'snapshot/startup-observer.js';p.write_text(p.read_text()+'\n'+(tools/'file-assets.js').read_text())
(run/'source-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
pre=json.loads((run/'preparation.json').read_text());pre.update(route='First save -> playground event18 Joker Jash; complete original SINV animation',protectedImages=108,sourceInputs=inputs)
(run/'preparation.json').write_text(json.dumps(pre,indent=2)+'\n')
manifest={str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file() and f.name!='recipe-manifest.json'}
(run/'recipe-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
