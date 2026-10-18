#!/usr/bin/env python3
"""Explicit-locale, source-bound plaintext tooling; never generates wording."""
import argparse
from collections import defaultdict
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys
import yaml
from source_prepare import sha, strict_json, save_json, canonical, encoded
from source_text_syntax import quick_macro_names
from unit_text_controls import compare_unit_controls
from text_resource_adapter import splice, exact_span_edit, verify_delivered_spans
from script_resource_adapter import programs, original_resource, recover_program, program_edit, verify_program, put, parse_config
from verify_source_inventory import compare_protected, parse
from encoded_dialogue import load_registry, validate_entry, authored_encoding
from prepare_source import native_parse, native_typed, at

STAGES = ['scope', 'probe', 'source', 'glossary', 'translate-edit', 'editorial', 'resources', 'package', 'runtime', 'delivery']
TOOL_ROOT = Path(__file__).resolve().parent


def unique(rows, key='id'):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError('Duplicate ' + key + ': ' + row[key])
        result[row[key]] = row
    return result


def locale_config(locale):
    matrix = strict_json((TOOL_ROOT / 'renderer-matrix.json').read_bytes())
    catalog = Path(matrix['catalogPath'])
    if sha(catalog.read_bytes()) != matrix['catalogSha256']:
        raise ValueError('Canonical locale catalog changed; reconcile shared configuration')
    configs = unique(matrix['locales'], 'siteLocale')
    if locale not in configs:
        raise ValueError('Unknown or excluded target locale: ' + str(locale))
    return configs[locale]


class Context:
    def __init__(self, root, data, locale):
        self.config = locale_config(locale)  # Reject before any write.
        self.locale = locale
        self.root, self.data = root.resolve(), data.resolve()
        if not self.data.is_relative_to(self.root / 'source/multilingual'):
            raise ValueError('Shared inventory must be inside source/multilingual')
        self.locale_root = self.root / 'runtime/multilingual/locales' / locale
        self.manifest = strict_json((self.data / 'verification.json').read_bytes())
        for name, digest in self.manifest['files'].items():
            if sha((self.data / name).read_bytes()) != digest:
                raise ValueError('Shared source evidence changed: ' + name)
        self.units = strict_json((self.data / 'units.json').read_bytes())
        self.by_id = unique(self.units)
        # Equality is to full immutable records, not just source text or counts.
        expected = strict_json((self.root / 'source/text-corpus-8879120-02/units.json').read_bytes()) + strict_json(
            (self.root / 'source/native-yaml-8879120-01/units.json').read_bytes())
        if self.units != expected:
            raise ValueError('Changed/missing/extra original source records')
        self.retained = unique(strict_json((self.data / 'technical-retentions.json').read_bytes()))
        self.inventory_sha = sha((self.data / 'units.json').read_bytes())
        for name in ['source/parameter-roles-8879120-01/parameters.json',
                     'source/classification-8879120-03/event-programs.json',
                     'source/note-programs-8879120-04/programs.json',
                     'source/embedded-programs-8879120-02/programs.json',
                     'source/encoded-dialogue-8879120-01.json',
                     'source/encoded-battle-dialogue-8879120-01.json']:
            self.verify_input(self.root / name)
        self.macros = quick_macro_names(strict_json((self.root / 'source/parameter-roles-8879120-01/parameters.json').read_bytes()))
        self.registry = load_registry(self.root, self.by_id)
        self.known = programs(self.root)
        self.native = {r['asset']: r['value'] for r in strict_json((self.data / 'native-source.json').read_bytes())}

    def verify_input(self, path):
        relative = str(path.relative_to(self.root))
        if self.manifest['inputHashes'].get(relative) != sha(path.read_bytes()):
            raise ValueError('Shared original dependency changed: ' + relative)

    def output(self, path):
        resolved = path.resolve()
        if not resolved.is_relative_to(self.locale_root.resolve()):
            raise ValueError('Locale write isolation: output must be under ' + str(self.locale_root))
        if resolved.exists():
            raise ValueError('Preserve existing locale evidence; use a new revision')
        return resolved

    def original(self, asset):
        self.verify_input(self.root / ('source/text-corpus-8879120-02/original-plugins.js.gz'
            if asset == 'js/plugins.js' else 'source/inventory-8879120-01/original/' + asset + '.gz'))
        text, tree = original_resource(self.root, asset)
        if asset in self.native:
            tree = native_typed(tree, self.native[asset])
        return text, copy.deepcopy(tree)

    def shared_gate(self):
        a = strict_json((self.root / 'source/multilingual/acceptance.json').read_bytes())
        if a.get('source') != 'passed' or a.get('adapters') != 'passed' or a.get('inventorySha256') != self.inventory_sha:
            raise ValueError('Shared source/adapter acceptance unmet; locale mass work blocked')
        if not a.get('evidence') or a.get('inventoryPath') != str((self.data / 'units.json').relative_to(self.root)):
            raise ValueError('Shared acceptance evidence/inventory path missing')
        if a.get('rendererMatrixSha256') != sha((TOOL_ROOT / 'renderer-matrix.json').read_bytes()) or a.get('processBindingSha256') != sha((TOOL_ROOT / 'process-binding.json').read_bytes()):
            raise ValueError('Shared process/renderer binding changed')
        if self.config['status'] == 'blocked':
            raise ValueError('Renderer mechanism failed for ' + self.locale + ': ' + self.config['reason'])
        for row in a['evidence']:
            file = (self.root / row['path']).resolve()
            if not file.is_relative_to(self.root) or sha(file.read_bytes()) != row['sha256']:
                raise ValueError('Shared acceptance evidence changed')


