"""Reproduce native name-variable provenance from pinned programs, without execution."""
import argparse
import json
import re
from pathlib import Path

from script_resource_adapter import at, original_resource, programs, recover_program
from source_prepare import sha, strict_json


REGISTRIES = [
    'source/classification-8879120-03/event-programs.json',
    'source/note-programs-8879120-04/programs.json',
    'source/embedded-programs-8879120-02/programs.json',
]


def collect(root):
    known = programs(root)
    originals = {}
    families = [[], [], []]
    for record in known.values():
        source = record['source']
        match = re.fullmatch(
            r'// set variable 49 to name of item\n'
            r'\$gameVariables\.setValue\(49, \$data(Items|Weapons|Armors)\[(\d+)\]\.name\);?\n',
            source)
        troop = re.fullmatch(r'\$gameTroop\.members\(\)\[(\d+)\]\.name\(\);?', source)
        if match:
            descriptor = {'kind': 'database', 'database': match[1],
                          'recordId': int(match[2]), 'variableId': 49}
            family = 0
            path = record['linePaths'][0][:-2]
        elif record.get('kind') == 'variable-script-operand' and source == 'this._gachaItem.name.toUpperCase();':
            descriptor = {'kind': 'gacha-item', 'upper': True,
                          'variableId': record['commandParameters'][0]}
            family = 1
            path = record['parentPath'][:-2]
        elif record.get('kind') == 'variable-script-operand' and troop:
            descriptor = {'kind': 'troop-member', 'index': int(troop[1]),
                          'variableId': record['commandParameters'][0]}
            family = 2
            path = record['parentPath'][:-2]
        else:
            continue
        asset = record['originalAsset']
        if asset not in originals:
            originals[asset] = original_resource(root, asset)[1]
        original = originals[asset]
        recover_program(record, original)
        command = at(original, path)
        if family == 0:
            if command['code'] != 355:
                raise ValueError('Database name writer is not a native script command')
        elif command['code'] != 122 or command['parameters'][:4] != [descriptor['variableId'], descriptor['variableId'], 0, 4]:
            raise ValueError('Name operand does not assign exactly one variable')
        families[family].append({
            'asset': asset, 'commandPath': path, 'code': command['code'],
            'parameters': json.dumps(command['parameters'], ensure_ascii=False, separators=(',', ':')),
            'dynamicName': descriptor, 'sourceProgram': record['asset'],
            'sourceProgramSha256': record['rawSha256'],
        })
    bindings = [row for family in families for row in family]
    identities = [(row['asset'], tuple(row['commandPath'])) for row in bindings]
    if len(set(identities)) != len(identities):
        raise ValueError('Multiple name descriptors target the same native command')
    return {'status': 'source-bound', 'count': len(bindings), 'bindings': bindings,
            'registryProgramsExamined': len(known),
            'registrySha256': {name: sha((root / name).read_bytes()) for name in REGISTRIES},
            'recipeSha256': sha(Path(__file__).read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = collect(root)
    if args.compare:
        prior = strict_json(args.compare.read_bytes())
        if result['bindings'] != prior['bindings']:
            raise ValueError('Reproduced binding list differs from reviewed evidence')
        result['reviewedEvidence'] = {'path': str(args.compare), 'sha256': sha(args.compare.read_bytes()),
                                     'bindingsEqual': True}
    output = args.output.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Output must be a new file inside the canonical project')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'bindings': result['count'],
                      'programsExamined': result['registryProgramsExamined']}))


if __name__ == '__main__':
    main()
