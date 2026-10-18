#!/usr/bin/env python3
"""Prepare licensed outline fallback; never modify the installed game.

Two faces match each original font's measured cap height and retain its baseline
metrics. CSS restricts them to missing characters. Existing Latin outlines stay
in original game fonts. Static bounds are evidence, not renderer acceptance.
"""
import argparse
import json
from pathlib import Path
from hashlib import sha256
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.varLib.instancer import instantiateVariableFont

def digest(p): return sha256(p.read_bytes()).hexdigest()
def bounds(font, char):
    gs = font.getGlyphSet(); pen = BoundsPen(gs)
    gs[font.getBestCmap()[ord(char)]].draw(pen)
    return pen.bounds

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game-root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists(): raise ValueError('Preserve previous font build')
    root=Path(__file__).resolve().parent.parent
    lock_path=root/'source/font-reference/inputs-8879120.json'
    lock=json.loads(lock_path.read_text())
    if __import__('fontTools').__version__ != lock['fontToolsVersion']:
        raise ValueError('Use the pinned fontTools version from requirements-fonts.txt')
    for row in lock['files']:
        path=(args.game_root if row['scope']=='game' else root)/row['path']
        if digest(path)!=row['sha256']:raise ValueError('Pinned font/license input changed: '+row['path'])
    donor=args.game_root/'fonts/NotoSans_Regular.ttf'
    if digest(donor)!='c8cff31fcae0edc0e4ffd3628f36361dfc24d71cc5b9793e5ffad8e76e6f182b':
        raise ValueError('Pinned bundled Noto donor changed')
    license_path=root/'source/font-reference/OFL.txt'
    if not license_path.is_file(): raise ValueError('Full OFL license required')
    targets=[];author_inputs={}
    for path in sorted((root/'translation/ru/batches').glob('*.json')):
        author_inputs[str(path.relative_to(root))]=digest(path)
        for entry in json.loads(path.read_text())['entries']:
            targets.append(entry.get('encodedPayload',{}).get('decodedTarget',entry['target']))
    required=set(ord(c) for c in ''.join(targets) if c.isprintable())
    keyboard=json.loads((root/'runtime/ru-name-input-layout.json').read_text())
    input_characters=''.join(keyboard['default']+keyboard['shift']+keyboard['nativeDisplayGlyphs'])
    required.update(ord(c) for c in input_characters if c.isprintable())
    required.update(range(0x410,0x450));required.update([0x401,0x451])
    args.output.mkdir(parents=True)
    reports=[];css=[]
    variants=[('GameFont','OMORI_GAME2.ttf','OMORI RU Primary'),
              ('OMORI_GAME','OMORI_GAME.ttf','OMORI RU Secondary')]
    for family,source_name,new_name in variants:
        base=args.game_root/'fonts'/source_name; original=TTFont(base)
        font=TTFont(donor); cmap=font.getBestCmap()
        missing=required-set(original.getBestCmap())
        unsupported=missing-set(cmap)
        bundled=args.game_root/'fonts/mplus-1m-regular.ttf'
        external=TTFont(bundled);external_cmap=external.getBestCmap();external_gs=external.getGlyphSet()
        external_checks=[]
        symbols=root/'source/font-reference/Symbols2-NotoSansSymbols2-Regular.ttf'
        symbols_font=TTFont(symbols); symbols_cmap=symbols_font.getBestCmap()
        extra_codes=unsupported-set(external_cmap)
        symbol_codes=extra_codes & set(symbols_cmap)
        cjk_codes=extra_codes-symbol_codes
        for code in sorted(unsupported-extra_codes):
            pen=BoundsPen(external_gs);g=external_gs[external_cmap[code]];g.draw(pen)
            if g.width<=0 or pen.bounds is None:raise ValueError('Empty bundled glyph: '+hex(code))
            external_checks.append({'codepoint':hex(code),'bounds':pen.bounds,'advance':g.width})
        missing-=unsupported
        # Measured primary cap height / donor cap height; scale advances and
        # bearings together. Do not stretch glyphs independently in x and y.
        ratio=bounds(original,'A')[3]/bounds(font,'A')[3]
        donor_gs=font.getGlyphSet();top=bottom=0
        for code in missing:
            p=BoundsPen(donor_gs);donor_gs[cmap[code]].draw(p)
            if p.bounds:top=max(top,p.bounds[3]);bottom=min(bottom,p.bounds[1])
        if top:ratio=min(ratio,original['hhea'].ascent/top)
        if bottom:ratio=min(ratio,original['hhea'].descent/bottom)
        opt=subset.Options();opt.recalc_timestamp=False
        sub=subset.Subsetter(options=opt);sub.populate(unicodes=missing|{32});sub.subset(font)
        gs=font.getGlyphSet(); converted={}
        for name in font.getGlyphOrder():
            recording=DecomposingRecordingPen(gs);gs[name].draw(recording)
            pen=TTGlyphPen(None);recording.replay(TransformPen(pen,(ratio,0,0,ratio,0,0)))
            converted[name]=pen.glyph()
        for name,glyph in converted.items():font['glyf'][name]=glyph
        for name,(advance,bearing) in list(font['hmtx'].metrics.items()):
            font['hmtx'].metrics[name]=(round(advance*ratio),round(bearing*ratio))
        font['head'].unitsPerEm=original['head'].unitsPerEm
        font['head'].created=font['head'].modified=3406620153
        for key in ['ascent','descent','lineGap']:setattr(font['hhea'],key,getattr(original['hhea'],key))
        for key in ['sTypoAscender','sTypoDescender','sTypoLineGap','usWinAscent','usWinDescent']:
            setattr(font['OS/2'],key,getattr(original['OS/2'],key))
        font['OS/2'].sxHeight=round(536*ratio);font['OS/2'].sCapHeight=round(714*ratio)
        font['OS/2'].fsType=0
        for nid,value in [(1,new_name),(2,'Regular'),(3,new_name+' 2026-10-14'),(4,new_name),
                          (6,new_name.replace(' ','')),(16,new_name),(17,'Regular')]:
            font['name'].removeNames(nameID=nid)
            font['name'].setName(value,nid,3,1,0x409);font['name'].setName(value,nid,1,0,0)
        font.recalcTimestamp=False
        output=args.output/(new_name.replace(' ','-')+'.ttf');font.save(output)
        reopened=TTFont(output); actual=reopened.getBestCmap();glyphs=reopened.getGlyphSet()
        glyph_checks=[]
        for code in sorted(missing):
            if code not in actual:raise ValueError('Readback cmap missing')
            pen=BoundsPen(glyphs);g=glyphs[actual[code]];g.draw(pen)
            if g.width<=0 or (pen.bounds is None and not chr(code).isspace()):
                raise ValueError('Empty/zero-advance visible fallback glyph: '+hex(code))
            glyph_checks.append({'codepoint':hex(code),'bounds':pen.bounds,'advance':g.width})
        filename=output.name;ranges=','.join('U+%X'%c for c in sorted(missing))
        css.append('@font-face {font-family: '+family+'; src: url("'+filename+'"); unicode-range: '+ranges+';}')
        if family=='GameFont':css.append(css[-1].replace('font-family: GameFont;','font-family: OMORI_GAME2;'))
        if unsupported-extra_codes:
            external_range=','.join('U+%X'%c for c in sorted(unsupported-extra_codes))
            css.append('@font-face {font-family: '+family+'; src: url("mplus-1m-regular.ttf"); unicode-range: '+external_range+';}')
            if family=='GameFont':css.append(css[-1].replace('font-family: GameFont;','font-family: OMORI_GAME2;'))
        if cjk_codes:
            cjk_source=root/'source/font-reference/CJK-NotoSansSC[wght].ttf'
            cjk=instantiateVariableFont(TTFont(cjk_source),{'wght':400},inplace=True)
            if cjk_codes-set(cjk.getBestCmap()):raise ValueError('Missing official Chinese glyph')
            cjk_opt=subset.Options();cjk_opt.recalc_timestamp=False
            cjk_sub=subset.Subsetter(options=cjk_opt);cjk_sub.populate(unicodes=cjk_codes);cjk_sub.subset(cjk)
            cjk_name='OMORI RU Chinese Fallback'
            for nid,value in [(1,cjk_name),(3,cjk_name+' 2026-10-14'),(4,cjk_name),(6,'OmoriRuChineseFallback'),(16,cjk_name)]:
                cjk['name'].removeNames(nameID=nid);cjk['name'].setName(value,nid,3,1,0x409)
            cjk['head'].created=cjk['head'].modified=3406620153
            cjk.recalcTimestamp=False
            target=args.output/'OMORI-RU-Chinese-Fallback.ttf';cjk.save(target)
            (args.output/'CJK-OFL.txt').write_bytes((root/'source/font-reference/CJK-OFL.txt').read_bytes())
            checked=TTFont(target);gs_cjk=checked.getGlyphSet();cmap_cjk=checked.getBestCmap()
            for code in cjk_codes:
                pen=BoundsPen(gs_cjk);gs_cjk[cmap_cjk[code]].draw(pen)
                if pen.bounds is None or gs_cjk[cmap_cjk[code]].width<=0:raise ValueError('Chinese outline readback failed')
            css.append('@font-face {font-family: '+family+'; src: url("'+target.name+'"); unicode-range: '+','.join('U+%X'%c for c in sorted(cjk_codes))+';}')
            if family=='GameFont':css.append(css[-1].replace('font-family: GameFont;','font-family: OMORI_GAME2;'))
        if symbol_codes:
            for code in symbol_codes:
                if code not in symbols_cmap:raise ValueError('Missing official symbols coverage')
                pen=BoundsPen(symbols_font.getGlyphSet());symbols_font.getGlyphSet()[symbols_cmap[code]].draw(pen)
                if pen.bounds is None:raise ValueError('Empty symbol outline')
            # Unmodified OFL donor; the face is restricted to missing symbols.
            target=args.output/'NotoSansSymbols2-Regular.ttf';target.write_bytes(symbols.read_bytes())
            (args.output/'Symbols2-OFL.txt').write_bytes((root/'source/font-reference/Symbols2-OFL.txt').read_bytes())
            css.append('@font-face {font-family: '+family+'; src: url("'+target.name+'"); unicode-range: '+','.join('U+%X'%c for c in sorted(symbol_codes))+';}')
            if family=='GameFont':css.append(css[-1].replace('font-family: GameFont;','font-family: OMORI_GAME2;'))
        reports.append({'family':family,'original':source_name,'originalSha256':digest(base),
            'donorSha256':digest(donor),'file':filename,'sha256':digest(output),'scale':ratio,
            'requiredFallbackGlyphs':len(missing),'glyphChecks':glyph_checks,
            'upem':reopened['head'].unitsPerEm,'ascent':reopened['hhea'].ascent,
            'descent':reopened['hhea'].descent,'lineGap':reopened['hhea'].lineGap,
            'spaceAdvance':reopened['hmtx'].metrics[actual[32]][0]})
        reports[-1]['bundledExternal']={'file':bundled.name,'sha256':digest(bundled),
            'redistributed':False,'glyphChecks':external_checks}
        reports[-1]['symbols']={'file':'NotoSansSymbols2-Regular.ttf','sha256':digest(symbols),'codepoints':sorted(symbol_codes)}
        reports[-1]['chinese']={'file':'OMORI-RU-Chinese-Fallback.ttf','sourceSha256':digest(root/'source/font-reference/CJK-NotoSansSC[wght].ttf'),
            'codepoints':sorted(cjk_codes),'sha256':digest(args.output/'OMORI-RU-Chinese-Fallback.ttf') if cjk_codes else None,
            'runtimeMetrics':'pending actual mixed-script rendering'}
    (args.output/'ru-fallback.css').write_text('\n'.join(css)+'\n')
    (args.output/'OFL.txt').write_text('Copyright 2015 Google Inc. All Rights Reserved.\n'+license_path.read_text())
    receipt={'status':'passed-static','requiredPrintableCodepoints':len(required),'fonts':reports,
        'requiredCodepoints':sorted(required),
        'requiredCodepointsSha256':sha256(json.dumps(sorted(required),separators=(',',':')).encode()).hexdigest(),
        'authorDependencies':author_inputs,'nameInputLayoutSha256':digest(root/'runtime/ru-name-input-layout.json'),
        'inputLockSha256':digest(lock_path),'requirementsSha256':digest(root/'requirements-fonts.txt'),
        'recipeSha256':digest(Path(__file__)),'fontToolsVersion':__import__('fontTools').__version__,
        'licenseSha256':digest(args.output/'OFL.txt'),
        'outlines':'All required missing visible glyphs have outlines and positive advances after readback.',
        'originalLatin':'CSS unicode-range excludes every original mapped character.',
        'runtime':'not-run','visualReadability':'not-run','texturePipeline':'excluded'}
    (args.output/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print({'status':receipt['status'],'faces':len(reports),'required':len(required)})

if __name__=='__main__': main()
