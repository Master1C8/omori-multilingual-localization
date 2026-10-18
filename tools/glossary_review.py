#!/usr/bin/env python3
"""Display native fields and record explicitly authored editorial decisions.

This helper checks linkage and hashes, never translates or judges semantic quality.
Record only after actual complete comparison AND a distinct native reading.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path('/Users/antonkrutov/Desktop/SiteForMods')
SOURCE = MASTER / 'data/games/omori/glossary.json'
PROTOCOL = MASTER / 'tools/codex-skills/shared/GLOSSARY-REVIEW.md'
EXPECTED_SOURCE = '11d48e714e6ba1652ca76ed45c4d7622e22312547410bc694c1f46181a18773b'
EXPECTED_PROTOCOL = '06c17e0cb278cb1beaa251f2c1cb7a220dac1397221236be9feebde765c17a03'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['native', 'record'])
parser.add_argument('locale')
parser.add_argument('start', type=int)
parser.add_argument('count', type=int)
parser.add_argument('--layer', type=int, choices=[1, 2])
parser.add_argument('--decision', type=Path)
args = parser.parse_args()
assert sha(SOURCE) == EXPECTED_SOURCE, 'Protected source changed'
assert sha(PROTOCOL) == EXPECTED_PROTOCOL, 'Review protocol changed'
source = json.loads(SOURCE.read_text())
assert source == json.loads((ROOT / 'glossary/source-draft.json').read_text())
directory = ROOT / 'glossary' / args.locale
draft = directory / 'draft.json'
target = json.loads(draft.read_text())
assert len(source) == 699 and list(target) == [x['id'] for x in source]
assert args.start >= 1 and args.count > 0 and args.start - 1 + args.count <= len(source)
selected = source[args.start - 1:args.start - 1 + args.count]
ids = [x['id'] for x in selected]
rules = directory / 'terminology-decisions.md'
binding = {'locale': args.locale, 'sourceRawSha256': sha(SOURCE),
           'targetRawSha256': sha(draft), 'terminologyRuleRawSha256': sha(rules),
           'protocolRawSha256': sha(PROTOCOL)}
if args.action == 'native':
    print('Native reading input binding:', json.dumps(binding))
    for ordinal, entry in enumerate(selected, args.start):
        row = target[entry['id']]
        print(f'{ordinal} {entry["id"]} | {row["term"]}\n{row["meaning"]}')
    raise SystemExit(0)

assert args.layer and args.decision, 'Recording requires layer and authored decision'
decision = json.loads(args.decision.read_text())
assert decision['locale'] == args.locale and decision['layer'] == args.layer
assert decision['reviewerKind'] == 'author self-review'
assert decision['model'] == 'gpt-6.1-sol' and decision['reasoning'] == 'high'
assert decision['actualReadIds'] == ids
assert decision['targetRawSha256'] == binding['targetRawSha256']
assert decision['comparisonToolChunks'] and decision['nativeToolChunks']
assert not decision['unreadOrTruncatedFields']
assert set(decision['dependencies']) == set(ids)
assert isinstance(decision['findings'], list) and decision['editorialAssessment'].strip()
source_by_id = {x['id']: x for x in source}
for entry_id, dependencies in decision['dependencies'].items():
    assert isinstance(dependencies, list) and len(dependencies) == len(set(dependencies))
    missing = set(dependencies) - set(source_by_id)
    assert not missing, f'Unknown dependency IDs for {entry_id}: {sorted(missing)}; inspect the canonical catalog before recording.'
for finding in decision['findings']:
    assert finding['id'] in ids and finding['field'] in ['term', 'meaning']

progress_path = directory / 'audit-progress.json'
progress = json.loads(progress_path.read_text())
assert not progress['accepted']
layer = progress[f'baseline{args.layer}']
assert layer['actualReadIds'] == [x['id'] for x in source[:args.start - 1]]
if layer['actualReadIds']:
    assert layer['initialTargetRawSha256'] == binding['targetRawSha256']
    assert layer['initialTerminologyRuleRawSha256'] == binding['terminologyRuleRawSha256']
else:
    layer['initialTargetRawSha256'] = binding['targetRawSha256']
    layer['initialTerminologyRuleRawSha256'] = binding['terminologyRuleRawSha256']
    snapshot = directory / 'review-history' / f'baseline-{args.layer}-initial-target.json'
    assert not snapshot.exists()
    layer['initialTargetSnapshot'] = str(snapshot.relative_to(directory))

receipt = dict(binding)
receipt.update(decision)
receipt['purpose'] = 'Actual complete-field editorial baseline reading, not independent review'
receipt['fieldsRead'] = ['source.term', 'source.meaning', 'target.term', 'target.meaning']
receipt['dimensions'] = ['English/target fidelity and concept/dependency comparison',
                         'distinct native target grammar, idiom and reference reading']
receipt['entries'] = []
for entry in selected:
    entry_id = entry['id']
    receipt['entries'].append({'id': entry_id,
        'sourceEntryContentSha256': digest(entry),
        'targetEntryContentSha256': digest(target[entry_id]),
        'dependencyInputs': [{'id': dep, 'sourceEntryContentSha256': digest(source_by_id[dep]),
                              'targetEntryContentSha256': digest(target[dep])}
                             for dep in decision['dependencies'][entry_id]]})
receipt_path = directory / 'review-history' / f'baseline-{args.layer}-read-{args.start:03d}-{args.start+args.count-1:03d}.json'
assert not receipt_path.exists()
raw = encode(receipt)
layer['actualReadIds'].extend(ids)
layer['receipts'].append({'path': str(receipt_path.relative_to(directory)),
                          'rawSha256': hashlib.sha256(raw.encode()).hexdigest()})
layer['complete'] = len(layer['actualReadIds']) == len(source)
layer['clean'] = False
layer['findingsRecorded'] = layer.get('findingsRecorded', 0) + len(decision['findings'])
progress['nextAction'] = ('Adjudicate the complete baseline findings and repair demonstrated closures; clean coverage is not inferred.'
                          if layer['complete'] else f'Continue baseline {args.layer} at ordinal {args.start+args.count}, with separate comparison and native reading.')
outputs = {receipt_path: raw, progress_path: encode(progress)}
if args.start == 1:
    outputs[snapshot] = draft.read_text()
    rule_snapshot = directory / 'review-history' / f'baseline-{args.layer}-initial-rules.md'
    assert not rule_snapshot.exists()
    outputs[rule_snapshot] = rules.read_text()
for destination, content in outputs.items():
    destination.write_text(content)
print(f'{args.locale} baseline {args.layer}: {len(layer["actualReadIds"])} complete paired/native entry readings recorded; clean acceptance not inferred.')
