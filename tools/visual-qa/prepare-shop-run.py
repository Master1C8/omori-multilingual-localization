"""Pin all sixth-frame dependencies and preserve every previously accepted image."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--draw-trace',action='store_true');p.add_argument('locale');a=p.parse_args()
root=Path(__file__).resolve().parents[2];tools=root/'tools/visual-qa';run=a.run.resolve()
subprocess.check_call([sys.executable,str(tools/'prepare-equipment-run.py'),'--run',str(run),'--catalog',str(a.catalog),a.locale])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((root/'runtime/visual-qa/20261018-wave/completion.json').read_text())['nativePngHashes']
assert len(base)==135 and all(sha(root/'dist/screenshots/20261017-native'/n)==h for n,h in base.items())
(run/'protected-135.json').write_text(json.dumps(base,indent=2)+'\n')
inputs=json.loads((run/'source-inputs.json').read_text())
for n in ['shop_route.py','shop-batch.py','shop-observer.js','file-assets.js','shop-assets.js']:
 inputs[str((tools/n).relative_to(root))]=sha(tools/n)
 if n.endswith('.py'):shutil.copy2(tools/n,run/'snapshot'/n)
p=run/'snapshot/runtime-observer.js';p.write_text(p.read_text()+'\n'+(tools/'shop-observer.js').read_text())
if a.draw_trace:
 inputs[str((tools/'shop-draw-observer.js').relative_to(root))]=sha(tools/'shop-draw-observer.js')
 p.write_text(p.read_text()+'\n'+(tools/'shop-draw-observer.js').read_text())
p=run/'snapshot/startup-observer.js';p.write_text(p.read_text()+'\n'+(tools/'file-assets.js').read_text()+'\n'+(tools/'shop-assets.js').read_text())
(run/'source-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
pre=json.loads((run/'preparation.json').read_text());pre.update(route='First save -> mailbox event24 -> Buy -> item78 Jacks; no purchase',protectedImages=135,sourceInputs=inputs)
(run/'preparation.json').write_text(json.dumps(pre,indent=2)+'\n')
manifest={str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file() and f.name!='recipe-manifest.json'}
(run/'recipe-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
