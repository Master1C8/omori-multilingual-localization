"""Publish a hash-bound gate only after the actual third frame was inspected."""
import argparse,json,hashlib,os
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('locale');p.add_argument('--note',action='append',required=True);p.add_argument('--reject',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[2];c=json.loads((a.run/a.locale/'mari-capture.json').read_text());image=root/'dist/screenshots/20261017-native'/c['file'];assert Image.open(image).size==(1280,960);assert hashlib.sha256(image.read_bytes()).hexdigest()==c['sha256']
r={'locale':a.locale,'status':'fail' if a.reject else 'pass','file':c['file'],'sha256':c['sha256'],'findings':a.note,'checks':['visible locale','glyphs and diacritics','spaces','wrapping and clipping','RTL and mixed text where applicable','same first quest and advice state','no non-game overlays'],'method':'Actual native frame visually inspected at original resolution'}
target=a.run/a.locale/'visual-review.json';assert not target.exists();aggregate=a.run/'mari-visual-reviews.json';all=json.loads(aggregate.read_text()) if aggregate.exists() else {}
if a.locale in all:assert all[a.locale]==r,'Interrupted publication conflicts with saved review'
else:
 all[a.locale]=r;temp=aggregate.with_suffix('.json.new');assert not temp.exists();temp.write_text(json.dumps(all,indent=2)+'\n');temp.replace(aggregate)
temp=target.with_suffix('.json.new');raw=json.dumps(r,indent=2)+'\n'
if temp.exists():assert temp.read_text()==raw
else:temp.write_text(raw)
os.link(temp,target);temp.unlink();print('MARI_REVIEW',a.locale,r['status'])
