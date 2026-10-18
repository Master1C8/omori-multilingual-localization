#!/usr/bin/env python3
"""Snapshot and page complete EN/RU pairs; never certify or generate meaning."""
import argparse
import json
from pathlib import Path
from source_prepare import save_json, strict_json, sha
from encoded_dialogue import load_registry

def prepare(root, output, package):
    if output.exists():raise ValueError('Preserve previous audit snapshot')
    corpus=root/'source/text-corpus-8879120-02';units={u['id']:u for u in strict_json((corpus/'units.json').read_bytes())}
    registry=load_registry(root,units);rows=[];dependencies={};seen=set()
    for path in sorted((root/'translation/ru/batches').glob('*.json')):
        batch=strict_json(path.read_bytes());dependencies[str(path.relative_to(root))]=sha(path.read_bytes())
        for entry in batch['entries']:
            unit=units[entry['id']]
            if entry['id'] in seen or entry['source']!=unit['source']:raise ValueError('Audit alignment mismatch')
            seen.add(entry['id'])
            row={'id':entry['id'],'batch':batch['batchId'],'asset':unit['asset'],
                'source':registry[entry['id']]['decodedEnglish'] if entry['id'] in registry else entry['source'],
                'target':entry.get('encodedPayload',{}).get('decodedTarget',entry['target']),
                'context':unit.get('context',{}),'contextNotes':batch.get('contextNotes',[]),
                'role':unit['role'],'sourceRoleDisposition':entry.get('sourceRoleDisposition'),
                'syntacticOmission':entry.get('syntacticOmission'),'encoded':entry['id'] in registry}
            rows.append(row)
    if seen!=units.keys():raise ValueError('Full semantic inventory required')
    output.mkdir(parents=True);raw=''.join(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n' for row in rows)
    (output/'rows.jsonl').write_text(raw)
    manifest={'status':'ready-for-manual-full-read','count':len(rows),'rowsSha256':sha(raw.encode()),
        'corpusManifestSha256':sha((corpus/'manifest.json').read_bytes()),'unitsSha256':sha((corpus/'units.json').read_bytes()),
        'glossaryRuSha256':sha((root/'glossary/ru/approved.json').read_bytes()),
        'glossarySourceSha256':sha((root/'glossary/en/approved.json').read_bytes()) if (root/'glossary/en/approved.json').exists() else '11d48e714e6ba1652ca76ed45c4d7622e22312547410bc694c1f46181a18773b',
        'authorDependencies':dependencies,'packageReceipt':str(package.relative_to(root)),'packageReceiptSha256':sha(package.read_bytes()),
        'reviewer':'Assigned coordinator model; self-audit, not independent','imagePlans':'excluded by owner; no text-bearing image plan in this scope',
        'fullSemanticAudit':'pending','independentDiffAudit':'pending','runtime':'not-run','visual':'not-run'}
    save_json(output/'manifest.json',manifest)
    save_json(output/'read-progress.json',{'nextOffset':0,'readRanges':[],'findings':[],'status':'in-progress','rowsSha256':manifest['rowsSha256']})
    print({'status':manifest['status'],'count':len(rows),'rowsSha256':manifest['rowsSha256']})

def page(output,offset,characters):
    manifest=strict_json((output/'manifest.json').read_bytes());raw=(output/'rows.jsonl').read_bytes()
    if sha(raw)!=manifest['rowsSha256']:raise ValueError('Immutable audit rows changed')
    rows=[strict_json(line) for line in raw.decode().splitlines()];used=0;end=offset;prior=None
    for i,row in enumerate(rows[offset:],offset):
        header=''
        identity=(row['batch'],row['asset'])
        if identity!=prior:
            header='\nBATCH '+row['batch']+' ASSET '+row['asset']+'\nCONTEXT '+json.dumps(row['contextNotes'],ensure_ascii=False)+'\n'
        suffix=row['id'][len(row['asset']):]
        text=header+str(i)+' '+suffix+'\nEN '+json.dumps(row['source'],ensure_ascii=False)+'\nRU '+json.dumps(row['target'],ensure_ascii=False)+'\n'
        context=row['context']
        if context.get('record'):text+='RECORD '+json.dumps(context['record'],ensure_ascii=False)+'\n'
        if context.get('statement'):text+='STATEMENT '+context['statement']+'\n'
        if row['sourceRoleDisposition']:text+='NATIVE '+row['sourceRoleDisposition']['reason']+'\n'
        if row['syntacticOmission']:text+='OMISSION '+row['syntacticOmission']['reason']+'\n'
        if used and used+len(text)>characters:break
        print(text,end='');used+=len(text);end=i+1;prior=identity
    print(json.dumps({'offset':offset,'nextOffset':end,'total':len(rows),'characters':used}))

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('--output',type=Path,required=True);p.add_argument('--package-receipt',type=Path,required=True)
    p=sub.add_parser('page');p.add_argument('audit',type=Path);p.add_argument('--offset',type=int,required=True);p.add_argument('--characters',type=int,default=30000)
    args=ap.parse_args();root=Path(__file__).resolve().parent.parent
    if args.action=='prepare':prepare(root,args.output,args.package_receipt.resolve())
    else:page(args.audit,args.offset,args.characters)

if __name__=='__main__':main()
