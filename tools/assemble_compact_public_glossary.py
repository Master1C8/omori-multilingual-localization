#!/usr/bin/env python3
"""Assemble fully reviewed meaning-only edits; never publish or change legacy pins."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'glossary/compact-public'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble():
    source_path = ROOT / 'glossary/source-draft.json'
    ru_path = ROOT / 'glossary/ru/approved.json'
    source, ru = read(source_path), read(ru_path)
    rows, receipts = [], []
    for part in sorted((BASE / 'parts').glob('part-???-???.json')):
        author = read(part.with_suffix('.receipt.json'))
        review = read(BASE / 'review' / part.name.replace('part-', 'root-layer2-'))
        chunk = read(part)
        digest = sha(part)
        assert author['outputs']['rawSha256'] == digest, f'Stale author review: {part}'
        assert review['partSha256'] == digest, f'Stale independent review: {part}'
        assert review['status'] == 'clean-for-this-part' and not review['unreadFields']
        assert author['inputs']['sourceRawSha256'] == sha(source_path)
        assert author['inputs']['ruRawSha256'] == sha(ru_path)
        assert review['sourceRawSha256'] == sha(source_path)
        assert review['targetPriorRawSha256'] == sha(ru_path)
        ids = [r['id'] for r in chunk]
        assert ids == author['coverage']['ids'] == review['ids']
        assert review['ordinalRange'] == [len(rows), len(rows) + len(chunk)]
        for key, value in author['coverage'].items():
            if key.startswith('unread') or key == 'truncatedFieldsRemaining':
                assert not value, f'Incomplete author coverage: {part}/{key}'
        rows.extend(chunk)
        receipts.append({'part': str(part.relative_to(ROOT)), 'sha256': digest})
    assert len(rows) == len(source) == 699, f'Incomplete coverage: {len(rows)}/699'
    assert [r['id'] for r in rows] == [s['id'] for s in source]
    new_source, new_ru = copy.deepcopy(source), copy.deepcopy(ru)
    for row, entry in zip(rows, new_source):
        assert row['enTerm'] == entry['term'] and row['ruTerm'] == ru[row['id']]['term']
        assert all(isinstance(row[k], str) and row[k].strip() for k in ['enMeaning', 'ruMeaning'])
        entry['meaning'] = row['enMeaning']
        new_ru[row['id']]['meaning'] = row['ruMeaning']
    metrics = {}
    for locale, old, new in [('en', source, new_source), ('ru', list(ru.values()), list(new_ru.values()))]:
        old_chars, new_chars = sum(len(r['meaning']) for r in old), sum(len(r['meaning']) for r in new)
        metrics[locale] = {'oldMeaningCharacters': old_chars, 'newMeaningCharacters': new_chars,
                           'meaningReductionPercent': (1 - new_chars / old_chars) * 100}
    # Validate everything before writing. Each file replacement is atomic; this is not
    # a two-file transaction. Publication/integration must verify BOTH output hashes.
    outputs = {}
    for name, data in [('approved-source.json', new_source), ('approved-ru.json', new_ru)]:
        target = BASE / name
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)
        outputs[name] = sha(target)
    receipt = {'entries': len(rows), 'parts': receipts, 'outputs': outputs, 'metrics': metrics,
               'scope': 'Meaning-only EN/RU edits. Legacy full references and game batch pins retained. No publication implied.'}
    (BASE / 'assembly.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    assemble()
