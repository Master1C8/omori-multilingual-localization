#!/usr/bin/env python3
"""Bind nested command strings, retaining dual-use logical identities."""
import argparse
from collections import Counter
from pathlib import Path
from classify_event_literals import role
from source_prepare import save_json, sha, strict_json


def classify(row, program):
    decision = role(row)
    if decision[0] != 'needs-role-review':
        return decision
    ctx = row['context']
    if ctx.get('callMethod') in {'setImage', 'albumHasPicture', 'contains', 'isTriggered', 'isCutsceneSkippable'}:
        return 'preserve-exactly', 'Native graphic, album/cutscene identity, matching or input operand.'
    if ctx.get('callMethod') == 'value' and (ctx.get('call') or '').startswith('$gameSelfSwitches.'):
        return 'preserve-exactly', 'Native self-switch alphabet key.'
    if ctx.get('assignmentTarget') == 'this._alertSound':
        return 'preserve-exactly', 'Event chase alert audio resource.'
    if program['kind'] == 'variable-script-operand' and ctx.get('parentType') == 'ExpressionStatement':
        var_id, end_id = program['commandParameters'][:2]
        if var_id != end_id:
            return 'needs-role-review', 'Multiple-variable assignment needs separate display/control binding.'
        asset = program['originalAsset']
        if ((asset == 'data/Map169.KEL' and 101 <= var_id <= 108) or
            (asset == 'data/Map343.KEL' and var_id == 102) or
            (asset == 'data/Map179.KEL' and var_id == 1001) or
            (asset == 'data/Troops.KEL' and var_id == 1003)):
            return 'visible-display-mapping', 'Dynamic word/name shown through native variable escape; original assignment and comparison values remain exact. Produce a predetermined display mapping, without mutating state.'
        if var_id in {11, 25, 30, 43, 141, 144, 255}:
            return 'preserve-exactly', 'Bound event direction, picture/atlas, balloon or battleback resource variable; not wording.'
    return 'needs-role-review', 'Nested script consumer not bound.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('programs', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve earlier classification')
    programs = {p['asset']: p for p in strict_json((args.programs / 'programs.json').read_bytes())}
    ast_path = args.programs / 'ast.json'
    ast = strict_json(ast_path.read_bytes())
    rows, counts = [], Counter()
    for original in ast['strings']:
        row = dict(original)
        program = programs[row['asset']]
        row['role'], row['reason'] = classify(row, program)
        row['originalAsset'], row['parentPath'] = program['originalAsset'], program['parentPath']
        row['programKind'] = program['kind']
        if row['role'] == 'visible-display-mapping':
            row['assignmentVariableRange'] = program['commandParameters'][:2]
            row['originalProgramPreserved'] = True
        rows.append(row)
        counts[row['role']] += 1
    save_json(args.output, {'schemaVersion': 1, 'roles': dict(counts), 'strings': rows,
                          'inputAstRawSha256': sha(ast_path.read_bytes()),
                          'recipeRawSha256': sha(Path(__file__).read_bytes()),
                          'originalAnomaliesPreserved': ast['errors'], 'sourceGate': 'needs-review',
                          'runtime': 'not-run'})
    pending = [r for r in rows if r['role'] == 'needs-role-review']
    print({'roles': dict(counts), 'pending': [{'id': r['id'], 'source': r['source']} for r in pending[:10]]})


if __name__ == '__main__':
    main()
