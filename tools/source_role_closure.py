#!/usr/bin/env python3
"""Reconcile all original roles plus explicit mixed-source inventories.

This is source accounting, not translation or inventory acceptance. It keeps
every original occurrence and refuses an unclassified source boundary.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from source_prepare import save_json, sha, strict_json

CHOICE_DISPATCH = {'Hardware Shelf', 'DishList', 'JukeboxList'}


def catalog_override(row):
    if row['role'].startswith('visible') and row['asset'].startswith('data/') and row.get('path'):
        key = row['path'][-1]
        database = Path(row['asset']).stem
        if key == 'name' and database in {'Actors','Classes','Skills','Items','Weapons','Armors','Enemies','States'}:
            return 'visible-display-mapping', 'Database label also seeds native name/ID lookup and comparison tables. Preserve the original name field and author a display label bound to database kind and record ID.'
        if key == 'displayName':
            return 'visible-display-mapping', 'Map label also becomes saved location identity and native locale-conversion input. Preserve original displayName field and supply a mapped visible location label.'
    if row['asset'] == 'languages/en/sidequest_farawaytown_ginojukebox.HERO' and row.get('path'):
        path = row['path']
        if len(path) == 2 and path[1] == 'text' and path[0].startswith('message_') and path[0][8:].isdigit() and 20 <= int(path[0][8:]) <= 32:
            return 'preserve-exactly', 'Jukebox first-column catalog value is AudioManager.playBgm name; display label is the second catalog reference. Jukebox plugin lines34–47.'
    if row.get('context', {}).get('commandCode') in {102, 402} and row['source'] in CHOICE_DISPATCH:
        return 'preserve-exactly', 'setupChoices intercept dispatch marker; native handler substitutes actual visible choices. HardwareShop/HomeAlone/Jukebox owning plugins.'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve prior source ledger')
    root = Path(__file__).resolve().parent.parent
    base = root / 'source/inventory-8879120-01'
    delta = root / 'source/classification-8879120-03'
    plugin_path = root / 'source/plugin-literal-roles-8879120-09.json'
    plugin = {x['id']: x for x in strict_json(plugin_path.read_bytes())['strings']}
    decisions = {x['id']: x for x in strict_json((delta / 'decisions.json').read_bytes())}
    events = strict_json((delta / 'event-programs.json').read_bytes())
    event_lines = {p['originalAsset'] + '#' + json.dumps(path, ensure_ascii=False, separators=(',', ':'))
                   for p in events for path in p['linePaths']}
    args.output.mkdir(parents=True)
    counts, extra, omitted, visible = Counter(), [], [], []
    technical_changes, pending = [], []
    with (args.output / 'occurrences.jsonl').open('w') as output:
        for line in (base / 'occurrences.jsonl').open():
            row = strict_json(line)
            identity = row['id']
            if identity in plugin:
                assert row['sourceValueSha256'] == plugin[identity]['sourceValueSha256']
                row = plugin[identity]
            elif identity in decisions:
                original = decisions[identity]
                assert row['sourceValueSha256'] == original['originalSourceValueSha256']
                row['role'], row['reason'] = original['role'], original['reason']
            override = catalog_override(row)
            if override:
                row['role'], row['reason'] = override
                technical_changes.append(row)
            if row['role'] == 'needs-role-review':
                code = row.get('context', {}).get('commandCode')
                if identity in event_lines:
                    row['role'], row['reason'] = 'mixed-program', 'Complete command355/655 boundary and all string literal roles are separately inventoried; untranslated program syntax stays exact.'
                elif row.get('path', [])[-1:] == ['note']:
                    row['role'], row['reason'] = 'mixed-note', 'Native notetag/action metadata stays exact. All declared JS blocks/eval slots and BlackLetterClue spans are separately inventoried.'
                elif code == 122:
                    row['role'], row['reason'] = 'mixed-program', 'Typed variable-script operand, separately parsed; dual-use display mappings preserve original assignment/comparison values.'
                elif code == 356:
                    row['role'], row['reason'] = 'preserve-exactly', 'Native plugin-command invocation: resource/control/reference syntax, not an editable display field. Embedded Wait For Condition expressions are separately parsed; original unknown/invalid dispatch remains exact.'
            if row['role'] == 'needs-role-review':
                pending.append(row)
            counts[row['role']] += 1
            if row['role'].startswith('visible'):
                visible.append(row)
            output.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    save_json(args.output / 'catalog-technical-decisions.json', technical_changes)
    save_json(args.output / 'pending.json', pending)
    # Separate stable occurrences preserve context; identical text is never
    # silently deduplicated into one editorial decision.
    additions = [
        ('source/event-literal-roles-8879120-04.json', 'event'),
        ('source/note-literal-roles-8879120-03.json', 'note'),
        ('source/embedded-literal-roles-8879120-01.json', 'embedded')]
    for path, kind in additions:
        for row in strict_json((root / path).read_bytes())['strings']:
            if row['role'].startswith('visible'):
                extra.append(dict(row, component=kind))
    params_path = root / 'source/parameter-roles-8879120-01/parameters.json'
    for row in strict_json(params_path.read_bytes()):
        if row['role'] == 'visible':
            extra.append(dict(row, component='parameter'))
    macros_path = root / 'source/macro-roles-8879120-01/macros.json'
    for row in strict_json(macros_path.read_bytes()):
        for part in row['parts']:
            if part['role'] == 'visible':
                extra.append(dict(part, asset=row['asset'], path=row['path'], component='macro'))
    save_json(args.output / 'visible-occurrences.json', visible + extra)
    inputs = [base / 'manifest.json', delta / 'manifest.json', plugin_path,
              params_path, macros_path] + [root / p for p, _ in additions]
    report = {'schemaVersion': 1, 'steamBuild': '8879120', 'sourceLocale': 'en',
              'scope': 'All extracted structured/enabled-script text; images/textures/OCR excluded by owner.',
              'originalOccurrences': sum(counts.values()), 'originalRoles': dict(counts),
              'originalPending': len(pending), 'visibleOccurrences': len(visible) + len(extra),
              'distinctVisibleSourceValues': len({r['source'] for r in visible + extra}),
              'additionalVisibleComponents': dict(Counter(r['component'] for r in extra)),
              'reclassifiedCatalogTechnicalOccurrences': len(technical_changes),
              'sourceGate': 'needs-reinsertion-binding-and-control-validation',
              'translationUnitsAuthored': 0, 'runtime': 'not-run',
              'inputs': {str(p.relative_to(root)): sha(p.read_bytes()) for p in inputs},
              'recipeRawSha256': sha(Path(__file__).read_bytes()),
              'limits': ['Complete source-role accounting is not protected reinsertion acceptance or semantic quality.',
                         'Display-only mapping integration and exact native escape grammar still require verification.',
                         'Original anomalies remain unchanged; static classification does not establish reachability.']}
    save_json(args.output / 'manifest.json', report)
    print({k: report[k] for k in ['originalOccurrences','originalRoles','originalPending','visibleOccurrences','distinctVisibleSourceValues','additionalVisibleComponents','reclassifiedCatalogTechnicalOccurrences','sourceGate']})
    if pending:
        raise ValueError('Unclassified original source boundary remains')


if __name__ == '__main__':
    main()
