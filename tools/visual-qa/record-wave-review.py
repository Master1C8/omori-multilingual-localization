"""Publish an wave review only after native pixels were inspected."""
import argparse,json,os,hashlib
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('locale');p.add_argument('--note',action='append',required=True);p.add_argument('--reject',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[2];c=json.loads((a.run/a.locale/'wave-capture.json').read_text())
image=root/'dist/screenshots/20261017-native'/c['file']
assert Image.open(image).size==(1280,960) and hashlib.sha256(image.read_bytes()).hexdigest()==c['sha256']
r=dict(locale=a.locale,status='fail' if a.reject else 'pass',file=c['file'],sha256=c['sha256'],findings=a.note,
       checks=['locale','glyphs and diacritics','spaces and wrapping','complete Joker Jash dialogue','visible wave deformation and native animation proof','RTL and mixed text where applicable','no non-game overlays'],
       method='Actual native fifth frame visually inspected')
target=a.run/a.locale/'visual-review.json';assert not target.exists()
aggregate=a.run/'wave-visual-reviews.json';all=json.loads(aggregate.read_text()) if aggregate.exists() else {}
if a.locale in all:assert all[a.locale]==r
else:
 all[a.locale]=r;temp=aggregate.with_suffix('.json.new');assert not temp.exists();temp.write_text(json.dumps(all,indent=2)+'\n');temp.replace(aggregate)
temp=target.with_suffix('.json.new');assert not temp.exists();temp.write_text(json.dumps(r,indent=2)+'\n');os.link(temp,target);temp.unlink()
print('WAVE_REVIEW',a.locale,r['status'])
