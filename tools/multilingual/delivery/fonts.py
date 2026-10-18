"""Select retained local font bytes and scoped fallback ranges; no rendering claim."""
from pathlib import Path
import sys
try:
    from fontTools.ttLib import TTFont
except ModuleNotFoundError:
    # Reuse the project's existing pinned pure-Python fontTools environment.
    font_site=Path('/Users/antonkrutov/Desktop/omori full translation mod/.venv-fonts/lib/python3.9/site-packages')
    sys.path.append(str(font_site))
    from fontTools.ttLib import TTFont
import fontTools
if fontTools.__version__ != '4.60.2':
    raise ValueError('Use the retained fontTools 4.60.2 environment')
from source_prepare import strict_json, sha

GAME = Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
SCRIPT_FONTS = Path(__file__).with_name('script-fonts.json')


def script_font_dependencies(root):
    """Pin supplemental font/license inputs without changing earlier font manifests."""
    result = {}
    for row in strict_json(SCRIPT_FONTS.read_bytes())['fonts']:
        for ref in (row['font'], row['license'], row['provenance'], *row.get('additionalInputs',[])):
            path = root / ref['path']
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Unsafe supplemental font input')
            if sha(path.read_bytes()) != ref['sha256']:
                raise ValueError('Supplemental font identity changed: ' + ref['path'])
            result[ref['path']] = ref['sha256']
    return result


def prepare(ctx, pairs, config):
    manifest=strict_json((ctx.root/'source/font-reference/inputs-8879120.json').read_bytes())
    sources={row['path']:row for row in manifest['files']}
    used=set(''.join(e['target'] + e.get('encodedPayload',{}).get('decodedTarget','') for u,e in pairs)) | set(config['keyboardExtra'])
    used |= set(config.get('renderingCharacters',''))
    used={ord(c) for c in used if not c.isspace() or c==' '}
    from font_metrics import normalized_face
    roles={};bases={}
    for family in config['fontRoles']:
        name='fonts/OMORI_GAME.ttf' if family=='OMORI_GAME' else 'fonts/OMORI_GAME2.ttf'
        p=GAME/name
        if sha(p.read_bytes())!=sources[name]['sha256']:raise ValueError('Original font identity changed: '+name)
        f=TTFont(p);cmap=f.getBestCmap();space=cmap.get(32)
        if not space or f['hmtx'][space][0]<=0:raise ValueError('Native font lacks a positive space advance')
        bases[family]=f;roles[family]=used-set(cmap)
    candidates=[('fonts/NotoSans_Regular.ttf',GAME/'fonts/NotoSans_Regular.ttf','fonts/Locale-Latin.ttf','source/font-reference/OFL.txt'),
                ('source/font-reference/Symbols2-NotoSansSymbols2-Regular.ttf',ctx.root/'source/font-reference/Symbols2-NotoSansSymbols2-Regular.ttf','fonts/Locale-Symbols.ttf','source/font-reference/Symbols2-OFL.txt'),
                ('source/font-reference/CJK-NotoSansSC[wght].ttf',ctx.root/'source/font-reference/CJK-NotoSansSC[wght].ttf','fonts/Locale-CJK.ttf','source/font-reference/CJK-OFL.txt')]
    script_font_dependencies(ctx.root)
    contextual={}
    for row in strict_json(SCRIPT_FONTS.read_bytes())['fonts']:
        if ctx.locale not in row['locales']:continue
        for key in ('font', 'license'):
            sources[row[key]['path']] = row[key]
        candidates.insert(1, (row['font']['path'], ctx.root/row['font']['path'], row['destination'], row['license']['path']))
        contextual[row['destination']]=set(row.get('contextCodepoints',[])) & used
    payload={};probes=[];faces=[];css=[];derived_cache={}
    for name,path,destination,license_path in candidates:
        raw=path.read_bytes()
        if sha(raw)!=sources[name]['sha256']:raise ValueError('Retained font identity changed: '+name)
        f=TTFont(path);cmap=f.getBestCmap();extra=contextual.get(destination,set())
        if not extra<=set(cmap):raise ValueError('Supplemental font lacks contextual rendering controls')
        for family in config['fontRoles']:
            base=bases[family];available=set(cmap)-set(base.getBestCmap())
            codes=(roles[family] & set(cmap)) | extra
            # Dynamic saved names may contain another supported script. Normalize
            # the bundled common fallback as well, instead of delegating Cyrillic
            # and Greek to an uncontrolled system face at unrelated metrics.
            if name=='fonts/NotoSans_Regular.ttf':
                codes |= {c for c in available if chr(c).isprintable()}
            codes=sorted(codes)
            if not codes:continue
            if any(cmap[c]=='.notdef' for c in codes):raise ValueError('Invalid fallback glyph')
            role='Secondary' if family=='OMORI_GAME' else 'Primary'
            face_path=str(Path(destination).with_name(Path(destination).stem+'-'+role+'.ttf'))
            identity='OMORI Locale '+role+' '+Path(destination).stem.replace('Locale-','')
            cache_key=(sha(raw),role,tuple(codes))
            if cache_key not in derived_cache:derived_cache[cache_key]=normalized_face(raw,base,codes,identity)
            derived,metrics=derived_cache[cache_key]
            if face_path in payload and payload[face_path]!=derived:raise ValueError('Conflicting font role output')
            payload[face_path]=derived
            if license_path:
                lic=ctx.root/license_path
                if sha(lic.read_bytes())!=sources[license_path]['sha256']:raise ValueError('Font license identity changed')
                payload[face_path+'.OFL.txt']=lic.read_bytes()
            ranges=','.join('U+%X'%c for c in codes)
            css.append('@font-face {font-family: '+family+'; src: url("'+Path(face_path).name+'"); unicode-range: '+ranges+';}')
            probes.append({'family':family,'file':Path(face_path).name,'text':''.join(chr(c) for c in codes)})
            faces.append(dict(metrics,input=str(path),inputSha256=sha(raw),sha256=sha(derived),destination=face_path,family=family,codes=codes,coverage='role-specific cmap and metric readback',rendering='not-run'))
            roles[family]-=set(codes)
        f.close()
    for family,needed in roles.items():
        if needed:raise ValueError('Unsupported font coverage boundary for '+ctx.locale+'/'+family+': '+','.join('U+%04X'%c for c in sorted(needed)))
    for f in bases.values():f.close()
    if css:payload['fonts/locale-fallback.css']=('\n'.join(css)+'\n').encode()
    return payload,probes,{'status':'passed-role-bound-static-metrics','faces':faces,'corpusCharacters':len(used),'rendering':'not-run','loading':'not-run',
                         'limitations':['Runtime readability, script shaping and layout still require native visual evidence.','Original usable game glyphs remain unchanged; missing common glyphs and per-script faces use shared role metrics.']}
