#!/usr/bin/env python3
"""Reuse exact verified font bytes only when all glyph/recipe inputs still match."""
import argparse
import json
import shutil
from pathlib import Path
from source_prepare import sha, strict_json, save_json


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--from-build',type=Path,required=True)
    ap.add_argument('--reproducibility',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parent.parent
    if args.output.exists():raise ValueError('Preserve previous font checkpoint')
    prior=args.from_build/'receipt.json';receipt=strict_json(prior.read_bytes())
    evidence=strict_json(args.reproducibility.read_bytes())
    if evidence['currentReceiptSha256']!=sha(prior.read_bytes()):raise ValueError('Prior font checkpoint mismatch')
    for path,digest in [('tools/build_ru_fonts.py',receipt['recipeSha256']),
                        ('source/font-reference/inputs-8879120.json',receipt['inputLockSha256']),
                        ('runtime/ru-name-input-layout.json',receipt['nameInputLayoutSha256']),
                        ('requirements-fonts.txt',receipt['requirementsSha256'])]:
        if sha((root/path).read_bytes())!=digest:raise ValueError('Font prerequisite changed')
    game=Path(strict_json((root/'source/inventory-8879120-01/manifest.json').read_bytes())['gameRoot'])
    lock=strict_json((root/'source/font-reference/inputs-8879120.json').read_bytes())
    for row in lock['files']:
        path=(game if row['scope']=='game' else root)/row['path']
        if sha(path.read_bytes())!=row['sha256']:raise ValueError('Actual pinned font/license input changed')
    targets=[];authors={}
    for path in sorted((root/'translation/ru/batches').glob('*.json')):
        authors[str(path.relative_to(root))]=sha(path.read_bytes())
        targets.extend(e.get('encodedPayload',{}).get('decodedTarget',e['target']) for e in strict_json(path.read_bytes())['entries'])
    keyboard=strict_json((root/'runtime/ru-name-input-layout.json').read_bytes())
    required={ord(c) for c in ''.join(targets+keyboard['default']+keyboard['shift']+keyboard['nativeDisplayGlyphs']) if c.isprintable()}
    required.update(range(0x410,0x450));required.update([0x401,0x451])
    if sorted(required)!=receipt['requiredCodepoints']:raise ValueError('Required glyph set changed; rebuild fonts')
    expected={e['path']:e['sha256'] for e in evidence['files']}
    if set(expected)!={p.name for p in args.from_build.iterdir() if p.name!='receipt.json'}:
        raise ValueError('Unexpected prior font files')
    for path,digest in expected.items():
        if sha((args.from_build/path).read_bytes())!=digest:raise ValueError('Verified font bytes changed')
    args.output.mkdir(parents=True)
    for path in expected:shutil.copyfile(args.from_build/path,args.output/path)
    receipt['authorDependencies']=authors
    receipt['reusedFrom']={'receipt':str(prior),'sha256':sha(prior.read_bytes()),
        'boundary':'Exact required codepoint set, font-generation recipe, keyboard, input lock and all verified output bytes unchanged. Current author revisions are rebound only after those checks; existing glyph readback and byte reproducibility are reused.'}
    receipt['reuseRecipeSha256']=sha(Path(__file__).read_bytes())
    save_json(args.output/'receipt.json',receipt)
    print('Reused',len(expected),'exact font/CSS/license files;',len(required),'required codepoints; final author hashes bound')


if __name__=='__main__':main()
