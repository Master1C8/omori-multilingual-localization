"""Lossless, unscaled text-region crops for reviewing every final frame.
These are review-only artifacts; original final PNGs are never edited.
"""
from pathlib import Path
from PIL import Image
import sys,json,hashlib
root=Path(__file__).resolve().parents[2];out=root/'runtime/visual-qa/review-20261017';out.mkdir(exist_ok=True);images=root/'dist/screenshots/20261017-native'
for code in sys.argv[1:]:
 menu=images/(code+'-01-main-menu.png');load=images/(code+'-02-load-game.png')
 if not menu.exists() or not load.exists():continue
 m=Image.open(menu);l=Image.open(load);assert m.size==l.size==(1280,960)
 # Every UI text area in the menu and all visible save-list text, at native pixels.
 board=Image.new('RGB',(1280,1170),'#808080');board.paste(m.crop((0,0,1280,65)),(0,0));board.paste(m.crop((0,865,1280,960)),(0,75));board.paste(l,(0,180));board.save(out/(code+'-text-review.png'))
 (out/(code+'-binding.json')).write_text(json.dumps({'menu':{'path':str(menu),'sha256':hashlib.sha256(menu.read_bytes()).hexdigest()},'load':{'path':str(load),'sha256':hashlib.sha256(load.read_bytes()).hexdigest()},'scale':1,'annotationsInFinalFrames':False},indent=2)+'\n')
 print(out/(code+'-text-review.png'))
