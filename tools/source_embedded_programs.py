#!/usr/bin/env python3
"""Parse omitted typed RPG command programs; never execute original code."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import subprocess
from source_prepare import identity, save_json, sha, strict_json


def discover(value, asset, path=()):
    if isinstance(value, dict):
        code, parameters = value.get('code'), value.get('parameters')
        if isinstance(parameters, list):
            slots = []
            if code == 45:
                slots = [(0, 'move-route-script')]
            elif code == 111 and parameters[:1] == [12]:
                slots = [(1, 'conditional-script')]
            elif code == 122 and len(parameters) > 4 and parameters[3] == 4:
                slots = [(4, 'variable-script-operand')]
            for slot, kind in slots:
                if len(parameters) <= slot or not isinstance(parameters[slot], str):
                    raise ValueError('Typed command has unexpected script operand: ' + identity(asset, path))
                source = parameters[slot]
                yield {'asset': identity(asset, path + ('parameters', slot)) + '@' + kind,
                       'originalAsset': asset, 'parentPath': list(path + ('parameters', slot)),
                       'source': source, 'kind': kind, 'rawSha256': sha(source.encode()),
                       'commandCode': code, 'commandParameters': parameters}
            if code == 356 and parameters and isinstance(parameters[0], str):
                match = re.fullmatch(r'Wait For Condition (.+)', parameters[0], re.I)
                if match:
                    source = match[1]
                    yield {'asset': identity(asset, path + ('parameters', 0)) + '@wait-condition',
                           'originalAsset': asset, 'parentPath': list(path + ('parameters', 0)),
                           'spanCodepoints': [match.start(1), match.end(1)], 'source': source,
                           'kind': 'plugin-wait-condition', 'rawSha256': sha(source.encode())}
        for key, child in value.items():
            yield from discover(child, asset, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from discover(child, asset, path + (index,))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-ast', type=Path, help='Reuse an unchanged complete first-pass parse; reclassify native route grammar.')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve earlier evidence')
    programs = []
    for asset in strict_json((args.inventory / 'structured-assets.json').read_bytes()):
        if asset['asset'].endswith('.KEL'):
            raw = gzip.decompress((args.inventory / asset['snapshot']).read_bytes())
            programs.extend(discover(strict_json(raw), asset['asset']))
    args.output.mkdir(parents=True)
    save_json(args.output / 'programs.json', programs)
    helper = Path(__file__).with_name('source_script_inventory.cjs')
    if args.reuse_ast:
        earlier = strict_json((args.reuse_ast / 'programs.json').read_bytes())
        if [(p['asset'], p['source']) for p in earlier] != [(p['asset'], p['source']) for p in programs]:
            raise ValueError('Reusable AST program identity/source mismatch')
        ast = strict_json((args.reuse_ast / 'ast.json').read_bytes())
    else:
        result = subprocess.run(['node', '--expose-internals', str(helper)], input=json.dumps(programs),
                                text=True, capture_output=True, check=True)
        ast = strict_json(result.stdout)
    # Exact owning source predicates take precedence over native JS eval in
    # code45. No prose is classified from the apparent English of this DSL.
    native_patterns = []
    for name in ['YEP_MoveRouteCore', 'YEP_X_ExtMovePack1']:
        asset_name = 'js/plugins/' + name + '.OMORI'
        source = gzip.decompress((args.inventory / 'original' / (asset_name + '.gz')).read_bytes()).decode()
        marker = 'Game_Character.prototype.processMoveRouteScriptCall = function(line) {'
        start = source.index(marker)
        end = source.index('\n};', start)
        for pattern in re.findall(r'line\.match\(/(.+?)/i\)', source[start:end]):
            native_patterns.append({'asset': asset_name, 'pattern': pattern, 'sourceRawSha256': sha(source.encode())})
    native = []
    for p in programs:
        if p['kind'] != 'move-route-script':
            continue
        matched = next((v for v in native_patterns if re.search(v['pattern'], p['source'], re.I)), None)
        if matched:
            if matched['pattern'].startswith(('EVAL:', '(?:SELF VARIABLE)')):
                raise ValueError('Native route DSL contains nested eval; add a separate span adapter before acceptance')
            native.append({'id': p['asset'], 'source': p['source'], 'role': 'preserve-exactly',
                           'consumer': matched, 'reason': 'Exact native movement/balloon/switch DSL predicate'})
    native_ids = {v['id'] for v in native}
    # All other failed sources stay original anomalies, visibly accounted for.
    original_errors = ast['errors']
    ast['errors'] = [v for v in original_errors if v['asset'] not in native_ids]
    ast['strings'] = [v for v in ast['strings'] if v['asset'] not in native_ids]
    save_json(args.output / 'native-route-roles.json', native)
    save_json(args.output / 'native-route-grammar.json', native_patterns)
    save_json(args.output / 'ast.json', ast)
    report = {'schemaVersion': 1, 'programKinds': dict(Counter(p['kind'] for p in programs)),
              'programs': len(programs), 'parseErrors': ast['errors'], 'strings': len(ast['strings']),
              'nativeRoutePrograms': len(native), 'firstPassJavaScriptParseErrors': len(original_errors),
              'displayCalls': len(ast['displayCalls']), 'sourceGate': 'needs-review', 'runtime': 'not-run',
              'recipeRawSha256': sha(Path(__file__).read_bytes()), 'parserRawSha256': sha(helper.read_bytes())}
    save_json(args.output / 'manifest.json', report)
    print(json.dumps(dict(report, parseErrors=len(report['parseErrors'])), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