def current_glossary(master):
    run = subprocess.run([str(master / 'vnrevival'), 'glossary', 'size', 'omori', '--json'],
                         text=True, capture_output=True, check=True)
    return strict_json(run.stdout)


def glossary_check(ctx, snapshot, master):
    document = strict_json(snapshot.read_bytes())
    if document.get('siteLocale') != ctx.locale or document.get('sourceLocale') != 'en':
        raise ValueError('Glossary snapshot locale mismatch')
    current = current_glossary(master)
    if document.get('sourceReferenceSha256') != current['reference']['sha256']:
        raise ValueError('Glossary dependency reconciliation required against CURRENT canonical English revision')
    source_path = snapshot.parent / document['sourceFile']
    target_path = snapshot.parent / document['targetFile']
    source = strict_json(source_path.read_bytes())
    source = source if isinstance(source, list) else source['entries']
    unique(source)
    reference = {'sourceLocale': 'en', 'entries': [{k: r[k] for k in ['id', 'term', 'meaning']} for r in source]}
    if sha(canonical(reference)) != current['reference']['sha256']:
        raise ValueError('Glossary English snapshot differs from canonical reference')
    target = strict_json(target_path.read_bytes())
    if not isinstance(target, list):
        raise ValueError('Glossary target snapshot must be an ordered entry array')
    unique(target)
    ids = [r['id'] for r in source]
    if [r['id'] for r in target] != ids or any(not isinstance(r.get(k), str) or not r[k].strip() for r in target for k in ['term', 'meaning']):
        raise ValueError('Glossary target coverage/order/fields mismatch')
    for role, path, rows in [('source', source_path, source), ('target', target_path, target)]:
        raw_sha = sha(path.read_bytes())
        if document.get(role + 'Sha256') != raw_sha:
            raise ValueError('Glossary snapshot file changed')
        receipt_path = snapshot.parent / document[role + 'ReadinessFile']
        if sha(receipt_path.read_bytes()) != document[role + 'ReadinessSha256']:
            raise ValueError('Glossary readiness evidence changed')
        receipt = strict_json(receipt_path.read_bytes())
        if receipt.get('status') != 'accepted' or receipt.get('standard') != 'standard' or receipt.get('artifactSha256') != raw_sha:
            raise ValueError('Glossary editorial readiness unmet')
        if receipt.get('sourceReferenceSha256') != current['reference']['sha256'] or receipt.get('unresolved') != []:
            raise ValueError('Glossary evidence has unreconciled source dependencies')
        layers = receipt.get('layers', [])
        if len(layers) != 2 or any(layer.get('status') != 'complete-clean' or layer.get('actualReadIds') != ids
            or layer.get('dimensions') != ['fidelity', 'native-language'] or not layer.get('reviewer') for layer in layers):
            raise ValueError('Two complete glossary reading layers required; counts are not review')
    return {'status': 'passed-structural-evidence-binding', 'siteLocale': ctx.locale, 'entries': len(ids),
            'sourceReferenceSha256': current['reference']['sha256'], 'snapshotSha256': sha(snapshot.read_bytes()),
            'targetEntries': target, 'note': 'Receipt binding checks do not perform semantic review.'}


