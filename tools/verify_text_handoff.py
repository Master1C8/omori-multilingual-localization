#!/usr/bin/env python3
"""Bind every text occurrence to original source and test exact reinsertion."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import subprocess
from source_prepare import save_json, sha, strict_json
from verify_source_inventory import parse, compare_protected
from source_text_syntax import protected_parts, quick_macro_names, compare_text_controls
from text_resource_adapter import splice, literal_edit, exact_span_edit


def get(value, path):
    for key in path:
        value = value[key]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roles', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-typed-noop', type=Path,
                        help='Reuse unchanged full typed no-op evidence after a display-role-only refinement.')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve earlier validation evidence')
    root = Path(__file__).resolve().parent.parent
    base = root / 'source/inventory-8879120-01'
    manifest = strict_json((base / 'manifest.json').read_bytes())
    prior_path = root / 'source/inventory-8879120-01-verification.json'
    prior = strict_json(prior_path.read_bytes())
    if prior['status'] != 'passed' or prior['inventoryManifestRawSha256'] != sha((base / 'manifest.json').read_bytes()):
        raise ValueError('No unchanged complete extraction/no-op checkpoint')
    role_manifest = strict_json((args.roles / 'manifest.json').read_bytes())
    for name, expected in role_manifest['inputs'].items():
        if sha((root / name).read_bytes()) != expected:
            raise ValueError('Role evidence changed: ' + name)
    if role_manifest['originalPending']:
        raise ValueError('Original role gaps remain')
    units = strict_json((args.roles / 'visible-occurrences.json').read_bytes())
    if len({u['id'] for u in units}) != len(units):
        raise ValueError('Duplicate stable visible occurrence ID')
    params = strict_json((root / 'source/parameter-roles-8879120-01/parameters.json').read_bytes())
    macros = quick_macro_names(params)
    # The immutable game snapshot predates separate configuration discovery.
    # Pin the actual config before using it, then keep a project-local snapshot.
    config_raw = (Path(manifest['gameRoot']) / 'js/plugins.js').read_bytes()
    if sha(config_raw) != manifest['pluginConfigurationRawSha256']:
        raise ValueError('Original plugin configuration changed')
    config_text = config_raw.decode()
    config = strict_json(config_text[config_text.index('['):].strip().removesuffix(';'))
    programs = {}
    for path in ['source/classification-8879120-03/event-programs.json',
                 'source/note-programs-8879120-04/programs.json',
                 'source/embedded-programs-8879120-02/programs.json']:
        for p in strict_json((root / path).read_bytes()):
            if sha(p['source'].encode()) != p['rawSha256']:
                raise ValueError('Original program snapshot changed: ' + p['asset'])
            programs[p['asset']] = p
    reports = {r['asset']: r for r in strict_json((base / 'structured-assets.json').read_bytes())}
    cache = {}
    def original(asset):
        if asset == 'js/plugins.js':
            return config
        if asset not in cache:
            report = reports[asset]
            raw = gzip.decompress((base / report['snapshot']).read_bytes())
            cache[asset] = parse(asset, raw)
        return cache[asset]
    syntax, kinds, modified_programs, program_edits = {}, Counter(), {}, defaultdict(list)
    field_spans, field_owners, mapped = defaultdict(list), {}, []
    for unit in units:
        syntax[unit['id']] = protected_parts(unit['source'], macros)
        compare_text_controls(unit['source'], unit['source'], macros)
        kinds[unit['role']] += 1
        if 'spanUtf16' in unit:
            if unit['asset'] in programs:
                p = programs[unit['asset']]
                source = p['source']
                asset = p['originalAsset']
                if 'linePaths' in p:
                    recovered = ''.join(get(original(asset), path) + '\n' for path in p['linePaths'])
                elif 'spanCodepoints' in p and 'parentPath' in p:
                    a,b = p['spanCodepoints']
                    recovered = get(original(asset), p['parentPath'])[a:b]
                elif 'parentPath' in p:
                    recovered = get(original(asset), p['parentPath'])
                else:
                    raise ValueError('Unbound original program parent: ' + p['asset'])
                if recovered != source:
                    raise ValueError('Program-versus-original parent mismatch: ' + p['asset'])
            else:
                source = gzip.decompress((base / 'original' / (unit['asset'] + '.gz')).read_bytes()).decode()
            a,b = unit['spanUtf16']
            if source.encode('utf-16-le')[a*2:b*2].decode('utf-16-le') != unit['rawSource']:
                raise ValueError('Original UTF16 span mismatch: ' + unit['id'])
            if unit['role'] == 'visible-display-mapping':
                mapped.append(unit['id'])
                continue
            modified_programs[unit['asset']] = source
            program_edits[unit['asset']].append(literal_edit(unit, unit['source'], macros))
        elif 'span' in unit or 'spanCodepoints' in unit:
            field = get(original(unit['asset']), unit['path'])
            if 'parentValueSha256' in unit and sha(field.encode()) != unit['parentValueSha256']:
                raise ValueError('Original mixed field changed: ' + unit['id'])
            key = (unit['asset'], tuple(unit['path']))
            field_owners[key] = field
            field_spans[key].append(exact_span_edit(unit, unit['source'], macros))
        else:
            value = get(original(unit['asset']), unit['path'])
            if type(value) is not str or value != unit['source']:
                raise ValueError('Original scalar source mismatch: ' + unit['id'])
            if unit['role'] == 'visible-display-mapping':
                mapped.append(unit['id'])
    # Preserve each mixed field byte-for-byte on no-op reinsertion, while the
    # span primitive verifies all inter-span text rather than substring presence.
    for key, edits in field_spans.items():
        if splice(field_owners[key], edits) != field_owners[key]:
            raise ValueError('Mixed-field no-op reinsertion changed source')
    # Complete source-role acceptance reuses only unchanged full typed equality.
    # Verify actual saved no-op structures against the original; no allowlisted
    # hole can hide a different numeric, boolean, key or branch order here.
    structured = 0
    reused_typed = None
    if args.reuse_typed_noop:
        old_path = args.reuse_typed_noop / 'manifest.json'
        checkpoint = strict_json(old_path.read_bytes())
        if (checkpoint['status'] != 'passed' or checkpoint['structuredAssetsExactNoop'] != len(reports)
            or checkpoint['reusedFullOriginalValidationRawSha256'] != sha(prior_path.read_bytes())):
            raise ValueError('Typed checkpoint does not bind to unchanged original validation')
        old_units = strict_json((args.reuse_typed_noop / 'units.json').read_bytes())
        def binding(row):
            return {k:v for k,v in row.items() if k not in {'role','reason'}}
        if [binding(r) for r in old_units] != [binding(r) for r in units]:
            raise ValueError('Only display-role refinements may reuse full typed no-op evidence')
        structured = checkpoint['structuredAssetsExactNoop']
        reused_typed = {'manifest':str(old_path.resolve().relative_to(root)), 'rawSha256':sha(old_path.read_bytes()),
                        'reason':'Identical original source, stable IDs, scalar paths, spans and values; only display roles/reasons refined.'}
    else:
        for asset, report in reports.items():
            source = original(asset)
            no_op = parse(asset, gzip.decompress((base / report['result']).read_bytes()))
            compare_protected(source, no_op, {})
            structured += 1
    candidate_programs = []
    for asset, source in modified_programs.items():
        result = splice(source, program_edits[asset], utf16=True)
        if source.count('\n') != result.count('\n'):
            raise ValueError('Event-program physical line cardinality changed: ' + asset)
        candidate_programs.append({'asset':asset,'source':result,'rawSha256':sha(result.encode())})
    helper = root / 'tools/source_script_inventory.cjs'
    checked = subprocess.run(['node','--expose-internals',str(helper)],input=json.dumps(candidate_programs),text=True,capture_output=True,check=True)
    ast = strict_json(checked.stdout)
    if ast['errors']:
        raise ValueError('Reinserted source parse errors: ' + str(ast['errors'][:5]))
    # Validate actual parsed values of every reinserted editable JS literal.
    # IDs shift after quote encoding, so bind by per-program source order.
    target_values = defaultdict(list)
    for row in ast['strings']:
        target_values[row['asset']].append(row)
    for asset, source in modified_programs.items():
        edits = sorted(program_edits[asset], key=lambda e:e['span'][0])
        delta = 0
        by_span = {tuple(r['spanUtf16']):r for r in target_values[asset]}
        for edit in edits:
            a,b = edit['span']
            length = len(edit['replacement'].encode('utf-16-le')) // 2
            node = by_span.get((a+delta,a+delta+length))
            expected = next(u for u in units if u['id']==edit['id'])
            if node is None or node['source'] != expected['source']:
                raise ValueError('Reinserted literal value mismatch: ' + edit['id'])
            delta += length - (b-a)
    args.output.mkdir(parents=True)
    save_json(args.output / 'units.json', units)
    save_json(args.output / 'protected-text-parts.json', syntax)
    (args.output / 'original-plugins.js.gz').write_bytes(gzip.compress(config_raw,mtime=0))
    save_json(args.output / 'display-mapping-ids.json', mapped)
    report = {'schemaVersion':1,'status':'passed','sourceGate':'accepted-text-inventory',
              'steamBuild':'8879120','visibleOccurrences':len(units),
              'distinctVisibleSourceValues':len({u['source'] for u in units}),
              'roles':dict(kinds),'structuredAssetsExactNoop':structured,
              'modifiedProgramNoopParseChecks':len(candidate_programs),
              'modifiedLiteralValueChecks':sum(map(len,program_edits.values())),
              'mixedFieldNoopChecks':len(field_spans),'originalDisplayMappingIdentitiesPreserved':len(mapped),
              'runtime':'not-run','translationUnitsAuthored':0,
              'roleManifestRawSha256':sha((args.roles / 'manifest.json').read_bytes()),
              'reusedFullOriginalValidationRawSha256':sha(prior_path.read_bytes()),
              'reusedTypedNoopCheckpoint':reused_typed,
              'recipeRawSha256':sha(Path(__file__).read_bytes()),
              'recipeHashes':{p.name:sha(p.read_bytes()) for p in [helper, root/'tools/text_resource_adapter.py',root/'tools/source_text_syntax.py']},
              'fileHashes':{p.name:sha(p.read_bytes()) for p in args.output.iterdir() if p.is_file()},
              'limits':['This verifies extraction, exact no-op reinsertion and the actual static AST output boundary.',
                        'Predetermined display mappings still need game integration without altering logical identities.',
                        'Original anomalies remain unchanged; no loader/game/renderer/save boundary was exercised.',
                        'Texture/image text is excluded by owner. All semantic/editorial translation audits remain unstarted.']}
    save_json(args.output / 'manifest.json', report)
    print({k:report[k] for k in ['status','sourceGate','visibleOccurrences','structuredAssetsExactNoop','modifiedProgramNoopParseChecks','modifiedLiteralValueChecks','mixedFieldNoopChecks','originalDisplayMappingIdentitiesPreserved']})


if __name__ == '__main__':
    main()
