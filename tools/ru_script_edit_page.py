"""Read bounded, complete source/target statement assemblies from an authored draft."""
import argparse
from pathlib import Path
from script_resource_adapter import original_resource, program_edit, programs, recover_program
from source_prepare import strict_json
from text_resource_adapter import splice
from source_text_syntax import quick_macro_names


def statement_rows(root, draft):
    units = [u for u in strict_json((root / 'source/text-corpus-8879120-02/units.json').read_bytes())
             if u['asset'] == draft['asset']]
    record = programs(root).get(draft['asset'])
    if record:
        _, tree = original_resource(root, record['originalAsset'])
        source = recover_program(record, tree)
    else:
        source, _ = original_resource(root, draft['asset'])
    macros = quick_macro_names(strict_json((root / 'source/parameter-roles-8879120-01/parameters.json').read_bytes()))
    spans = {}
    for unit in units:
        statement = unit['context']['statement']
        start = len(source.encode('utf-16-le')[:unit['spanUtf16'][0] * 2].decode('utf-16-le'))
        position, matches = source.find(statement), []
        while position != -1:
            if position <= start < position + len(statement): matches.append(position)
            position = source.find(statement, position + 1)
        if len(matches) != 1:
            raise ValueError('Statement context does not bind uniquely: ' + unit['id'])
        spans[(matches[0], matches[0] + len(statement))] = statement
    rows = []
    for (start, stop), statement in sorted(spans.items()):
        a = len(source[:start].encode('utf-16-le')) // 2
        b = len(source[:stop].encode('utf-16-le')) // 2
        parts, ids = [], []
        for unit in units:
            lo, hi = unit['spanUtf16']
            if a <= lo and hi <= b:
                part = program_edit(unit, {'target': draft['targets'][unit['id']]}, macros)
                part['span'] = [lo - a, hi - a]
                parts.append(part); ids.append(unit['id'])
        rows.append({'source': statement, 'target': splice(statement, parts, utf16=True),
                     'line': source.count('\n', 0, start) + 1, 'ids': ids})
    if {i for r in rows for i in r['ids']} != {u['id'] for u in units}:
        raise ValueError('Statement edit pages omit source occurrences')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft', type=Path)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--characters', type=int, default=15000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    rows = statement_rows(root, strict_json(args.draft.read_bytes()))
    used, end = 0, args.offset
    for i, row in enumerate(rows[args.offset:], args.offset):
        size = len(row['source']) + len(row['target'])
        if used and used + size > args.characters: break
        print(i, 'line', row['line'], 'source IDs', len(row['ids']))
        print('EN', row['source'])
        print('RU', row['target'])
        used += size; end = i + 1
    print({'statementCount':len(rows), 'nextOffset':end if end < len(rows) else None})


if __name__ == '__main__': main()
