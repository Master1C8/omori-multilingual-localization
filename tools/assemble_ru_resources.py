#!/usr/bin/env python3
"""Merge all authored occurrences against one immutable original per resource.

Never copy per-batch whole-resource outputs over one another. No translation,
game execution, installed-game writes, or mutable-source word replacement.
"""
import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path
import yaml
from source_prepare import strict_json, save_json, sha
from script_resource_adapter import (programs, original_resource, recover_program,
    program_edit, verify_program, at, put, parse_config, parsed_literals)
from text_resource_adapter import splice, exact_span_edit
from verify_source_inventory import parse, compare_protected
from source_text_syntax import quick_macro_names
from display_mapping import mapping_row, validate_mapping_document
from encoded_dialogue import load_registry, validate_entry
from database_modifiers import validate_description_modifiers
from authoring_omissions import validate_target_presence, validate_source_disposition


def read_pairs(root):
    corpus = root / 'source/text-corpus-8879120-02'
    manifest_raw = (corpus / 'manifest.json').read_bytes()
    manifest = strict_json(manifest_raw)
    for name, digest in manifest['fileHashes'].items():
        if sha((corpus / name).read_bytes()) != digest:
            raise ValueError('Corpus changed: ' + name)
    units = {u['id']: u for u in strict_json((corpus / 'units.json').read_bytes())}
    index = strict_json((root / 'translation/ru/current-builds.json').read_bytes())
    from native_yaml_supplement import read_supplement
    recovered, recovered_dependencies = read_supplement(root)
    if index['authoredEditedOccurrences'] != len(units) + len(recovered):
        raise ValueError('Full delivered reconciliation required before assembly')
    entries, dependencies = {}, {}
    for path in sorted((root / 'translation/ru/batches').glob('*.json')):
        raw = path.read_bytes(); batch = strict_json(raw)
        receipt_path = root / index['buildReceipts'][batch['batchId']]
        receipt = strict_json(receipt_path.read_bytes())
        if receipt['batchRawSha256'] != sha(raw) or receipt['status'] != 'passed':
            raise ValueError('Current build does not bind author data')
        if batch['corpusManifestRawSha256'] != sha(manifest_raw):
            raise ValueError('Corpus identity changed')
        dependencies[str(path.relative_to(root))] = sha(raw)
        dependencies[str(receipt_path.relative_to(root))] = sha(receipt_path.read_bytes())
        for entry in batch['entries']:
            if entry['id'] in entries or entry['id'] not in units:
                raise ValueError('Duplicate/unknown source occurrence')
            entries[entry['id']] = entry
    if entries.keys() != units.keys():
        raise ValueError('Full source occurrence coverage required')
    base_pairs = [(u, entries[k]) for k, u in units.items()]
    if any(u['id'] in units for u, _ in recovered):
        raise ValueError('Recovered native YAML unit collides with legacy corpus')
    dependencies.update(recovered_dependencies)
    return base_pairs + recovered, sha(manifest_raw), dependencies


