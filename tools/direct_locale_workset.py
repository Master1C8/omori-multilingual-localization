#!/usr/bin/env python3
"""Owner-authorized direct authoring inputs; no generated translation or review credit."""
import argparse
from collections import defaultdict
import hashlib
import importlib
import json
from pathlib import Path
import sys


def read(p):
    return json.loads(p.read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--tooling', type=Path, required=True)
    p.add_argument('--locale', required=True)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('queue'); q.add_argument('--limit', type=int, default=12)
    s = sub.add_parser('source'); s.add_argument('asset'); s.add_argument('--offset', type=int, default=0); s.add_argument('--max-chars', type=int, default=20000)
    v = sub.add_parser('validate'); v.add_argument('batch', type=Path)
    b = sub.add_parser('assemble'); b.add_argument('--output', type=Path, required=True)
    b.add_argument('--yaml-module', required=True)
    sub.add_parser('progress')
    a = p.parse_args()
    if a.locale in {'ru', 'en', 'zh', 'ja', 'ko'}:
        raise ValueError('Protected or official locale')
    root = a.root.resolve()
    sys.path.insert(0, str(a.tooling.resolve()))
    tools = importlib.import_module('locale_tools')
    ctx = tools.Context(root, root / 'source/multilingual/shared-8879120-03', a.locale)
    work = root / 'translation' / a.locale
    glossary = read(work / 'glossary-snapshot.json')
    if glossary['siteLocale'] != a.locale:
        raise ValueError('Glossary language differs')
    target_namebox = glossary['target']['roboheart']['term']
    authored = {}
    batches = []
    for f in sorted((work / 'batches').glob('*.json')):
        batch = read(f)
        if batch.get('siteLocale') != a.locale or batch.get('sourceLocale') != 'en' or batch.get('inventorySha256') != ctx.inventory_sha:
            raise ValueError('Batch locale/inventory differs: ' + str(f))
        for e in batch['entries']:
            if e['id'] in authored:
                raise ValueError('Duplicate canonical authored ID: ' + e['id'])
            authored[e['id']] = e
        batches.append(batch)
    if a.command == 'validate':
        batch = read(a.batch)
        if batch.get('siteLocale') != a.locale or batch.get('sourceLocale') != 'en' or batch.get('inventorySha256') != ctx.inventory_sha:
            raise ValueError('Batch locale/inventory differs')
        if any(e.get('immediateEdit') is not True for e in batch['entries']):
            raise ValueError('Actual immediate editing must be recorded')
        tools.validate_entries(ctx, batch['entries'], target_namebox)
        result = {'status': 'passed-controls-only', 'entries': len(batch['entries']), 'semantic': 'not-established', 'runtime': 'not-run'}
    elif a.command == 'assemble':
        pairs = tools.validate_entries(ctx, list(authored.values()), target_namebox)
        output = ctx.output(a.output)
        result = tools.assemble(ctx, pairs, output, a.yaml_module)
    elif a.command == 'queue':
        groups = defaultdict(list)
        for u in ctx.units:
            if u['id'] not in authored and u['id'] not in ctx.retained:
                groups[u['asset']].append(u)
        rows = [{'asset': asset, 'remaining': len(units), 'characters': sum(len(u['source']) for u in units)} for asset, units in groups.items()]
        rows.sort(key=lambda r: (not r['asset'].startswith('languages/en/'), r['asset']))
        result = {'inventorySha256': ctx.inventory_sha, 'assetsRemaining': len(rows), 'rows': rows[:a.limit]}
    elif a.command == 'source':
        units = [u for u in ctx.units if u['asset'] == a.asset]
        if not units or a.offset < 0 or a.offset >= len(units) or a.max_chars < 1:
            raise ValueError('Invalid complete-source page')
        rows = []; used = 0
        for u in units[a.offset:]:
            row = dict(u)
            if u['id'] in ctx.registry:
                row['encodedContext'] = ctx.registry[u['id']]
            if u['id'] in authored:
                row['authoredTarget'] = authored[u['id']]['target']
            n = len(json.dumps(row, ensure_ascii=False))
            if used + n > a.max_chars:
                if not rows:
                    raise ValueError('A whole source row exceeds max-chars; increase the explicit limit')
                break
            rows.append(row); used += n
        end = a.offset + len(rows)
        result = {'asset': a.asset, 'total': len(units), 'offset': a.offset, 'nextOffset': end if end < len(units) else None, 'rows': rows}
    else:
        tools.validate_entries(ctx, list(authored.values()), target_namebox)
        result = {'siteLocale': a.locale, 'inventorySha256': ctx.inventory_sha,
                  'draftAuthoredEditedOccurrences': len(authored), 'totalOccurrences': len(ctx.units),
                  'technicalRetentions': len(ctx.retained), 'batches': len(batches),
                  'editorialAcceptance': 'pending', 'deliveredCoverage': 'not-established', 'runtime': 'not-run'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
