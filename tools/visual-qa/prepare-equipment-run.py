"""Pin complete fourth-screen capture recipes before any game launch."""
import argparse,hashlib,json,shutil,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('locale');a=p.parse_args()
root=Path(__file__).resolve().parents[2];tools=root/'tools/visual-qa';run=a.run.resolve();catalog=a.catalog.resolve()
assert run.is_relative_to(root/'runtime/visual-qa') and not run.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((catalog/'catalog.json').read_text());assert a.locale in [r['code'] for r in c['locales']]
assert sha(catalog/'catalog.json')==json.loads((catalog/'payload-receipt.json').read_text())['catalogSha256']
images=root/'dist/screenshots/20261017-native'
base=json.loads((root/'runtime/visual-qa/20261017-mari-manual-01/accepted-54.json').read_text())
fix=json.loads((root/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json').read_text());base['ru-02-load-game.png']=fix['newImageSha256']
final=json.loads((root/'runtime/visual-qa/20261017-final-81/report.json').read_text());assert final['status']=='complete'
for r in final['thirdFrameReviews'].values():base[r['file']]=r['sha256']
assert len(base)==81 and all(sha(images/n)==h for n,h in base.items())
run.mkdir(parents=True);(run/'snapshot').mkdir();(run/'templates').mkdir()
source_inputs={}
launch_proof=root/'runtime/visual-qa/20261018-equipment/run-pt-BR-02/owned-game.json'
source_inputs[str(launch_proof.relative_to(root))]=sha(launch_proof)
names=['runtime.py','vision.py','batch.py','mari_route.py','equipment_route.py','equipment-batch.py','ack-input.py','bridge-input.py','adopt-verified-ru.py',
       'native-control.m','native-window.m','OculixMatch.java']
for n in names:
 source_inputs[str((tools/n).relative_to(root))]=sha(tools/n);shutil.copy2(tools/n,run/'snapshot'/n)
parts=['runtime-observer.js','background-adapter.js','mari-observer.js','input-bridge.js']
for n in parts:source_inputs[str((tools/n).relative_to(root))]=sha(tools/n)
(run/'snapshot/runtime-observer.js').write_text('\n'.join((tools/n).read_text() for n in parts))
for n in ['startup-observer.js','background-frame-adapter.js','background-window-adapter.js','equipment-assets.js']:source_inputs[str((tools/n).relative_to(root))]=sha(tools/n)
(run/'snapshot/startup-observer.js').write_text('\n'.join((tools/n).read_text() for n in ['background-frame-adapter.js','startup-observer.js','equipment-assets.js','background-window-adapter.js']))
helpers=root/'runtime/visual-qa/20261017-mari-series-40/run-sw'
for n in ['native-control','native-window','OculixMatch.class']:
 source_inputs[str((helpers/n).relative_to(root))]=sha(helpers/n);shutil.copy2(helpers/n,run/n)
assert os.access(run/'native-control',os.X_OK) and os.access(run/'native-window',os.X_OK)
for f in (tools/'templates').glob('*.png'):
 source_inputs[str(f.relative_to(root))]=sha(f);shutil.copy2(f,run/'templates'/f.name)
assert all((run/'templates'/n).is_file() for n in ['character-menu-frame.png','equipment-knife.png','mari-picnic.png'])
(run/'protected-81.json').write_text(json.dumps(base,indent=2)+'\n')
(run/'source-inputs.json').write_text(json.dumps(source_inputs,indent=2)+'\n')
manifest={str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file()}
(run/'recipe-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(run/'preparation.json').write_text(json.dumps(dict(locale=a.locale,catalog=str(catalog),catalogSha256=sha(catalog/'catalog.json'),
  route='First save -> X -> equip -> OMORI; stop before item confirmation',protectedImages=81,sourceInputs=source_inputs),indent=2)+'\n')
print('Prepared immutable equipment run:',run)
