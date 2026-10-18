"""Record an already performed visual review; never infer acceptance from capture."""
import argparse,json,hashlib,os
from pathlib import Path
from PIL import Image

p=argparse.ArgumentParser()
p.add_argument('run',type=Path);p.add_argument('locale')
p.add_argument('--note',action='append',required=True)
p.add_argument('--reject',action='store_true')
a=p.parse_args();root=Path(__file__).resolve().parents[2]
receipt=json.loads((a.run/a.locale/'capture.json').read_text());files={}
for key in ['mainMenu','loadGame']:
 row=receipt[key];image=root/'dist/screenshots/20261017-native'/row['file']
 assert Image.open(image).size==(1280,960)
 digest=hashlib.sha256(image.read_bytes()).hexdigest();assert digest==row['sha256'];files[row['file']]=digest
review={'locale':a.locale,'status':'fail' if a.reject else 'pass','files':files,
 'method':'Both actual captured frames visually inspected; native-scale text regions inspected when needed',
 'checks':['visible language','glyphs and diacritics','spaces','text clipping and overlap','RTL and mixed runs where applicable','non-game overlays'],
 'findings':a.note,'scope':'Main menu and save-list screen only; no translation editorial or save-slot load'}
target=a.run/a.locale/'visual-review.json';assert not target.exists()
# Write the batch gate last, after the durable aggregate review record.
aggregate=a.run/'visual-reviews.json';reviews=json.loads(aggregate.read_text()) if aggregate.exists() else {}
if a.locale in reviews:
 assert reviews[a.locale]==review,'Interrupted publication conflicts with the saved review'
else:
 reviews[a.locale]=review;temporary=aggregate.with_suffix('.json.new');assert not temporary.exists()
 temporary.write_text(json.dumps(reviews,indent=2)+'\n');temporary.replace(aggregate)
# Canonical aggregate commits first. A retry with identical evidence resumes the
# gate publication after an interruption; a half-written file is never a gate.
temporary=target.with_suffix('.json.new');raw=json.dumps(review,indent=2)+'\n'
if temporary.exists():assert temporary.read_text()==raw
else:temporary.write_text(raw)
os.link(temporary,target);temporary.unlink();print('RECORDED',a.locale,review['status'])