def case_gate(ctx, decisions, snapshot_sha):
    registry_path = ctx.root / 'source/special-scenes-8879120.json'
    registry = strict_json(registry_path.read_bytes())
    document = strict_json(decisions.read_bytes())
    if document.get('siteLocale') != ctx.locale or document.get('inventorySha256') != ctx.inventory_sha or document.get('glossarySnapshotSha256') != snapshot_sha:
        raise ValueError('Special-scene decision input binding mismatch')
    if document.get('registrySha256') != sha(registry_path.read_bytes()):
        raise ValueError('Special-scene registry changed')
    records = unique(document.get('cases', []))
    if set(records) != {c['id'] for c in registry['cases']}:
        raise ValueError('Every discovered special scene needs a reviewed locale decision')
    for case in registry['cases']:
        row = records[case['id']]
        if row.get('status') != 'reviewed' or row.get('unresolved') != [] or row.get('unitIds') != case['unitIds']:
            raise ValueError('Unresolved or incomplete special-scene decision: ' + case['id'])
        for field in ['effectOrSolution', 'identityContract', 'adaptationContract', 'positiveScenario', 'negativeScenario', 'reviewer']:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('Missing concrete special-scene decision field: ' + field)
        authored = decisions.parent / row['authoredFile']
        if sha(authored.read_bytes()) != row['authoredSha256']:
            raise ValueError('Special-scene accepted wording changed')
        targets = unique(strict_json(authored.read_bytes())['entries'])
        if not set(case['unitIds']).issubset(targets):
            raise ValueError('Special-scene full wording group missing')
        validate_entries(ctx, [targets[id] for id in case['unitIds']], document['targetNamebox'])
    return {'status': 'passed-evidence-binding', 'cases': len(records), 'sha256': sha(decisions.read_bytes())}


def validate_entries(ctx, entries, target_namebox):
    unique(entries)
    pairs = []
    for entry in entries:
        u = ctx.by_id.get(entry['id'])
        if not u or entry.get('source') != u['source']:
            raise ValueError('Unknown ID or changed authored source')
        target = entry.get('target')
        if not isinstance(target, str):
            raise ValueError('Invalid target type')
        if u['id'] in ctx.retained:
            if target != u['source']:
                raise ValueError('Technical preserved value changed: ' + u['id'])
        else:
            if not target.strip():
                omission = entry.get('syntacticOmission', {})
                if 'spanUtf16' not in u or u['role'] != 'visible' or omission.get('kind') != 'grammatical-fragment' or omission.get('sourceValueSha256') != sha(u['source'].encode()) or not omission.get('reason'):
                    raise ValueError('Blank target lacks source-bound grammatical omission')
            validate_entry(u, entry, ctx.macros, ctx.registry, target_namebox)
        pairs.append((u, entry))
    return pairs


def validate_batch(ctx, batch_path):
    batch = strict_json(batch_path.read_bytes())
    if batch.get('siteLocale') != ctx.locale or batch.get('sourceLocale') != 'en' or batch.get('inventorySha256') != ctx.inventory_sha:
        raise ValueError('Batch locale/source inventory mismatch')
    if not batch.get('glossarySnapshotSha256') or not batch.get('specialSceneDecisionsSha256'):
        raise ValueError('Batch prerequisite fingerprints missing')
    if any(e.get('immediateEdit') is not True for e in batch['entries']):
        raise ValueError('Every authored entry requires actual immediate-edit record')
    return batch, validate_entries(ctx, batch['entries'], batch['targetNamebox'])


def mapping_row(u, entry):
    return {k: u[k] for k in ['id', 'asset', 'source', 'path', 'spanUtf16', 'nodeType', 'rawSource', 'sourceValueSha256'] if k in u} | {'target': entry['target']}


