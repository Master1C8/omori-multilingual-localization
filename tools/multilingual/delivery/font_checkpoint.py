"""Reuse accepted font bytes only with identical font algorithms and inputs."""
from pathlib import Path
from source_prepare import sha,strict_json
from fonts import GAME,script_font_dependencies

ALGORITHMS=['tools/multilingual/delivery/fonts.py','tools/multilingual/delivery/font_metrics.py',
            'tools/multilingual/delivery/script-fonts.json','tools/multilingual/source_prepare.py']

def checkpoint(root,build):
    candidate=Path(build).absolute()
    for part in [candidate,*candidate.parents]:
        if part==root/'build/multilingual-delivery':break
        if part.is_symlink():raise ValueError('Font checkpoint symlink')
    build=Path(build).resolve()
    if not build.is_relative_to(root/'build/multilingual-delivery') or build.is_symlink():
        raise ValueError('Font checkpoint outside canonical native builds')
    return {'build':str(build.relative_to(root)),
            'manifestSha256':sha((build/'manifest.json').read_bytes()),
            'acceptanceSha256':sha((build/'ACCEPTANCE.json').read_bytes()),
            'baseReferenceSha256':sha((root/'source/font-reference/inputs-8879120.json').read_bytes())}

def reuse(ctx,pinned,config,receipt):
    root=ctx.root;build=(root/receipt['build']).resolve()
    if not build.is_relative_to(root/'build/multilingual-delivery'):
        raise ValueError('Font checkpoint outside canonical native builds')
    raw=(build/'manifest.json').read_bytes();accepted=(build/'ACCEPTANCE.json').read_bytes()
    if sha(raw)!=receipt['manifestSha256'] or sha(accepted)!=receipt['acceptanceSha256']:
        raise ValueError('Font checkpoint evidence changed')
    old=strict_json(raw);gate=strict_json(accepted)
    if gate['manifestSha256']!=sha(raw) or gate['status']!='passed-technical-candidate' or old['siteLocale']!=ctx.locale:
        raise ValueError('Font checkpoint is not accepted for this locale')
    if old['inputs']!=pinned:raise ValueError('Font checkpoint authored/source inputs changed')
    if old['config']!=config:raise ValueError('Font checkpoint locale configuration changed')
    for name in ALGORITHMS:
        if sha((root/name).read_bytes())!=old['recipeDependencies'][name]:
            raise ValueError('Font checkpoint algorithm changed: '+name)
    reference=root/'source/font-reference/inputs-8879120.json'
    if sha(reference.read_bytes())!=receipt['baseReferenceSha256']:raise ValueError('Font base reference changed')
    sources={r['path']:r for r in strict_json(reference.read_bytes())['files']}
    for name,row in sources.items():
        path=GAME/name if name.startswith('fonts/') else root/name
        if sha(path.read_bytes())!=row['sha256']:raise ValueError('Native font input changed: '+name)
    script_font_dependencies(root)
    evidence=old['fonts'];payload={};probes=[]
    for face in evidence['faces']:
        path=Path(face['input']).resolve()
        if not (path.is_relative_to(root/'source/font-reference') or path==GAME/'fonts/NotoSans_Regular.ttf'):
            raise ValueError('Unsafe font donor checkpoint')
        if sha(path.read_bytes())!=face['inputSha256']:raise ValueError('Font donor input changed')
        probes.append({'family':face['family'],'file':Path(face['destination']).name,'text':''.join(chr(c) for c in face['codes'])})
    for row in old['files']:
        name=row['path']
        if not name.startswith('fonts/'):continue
        if any(p in ('','.','..') for p in name.split('/')) or '\\' in name:raise ValueError('Unsafe font checkpoint path')
        path=build/'files'/name
        if path.is_symlink():raise ValueError('Font checkpoint payload symlink')
        data=path.read_bytes()
        if sha(data)!=row['sha256'] or len(data)!=row['bytes']:raise ValueError('Font checkpoint payload changed: '+name)
        payload[name]=data
    if not payload:raise ValueError('Font checkpoint has no font payload')
    if any(sha(payload[f['destination']])!=f['sha256'] for f in evidence['faces']):raise ValueError('Font face proof differs from payload')
    return payload,probes,evidence
