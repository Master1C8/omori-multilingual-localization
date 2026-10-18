#!/usr/bin/env python3
"""Expose JS fragments in original notetags without executing or translating them."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from source_prepare import save_json, sha, strict_json

JS_TAG = re.compile(r'(?:Custom (?:.* Effect|.* Condition|Requirement|.* Cost|Parameters)|Before Eval|After Eval|Post-Damage Eval|Damage Formula)', re.I)
OPEN = re.compile(r'^\s*<([^<>:/]+)>\s*$')
CLOSE = re.compile(r'^\s*</([^<>:]+)>\s*$')
EVAL = re.compile(r'^\s*eval\s*:\s*(.*)$', re.I)


def fragments(source):
    lines, offsets = source.splitlines(keepends=True), []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)
    ix = 0
    while ix < len(lines):
        stripped = lines[ix].rstrip('\r\n')
        opening = OPEN.fullmatch(stripped)
        if opening and JS_TAG.fullmatch(opening[1]):
            tag = opening[1]
            end = ix + 1
            while end < len(lines):
                closing = CLOSE.fullmatch(lines[end].rstrip('\r\n'))
                if closing and closing[1].casefold() == tag.casefold():
                    break
                # EquipCore recognizes repeated opening headers before it
                # appends parameterEval lines. Current originals use an opening
                # header twice; retain both and expose only the formula body.
                repeated = OPEN.fullmatch(lines[end].rstrip('\r\n'))
                if tag.casefold() == 'custom parameters' and repeated and repeated[1].casefold() == tag.casefold():
                    break
                end += 1
            if end == len(lines):
                if tag.casefold() == 'custom parameters':
                    start = offsets[ix] + len(lines[ix])
                    if start < len(source):
                        yield {'kind': 'notetag-js-block', 'tag': tag, 'spanCodepoints': [start, len(source)], 'source': source[start:]}
                    return
                yield {'kind': 'unclosed-block', 'tag': tag, 'spanCodepoints': [offsets[ix], len(source)], 'source': source[offsets[ix]:]}
                return
            start, stop = offsets[ix] + len(lines[ix]), offsets[end]
            yield {'kind': 'notetag-js-block', 'tag': tag, 'spanCodepoints': [start, stop], 'source': source[start:stop]}
            ix = end + 1
            continue
        match = EVAL.fullmatch(stripped)
        if match:
            start = offsets[ix] + match.start(1)
            stop = offsets[ix] + match.end(1)
            yield {'kind': 'action-sequence-eval', 'tag': 'eval', 'spanCodepoints': [start, stop], 'source': source[start:stop]}
        ix += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    if args.output.exists() or project not in args.output.resolve().parents:
        raise ValueError('Choose a new immutable canonical-project output')
    programs, errors, notes = [], [], 0
    for line in (args.inventory / 'occurrences.jsonl').open():
        row = strict_json(line)
        if not row.get('path') or row['path'][-1] != 'note' or 'span' in row:
            continue
        notes += 1
        for part in fragments(row['source']):
            part.update({'asset': row['id'] + '@note:' + str(part['spanCodepoints'][0]),
                         'originalAsset': row['asset'], 'parentId': row['id'], 'parentPath': row['path'],
                         'parentValueSha256': row['sourceValueSha256'], 'rawSha256': sha(part['source'].encode())})
            if part['kind'] == 'unclosed-block':
                errors.append(part)
            else:
                programs.append(part)
    args.output.mkdir(parents=True)
    save_json(args.output / 'programs.json', programs)
    helper = project / 'tools/source_script_inventory.cjs'
    result = subprocess.run(['node', '--expose-internals', str(helper)], input=json.dumps(programs),
                            text=True, capture_output=True, check=True)
    ast = strict_json(result.stdout)
    save_json(args.output / 'ast.json', ast)
    save_json(args.output / 'manifest.json', {'schemaVersion': 1, 'notesScanned': notes, 'programs': len(programs),
                                           'unclosedBlocks': errors, 'parseErrors': ast['errors'],
                                           'stringLiterals': len(ast['strings']), 'displayCalls': len(ast['displayCalls']),
                                           'recipeRawSha256': sha(Path(__file__).read_bytes()),
                                           'parserRawSha256': sha(helper.read_bytes()),
                                           'sourceGate': 'needs-review', 'runtime': 'not-run',
                                           'limits': ['Only declared JS block/eval grammar is parsed; other notetag/action operands remain exact.',
                                                      'Names assigned inside scripts require consumer evidence; parse success is not display classification.']})
    print(json.dumps({'notesScanned': notes, 'programs': len(programs), 'unclosedBlocks': len(errors),
                      'parseErrors': len(ast['errors']), 'stringLiterals': len(ast['strings']), 'displayCalls': len(ast['displayCalls'])}, indent=2))


if __name__ == '__main__':
    main()
