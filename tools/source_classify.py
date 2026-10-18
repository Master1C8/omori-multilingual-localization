#!/usr/bin/env python3
"""Bounded role decisions and missing mixed-source discovery, shared by locales."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import subprocess

from source_prepare import canonical, identity, save_json, sha, strict_json, strict_yaml

TILED_KEYS = {'name', 'type', 'orientation', 'renderorder', 'tiledversion', 'source', 'image', 'draworder'}
TILED_PROPERTIES = {'priority', 'zIndex', 'collision', 'regionId', 'hideOnLevel', 'level', 'arrowImpassable', 'flags'}


def decide(row):
    path, asset = row.get('path', []), row['asset']
    if asset.endswith('.AUBREY'):
        if path[-1] in TILED_KEYS or any(k in path for k in ('propertytypes', 'tilepropertytypes')):
            return 'preserve-exactly', 'Tiled importer metadata/enum/resource/label, not a text object; YED_Tiled original consumer.'
        if 'tileproperties' in path and path[-1] in TILED_PROPERTIES:
            return 'preserve-exactly', 'Tile collision/arrow control consumed by YED_Tiled lines 1319–1322, 1393–1394, 1539–1542.'
        if 'properties' in path:
            pos = path.index('properties')
            if path[-1] in TILED_PROPERTIES or (pos + 1 < len(path) and isinstance(path[pos + 1], int) and path[-1] in {'name', 'type', 'value'}):
                return 'preserve-exactly', 'Tiled collision/layer/rendering property; preserve even numeric-looking strings.'
    if asset.endswith('/XX_BLUE.HERO') and path[0] == 'Yin_Blackjack':
        return 'visible', 'Blackjack display labels separate from command symbols; original plugin lines 793–797, 879, 926–930, 1120.'
    if asset.endswith('/XX_BLUE.HERO') and path[0] == 'World_Currency_Unit':
        return 'preserve-exactly', 'Currency display symbols C/$ remain original symbols; Omori BASE drawCurrencyValue consumes this table.'
    if asset.endswith('/System.HERO') and path[0] == 'InputNames':
        return 'preserve-exactly', 'Input table used for validity and internal option.name; actual controls draw icons (Options lines 1444–1448, 1495–1512, 1631).'
    code = row.get('context', {}).get('commandCode')
    if code == 111:
        return 'preserve-exactly', 'Conditional-branch operand, including input symbols and script predicates; dynamic side effects still require mixed-script review.'
    if code == 356:
        text = row['source']
        if re.fullmatch(r'ShowMessage\s+[\w-]+\.message_\w+', text):
            return 'preserve-exactly', 'ShowMessage dispatcher plus exact catalog reference (Text_Language_Processor).'
        if re.fullmatch(r'AddChoice\s+[\w-]+\.message_\w+\s+\S+', text):
            return 'preserve-exactly', 'AddChoice catalog reference and jump label; visible option is catalog text.'
        if re.fullmatch(r'ShowChoices\s+-?\d+', text):
            return 'preserve-exactly', 'ShowChoices cancellation/branch control integer.'
    return None


def command_lists(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'list' and isinstance(child, list) and all(isinstance(c, dict) and 'code' in c for c in child):
                yield path + (key,), child
            else:
                yield from command_lists(child, path + (key,))
    elif isinstance(value, list):
        for ix, child in enumerate(value):
            yield from command_lists(child, path + (ix,))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-mixed-sources', type=Path,
                        help='Reuse unchanged, hash-verified event/parameter evidence from a prior classification.')
    args = parser.parse_args()
    base, out = args.inventory.resolve(), args.output.resolve()
    project = Path(__file__).resolve().parent.parent
    if out.exists() or project not in out.parents:
        raise ValueError('Choose a new immutable classification output in the canonical project')
    manifest = strict_json((base / 'manifest.json').read_bytes())
    out.mkdir(parents=True)
    overrides, resolved, remaining, visible = [], Counter(), Counter(), 0
    with (out / 'remaining.jsonl').open('w') as pending:
        for line in (base / 'unresolved.jsonl').open():
            row = strict_json(line)
            result = decide(row)
            if result:
                role, reason = result
                overrides.append({'id': row['id'], 'originalSourceValueSha256': row['sourceValueSha256'],
                                  'role': role, 'reason': reason})
                resolved[role] += 1
                visible += role == 'visible'
            else:
                pending.write(line)
                remaining[Path(row['asset']).suffix] += 1
    save_json(out / 'decisions.json', overrides)
    if args.reuse_mixed_sources:
        previous = args.reuse_mixed_sources.resolve()
        evidence = strict_json((previous / 'manifest.json').read_bytes())
        if evidence['parentManifestRawSha256'] != sha((base / 'manifest.json').read_bytes()):
            raise ValueError('Reused mixed-source evidence belongs to another inventory')
        for name in ['event-programs.json', 'event-program-ast.json', 'plugin-parameters.json']:
            raw = (previous / name).read_bytes()
            if sha(raw) != evidence['fileHashes'][name]:
                raise ValueError('Reused mixed-source evidence bytes changed: ' + name)
        summary = {'schemaVersion': 1, 'parentInventory': str(base.relative_to(project)),
                   'parentManifestRawSha256': sha((base / 'manifest.json').read_bytes()),
                   'resolvedExistingRoles': dict(resolved), 'existingRemainingByFormat': dict(remaining),
                   'mixedSourcesReusedFrom': str(previous.relative_to(project)),
                   'mixedSourceManifestRawSha256': sha((previous / 'manifest.json').read_bytes()),
                   'sourceGate': 'needs-review', 'recipeRawSha256': sha(Path(__file__).read_bytes()),
                   'fileHashes': {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
        save_json(out / 'manifest.json', summary)
        print(json.dumps(summary, indent=2))
        return
    # Reconstruct the exact engine command355 + consecutive command655 script
    # boundaries. Individual lines are not separately parseable programs.
    programs = []
    for report in strict_json((base / 'structured-assets.json').read_bytes()):
        if not report['asset'].endswith('.KEL'):
            continue
        raw = gzip.decompress((base / report['snapshot']).read_bytes())
        value = strict_json(raw)
        for path, commands in command_lists(value):
            for ix, command in enumerate(commands):
                if command['code'] != 355:
                    continue
                lines = [command['parameters'][0]]
                locations = [list(path + (ix, 'parameters', 0))]
                j = ix + 1
                while j < len(commands) and commands[j]['code'] == 655:
                    lines.append(commands[j]['parameters'][0])
                    locations.append(list(path + (j, 'parameters', 0)))
                    j += 1
                source = ''.join(line + '\n' for line in lines)
                programs.append({'asset': identity(report['asset'], path + (ix,)) + '@event-program',
                                 'originalAsset': report['asset'], 'linePaths': locations,
                                 'source': source, 'rawSha256': sha(source.encode())})
    save_json(out / 'event-programs.json', programs)
    result = subprocess.run(['node', '--expose-internals', str(project / 'tools/source_script_inventory.cjs')],
                            input=json.dumps(programs), text=True, capture_output=True, check=True)
    ast = strict_json(result.stdout)
    save_json(out / 'event-program-ast.json', ast)
    # Plugin configuration is a separate source surface. Earlier research
    # indexed only macro definitions with speaker labels, omitting other text.
    root = Path(manifest['gameRoot'])
    raw = (root / 'js/plugins.js').read_bytes()
    if sha(raw) != manifest['pluginConfigurationRawSha256']:
        raise ValueError('Plugin configuration version changed')
    text = raw.decode()
    config = strict_json(text[text.index('['):].strip().removesuffix(';'))
    from research_source import scalars
    params = []
    for ix, plugin in enumerate(config):
        for path, value, _ in scalars(plugin):
            if not isinstance(value, str):
                continue
            is_macro_text = plugin['status'] and plugin['name'].startswith('YEP_X_MessageMacros') and re.fullmatch(r'Macro \d+ Text', str(path[-1]))
            params.append({'id': identity('js/plugins.js', (ix,) + path), 'asset': 'js/plugins.js',
                           'path': [ix] + list(path), 'source': value, 'sourceValueSha256': sha(value.encode()),
                           'plugin': plugin['name'], 'enabled': plugin['status'],
                           'role': 'needs-role-review' if path[0] == 'parameters' and value.strip() else 'preserve-exactly',
                           'reason': 'Macro expansion may contain visible nameboxes' if is_macro_text else 'Plugin parameter grammar/consumer must be resolved before exclusion.'})
    save_json(out / 'plugin-parameters.json', params)
    final = {'schemaVersion': 1, 'parentInventory': str(base.relative_to(project)),
             'parentManifestRawSha256': sha((base / 'manifest.json').read_bytes()),
             'resolvedExistingRoles': dict(resolved), 'existingRemainingByFormat': dict(remaining),
             'newVisibleDiscoveries': visible, 'eventPrograms': len(programs),
             'eventProgramParseErrors': ast['errors'], 'eventStringLiterals': len(ast['strings']),
             'pluginParameters': len(params), 'pluginParametersPending': sum(p['role'] == 'needs-role-review' for p in params),
             'sourceGate': 'needs-review', 'runtime': 'not-run',
             'limits': ['Classification decisions are evidence-backed deltas, not final whole-corpus acceptance.',
                        'Event AST fragments retain exact program identity and original line paths.',
                        'Acorn parse errors need engine-context diagnosis; no original program was executed.'],
             'recipeHashes': {p.name: sha(p.read_bytes()) for p in [Path(__file__), project / 'tools/source_script_inventory.cjs']},
             'fileHashes': {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
    save_json(out / 'manifest.json', final)
    print(json.dumps({k: final[k] for k in ['resolvedExistingRoles', 'existingRemainingByFormat', 'newVisibleDiscoveries',
                                          'eventPrograms', 'eventStringLiterals', 'pluginParametersPending', 'sourceGate']}, indent=2))
    print('Event parse errors:', len(ast['errors']))


if __name__ == '__main__':
    main()
