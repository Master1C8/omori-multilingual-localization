#!/usr/bin/env python3
"""Check source bindings and select special-scene context; never certify adaptation."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / 'source/special-scenes-8879120.json'


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_pairs)


def validate(path=DEFAULT):
    data = read(path)
    if data['schemaVersion'] != 1 or data['game'] != 'omori':
        raise ValueError('Unexpected registry identity')
    evidence = [{'path': p, 'sha256': h} for p, h in data['sourceBindings'].items()]
    corpus_path = 'source/text-corpus-8879120-02/units.json'
    if corpus_path not in data['sourceBindings']:
        raise ValueError('Unbound source corpus')
    units = read(ROOT / corpus_path)
    ids = [u['id'] for u in units]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source occurrence ID')
    known = set(ids)
    seen = set()
    for case in data['cases']:
        if case['id'] in seen:
            raise ValueError('Duplicate case ID: ' + case['id'])
        seen.add(case['id'])
        members = case['unitIds']
        if not members or len(members) != len(set(members)) or set(members) - known:
            raise ValueError('Invalid source membership: ' + case['id'])
        for key in ('title', 'category', 'observed', 'invariants', 'dependencyLimits', 'evidence'):
            if not case[key]:
                raise ValueError('Missing case contract: ' + case['id'] + '/' + key)
        for key in ('adaptationRoute', 'status', 'acceptanceScenarios'):
            if not case['ru'][key]:
                raise ValueError('Missing adaptation contract: ' + case['id'] + '/' + key)
        if any(not e.get('locator') for e in case['evidence']):
            raise ValueError('Missing evidence locator: ' + case['id'])
        evidence.extend(case['evidence'])
        evidence.extend(case['ru'].get('existingEvidence', []))
    for item in evidence:
        p = (ROOT / item['path']).resolve()
        if not p.is_relative_to(ROOT) or not p.is_file():
            raise ValueError('Missing/out-of-project evidence: ' + item['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Stale evidence: ' + item['path'])
    return data, known


def index(data):
    rows = ['# OMORI special-scene registry', '',
            'Source build 8879120; source English; current adaptation notes Russian.', '',
            'Canonical data: [special-scenes-8879120.json](special-scenes-8879120.json).',
            'This generated index is not a second source of truth. Regenerate with',
            '`python3 -B tools/special_scene_registry.py --write-index`.', '',
            '**Discovery is targeted, not exhaustive. Registration is not adaptation acceptance.**',
            f"The registry binds {len(data['cases'])} identified cases covering "
            f"{len({i for c in data['cases'] for i in c['unitIds']})} distinct source units; "
            'pending coverage is recorded in its coverage field.',
            'All runtime checks remain not-run. Registry tooling does not launch the game or alter installed assets.', '',
            '| ID | Case | Source units | Category |', '| --- | --- | ---: | --- |']
    for c in data['cases']:
        rows.append(f"| {c['id']} | {c['title']} | {len(c['unitIds'])} | {c['category']} |")
    rows += ['', '## Use', '',
             '- Check hashes and membership: `python3 -B tools/special_scene_registry.py`.',
             '- Read one full case: `python3 -B tools/special_scene_registry.py --case OMORI-SP002`.',
             '- Select cases for authored IDs: `python3 -B tools/special_scene_registry.py --batch PATH`.',
             '- Read selected complete semantic groups before authoring; preserve their dependencies.', '',
             'The checker validates linkage and emits applicable context. It does not automatically',
             'discover literary devices, run gameplay or enforce adapters inside translation_batch.py.',
             'Case statuses and acceptance scenarios govern manual review and future integration.', '',
             '## Known source gate impact', '', data['sourceGateImpact']['observed'], '',
             data['sourceGateImpact']['required'], '',
             'The existing 19,944-case pizza assembly receipt remains scoped to sentence generation;',
             'it does not exercise the word-sprite renderer. Do not discard that valid evidence or',
             'treat it as proof of image lookup, layout or playability.', '']
    rows += ['The current pizza text adapter has a separate isolated 19,944-case test with',
             'final-font static advances and background-only image requests. It replaces the',
             'word-sprite presentation without editing images. Actual Canvas/game appearance',
             'remains not-run; see OMORI-SP002 for current source-bound evidence.', '']
    return '\n'.join(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', type=Path, default=DEFAULT)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--case')
    group.add_argument('--batch', type=Path)
    group.add_argument('--write-index', action='store_true')
    args = p.parse_args()
    data, known = validate(args.registry)
    if args.write_index:
        if args.registry.resolve() != DEFAULT.resolve():
            raise ValueError('Index generation requires the canonical registry')
        DEFAULT.with_suffix('.md').write_text(index(data))
        print('Generated canonical registry index.')
        return
    cases = data['cases']
    if args.case:
        cases = [c for c in cases if c['id'] == args.case]
        if not cases:
            raise ValueError('Unknown case: ' + args.case)
    if args.batch:
        batch = read(args.batch)
        ids = [e['id'] for e in batch['entries']]
        if len(ids) != len(set(ids)) or set(ids) - known:
            raise ValueError('Invalid batch occurrence IDs')
        cases = [c for c in cases if set(c['unitIds']) & set(ids)]
        print(json.dumps([{'id': c['id'], 'title': c['title'],
                           'matchedUnits': len(set(c['unitIds']) & set(ids)),
                           'groupUnits': len(c['unitIds']), 'status': c['ru']['status'],
                           'adaptationRoute': c['ru']['adaptationRoute'],
                           'readGroup': '--case ' + c['id']} for c in cases],
                         ensure_ascii=False, indent=2))
    elif args.case:
        print(json.dumps(cases, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({'linkage': 'passed', 'cases': len(cases),
                         'distinctUnits': len({i for c in cases for i in c['unitIds']}),
                         'discovery': data['coverage']['status'],
                         'sourceGateImpact': data['sourceGateImpact']['status'],
                         'adaptationReadiness': 'not-certified'}, indent=2))


if __name__ == '__main__':
    main()
