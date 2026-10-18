#!/usr/bin/env python3
"""Assemble and inspect directly authored glossary batches; never generate wording."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path('/Users/antonkrutov/Desktop/SiteForMods')
SOURCE = MASTER / 'data/games/omori/glossary.json'
APPROVED = ROOT / 'glossary/source-draft.json'
SOURCE_CLI = '3f1a11ea9079027d4ac258f9851629e5cafd2eca8c34f34483688b4286df25db'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(locale):
    source = json.loads(SOURCE.read_text())
    assert source == json.loads(APPROVED.read_text()), 'Canonical source content differs from approved reviewed source; inspect through the CLI.'
    directory = ROOT / 'glossary' / locale
    entries = []
    for batch in sorted((directory / 'batches').glob('*.json')):
        records = json.loads(batch.read_text())
        assert isinstance(records, list), f'Not a batch array: {batch}'
        for record in records:
            assert set(record) == {'id', 'term', 'meaning'}, f'Unexpected batch fields: {batch}'
            assert all(isinstance(record[key], str) and record[key].strip() for key in record), f'Empty value: {batch}'
            assert not any(0xD800 <= ord(c) <= 0xDFFF for key in record for c in record[key]), f'Invalid Unicode: {batch}'
        entries.extend(records)
    assert len(entries) <= len(source), 'Extra target rows'
    assert [e['id'] for e in entries] == [e['id'] for e in source[:len(entries)]], 'Missing, duplicate or misordered target IDs'
    return source, directory, entries

parser = argparse.ArgumentParser()
parser.add_argument('locale')
parser.add_argument('--view', nargs=2, type=int, metavar=('START', 'COUNT'))
args = parser.parse_args()
catalog = (MASTER / 'lib/language-data/site-locales.ts').read_text().split('export const SITE_LOCALE_CODES = [', 1)[1].split('] as const;', 1)[0]
assert f'"{args.locale}"' in catalog and args.locale != 'en', 'Unsupported target locale'
source, directory, entries = load(args.locale)
if args.view:
    start, count = args.view
    assert start >= 1 and count > 0 and start - 1 + count <= len(source), 'Invalid source range'
    target = {entry['id']: entry for entry in entries}
    serialized = (json.dumps({e['id']: {'term': e['term'], 'meaning': e['meaning']} for e in entries}, ensure_ascii=False, indent=2) + '\n').encode()
    print(f'Input binding: source CLI {SOURCE_CLI}; source raw {sha(SOURCE)}; target raw {hashlib.sha256(serialized).hexdigest()}; range {start}–{start+count-1}.')
    for index in range(start - 1, start - 1 + count):
        entry = source[index]
        print(f'{index+1} {entry["id"]} | {entry["term"]}\nEN: {entry["meaning"]}')
        if entry['id'] in target:
            translated = target[entry['id']]
            print(f'Target term: {translated["term"]}\nTarget meaning: {translated["meaning"]}')
    raise SystemExit(0)
directory.mkdir(parents=True, exist_ok=True)
draft = directory / 'draft.json'
draft.write_text(json.dumps({entry['id']: {'term': entry['term'], 'meaning': entry['meaning']} for entry in entries}, ensure_ascii=False, indent=2) + '\n')
status = {
    'locale': args.locale, 'stage': 'glossary', 'status': 'drafting',
    'sourceEntries': len(source), 'draftEntries': len(entries), 'remainingEntries': len(source) - len(entries),
    'sourceCliFingerprint': SOURCE_CLI, 'sourceRawSha256': sha(SOURCE), 'draftRawSha256': sha(draft),
    'completeIdsAndOrder': len(entries) == len(source),
    'validation': 'Authored rows parse, contain only id/term/meaning, use valid Unicode, and match the canonical prefix without duplicates.',
    'editorialAcceptance': 'not inferred; full authored audit records required',
    'publication': 'not performed',
}
(directory / 'draft-status.json').write_text(json.dumps(status, indent=2) + '\n')
print(f'{args.locale}: {len(entries)}/{len(source)} authored draft entries; canonical prefix verified. No editorial acceptance inferred.')
