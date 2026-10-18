#!/usr/bin/env python3
"""Bounded read-only inputs for direct RU authoring; never generates wording/review credit."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from source_prepare import strict_json, sha, EXPECTED_SOURCE, EXPECTED_RU

ROOT = Path(__file__).resolve().parent.parent
CORPUS = 'source/text-corpus-8879120-02'
MANIFEST_SHA = 'a55c246992fc1ea672aba77ae0cbdc3ba67aa8ac8d84dd6b78a673addbb1c144'


def read_pinned(root, name, expected):
    raw = (root / name).read_bytes()
    if sha(raw) != expected:
        raise ValueError('Pinned input changed: ' + name)
    return strict_json(raw)


def glossary(root):
    source = read_pinned(root, 'glossary/source-draft.json', EXPECTED_SOURCE)
    target = read_pinned(root, 'glossary/ru/approved.json', EXPECTED_RU)
    if len({x['id'] for x in source}) != len(source) or set(target) != {x['id'] for x in source}:
        raise ValueError('Glossary ID coverage differs')
    return [{ 'id':x['id'], 'ENterm':x['term'], 'ENmeaning':x['meaning'],
              'RUterm':target[x['id']]['term'], 'RUmeaning':target[x['id']]['meaning']}
            for x in source]


def search(rows, queries):
    # Search meanings as well as labels: POOL NOODLE is defined under MAILBOX.
    result = []
    for row in rows:
        fields = [k for k in ('ENterm', 'ENmeaning', 'RUterm', 'RUmeaning')
                  if any(q.casefold() in row[k].casefold() for q in queries)]
        if fields:
            result.append({'id':row['id'], 'en':row['ENterm'], 'ru':row['RUterm'], 'matchedFields':fields})
    return result


def select_entries(rows, ids, max_chars):
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate requested glossary ID')
    by_id = {r['id']:r for r in rows}
    unknown = set(ids) - set(by_id)
    if unknown:
        raise ValueError('Unknown glossary IDs: ' + ', '.join(sorted(unknown)))
    selected = [by_id[k] for k in ids]
    if len(json.dumps(selected, ensure_ascii=False)) > max_chars:
        raise ValueError('Complete glossary fields exceed character limit; split the explicit ID list. No fields printed or credited.')
    return selected


def compact_glossary(root):
    # Rebuild in memory to reject stale or manually corrupted derived content.
    # The accepted full glossary remains immutable provenance for existing batches.
    from build_ru_compact_glossary import build, OUTPUT
    expected = build(root)
    actual = strict_json((root / OUTPUT).read_bytes())
    if actual != expected:
        raise ValueError('Compact glossary is stale or changed; rebuild with tools/build_ru_compact_glossary.py')
    columns = actual['columns']
    return actual, [dict(zip(columns, row)) for row in actual['entries']]


def select_briefs(document, rows, ids, max_chars):
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate requested glossary ID')
    by_id = {row['id']: row for row in rows}
    missing = set(ids) - set(by_id)
    if missing:
        raise ValueError('Unknown glossary IDs: ' + ', '.join(sorted(missing)))
    result = {'pins': document['pins'], 'legend': document['legend'],
              'rules': document['rules'], 'entries': [by_id[id] for id in ids]}
    if len(json.dumps(result, ensure_ascii=False)) > max_chars:
        raise ValueError('Complete compact entries exceed character limit; split the explicit ID list')
    return result


def corpus(root):
    manifest = read_pinned(root, CORPUS + '/manifest.json', MANIFEST_SHA)
    return read_pinned(root, CORPUS + '/units.json', manifest['fileHashes']['units.json'])


def authored(root, units):
    by_id = {u['id']:u for u in units}
    result = {}
    for p in sorted((root / 'translation/ru/batches').glob('*.json')):
        batch = strict_json(p.read_bytes())
        if batch['corpusManifestRawSha256'] != MANIFEST_SHA or batch['glossaryRuRawSha256'] != EXPECTED_RU:
            raise ValueError('Batch input binding differs: ' + p.name)
        for e in batch['entries']:
            if e['id'] in result or e['id'] not in by_id or e['source'] != by_id[e['id']]['source']:
                raise ValueError('Duplicate/unknown/changed source ID: ' + e['id'])
            result[e['id']] = e['target']
    return result


def source_page(units, targets, asset, offset, max_chars):
    rows = [u for u in units if u['asset'] == asset]
    if not rows:
        raise ValueError('Unknown source asset: ' + asset)
    if offset < 0 or offset >= len(rows):
        raise ValueError('Offset outside asset')
    selected, size = [], 0
    for u in rows[offset:]:
        row = {'ordinal':offset + len(selected), 'path':u.get('path'), 'source':u['source'],
               'role':u['role'], 'context':u.get('context', {})}
        if any(k in u for k in ('spanUtf16', 'span', 'spanCodepoints')) or 'path' not in u:
            row['id'] = u['id']
            row['spans'] = {k:u[k] for k in ('spanUtf16', 'span', 'spanCodepoints') if k in u}
        if u['id'] in targets:
            row['authoredTarget'] = targets[u['id']]
        row_size = len(json.dumps(row, ensure_ascii=False))
        if size + row_size > max_chars:
            if not selected:
                raise ValueError('One complete source unit exceeds limit; increase --max-chars explicitly')
            break
        selected.append(row)
        size += row_size
    end = offset + len(selected)
    return {'asset':asset, 'totalAssetUnits':len(rows), 'offset':offset,
            'nextOffset':end if end < len(rows) else None, 'rows':selected,
            'note':'Complete rows only. Asset order is not proof of runtime dialogue/branch order. Read necessary neighbors and actual callers.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    find = sub.add_parser('glossary-find')
    find.add_argument('queries', nargs='+')
    find.add_argument('--offset', type=int, default=0)
    find.add_argument('--limit', type=int, default=25)
    read = sub.add_parser('glossary-read')
    read.add_argument('ids', nargs='+')
    read.add_argument('--max-chars', type=int, default=14000)
    brief = sub.add_parser('glossary-brief')
    brief.add_argument('ids', nargs='+')
    brief.add_argument('--max-chars', type=int, default=14000)
    queue = sub.add_parser('queue')
    queue.add_argument('--offset', type=int, default=0)
    queue.add_argument('--limit', type=int, default=15)
    view = sub.add_parser('source')
    view.add_argument('asset')
    view.add_argument('--offset', type=int, default=0)
    view.add_argument('--max-chars', type=int, default=18000)
    args = parser.parse_args()
    if getattr(args, 'offset', 0) < 0 or getattr(args, 'limit', 1) < 1 or getattr(args, 'max_chars', 1) < 1:
        parser.error('Offsets must be nonnegative; limits must be positive')
    if args.command.startswith('glossary-'):
        if args.command == 'glossary-brief':
            document, brief_rows = compact_glossary(ROOT)
            result = select_briefs(document, brief_rows, args.ids, args.max_chars)
        elif args.command == 'glossary-find':
            rows = glossary(ROOT)
            matches = search(rows, args.queries)
            end = min(args.offset + args.limit, len(matches))
            result = {'matches':len(matches), 'nextOffset':end if end < len(matches) else None,
                      'rows':matches[args.offset:end], 'note':'Read relevant glossary-brief entries first. Full glossary-read is for ambiguity, conflicts or embedded terminology absent from brief notes; searches still cover full meanings.'}
        else:
            rows = glossary(ROOT)
            result = {'sourceSha256':EXPECTED_SOURCE, 'targetSha256':EXPECTED_RU,
                      'entries':select_entries(rows, args.ids, args.max_chars)}
    else:
        units = corpus(ROOT)
        targets = authored(ROOT, units)
        if args.command == 'source':
            result = source_page(units, targets, args.asset, args.offset, args.max_chars)
        else:
            groups = defaultdict(list)
            for u in units:
                if u['id'] not in targets:
                    groups[u['asset']].append(u)
            rows = [{'asset':asset, 'remaining':len(rows), 'sourceCharacters':sum(len(u['source']) for u in rows),
                     'scalarBuilderCandidate':all(u['role'] == 'visible' and not any(k in u for k in ('spanUtf16','span','spanCodepoints'))
                                                  and u['asset'] != 'js/plugins.js' for u in rows)} for asset, rows in groups.items()]
            # Ordinary language catalogs first; preserve original order within each group.
            rows.sort(key=lambda r: (not r['scalarBuilderCandidate'], not r['asset'].startswith('languages/')))
            end = min(args.offset + args.limit, len(rows))
            result = {'authoredIds':len(targets), 'corpusIds':len(units), 'remainingAssets':len(rows),
                      'nextOffset':end if end < len(rows) else None, 'rows':rows[args.offset:end],
                      'note':'Draft inventory only; no build, semantic or runtime acceptance. Builder still validates every application.'}
    print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
