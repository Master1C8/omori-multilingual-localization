#!/usr/bin/env python3
"""Bind model-authored target JSON to accepted source IDs. No wording generation."""
import argparse
from pathlib import Path
from source_prepare import strict_json, save_json, sha
from encoded_dialogue import load_registry, authored_encoding
from authoring_keys import target_key
from authoring_omissions import validate_target_presence, validate_source_disposition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft', type=Path)
    parser.add_argument('--corpus', type=Path, default=Path('source/text-corpus-8879120-02'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    draft = strict_json(args.draft.read_bytes())
    if draft.get('immediateEditByAssignedModel') is not True:
        raise ValueError('Author must finish the immediate complete source/target edit')
    manifest_path = args.corpus / 'manifest.json'
    manifest = strict_json(manifest_path.read_bytes())
    if manifest['status'] != 'passed' or manifest['sourceGate'] != 'accepted-text-inventory':
        raise ValueError('Corpus is not accepted')
    units = strict_json((args.corpus / 'units.json').read_bytes())
    selected = [u for u in units if u['asset'] == draft['asset']]
    registry = load_registry(root, {u['id']:u for u in units})
    target_label = strict_json((root / 'glossary/ru/approved.json').read_bytes())['roboheart']['term']
    targets = dict(draft['targets'])
    if not set(draft.get('omissionReasons', {})) <= set(targets):
        raise ValueError('Unknown authored omission key')
    if not set(draft.get('preservedTechnicalReasons', {})) <= set(targets):
        raise ValueError('Unknown authored technical source key')
    if not set(draft.get('preservedTechnicalConsumerHashes', {})) <= set(draft.get('preservedTechnicalReasons', {})):
        raise ValueError('Technical consumer hash without an explicit technical disposition')
    encoded_keys = set(draft.get('encodedTargets', []))
    if not encoded_keys <= set(targets):
        raise ValueError('Unknown encoded author target key')
    entries = []
    for unit in selected:
        key = target_key(unit, draft.get('targetKeyMode', 'catalog-text'))
        if key not in targets:
            raise ValueError('Authored catalog is incomplete: ' + key)
        target = targets.pop(key)
        entry = {'id':unit['id'],'source':unit['source'],'target':target,'state':'authored-edited'}
        if key in draft.get('omissionReasons', {}):
            entry['syntacticOmission'] = {'kind':'grammatical-fragment',
                'reason':draft['omissionReasons'][key], 'sourceValueSha256':sha(unit['source'].encode())}
        validate_target_presence(unit, entry)
        if key in draft.get('preservedTechnicalReasons', {}):
            entry['sourceRoleDisposition'] = {'role':'preserve-exactly',
                'reason':draft['preservedTechnicalReasons'][key], 'sourceValueSha256':sha(unit['source'].encode())}
            if key in draft.get('preservedTechnicalConsumerHashes', {}):
                entry['sourceRoleDisposition']['consumerSourceSha256']=draft['preservedTechnicalConsumerHashes'][key]
        validate_source_disposition(unit, entry)
        if key in encoded_keys:
            entry['target'], entry['encodedPayload'] = authored_encoding(unit, target, target_label, registry)
        elif unit['id'] in registry:
            raise ValueError('Encoded target must be directly authored in decoded form')
        if key in draft.get('placeholderForms', {}):
            entry['placeholderForms'] = draft['placeholderForms'][key]
        entries.append(entry)
    if targets or not entries:
        raise ValueError('Extra target keys or empty catalog')
    out = root / 'translation/ru/batches' / (draft['batchId'] + '.json')
    if out.exists():
        raise ValueError('Do not silently overwrite canonical authored data')
    glossary = root / 'glossary/ru/approved.json'
    if sha(glossary.read_bytes()) != '100e203e9ce6282bc2023e13f8b239dbcacdb552da24a05324d7789e952c8d15':
        raise ValueError('Accepted glossary changed')
    save_json(out, {'schemaVersion':1,'batchId':draft['batchId'],'sourceLocale':'en','siteLocale':'ru',
        'steamBuild':'8879120','corpusManifestRawSha256':sha(manifest_path.read_bytes()),
        'glossarySourceRawSha256':'11d48e714e6ba1652ca76ed45c4d7622e22312547410bc694c1f46181a18773b',
        'glossaryRuRawSha256':sha(glossary.read_bytes()),
        'author':'assigned Codex model; direct English-to-Russian authoring; no translation service or other model',
        'scope':draft['scope'],'contextNotes':draft['contextNotes'],
        'authoringDraft':str(args.draft.resolve().relative_to(root)), 'authoringDraftRawSha256':sha(args.draft.read_bytes()),
        'immediateEdit':{'status':'complete','readIds':[e['id'] for e in entries],
            'checks':draft.get('editChecks',['Complete English/target catalog read','Voice/knowledge timing and approved terms','Native controls and mechanics']),
            'independent':False},'semanticAudit':'pending-full-corpus','entries':entries})
    print({'batchId':draft['batchId'],'authoredEditedOccurrences':len(entries),'output':str(out.relative_to(root))})


if __name__ == '__main__':
    main()