def assemble(ctx, pairs, output, yaml_module, fail_after=None, verify_only=False):
    """One merged revision, exact source edits; partial output is never accepted."""
    unique([e for _, e in pairs])
    originals, texts, results, holes = {}, {}, {}, defaultdict(dict)
    field_edits, program_rows = defaultdict(list), defaultdict(list)
    delivered_programs, mapped = {}, []
    for u, entry in pairs:
        record = ctx.known.get(u['asset'])
        asset = record['originalAsset'] if record else u['asset']
        if asset not in originals:
            texts[asset], originals[asset] = ctx.original(asset)
            results[asset] = copy.deepcopy(originals[asset])
        if u['role'] == 'visible-display-mapping':
            mapped.append(mapping_row(u, entry))
        if 'spanUtf16' in u:
            program_rows[u['asset']].append((u, entry))
        elif u['role'] != 'visible-display-mapping':
            path = tuple(u['path'])
            original = at(originals[asset], path)
            if 'span' in u or 'spanCodepoints' in u:
                if sha(original.encode()) != u['parentValueSha256']:
                    raise ValueError('Mixed source parent hash changed')
                field_edits[(asset, path)].append(exact_span_edit(u, entry['target'], ctx.macros))
            else:
                if type(original) is not str or original != u['source']:
                    raise ValueError('Original typed scalar changed')
                put(results[asset], path, entry['target'])
            holes[asset][path] = u['id']
    for source_asset, rows in program_rows.items():
        record = ctx.known.get(source_asset)
        asset = record['originalAsset'] if record else source_asset
        source = recover_program(record, originals[asset]) if record else texts[asset]
        delivered = splice(source, [program_edit(u, e, ctx.macros) for u, e in rows], utf16=True)
        verify_program(ctx.root, source_asset, source, delivered, rows, ctx.macros)
        delivered_programs[source_asset] = delivered
        if not record:
            results[asset] = delivered
        elif 'linePaths' in record:
            lines = delivered.splitlines(keepends=True)
            if len(lines) != len(record['linePaths']) or any(not line.endswith('\n') for line in lines):
                raise ValueError('Embedded program physical line binding changed')
            for path, line in zip(record['linePaths'], lines):
                put(results[asset], path, line[:-1])
                holes[asset][tuple(path)] = source_asset
        elif 'spanCodepoints' in record:
            path = tuple(record['parentPath'])
            field_edits[(asset, path)].append({'id': source_asset, 'span': record['spanCodepoints'], 'original': source, 'replacement': delivered})
            holes[asset][path] = source_asset
        else:
            put(results[asset], record['parentPath'], delivered)
            holes[asset][tuple(record['parentPath'])] = source_asset
    for (asset, path), edits in field_edits.items():
        put(results[asset], path, splice(at(originals[asset], path), edits))
    serialized = {}
    for asset, result in results.items():
        if asset == 'js/plugins.js':
            src = texts[asset]
            text = src[:src.index('[')] + json.dumps(result, ensure_ascii=False, indent=2) + src[src.rfind(']') + 1:]
            compare_protected(originals[asset], parse_config(text), holes[asset])
            ext = 'js'
        elif asset.startswith('js/'):
            text, ext = result, 'js'
        elif asset in ctx.native:
            text, ext = yaml.safe_dump(result, allow_unicode=True, sort_keys=False, width=100000), 'yaml'
            compare_protected(originals[asset], result, holes[asset])
        else:
            text, ext = json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'json'
            compare_protected(originals[asset], strict_json(text), holes[asset])
        serialized[asset] = (text, ext)
    native_rows = native_parse(yaml_module, [{'asset': a, 'text': t} for a, (t, ext) in serialized.items() if ext == 'yaml'])
    for row in native_rows:
        if encoded(native_typed(results[row['asset']], row['value'])) != encoded(results[row['asset']]):
            raise ValueError('Actual native YAML serialization changed typed values')
    if not verify_only:
        output.mkdir(parents=True)
    files = []
    for asset, (text, ext) in serialized.items():
        path = output / 'resources' / (asset + '.plaintext.' + ext)
        if verify_only:
            if path.read_bytes() != text.encode():
                raise ValueError('Delivered plaintext differs from current authored source assembly: ' + asset)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        files.append({'originalAsset': asset, 'path': str(path.relative_to(output)), 'sha256': sha(path.read_bytes()), 'format': ext})
        if fail_after is not None and len(files) == fail_after:
            raise ValueError('Injected between-file failure; partial revision has no receipt')
    mapping_document = {'schemaVersion': 1, 'siteLocale': ctx.locale, 'inventorySha256': ctx.inventory_sha,
                        'entries': mapped, 'integration': 'pending-native-display-compiler'}
    if verify_only:
        if strict_json((output / 'display-mappings.json').read_bytes()) != mapping_document:
            raise ValueError('Delivered display mapping differs from authored source binding')
        if {str(p.relative_to(output)) for p in (output / 'resources').rglob('*') if p.is_file()} != {r['path'] for r in files}:
            raise ValueError('Delivered resource file set mismatch')
    else:
        save_json(output / 'display-mappings.json', mapping_document)
    # Read actual delivered files again, including every protected field and target.
    readback = {}
    for row in files:
        raw = (output / row['path']).read_bytes()
        if sha(raw) != row['sha256']:
            raise ValueError('Delivered plaintext changed')
        asset = row['originalAsset']
        readback[asset] = raw.decode() if row['format'] == 'js' and asset != 'js/plugins.js' else parse_config(raw) if asset == 'js/plugins.js' else parse(asset, raw)
        if row['format'] != 'yaml' and encoded(readback[asset]) != encoded(results[asset]):
            raise ValueError('Actual plaintext readback differs')
    actual_native = native_parse(yaml_module, [{'asset': r['originalAsset'], 'text': (output / r['path']).read_text()} for r in files if r['format'] == 'yaml'])
    for row in actual_native:
        readback[row['asset']] = native_typed(results[row['asset']], row['value'])
        if encoded(readback[row['asset']]) != encoded(results[row['asset']]):
            raise ValueError('Actual native plaintext readback differs')
    for source_asset, rows in program_rows.items():
        record = ctx.known.get(source_asset)
        asset = record['originalAsset'] if record else source_asset
        source = recover_program(record, originals[asset]) if record else texts[asset]
        if not record:
            delivered = readback[asset]
        elif 'linePaths' in record:
            delivered = ''.join(at(readback[asset], p) + '\n' for p in record['linePaths'])
        elif 'spanCodepoints' in record:
            # Exact whole mixed parent equality establishes adjusted block boundaries.
            path = tuple(record['parentPath'])
            if at(readback[asset], path) != splice(at(originals[asset], path), field_edits[(asset, path)]):
                raise ValueError('Actual delivered program parent differs')
            delivered = delivered_programs[source_asset]
        else:
            delivered = at(readback[asset], record['parentPath'])
        verify_program(ctx.root, source_asset, source, delivered, rows, ctx.macros)
    for u, e in pairs:
        if 'spanUtf16' in u:
            continue
        actual = at(readback[u['asset']], u['path'])
        if u['role'] == 'visible-display-mapping':
            if actual != u['source']:
                raise ValueError('Delivered logical identity changed')
        elif 'span' not in u and 'spanCodepoints' not in u and actual != e['target']:
            raise ValueError('Delivered scalar target mismatch')
    for (asset, path), edits in field_edits.items():
        if at(readback[asset], path) != splice(at(originals[asset], path), edits):
            raise ValueError('Delivered spanned field differs at exact boundary')
    receipt = {'schemaVersion': 1, 'siteLocale': ctx.locale, 'status': 'passed-plaintext', 'inventorySha256': ctx.inventory_sha,
        'entries': [e for _, e in pairs], 'entryIds': [u['id'] for u, _ in pairs], 'files': files,
        'displayMappingsSha256': sha((output / 'display-mappings.json').read_bytes()), 'displayMappings': len(mapped),
        'runtime': 'not-run', 'visual': 'not-run', 'nativeOverlay': 'not-built', 'editorial': 'pending',
        'limitations': ['Plaintext assembly is not native overlay compilation, packaging, font readiness or engine integration.',
            'A failure between writes leaves an incomplete immutable revision; no cross-file rollback is claimed.']}
    if verify_only:
        existing = strict_json((output / 'receipt.json').read_bytes())
        for key in ['siteLocale', 'inventorySha256', 'entries', 'entryIds', 'files', 'displayMappingsSha256', 'displayMappings']:
            if existing.get(key) != receipt[key]:
                raise ValueError('Delivered receipt/author binding changed: ' + key)
    else:
        save_json(output / 'receipt.json', receipt)
    return {'status': receipt['status'], 'units': len(pairs), 'files': len(files), 'siteLocale': ctx.locale}


