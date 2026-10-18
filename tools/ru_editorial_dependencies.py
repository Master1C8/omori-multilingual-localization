#!/usr/bin/env python3
"""Bind recorded manual editorial decisions to exact current author revisions.

This records completed human/model reading; it does not infer or certify meaning.
Unchanged dependencies reuse the complete paired-read snapshot. Every changed
pair and all 47 affected battle statements were explicitly reread by the author.
"""
import argparse
import json
from pathlib import Path
from source_prepare import strict_json, sha, save_json

SOURCE_CLOSURE = ('least i could do','nervous wreck','back in full force',
    'sticky situations','become a lucius','be a lucius','arcade piece',
    'dino pasta','dino melon soda','dino jam','slimy key','matchbox',
    'red glasses lady','memory lane',"mom's room",'tomato girl','tomatogirl',
    'ears pop','ears are popping','too ambitious','real challenge',
    'if i do say so myself','came back to this photo','made friends')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('audit',type=Path)
    ap.add_argument('--corrections',type=Path,required=True)
    ap.add_argument('--application',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parent.parent
    if args.output.exists():raise ValueError('Preserve prior editorial evidence')
    manifest=strict_json((args.audit/'manifest.json').read_bytes())
    raw=(args.audit/'rows.jsonl').read_bytes()
    if sha(raw)!=manifest['rowsSha256']:raise ValueError('Immutable full read changed')
    rows=[strict_json(x) for x in raw.decode().splitlines()];byid={r['id']:r for r in rows}
    progress=strict_json((args.audit/'read-progress.json').read_bytes())
    covered=set()
    for a,b in progress['readRanges']:
        if not 0<=a<=b<=len(rows):raise ValueError('Invalid credited read range')
        covered.update(range(a,b))
    if progress['nextOffset']!=len(rows) or covered!=set(range(len(rows))):
        raise ValueError('Actual complete paired reading required')
    corrections=strict_json(args.corrections.read_bytes())
    application=strict_json(args.application.read_bytes())
    if application.get('status')!='passed; all selected canonical batches and new resources verified':
        raise ValueError('Canonical application incomplete')
    current={};dependencies={}
    for path in sorted((root/'translation/ru/batches').glob('*.json')):
        dependencies[str(path.relative_to(root))]=sha(path.read_bytes())
        for e in strict_json(path.read_bytes())['entries']:
            if e['id'] in current:raise ValueError('Duplicate current source ID')
            current[e['id']]=e
    if current.keys()!=byid.keys():raise ValueError('Current full coverage changed')
    changed={e['id']:e for e in corrections['changes']}
    for id,old in byid.items():
        actual=current[id]
        target=actual.get('encodedPayload',{}).get('decodedTarget',actual['target'])
        expected=changed[id]['target'] if id in changed else old['target']
        if target!=expected:raise ValueError('Unexpected author change: '+id)
    closure=set(changed)
    pizza_ids={'languages/en/XX_BLUE.HERO#["Yin_Pizza_Delivery","theNo",'+str(i)+']' for i in [0,1]}
    closure.update(pizza_ids)
    for id in pizza_ids:
        if current[id].get('sourceRoleDisposition',{}).get('role')!='preserve-exactly':
            raise ValueError('Exact pizza normalization operands require retention metadata')
    for f in progress['findings']:
        closure.add(f['id']);closure.update(f.get('contextIds',[]))
    for r in rows:
        if any(term in r['source'].lower() for term in SOURCE_CLOSURE):closure.add(r['id'])
    if not closure<=byid.keys():raise ValueError('Unknown editorial dependency')
    decisions=[]
    for i,f in enumerate(progress['findings']):
        outcome='corrected with source-bound dependency closure'
        note=f['reason']
        if i==0:
            outcome='resolved in prepared shared display adapter; final compiled verification required'
            note+=' Exact catalog/actor genitive view preserves the original catalog and native actor name.'
        elif i==51:
            outcome='retain intentional Latin password spellings'
            note+=' Map236 event6 page5 uses AddChoice with fixed oops/Label2 branch labels, including BOMB/BOMO/MOMB/BOOM letter distractors. Retain the same Latin password alphabet and the correct BOOM literal; image clue review is excluded and not claimed.'
        elif i==52:
            outcome='no change; accepted glossary explicitly establishes male gender'
        elif i==58:
            outcome='no change; native Troop432 Robo Heart and accepted ROBOHEART female identity'
        elif i==13:
            note+=' Map374 event5 provides no explicit disambiguating object. The neutral search wording preserves the request without inventing a pronoun referent.'
        elif i==14:
            note+=' No exact use was found in saved native structured event calls. The prototype remains translated with a passage restriction, removing the unsupported queue interpretation.'
        elif i==39:
            note+=' Native BunLady3D events and approved mother identity checked; neutral у тебя появились друзья works for either addressee.'
        elif i==48:
            note+=' Map123 event35 selects a party member, then completes and throws the bottle. Дополнил preserves completion without asserting an input UI or particular writing action.'
        elif i==59:
            note+=' Troops425/602 explicitly bind the lines to Hero smile/charm skills; heroine Sweetheart appropriates the named smile.'
        elif i==63:
            note+=' Skills83/692/702 all have self scope11 and explicit emotion state effects; Russian labels preserve this self-directed activation, not anger at oneself.'
        decisions.append({'finding':i+1,'id':f['id'],'outcome':outcome,'evidence':note})
    result={'schemaVersion':1,'status':'complete coordinator semantic self-audit; independent diff review pending',
        'fullPairedRead':len(rows),'correctedOccurrences':len(changed),'correctedBatches':len(application['batches']),
        'retainedTechnicalUnits':sum(bool(e.get('sourceRoleDisposition')) for e in current.values()),
        'additionalSourceRoleMetadata':{'catalogScalars':2,'wordingChanged':False,'evidence':'source/ru-pizza-source-role-delta-2026-10-14-01.json'},
        'reviewDecisions':decisions,'dependencyIds':sorted(closure),
        'dependencyChecks':{id:{'sourceSha256':sha(byid[id]['source'].encode()),
            'targetSha256':sha(current[id].get('encodedPayload',{}).get('decodedTarget',current[id]['target']).encode()),
            'disposition':'changed pair reread' if id in changed else 'unchanged complete paired-read result reused'} for id in sorted(closure)},
        'authorDependencies':dependencies,'sourceClosureQueries':list(SOURCE_CLOSURE),
        'inputDependencies':{str(p.relative_to(root)):sha(p.read_bytes()) for p in [args.audit/'manifest.json',
            args.audit/'read-progress.json',args.corrections,args.application,args.audit/'changed-battle-assemblies.json',
            args.audit/'context-evidence.json',root/'glossary/compact-public/v2/working-ru.json',
            root/'tools/ru_editorial_dependencies.py',root/'tools/source_text_syntax.py']},
        'changedBattleAssemblies':47,'independentDiffReview':'pending; no separately authorized reviewer',
        'runtime':'not-run','visual':'not-run','installation':'not-run','images':'excluded',
        'limits':['Manual paired read and correction review were performed by the same assigned model, not an independent reviewer.',
                  'These source and target pins do not establish loader boot, rendered wrapping or installed-game behavior.']}
    save_json(args.output,result)
    print({k:result[k] for k in ['status','fullPairedRead','correctedOccurrences','correctedBatches']},'dependencies',len(closure))


if __name__=='__main__':main()
