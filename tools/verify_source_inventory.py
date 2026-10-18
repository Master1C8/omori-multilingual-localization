#!/usr/bin/env python3
"""Verify saved original, extracted and reserialized OMORI source evidence."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from source_prepare import canonical, encoded, identity, protected_tree, sha, strict_json, strict_yaml


def parse(asset, raw):
    return strict_json(raw) if Path(asset).suffix in {'.KEL', '.AUBREY'} else strict_yaml(raw.decode())


def compare_protected(original, result, editable):
    if protected_tree(original, editable) != protected_tree(result, editable):
        raise ValueError('Exact protected value/structure/type/order mismatch')


def check(directory, game_root=None):
    directory = directory.resolve()
    manifest = strict_json((directory / 'manifest.json').read_bytes())
    for name, expected in manifest['fileHashes'].items():
        if sha((directory / name).read_bytes()) != expected:
            raise ValueError('Evidence bytes changed: ' + name)
    counts = Counter()
    editable = {}
    occurrences = {}
    for line in (directory / 'occurrences.jsonl').open():
        record = strict_json(line)
        if record['id'] in occurrences:
            raise ValueError('Duplicate stable occurrence ID')
        occurrences[record['id']] = record
        counts[record['role']] += 1
        if record['role'] == 'visible' and 'path' in record and 'span' not in record:
            editable.setdefault(record['asset'], {})[tuple(record['path'])] = record['id']
    if dict(counts) != manifest['roles'] or len(occurrences) != manifest['occurrenceCount']:
        raise ValueError('Manifest occurrence/role coverage mismatch')
    assets = strict_json((directory / 'structured-assets.json').read_bytes())
    checked = 0
    for report in assets:
        source_raw = gzip.decompress((directory / report['snapshot']).read_bytes())
        result_raw = gzip.decompress((directory / report['result']).read_bytes())
        original, result = parse(report['asset'], source_raw), parse(report['asset'], result_raw)
        if encoded(original) != encoded(result):
            raise ValueError('Full source-versus-reinserted parsed values mismatch: ' + report['asset'])
        if sha(canonical(encoded(original))) != report['parsedSha256']:
            raise ValueError('Original parsed fingerprint changed')
        holes = editable.get(report['asset'], {})
        protected = protected_tree(original, holes)
        frozen = strict_json(gzip.decompress((directory / report['preserveExactly']).read_bytes()))
        if frozen != protected or sha(canonical(protected)) != report['preserveExactlySha256']:
            raise ValueError('Preserve-exactly manifest does not match original values')
        compare_protected(original, result, holes)
        # Compare every original extracted string, including pending/technical
        # fields, against its exact typed path; a token-presence check is insufficient.
        from research_source import scalars
        for path, value, _ in scalars(original):
            if not isinstance(value, str):
                continue
            rid = identity(report['asset'], path)
            record = occurrences.get(rid)
            if record is None or record['source'] != value or record['path'] != list(path):
                raise ValueError('Source-versus-extracted value mismatch: ' + rid)
        checked += 1
    scripts = strict_json((directory / 'scripts.json').read_bytes())
    # JS spans are UTF-16 indices as defined by Acorn, not Python code points.
    for report in scripts['scripts']:
        source = gzip.decompress((directory / ('original/' + report['asset'] + '.gz')) .read_bytes()).decode()
        utf16 = source.encode('utf-16-le')
        for record in (r for r in scripts['strings'] if r['asset'] == report['asset']):
            a, b = record['spanUtf16']
            if utf16[2 * a:2 * b].decode('utf-16-le') != record['rawSource']:
                raise ValueError('AST original span mismatch: ' + record['id'])
    if game_root:
        graph = strict_json((directory / 'resource-graph.json').read_bytes())
        current = {p.relative_to(game_root).as_posix() for p in game_root.rglob('*') if p.is_file()}
        if current != {r['asset'] for r in graph}:
            raise ValueError('Original resource file set changed')
        for record in graph:
            if sha((game_root / record['asset']).read_bytes()) != record['rawSha256']:
                raise ValueError('Original resource bytes changed: ' + record['asset'])
    return {'status': 'passed', 'structuredAssets': checked, 'scriptAssets': len(scripts['scripts']),
            'sourceVersusExtractedExactValues': 'passed', 'sourceVersusNoopReinsertedExactValues': 'passed',
            'protectedStructureValuesTypesOrder': 'passed', 'originalResourceParity': 'passed' if game_root else 'not-run',
            'sourceGate': manifest['sourceGate'], 'translationReady': False,
            'inventoryManifestRawSha256': sha((directory / 'manifest.json').read_bytes()),
            'validatorRawSha256': sha(Path(__file__).read_bytes()),
            'limits': ['No-op reinsertion replaces the actual loader, installer, renderer and storage boundaries.',
                       'Unresolved roles, tokens, images and movie text still block translation handoff.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    result = check(args.inventory, args.game_root)
    raw = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.receipt:
        if args.receipt.exists():
            raise ValueError('Preserve prior receipt; choose a new filename')
        args.receipt.write_text(raw)
    print(raw)


if __name__ == '__main__':
    main()