def authored(ctx, batch_dir):
    rows = []
    for path in sorted(batch_dir.glob('*.json')):
        _, pairs = validate_batch(ctx, path)
        rows.extend(pairs)
    unique([e for _, e in rows])
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root', type=Path, required=True)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--locale', required=True)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('scope'); sub.add_parser('probe'); sub.add_parser('source-check')
    queue = sub.add_parser('queue'); queue.add_argument('--offset', type=int, default=0); queue.add_argument('--limit', type=int, default=15)
    source = sub.add_parser('source'); source.add_argument('asset'); source.add_argument('--offset', type=int, default=0); source.add_argument('--max-chars', type=int, default=18000)
    sub.add_parser('case-index')
    case_source = sub.add_parser('case-source'); case_source.add_argument('case_id'); case_source.add_argument('--offset', type=int, default=0); case_source.add_argument('--max-chars', type=int, default=18000)
    for command in ['glossary-check', 'case-check', 'validate-batch', 'assemble']:
        tool = sub.add_parser(command)
        tool.add_argument('--glossary-snapshot', type=Path, required=True)
        tool.add_argument('--master-root', type=Path, required=True)
        if command != 'glossary-check':
            tool.add_argument('--decisions', type=Path, required=True)
        if command == 'validate-batch':
            tool.add_argument('--batch', type=Path, required=True)
        if command == 'assemble':
            tool.add_argument('--batch-dir', type=Path, required=True); tool.add_argument('--output', type=Path, required=True)
            tool.add_argument('--yaml-module', type=Path, required=True)
    progress = sub.add_parser('progress'); progress.add_argument('--batch-dir', type=Path, required=True)
    progress.add_argument('--build-dir', type=Path); progress.add_argument('--yaml-module', type=Path)
    stage = sub.add_parser('stage-check'); stage.add_argument('stage', choices=STAGES)
    a = p.parse_args()
    ctx = Context(a.project_root, a.data_root, a.locale)
    if a.command == 'scope':
        result = {'siteLocale': ctx.locale, 'sourceLocale': 'en', 'build': '8879120', 'type': 'standard', 'localeRoot': str(ctx.locale_root), 'processBinding': sha((TOOL_ROOT / 'process-binding.json').read_bytes())}
    elif a.command == 'probe':
        result = ctx.config
    elif a.command == 'source-check':
        result = {k: ctx.manifest[k] for k in ['sourceGate', 'recordEquality', 'totalRecords', 'inventorySha256', 'specialScenes']}
    elif a.command == 'queue':
        if a.offset < 0 or not 1 <= a.limit <= 100:
            raise ValueError('Queue bounds invalid')
        grouped = defaultdict(list)
        for u in ctx.units: grouped[u['asset']].append(u)
        assets = list(grouped)
        end = min(a.offset + a.limit, len(assets))
        result = {'assets': len(assets), 'nextOffset': end if end < len(assets) else None,
            'rows': [{'asset': asset, 'units': len(grouped[asset]), 'adapters': sorted(set('ast' if 'spanUtf16' in u else 'span' if 'span' in u or 'spanCodepoints' in u else u['role'] for u in grouped[asset]))} for asset in assets[a.offset:end]],
            'note': 'All source families retained, including harder adapters. Queue counts are not editorial coverage.'}
    elif a.command == 'case-index':
        registry = strict_json((ctx.root / 'source/special-scenes-8879120.json').read_bytes())
        result = {'discovery': registry['coverage']['status'],
            'cases': [{'id': c['id'], 'title': c['title'], 'category': c['category'], 'members': len(c['unitIds']), 'dependencyLimits': c['dependencyLimits']} for c in registry['cases']]}
    elif a.command in ['source', 'case-source']:
        if a.command == 'case-source':
            registry = strict_json((ctx.root / 'source/special-scenes-8879120.json').read_bytes())
            cases = unique(registry['cases'])
            if a.case_id not in cases: raise ValueError('Unknown source case')
            case = cases[a.case_id]
            rows = [ctx.by_id[id] for id in case['unitIds']]
        else:
            rows = [u for u in ctx.units if u['asset'] == a.asset]
        if not rows or a.offset < 0 or a.offset >= len(rows) or not 1 <= a.max_chars <= 100000:
            raise ValueError('Source page bounds invalid')
        selected, size = [], 0
        for u in rows[a.offset:]:
            row = copy.deepcopy(u)
            if u['id'] in ctx.registry: row['encodedSource'] = ctx.registry[u['id']]
            if u['id'] in ctx.retained: row['technicalRetention'] = ctx.retained[u['id']]
            length = len(json.dumps(row, ensure_ascii=False))
            if size + length > a.max_chars:
                if not selected: raise ValueError('One complete row exceeds bound; increase --max-chars')
                break
            selected.append(row); size += length
        end = a.offset + len(selected)
        result = {'asset': a.asset if a.command == 'source' else a.case_id, 'total': len(rows), 'nextOffset': end if end < len(rows) else None, 'rows': selected}
        if a.command == 'case-source':
            result['contract'] = {k:case[k] for k in ['id', 'title', 'category', 'evidence', 'observed', 'invariants', 'dependencyLimits', 'analysisStatus']}
    elif a.command in ['glossary-check', 'case-check', 'validate-batch', 'assemble']:
        glossary = glossary_check(ctx, a.glossary_snapshot, a.master_root)
        result = {k:v for k,v in glossary.items() if k != 'targetEntries'}
        if a.command != 'glossary-check':
            ctx.shared_gate()
            label = next((r['term'] for r in glossary['targetEntries'] if r['id'] == 'roboheart'), None)
            if not label or strict_json(a.decisions.read_bytes()).get('targetNamebox') != label:
                raise ValueError('Encoded namebox differs from approved target glossary')
            result = case_gate(ctx, a.decisions, glossary['snapshotSha256'])
        if a.command == 'validate-batch':
            batch, pairs = validate_batch(ctx, a.batch)
            if batch['targetNamebox'] != label:
                raise ValueError('Encoded namebox differs from approved target glossary')
            if batch['glossarySnapshotSha256'] != glossary['snapshotSha256'] or batch['specialSceneDecisionsSha256'] != result['sha256']:
                raise ValueError('Batch prerequisites changed')
            result = {'status': 'passed-structural', 'units': len(pairs), 'editorial': 'pending'}
        elif a.command == 'assemble':
            pairs = authored(ctx, a.batch_dir)
            for path in a.batch_dir.glob('*.json'):
                b = strict_json(path.read_bytes())
                if b['glossarySnapshotSha256'] != glossary['snapshotSha256'] or b['specialSceneDecisionsSha256'] != result['sha256']:
                    raise ValueError('Assembly batch prerequisites changed')
                if b['targetNamebox'] != label:
                    raise ValueError('Encoded namebox differs from approved target glossary')
            result = assemble(ctx, pairs, ctx.output(a.output), a.yaml_module)
    elif a.command == 'progress':
        pairs = authored(ctx, a.batch_dir)
        retained = sum(u['id'] in ctx.retained for u,_ in pairs)
        delivery = 'not-verified'
        if a.build_dir:
            if not a.yaml_module:
                raise ValueError('--yaml-module required for actual delivered readback')
            if not a.build_dir.resolve().is_relative_to(ctx.locale_root.resolve()):
                raise ValueError('Build belongs to another locale')
            delivery = assemble(ctx, pairs, a.build_dir.resolve(), a.yaml_module, verify_only=True)
        result = {'siteLocale': ctx.locale, 'draftEdited': len(pairs)-retained, 'visibleDenominator': len(ctx.units)-len(ctx.retained),
            'technicalRetentions': retained, 'accountedDenominator': len(ctx.units), 'delivered': delivery,
            'editorial': 'pending-full-semantic-and-independent-diff', 'runtime': 'not-run'}
    else:
        if a.stage in ['scope', 'probe', 'source']:
            result = {'stage': a.stage, 'scope': 'established', 'probe': ctx.config['status'], 'source': ctx.manifest['sourceGate']}
        else:
            raise ValueError('Stage gate unmet: ' + a.stage + '; see PROCESS.md for required evidence. No acceptance inferred.')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
