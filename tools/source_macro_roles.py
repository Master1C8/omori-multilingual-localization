#!/usr/bin/env python3
"""Bind native quick-macro expansion spans and callback control fragments."""
import argparse
from collections import Counter
from pathlib import Path
import re
from source_prepare import save_json, sha, strict_json


def macro_parts(source):
    """Current complete macro-body schema; unknown controls fail closed."""
    parts, cursor = [], 0
    pattern = re.compile(r'\\n<(.*?)>|\\[nv]\[\d+\]', re.I)
    for match in pattern.finditer(source):
        if cursor < match.start():
            parts.append({'spanCodepoints': [cursor, match.start()], 'source': source[cursor:match.start()], 'role': 'visible'})
        if match[1] is not None:
            start, end = match.start(1), match.end(1)
            parts.append({'spanCodepoints': [match.start(), start], 'source': source[match.start():start], 'role': 'preserve-exactly'})
            parts.extend(dict(p, spanCodepoints=[p['spanCodepoints'][0] + start, p['spanCodepoints'][1] + start]) for p in macro_parts(match[1]))
            parts.append({'spanCodepoints': [end, match.end()], 'source': source[end:match.end()], 'role': 'preserve-exactly'})
        else:
            parts.append({'spanCodepoints': [match.start(), match.end()], 'source': match[0], 'role': 'preserve-exactly'})
        cursor = match.end()
    if cursor < len(source):
        parts.append({'spanCodepoints': [cursor, len(source)], 'source': source[cursor:], 'role': 'visible'})
    for part in parts:
        if part['role'] == 'visible':
            if '\\' in part['source']:
                raise ValueError('Unbound native macro control: ' + repr(part['source']))
            if not part['source'].strip() or part['source'] == '???':
                part['role'] = 'preserve-exactly'
    if ''.join(p['source'] for p in parts) != source:
        raise ValueError('Macro segmentation lost original bytes')
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve earlier source evidence')
    rows = strict_json((args.parameters / 'parameters.json').read_bytes())
    macros = []
    for row in rows:
        if row['role'] != 'mixed-display':
            continue
        parts = macro_parts(row['source'])
        for part in parts:
            part['id'] = row['id'] + '@macro:' + str(part['spanCodepoints'][0])
            part['parentId'] = row['id']
            part['parentValueSha256'] = row['sourceValueSha256']
            part['reason'] = 'Native namebox/display body' if part['role'] == 'visible' else 'Native namebox/variable/actor control or unchanged placeholder'
        macros.append(dict(row, parts=parts))
    callbacks = strict_json((args.parameters / 'callback-ast.json').read_bytes())
    for row in callbacks['strings']:
        if not re.fullmatch(r'\x1bc\[|\]|%', row['source']):
            raise ValueError('Unbound callback literal: ' + row['id'])
        row['role'], row['reason'] = 'preserve-exactly', 'Native color control scaffold or numeric percentage suffix in JSON-decoded escape callback.'
    args.output.mkdir(parents=True)
    save_json(args.output / 'macros.json', macros)
    save_json(args.output / 'callback-roles.json', callbacks)
    report = {'schemaVersion': 1, 'macros': len(macros),
              'macroParts': dict(Counter(p['role'] for m in macros for p in m['parts'])),
              'callbacks': len(callbacks['scripts']), 'callbackStrings': len(callbacks['strings']),
              'parseErrors': callbacks['errors'], 'sourceGate': 'needs-review',
              'recipeRawSha256': sha(Path(__file__).read_bytes()),
              'parameterManifestRawSha256': sha((args.parameters / 'manifest.json').read_bytes()),
              'runtime': 'not-run'}
    save_json(args.output / 'manifest.json', report)
    print(report)


if __name__ == '__main__':
    main()
