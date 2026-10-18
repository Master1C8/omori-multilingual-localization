#!/usr/bin/env python3
"""Build a derived term/agreement desk reference; never rewrite approved meanings."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from ru_workset import ROOT, glossary

OUTPUT = 'glossary/ru/compact.json'
NOTES = 'glossary/ru/compact-notes.json'
OWNERS = 'glossary/owner-decisions.json'
GENDER_EXCEPTIONS = {
    'cat': 'mixed', 'othermart-cashier': 'mixed', 'veggie-kids': 'mixed',
    'mr-scarebro': 'M', 'mr-scarecrow': 'M', 'mr-scarethrow': 'M',
    'veggie-eggplant': 'M', 'veggie-onion': 'M',
    'veggie-potatogirl': 'F', 'veggie-tomatogirl': 'F',
    'recycultists': 'M', 'sweetheart-contestant-1': 'M', 'sweetheart-contestant-2': 'M',
    'map-of-truth-voice': '?', 'recycling-machine': '-', 'sprout-mole': 'individual',
    'hooligans': 'mixed', 'space-pirates': 'M', 'unbread-twins': 'mixed',
    'slime-girls': 'F', 'roboheart-mutantheart-perfectheart': 'F',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gender(entry):
    if entry['id'] in GENDER_EXCEPTIONS:
        return GENDER_EXCEPTIONS[entry['id']]
    if entry['category'] not in {'Character', 'Character group', 'Entity', 'Species'}:
        return '-'
    meaning = entry['meaning']
    if re.match(r'^Male(?:;|\.| according)', meaning):
        return 'M'
    if re.match(r'^Female(?:;| according)', meaning):
        return 'F'
    if (meaning.startswith('Canonical gender and personal pronouns are not') or
            re.search(r'Gender and canonical (?:third-person|personal) pronouns(?: for [^.]+?)? are not established', meaning)):
        return '?'
    raise ValueError('Unclassified canonical gender; inspect exact meaning: ' + entry['id'])


def build(root=ROOT):
    rows = glossary(root)  # Verify exact approved EN/RU fingerprints and all IDs.
    source = json.loads((root / 'glossary/source-draft.json').read_text())
    notes = json.loads((root / NOTES).read_text())
    if set(notes) - {e['id'] for e in source}:
        raise ValueError('Unknown note IDs')
    owners = json.loads((root / OWNERS).read_text())
    neutral_ids = {d['glossaryId'] for d in owners['decisions']}
    for policy in owners['minorSpeakerPolicies']:
        neutral_ids.update(m['glossaryId'] for m in policy['mappings'])
    entries = []
    for en, row in zip(source, rows):
        sex = gender(en)
        # Canonical facts stay separate from regional or unknown-speaker strategy.
        agreement = {'M': 'm', 'F': 'f', '?': 'neutral', '-': '-',
                     'mixed': 'resolve', 'individual': 'resolve'}[sex]
        if en['id'] in neutral_ids and sex in {'?', 'mixed'}:
            agreement = 'neutral'
        entries.append([en['id'], row['ENterm'], row['RUterm'], sex, agreement,
                        notes.get(en['id'], '')])
    return {
        'schemaVersion': 1,
        'purpose': 'Owner-requested compact Russian authoring reference; full approved meanings remain available on demand. Not a replacement canonical glossary or new editorial acceptance.',
        'pins': {p: digest(root / p) for p in ['glossary/source-draft.json',
                 'glossary/ru/approved.json', OWNERS, NOTES, 'tools/build_ru_compact_glossary.py']},
        'columns': ['id', 'en', 'ru', 'canonicalGender', 'ruAgreement', 'note'],
        'legend': {'M': 'male', 'F': 'female', '?': 'not established',
                   'mixed': 'group/shared label with male and female instances',
                   'individual': 'species does not establish individual gender',
                   '-': 'no personal gender field applicable', 'm': 'masculine',
                   'f': 'feminine', 'neutral': 'retain name, agency and number; avoid unsupported gender, not neuter predicates',
                   'resolve': 'identify scene participant before choosing agreement'},
        'rules': [
            'Use the exact approved term or its context-appropriate inflection/alias. Slash-separated aliases are not interchangeable in every scene.',
            'No biographies are required for routine name/agreement use. Read full entries for unresolved identity, relationships, wordplay, meaning-only terms or conflicts with the scene.',
            'Search still covers complete EN/RU meanings so omitted embedded terminology remains discoverable.',
            'Do not infer personal gender from a name, role, grammatical gender, random graphic or another participant pronoun.',
            'R001: DEEPER WELL resident speakers use neutral constructions, including HUMPHREY locally; keep canonical facts, agency and number. Visiting party/other regions excluded.',
            'Owner decisions and source/consumer mappings remain in glossary/owner-decisions.json; inspect only relevant mappings for ambiguous scope.',
            'No new runtime, independent review or semantic audit acceptance. Compact-reference size is not a speed or billing measurement.'
        ],
        'regionalNeutralIds': [m['glossaryId'] for m in owners['regionalDecisions'][0]['mappings']],
        'entries': entries,
    }


def serialize(document):
    # One readable row per line, without repeating six property names 699 times.
    head = {k: v for k, v in document.items() if k != 'entries'}
    prefix = json.dumps(head, ensure_ascii=False, indent=2)[:-2]
    rows = ',\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in document['entries'])
    return (prefix + ',\n  "entries": [\n' + rows + '\n  ]\n}\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    document = build()
    raw = serialize(document)
    json.loads(raw)  # Validate serialization before changing a file.
    path = ROOT / OUTPUT
    if args.check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError('Compact reference differs from current pinned inputs; rebuild')
    else:
        temporary = path.with_suffix('.json.tmp')
        temporary.write_bytes(raw)
        temporary.replace(path)
    full = sum((ROOT / p).stat().st_size for p in ['glossary/source-draft.json', 'glossary/ru/approved.json'])
    print(json.dumps({'entries': len(document['entries']), 'fullBytes': full,
                      'compactBytes': len(raw), 'byteReductionPercent': (1-len(raw)/full)*100,
                      'genderCounts': dict(Counter(r[3] for r in document['entries'])),
                      'status': 'verified' if args.check else 'built'}))


if __name__ == '__main__':
    main()
