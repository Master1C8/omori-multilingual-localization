#!/usr/bin/env python3
"""Create a regular static Hebrew fallback from the pinned official OFL variable font."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.venv-fonts/lib/python3.9/site-packages'))
import fontTools
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.boundsPen import BoundsPen
assert fontTools.__version__=='4.60.2'
source=ROOT/'source/font-reference/Hebrew-NotoSansHebrew[wdth,wght].ttf'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='7ef36a2c3593758cdb622e1bdef4f84523e92fbc3ccc667438dd80ff54c2de88'
target=source.with_name('Hebrew-OMORIHebrew-Regular.ttf')
if target.exists():raise ValueError('Preserve existing derived font; verify it instead of overwriting')
font=instantiateVariableFont(TTFont(source),{'wght':400,'wdth':100},inplace=False)
# A distinct derivative family avoids carrying the variable font's Thin default name.
values={1:'OMORI Hebrew Fallback',2:'Regular',3:'3.001;OMORIHebrewFallback-Regular',4:'OMORI Hebrew Fallback Regular',6:'OMORIHebrewFallback-Regular',16:'OMORI Hebrew Fallback',17:'Regular'}
for record in font['name'].names:
 if record.nameID in values:record.string=values[record.nameID].encode(record.getEncoding())
font.save(target);font.close();font=TTFont(target)
assert 'fvar' not in font and font['OS/2'].usWeightClass==400
cmap=font.getBestCmap();glyphs=font.getGlyphSet();needed=[0x5b4,0x5b6,0x5bc,0x5be]+list(range(0x5d0,0x5eb))+[0x5f4]
for code in needed:
 assert code in cmap and cmap[code]!='.notdef';pen=BoundsPen(glyphs);glyphs[cmap[code]].draw(pen);assert pen.bounds is not None,hex(code)
assert font['hmtx'][cmap[32]][0]>0 and 'GPOS' in font
p=ROOT/'source/font-reference/Hebrew-provenance-v1.json';record=json.loads(p.read_text());record['derived']={'path':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'recipe':'tools/prepare_hebrew_font.py','fontTools':'4.60.2','axes':{'wght':400,'wdth':100},'reason':'Upstream variable default is weight100/Thin. Bind a regular static face for the Chromium65 renderer, without relying on variable-font axis selection.','family':'OMORI Hebrew Fallback','outlinesChecked':len(needed),'metrics':{'unitsPerEm':font['head'].unitsPerEm,'ascender':font['hhea'].ascent,'descender':font['hhea'].descent,'spaceAdvance':font['hmtx'][cmap[32]][0]},'license':'Derivative renamed; original copyright and OFL preserved; original font and license retained.'};p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record['derived'],indent=2))