def assemble(root, output, pairs, corpus_sha):
    known = programs(root)
    macros = quick_macro_names(strict_json((root / 'source/parameter-roles-8879120-01/parameters.json').read_bytes()))
    registry = load_registry(root, {u['id']: u for u, _ in pairs})
    label = strict_json((root / 'glossary/ru/approved.json').read_bytes())['roboheart']['term']
    grouped = defaultdict(list)
    for unit, entry in pairs:
        if unit['source'] != entry['source']:
            raise ValueError('Author source mismatch')
        validate_target_presence(unit, entry); validate_source_disposition(unit, entry)
        validate_entry(unit, entry, macros, registry, label)
        validate_description_modifiers(unit, entry['target'])
        asset = known[unit['asset']]['originalAsset'] if unit['asset'] in known else unit['asset']
        grouped[asset].append((unit, entry))
    resources, mappings, checks = [], [], []
    for asset, rows in sorted(grouped.items()):
        text, original = original_resource(root, asset)
        tree = copy.deepcopy(original)
        holes, fields, blocks = {}, defaultdict(list), defaultdict(list)
        for u, e in rows:
            if u['role'] == 'visible-display-mapping':
                mappings.append((u, e))
            if u['asset'] in known or 'spanUtf16' in u:
                blocks[u['asset']].append((u, e)); continue
            path = tuple(u['path'])
            if u['role'] == 'visible-display-mapping':
                if at(original, path) != u['source']:
                    raise ValueError('Logical display identity changed')
                continue
            if 'spanCodepoints' in u or 'span' in u:
                fields[path].append(exact_span_edit(u, e['target'], macros))
            else:
                if at(original, path) != u['source']:
                    raise ValueError('Original scalar changed')
                if path in holes:
                    raise ValueError('Overlapping scalar edit')
                put(tree, path, e['target'])
            holes[path] = u['id']
        direct = None
        for source_asset, pp in blocks.items():
            record = known.get(source_asset)
            src = recover_program(record, original) if record else text
            dst = splice(src, [program_edit(u, e, macros) for u, e in pp], utf16=True)
            verify_program(root, source_asset, src, dst, pp, macros)
            if not record:
                if original is not None:
                    raise ValueError('Direct AST and configuration edits must not overlap')
                direct = dst
            elif 'linePaths' in record:
                lines = dst.splitlines(keepends=True)
                if len(lines) != len(record['linePaths']) or any(not x.endswith('\n') for x in lines):
                    raise ValueError('Event physical line cardinality changed')
                for path, value in zip(record['linePaths'], lines):
                    path = tuple(path)
                    if path in holes: raise ValueError('Event/scalar edit collision')
                    put(tree, path, value[:-1]); holes[path] = source_asset
            elif 'spanCodepoints' in record:
                path = tuple(record['parentPath'])
                fields[path].append({'id': source_asset, 'span': record['spanCodepoints'],
                    'original': src, 'replacement': dst})
                holes[path] = source_asset
            else:
                path = tuple(record['parentPath'])
                if path in holes: raise ValueError('Whole-parent edit collision')
                put(tree, path, dst); holes[path] = source_asset
        for path, edits in fields.items():
            if at(tree, path) != at(original, path):
                raise ValueError('Whole-field and span edit collision')
            put(tree, path, splice(at(original, path), edits))
        if direct is not None:
            serialized, extension, kind = direct, '', 'script'
        elif asset == 'js/plugins.js':
            serialized = text[:text.index('[')] + json.dumps(tree, ensure_ascii=False, indent=2) + text[text.rfind(']')+1:]
            extension, kind = '', 'plugin-config'
        elif Path(asset).suffix in {'.KEL', '.AUBREY'}:
            serialized = json.dumps(tree, ensure_ascii=False, indent=2) + '\n'
            extension, kind = '.json', 'structured'
        else:
            serialized = yaml.safe_dump(tree, allow_unicode=True, sort_keys=False, width=100000)
            extension, kind = '.yaml', 'structured'
        path = output / 'resources' / (asset + extension)
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(serialized)
        raw = path.read_bytes()
        if raw.decode() != serialized: raise ValueError('Delivered bytes differ')
        if direct is None:
            delivered = parse_config(raw) if kind == 'plugin-config' else parse(asset, raw)
            compare_protected(tree, delivered, {})
            compare_protected(original, delivered, holes)
            # Whole-tree equality includes all edited targets, sibling blocks,
            # unedited mixed-field bytes, original mapped values and typed logic.
        resources.append({'originalAsset': asset, 'output': str(path.relative_to(output)),
            'rawSha256': sha(raw), 'originalPlaintextSha256': sha(text.encode()),
            'kind': kind, 'occurrences': len(rows), 'editedTypedPaths': len(holes)})
        checks.extend(u['id'] for u, _ in rows)
    mapping = {'schemaVersion': 1, 'siteLocale': 'ru', 'steamBuild': '8879120',
        'corpusManifestRawSha256': corpus_sha, 'entries': [mapping_row(u, e['target']) for u, e in mappings]}
    validate_mapping_document(mapping, mappings, corpus_sha)
    save_json(output / 'display-mappings.json', mapping)
    if len(checks) != len(pairs) or len(set(checks)) != len(pairs):
        raise ValueError('Assembly coverage mismatch')
    return resources, len(mappings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('Preserve previous assembled output')
    root = Path(__file__).resolve().parent.parent
    pairs, corpus_sha, deps = read_pairs(root)
    args.output.mkdir(parents=True)
    resources, mapped = assemble(root, args.output, pairs, corpus_sha)
    save_json(args.output / 'receipt.json', {'status': 'passed', 'stage': 'combined-plaintext',
        'corpusManifestRawSha256': corpus_sha, 'occurrences': len(pairs), 'displayMappings': mapped,
        'resources': resources, 'dependencies': deps,
        'compiledOutputs': {str(p.relative_to(args.output)):sha(p.read_bytes()) for p in sorted(args.output.rglob('*')) if p.is_file()},
        'recipeDependencies': {p.name: sha(p.read_bytes()) for p in (root / 'tools').glob('*.py')},
        'runtime': 'not-run', 'independentReview': 'pending', 'loaderPackage': 'pending'})
    print({'status': 'passed', 'occurrences': len(pairs), 'resources': len(resources), 'mapped': mapped})


if __name__ == '__main__': main()
