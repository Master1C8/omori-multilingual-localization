#!/usr/bin/env python3
"""Verify immutable original snapshots and combine exact source records once."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import subprocess
import yaml
from source_prepare import sha, strict_json, strict_yaml, save_json, encoded, canonical
from script_resource_adapter import programs, recover_program, parse_config


def at(value, path):
    for key in path:
        value = value[key]
    return value


def native_parse(module, requests):
    run = subprocess.run(['node', str(Path(__file__).with_name('native_yaml.cjs')), str(module)],
        input=json.dumps(requests), text=True, capture_output=True, check=True)
    return strict_json(run.stdout)


def native_typed(original, native):
    """Keep original YAML key types/order; verify native JS property projection."""
    if isinstance(original, dict):
        if not isinstance(native, dict) or len({str(k) for k in original}) != len(original):
            raise ValueError('Ambiguous native YAML property projection')
        if {str(k) for k in original} != set(native):
            raise ValueError('Native YAML property set mismatch')
        return {k: native_typed(v, native[str(k)]) for k, v in original.items()}
    if isinstance(original, list):
        if not isinstance(native, list) or len(original) != len(native):
            raise ValueError('Native YAML array shape mismatch')
        return [native_typed(a, b) for a, b in zip(original, native)]
    if isinstance(native, (dict, list)):
        raise ValueError('Native scalar became a container')
    return native


def differences(a, b, path=()):
    if type(a) is not type(b):
        return [(list(path), a, b)]
    if isinstance(a, dict):
        if list(a) != list(b):
            raise ValueError('Native mapping keys/order mismatch')
        return [d for k in a for d in differences(a[k], b[k], path + (k,))]
    if isinstance(a, list):
        if len(a) != len(b):
            raise ValueError('Native array cardinality mismatch')
        return [d for i in range(len(a)) for d in differences(a[i], b[i], path + (i,))]
    return [] if a == b else [(list(path), a, b)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--yaml-module', type=Path, required=True)
    a = p.parse_args()
    root, output = a.project_root.resolve(), a.output.resolve()
    if not output.is_relative_to(root / 'source/multilingual'):
        raise ValueError('Shared source write outside source/multilingual')
    if output.exists():
        raise ValueError('Preserve source revisions; use a new output directory')
    evidence = {}
    def pin(path, expected=None):
        raw = path.read_bytes()
        digest = sha(raw)
        if expected and digest != expected:
            raise ValueError('Pinned input changed: ' + str(path))
        evidence[str(path.relative_to(root))] = digest
        return raw
    base = root / 'source/inventory-8879120-01'
    manifest = strict_json(pin(base / 'manifest.json'))
    assert manifest['steamBuild'] == '8879120'
    # Cheap authoritative input checks precede the large snapshot verification.
    corpus = root / 'source/text-corpus-8879120-02'
    cm = strict_json(pin(corpus / 'manifest.json', 'a55c246992fc1ea672aba77ae0cbdc3ba67aa8ac8d84dd6b78a673addbb1c144'))
    for name, digest in cm['fileHashes'].items():
        pin(corpus / name, digest)
    supplement = root / 'source/native-yaml-8879120-01'
    sm = strict_json(pin(supplement / 'manifest.json'))
    if sm['baseCorpusManifest']['sha256'] != sha((corpus / 'manifest.json').read_bytes()):
        raise ValueError('Supplement base revision mismatch')
    for name, digest in sm['files'].items():
        pin(supplement / name, digest)
    old = strict_json((corpus / 'units.json').read_bytes())
    extra = strict_json((supplement / 'units.json').read_bytes())
    units = old + extra
    if len(old) != 20775 or len(extra) != 19 or len({u['id'] for u in units}) != 20794:
        raise ValueError('Missing/extra/duplicate source records')
    for name, digest in manifest['fileHashes'].items():
        pin(base / name, digest)
    prior = strict_json(pin(root / 'source/inventory-8879120-01-verification.json'))
    if prior['inventoryManifestRawSha256'] != sha((base / 'manifest.json').read_bytes()):
        raise ValueError('Original verification revision mismatch')
    graph = strict_json((base / 'resource-graph.json').read_bytes())
    # Only the read-only parser library is accessed in the current installation.
    # The installed overlay is deliberately not treated as original source.
    module = a.yaml_module.resolve()
    game_root = Path(manifest['gameRoot'])
    module_prefix = str(module.relative_to(game_root)) + '/'
    parser_pins = {}
    for row in graph:
        if row['asset'].startswith(module_prefix):
            f = game_root / row['asset']
            if sha(f.read_bytes()) != row['rawSha256']:
                raise ValueError('Bundled parser differs from original resource graph')
            parser_pins[row['asset']] = row['rawSha256']
    if not parser_pins:
        raise ValueError('Bundled parser missing from original graph')
    reports = strict_json((base / 'structured-assets.json').read_bytes())
    originals, native_requests, old_noop_differences = {}, [], []
    for row in reports:
        raw = gzip.decompress((base / row['snapshot']).read_bytes())
        noop = gzip.decompress((base / row['result']).read_bytes())
        is_json = Path(row['asset']).suffix in {'.KEL', '.AUBREY'}
        legacy = strict_json(raw) if is_json else yaml.safe_load(raw.decode())
        legacy_noop = strict_json(noop) if is_json else yaml.safe_load(noop.decode())
        if encoded(legacy) != encoded(legacy_noop) or sha(canonical(encoded(legacy))) != row['parsedSha256']:
            raise ValueError('Historical extraction/noop values changed: ' + row['asset'])
        parsed = strict_json(raw) if is_json else strict_yaml(raw.decode())
        originals[row['asset']] = parsed
        if not is_json:
            native_requests.append({'asset': row['asset'], 'text': raw.decode()})
    native = native_parse(module, native_requests)
    saved_native = strict_json((supplement / 'native-source.json').read_bytes())
    if len(native) != 211 or {r['asset']: r['value'] for r in native} != {r['asset']: r['native'] for r in saved_native}:
        raise ValueError('Bundled native parser evidence changed')
    residual = []
    for row in native:
        asset = row['asset']
        value = native_typed(originals[asset], row['value'])
        residual.extend({'asset': asset, 'path': path, 'python': before, 'native': after}
                        for path, before, after in differences(originals[asset], value))
        originals[asset] = value
    if residual != [{'asset': 'data/Notes.PLUTO', 'path': ['NOTES', 'Enemies', 'Bunyum2', 'Notes'],
                     'python': 'Oooooooh!', 'native': 'Oooooooh!\n'}]:
        raise ValueError('Unknown native scalar typing/structure difference: ' + repr(residual))
    # Actual serialization and bundled-parser readback of every native YAML tree.
    delivered = native_parse(module, [{'asset': r['asset'],
        'text': yaml.safe_dump(r['value'], allow_unicode=True, sort_keys=False, width=100000)} for r in native])
    if delivered != native:
        raise ValueError('Native full-tree no-op reinsertion mismatch')
    for row in reports:
        if Path(row['asset']).suffix not in {'.KEL', '.AUBREY'}:
            before = yaml.safe_load(gzip.decompress((base / row['result']).read_bytes()).decode())
            old_noop_differences.extend({'asset': row['asset'], 'path': p, 'before': b, 'after': c}
                for p, b, c in differences(before, originals[row['asset']]))
    expected = {(u['asset'], tuple(u['path'])) for u in extra}
    actual = {(r['asset'], tuple(r['path'])) for r in old_noop_differences}
    if actual != expected | {('data/Notes.PLUTO', ('NOTES', 'Enemies', 'Bunyum2', 'Notes'))}:
        raise ValueError('Unknown legacy no-op parser delta')
    known = programs(root)
    for name in ['classification-8879120-03/event-programs.json', 'note-programs-8879120-04/programs.json',
                 'embedded-programs-8879120-02/programs.json']:
        pin(root / 'source' / name)
    for name in ['source/parameter-roles-8879120-01/parameters.json',
                 'source/encoded-dialogue-8879120-01.json', 'source/encoded-battle-dialogue-8879120-01.json']:
        pin(root / name)
    config = gzip.decompress((corpus / 'original-plugins.js.gz').read_bytes())
    if sha(config) != manifest['pluginConfigurationRawSha256']:
        raise ValueError('Original plugins configuration changed')
    originals['js/plugins.js'] = parse_config(config)
    by_program = defaultdict(list)
    for unit in units:
        if unit.get('sourceValueSha256') and sha(unit['source'].encode()) != unit['sourceValueSha256']:
            raise ValueError('Source value digest mismatch')
        if 'spanUtf16' in unit:
            by_program[unit['asset']].append(unit)
        else:
            value = at(originals[unit['asset']], unit['path'])
            if 'span' in unit or 'spanCodepoints' in unit:
                if sha(value.encode()) != unit['parentValueSha256']:
                    raise ValueError('Mixed field parent hash mismatch')
                start, stop = unit.get('spanCodepoints', unit.get('span'))
                value = value[start:stop]
            if type(value) is not str or value != unit['source']:
                raise ValueError('Original typed source boundary mismatch: ' + unit['id'])
    requests = []
    for asset, rows in by_program.items():
        record = known.get(asset)
        source = recover_program(record, originals[record['originalAsset']]) if record else gzip.decompress(
            (base / 'original' / (asset + '.gz')).read_bytes()).decode()
        for unit in rows:
            start, stop = unit['spanUtf16']
            if source.encode('utf-16-le')[start*2:stop*2].decode('utf-16-le') != unit['rawSource']:
                raise ValueError('Original UTF16 literal boundary mismatch')
        requests.append({'asset': asset, 'source': source})
    parser = subprocess.run(['node', '--expose-internals', str(Path(__file__).with_name('source_literal_values.cjs'))],
        input=json.dumps(requests), text=True, capture_output=True, check=True)
    parsed = strict_json(parser.stdout)
    if parsed['errors']:
        raise ValueError('Original visible program parse failure')
    literals = {(r['asset'], tuple(r['spanUtf16'])): r for r in parsed['strings']}
    for rows in by_program.values():
        for unit in rows:
            actual = literals[(unit['asset'], tuple(unit['spanUtf16']))]
            if any(actual[k] != unit[k] for k in ('source', 'rawSource', 'nodeType')):
                raise ValueError('Parsed source literal value mismatch')
    delta = strict_json(pin(root / 'source/ru-effective-role-delta-2026-10-14-01.json'))
    pizza = strict_json(pin(root / 'source/ru-pizza-source-role-delta-2026-10-14-01.json'))
    by_id = {u['id']: u for u in units}
    retained = []
    for row in delta['rows']:
        u = by_id[row['id']]
        if 'spanUtf16' not in u or u['sourceValueSha256'] != row['sourceValueSha256']:
            raise ValueError('Technical retention source boundary changed')
        retained.append({'id': u['id'], 'source': u['source'], **row['disposition']})
    consumer = gzip.decompress((base / 'original/js/plugins/YIN - Minigame - PizzaDelivery.OMORI.gz').read_bytes())
    if sha(consumer) != pizza['consumerPlaintextSha256']:
        raise ValueError('Pizza normalization consumer changed')
    for id, source in zip(pizza['sourceIds'], pizza['originalValues']):
        if by_id[id]['source'] != source:
            raise ValueError('Pizza retention value changed')
        retained.append({'id': id, 'source': source, 'role': 'preserve-exactly',
            'sourceValueSha256': sha(source.encode()), 'reason': 'Native substring normalization operand; preserve source identity.',
            'consumerSourceSha256': pizza['consumerPlaintextSha256']})
    if len(retained) != 77 or len({r['id'] for r in retained}) != 77:
        raise ValueError('Technical retention set mismatch')
    registry = strict_json(pin(root / 'source/special-scenes-8879120.json'))
    pin(root / 'source/special-scenes-8879120.md')
    for name, digest in registry['sourceBindings'].items():
        pin(root / name, digest)
    case_ids = []
    for case in registry['cases']:
        case_ids.extend(case['unitIds'])
        if any(id not in by_id for id in case['unitIds']):
            raise ValueError('Special scene references missing source ID')
        for row in case['evidence']:
            if isinstance(row, dict) and 'path' in row and 'sha256' in row:
                pin(root / row['path'], row['sha256'])
    save_json(output / 'units.json', units)
    save_json(output / 'technical-retentions.json', retained)
    save_json(output / 'native-source.json', native)
    result = {'schemaVersion': 1, 'build': '8879120', 'sourceLocale': 'en',
        'recordEquality': 'passed', 'sourceGate': 'needs-review',
        'baseRecords': len(old), 'supplementRecords': len(extra), 'totalRecords': len(units),
        'technicalRetentions': 77, 'visibleTextRecords': 20717,
        'scalarOrSpannedTextRecords': 17212, 'displayMappingRecords': 3505,
        'boundaryCounts': dict(Counter('utf16' if 'spanUtf16' in u else 'span' if 'span' in u or 'spanCodepoints' in u else 'scalar' for u in units)),
        'structuredSnapshotAssets': len(reports), 'nativeYamlAssets': len(native),
        'originalScriptAssets': len(strict_json((base / 'scripts.json').read_bytes())['scripts']),
        'visibleProgramsParsed': len(requests), 'astLiteralValues': sum(map(len, by_program.values())),
        'nativeTypedNoop': 'passed', 'nativeParserPins': parser_pins, 'parserResidual': residual,
        'legacyNoopDeltas': old_noop_differences, 'inputHashes': evidence,
        'inventoryPath': str((output / 'units.json').relative_to(root)),
        'inventorySha256': sha((output / 'units.json').read_bytes()),
        'files': {n: sha((output / n).read_bytes()) for n in ['units.json', 'technical-retentions.json', 'native-source.json']},
        'specialScenes': {'count': len(registry['cases']), 'uniqueMembers': len(set(case_ids)),
            'discovery': registry['coverage'], 'gate': 'needs-review'},
        'runtime': 'not-run', 'visual': 'not-run',
        'limitations': ['Exact combination and extraction/no-op checks do not establish complete special-scene discovery.',
            'Current installed overlay is not original source; immutable snapshots and the historical original-byte receipt are pinned.',
            'Native parser comparison fixes 19 boolean coercions and retains the protected Notes trailing newline.',
            'No source, target, glossary or editorial acceptance transferred from Russian.',
            'Native overlay compilation, font resources and packaging are separate gates.'],
        'recipeSha256': sha(Path(__file__).read_bytes())}
    save_json(output / 'verification.json', result)
    print(json.dumps({k: result[k] for k in ['sourceGate', 'recordEquality', 'totalRecords', 'nativeYamlAssets', 'inventorySha256']}))


if __name__ == '__main__':
    main()
