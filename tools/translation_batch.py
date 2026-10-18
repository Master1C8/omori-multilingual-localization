#!/usr/bin/env python3
"""Validate directly authored RU batches and rebuild localized scalar resources.

The tool never generates translations. Target wording must be authored by the
assigned model in batch JSON. Unsupported adapters fail rather than falling back
to global replacement or overwriting original technical source.
"""
import argparse
from collections import defaultdict
import copy
import gzip
import json
from pathlib import Path
import yaml
from source_prepare import save_json, sha, strict_json
from source_text_syntax import compare_text_controls, quick_macro_names
from text_resource_adapter import splice, exact_span_edit
from verify_source_inventory import parse, compare_protected
from encoded_dialogue import load_registry, validate_entry
from display_mapping import mapping_row, validate_mapping_document
from database_modifiers import validate_description_modifiers
from script_resource_adapter import build_resources as build_script_resources
from authoring_omissions import validate_target_presence, validate_source_disposition


def at(value, path):
    for key in path:
        value = value[key]
    return value


def replace(value, path, text):
    owner = at(value, path[:-1])
    owner[path[-1]] = text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve previous built batch')
    root = Path(__file__).resolve().parent.parent
    corpus_manifest = strict_json((args.corpus / 'manifest.json').read_bytes())
    if corpus_manifest['sourceGate'] != 'accepted-text-inventory' or corpus_manifest['status'] != 'passed':
        raise ValueError('Text corpus is not accepted')
    for name, digest in corpus_manifest['fileHashes'].items():
        if sha((args.corpus / name).read_bytes()) != digest:
            raise ValueError('Accepted corpus artifact changed: ' + name)
    batch = strict_json(args.batch.read_bytes())
    if batch['siteLocale'] != 'ru' or batch['sourceLocale'] != 'en':
        raise ValueError('Batch locale mismatch')
    if batch['corpusManifestRawSha256'] != sha((args.corpus / 'manifest.json').read_bytes()):
        raise ValueError('Batch belongs to another corpus')
    if batch['glossaryRuRawSha256'] != sha((root / 'glossary/ru/approved.json').read_bytes()):
        raise ValueError('Accepted glossary changed')
    units = {u['id']:u for u in strict_json((args.corpus / 'units.json').read_bytes())}
    registry = load_registry(root, units)
    target_label = strict_json((root / 'glossary/ru/approved.json').read_bytes())['roboheart']['term']
    entries = batch['entries']
    if len({e['id'] for e in entries}) != len(entries):
        raise ValueError('Duplicate authored occurrence')
    macros = quick_macro_names(strict_json((root / 'source/parameter-roles-8879120-01/parameters.json').read_bytes()))
    grouped = defaultdict(list)
    for entry in entries:
        if entry['id'] not in units:
            raise ValueError('Unknown occurrence ID: ' + entry['id'])
        unit = units[entry['id']]
        if entry['source'] != unit['source']:
            raise ValueError('Authored source changed: ' + entry['id'])
        validate_target_presence(unit, entry)
        validate_source_disposition(unit, entry)
        validate_entry(unit, entry, macros, registry, target_label)
        validate_description_modifiers(unit, entry['target'])
        if unit['role'] not in {'visible', 'visible-display-mapping'}:
            raise ValueError('Batch has no accepted adapter for: ' + entry['id'])
        if unit['role'] == 'visible-display-mapping':
            mapping_row(unit, entry['target'])
        grouped[unit['asset']].append((unit,entry))
    base = root / 'source/inventory-8879120-01'
    reports = {r['asset']:r for r in strict_json((base / 'structured-assets.json').read_bytes())}
    built, mapped = [], []
    args.output.mkdir(parents=True)
    script_pairs = [(units[e['id']], e) for e in entries
                    if 'spanUtf16' in units[e['id']] or units[e['id']]['asset'] == 'js/plugins.js']
    if script_pairs:
        built.extend(build_script_resources(root, args.output, script_pairs, macros))
        mapped.extend((u, e) for u, e in script_pairs if u['role'] == 'visible-display-mapping')
    for asset, edits in grouped.items():
        if 'spanUtf16' in edits[0][0] or asset == 'js/plugins.js':
            continue
        report = reports[asset]
        original = parse(asset, gzip.decompress((base / report['snapshot']).read_bytes()))
        result = copy.deepcopy(original)
        holes, mixed = {}, defaultdict(list)
        for unit, entry in edits:
            path = tuple(unit['path'])
            if unit['role'] == 'visible-display-mapping':
                if at(original, path) != unit['source']:
                    raise ValueError('Original display identity changed')
                mapped.append((unit, entry))
                continue
            if 'span' in unit or 'spanCodepoints' in unit:
                if ('parentValueSha256' in unit
                        and sha(at(original, path).encode()) != unit['parentValueSha256']):
                    raise ValueError('Pinned original mixed field changed')
                mixed[path].append(exact_span_edit(unit, entry['target'], macros))
            else:
                if at(original,path) != unit['source']:
                    raise ValueError('Original scalar value changed')
                replace(result,path,entry['target'])
            holes[path] = unit['id']
        for path, parts in mixed.items():
            replace(result,path,splice(at(original,path),parts))
        compare_protected(original,result,holes)
        if Path(asset).suffix in {'.KEL','.AUBREY'}:
            serialized = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
            extension = '.json'
        else:
            serialized = yaml.safe_dump(result,allow_unicode=True,sort_keys=False,width=100000)
            extension = '.yaml'
        output_path = args.output / 'resources' / (asset + extension)
        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(serialized)
        reinserted = parse(asset,output_path.read_bytes())
        compare_protected(result,reinserted,{})
        compare_protected(original,reinserted,holes)
        for unit,entry in edits:
            if unit['role'] == 'visible-display-mapping':
                if at(reinserted, unit['path']) != unit['source']:
                    raise ValueError('Delivered logical identity changed')
                continue
            if not ('span' in unit or 'spanCodepoints' in unit) and at(reinserted,unit['path']) != entry['target']:
                raise ValueError('Actual built target differs from authored data')
            if entry.get('encodedPayload'):
                validate_entry(unit, dict(entry, target=at(reinserted,unit['path'])), macros, registry, target_label)
        built.append({'originalAsset':asset,'output':str(output_path.relative_to(args.output)),
                      'rawSha256':sha(output_path.read_bytes()),'units':len(edits),
                      'originalParsedSha256':report['parsedSha256']})
    mapping_receipt = None
    if mapped:
        mapping_path = args.output / 'display-mappings.json'
        save_json(mapping_path, {'schemaVersion': 1, 'siteLocale': 'ru', 'steamBuild': '8879120',
                  'corpusManifestRawSha256': batch['corpusManifestRawSha256'],
                  'entries': [mapping_row(unit, entry['target']) for unit, entry in mapped]})
        validate_mapping_document(strict_json(mapping_path.read_bytes()), mapped, batch['corpusManifestRawSha256'])
        mapping_receipt = {'output': 'display-mappings.json', 'rawSha256': sha(mapping_path.read_bytes()),
                           'units': len(mapped), 'integration': 'pending-display-consumer-bindings'}
    receipt = {'schemaVersion':1,'status':'passed','batchId':batch['batchId'],
               'authoredUnits':len(entries),'resources':built,'siteLocale':'ru',
               'batchRawSha256':sha(args.batch.read_bytes()),
               'corpusManifestRawSha256':batch['corpusManifestRawSha256'],
               'glossaryRuRawSha256':batch['glossaryRuRawSha256'],
               'recipeRawSha256':sha(Path(__file__).read_bytes()),
               'recipeDependencyHashes':{name:sha((root / 'tools' / name).read_bytes()) for name in
                   ['encoded_dialogue.py','source_text_syntax.py','unit_text_controls.py','authoring_omissions.py','text_resource_adapter.py','display_mapping.py','database_modifiers.py','script_resource_adapter.py','source_literal_values.cjs']},
               'displayMappings': mapping_receipt,
               'encodedPayloadChecks':[
                   {'id':e['id'],'codec':e['encodedPayload']['codec'],
                    'decodedTargetRawSha256':sha(e['encodedPayload']['decodedTarget'].encode('utf-8')),
                    'lineBreakCount':e['encodedPayload']['lineBreakCount']}
                   for e in entries if e.get('encodedPayload')],
               'tests':['Exact original stable IDs and source values','Native controls/placeholders/number equality',
                        'All other original typed values/keys/branches equal','Actual serialized resource reparsed with full target-value equality'],
               'runtime':'not-run','semanticAudit':'pending-full-corpus','independentReview':'pending',
               'placeholderFormsPendingDisplayBinding':[
                   {'id':e['id'],'forms':e['placeholderForms']} for e in entries if e.get('placeholderForms')],
               'limits':['This validates plaintext localized resources and source-bound display-label sidecars, not loader packaging or in-game rendering.',
                         'Sidecar labels preserve logical values; actual display-consumer integration remains a separate required gate.',
                         'Translation wording is directly authored; this builder performs no translation.']}
    save_json(args.output / 'receipt.json',receipt)
    print({'status':'passed','batchId':batch['batchId'],'units':len(entries),'resources':len(built)})


if __name__ == '__main__':
    main()
