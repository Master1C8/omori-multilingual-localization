"""Reproduce every native catalog-to-password writer from pinned programs."""
import argparse
import json
import re
from pathlib import Path
from script_resource_adapter import at, original_resource, programs, recover_program
from source_prepare import sha, strict_json, save_json
from source_name_variable_bindings import REGISTRIES

ASSIGN = re.compile(r'\$gameVariables\.setValue\((10[1-8]), LanguageManager\.getMessageData\("XX_MELON\.message_(\d+)"\)\.text\)\n')


def collect(root):
    known = programs(root)
    units = strict_json((root/'source/text-corpus-8879120-02/units.json').read_bytes())
    catalog = {u['path'][0]: u for u in units
               if u['asset'] == 'languages/en/XX_MELON.HERO' and u['path'][-1] == 'text'}
    tokens = {}
    for u in units:
        rec = known.get(u['asset'])
        if not rec or rec['originalAsset'] != 'data/Map169.KEL' or rec.get('kind') != 'variable-script-operand':
            continue
        if rec['parentPath'][:5] != ['events', 6, 'pages', 2, 'list']:
            continue
        key = (rec['commandParameters'][0], u['source'])
        if u['role'] == 'visible-display-mapping' and 101 <= key[0] <= 108:
            if key in tokens: raise ValueError('Ambiguous native password token')
            tokens[key] = u['id']
    owners = {'data/Map169.KEL':['events', 6, 'pages', 0, 'list'],
              'data/Map006.KEL':['events', 42, 'pages', 0, 'list']}
    trees = {asset:original_resource(root, asset)[1] for asset in owners}
    result = []; assignments = 0
    for rec in known.values():
        if not re.search(r'XX_MELON\.message_(?:2[7-9]|[34][0-9])\b', rec['source']):
            continue
        hits = list(ASSIGN.finditer(rec['source']))
        if not hits: continue
        if ''.join(m.group(0) for m in hits) != rec['source']:
            raise ValueError('Password writer has unreviewed side effects')
        asset = rec['originalAsset']
        if asset not in owners or rec['linePaths'][0][:5] != owners[asset]:
            raise ValueError('Unreviewed alternate password writer')
        tree = trees[asset]
        recover_program(rec, tree)
        path = rec['linePaths'][0][:-2]; command = at(tree, path)
        source_commands = [at(tree, p[:-2]) for p in rec['linePaths']]
        labels = []
        for m in hits:
            variable, number = map(int, m.groups())
            if not 27 <= number <= 46: raise ValueError('Unknown password catalog key')
            unit = catalog['message_'+str(number)]
            labels.append({'variableId':variable, 'unitId':tokens[(variable, unit['source'])],
                           'catalogUnitId':unit['id']})
        assignments += len(labels)
        result.append({'asset':asset, 'commandPath':path, 'code':355,
                       'parameters':json.dumps(command['parameters'], ensure_ascii=False, separators=(',', ':')),
                       'sourceCommands':source_commands, 'passwordCatalog':True, 'labels':labels,
                       'sourceProgram':rec['asset'], 'sourceProgramSha256':rec['rawSha256']})
    if len(result) != 42 or assignments != 48 or len(tokens) != 24:
        raise ValueError('Both password writer topologies need reconciliation')
    return {'status':'source-bound', 'count':42, 'assignments':48, 'bindings':result,
            'registryProgramsExamined':len(known),
            'registrySha256':{p:sha((root/p).read_bytes()) for p in REGISTRIES},
            'unitsSha256':sha((root/'source/text-corpus-8879120-02/units.json').read_bytes()),
            'recipeSha256':sha(Path(__file__).read_bytes())}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    if args.output.exists(): raise ValueError('Preserve prior source evidence')
    result=collect(root);save_json(args.output,result)
    print({'commands':result['count'],'assignments':result['assignments'],
           'programsExamined':result['registryProgramsExamined']})


if __name__=='__main__':main()
