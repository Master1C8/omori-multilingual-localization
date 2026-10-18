#!/usr/bin/env python3
"""Exercise intended glossary rejection boundaries using in-memory document views."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / 'glossary'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    validator = module('draft_validator', 'validate_glossary_draft.py')
    refresh = module('draft_refresh', 'refresh_glossary_documents.py')
    names = ['source-draft.json', 'entry-evidence.json', 'roster-review.json', 'owner-decisions.json',
             'editorial-audits.json']
    baseline = {name: json.loads((GLOSSARY / name).read_text()) for name in names}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    before = {name: digest(original_bytes(GLOSSARY / name)) for name in names}
    meat_ids = next(row['sourceIds'] for row in baseline['roster-review.json']['labels']
                    if row['label'] == 'MEAT MAN')
    meat_records = {}
    with (ROOT / 'source/research-8879120-02/strings.jsonl').open() as source:
        for line in source:
            record = json.loads(line)
            if record['id'] in meat_ids:
                meat_records[record['id']] = record
    meat_groups = validator.utterance_groups(meat_records)
    assert len(meat_groups) == 10, 'Exact ten-message negative fixture changed'

    def views(documents):
        return {GLOSSARY / name: json.dumps(value, ensure_ascii=False, indent=2) + '\n'
                for name, value in documents.items()}

    def read_text(path, *args, **kwargs):
        return memory[path] if path in memory else original_text(path, *args, **kwargs)

    def read_bytes(path, *args, **kwargs):
        return memory[path].encode() if path in memory else original_bytes(path, *args, **kwargs)

    def verify():
        with patch.object(Path, 'read_text', read_text), patch.object(Path, 'read_bytes', read_bytes), \
                patch.object(sys, 'argv', ['validator']), redirect_stdout(io.StringIO()):
            validator.main()

    memory = {GLOSSARY / name: original_text(GLOSSARY / name) for name in names}
    verify()
    cases = []
    experiments = [
        ('unapproved-individual-policy', 'Unapproved or omitted individual strategy'),
        ('whole-stranger-label', 'Scoped approval was applied to the whole mixed label'),
        ('outside-individual-catalog', 'Decision evidence exceeds catalog scope'),
        ('omitted-regional-policy', 'Unapproved or omitted regional strategy'),
        ('outside-regional-map', 'Regional consumer outside approved maps'),
        ('whole-anonymous-label', 'Regional identity was applied to the whole anonymous label'),
        ('erased-canonical-facts', 'Regional strategy erased canonical facts'),
        ('interrupted-refresh', 'Stale draft binding'),
        ('unapproved-minor-policy', 'Unapproved or omitted minor-speaker strategy'),
        ('changed-minor-threshold', 'Owner minor-speaker threshold changed'),
        ('omitted-minor-occurrence', 'Minor-speaker count omitted or exceeded bound occurrences'),
        ('forged-minor-deduplication', 'Minor-speaker duplicate accounting differs'),
        ('exactly-ten-utterances', 'Minor-speaker has ten or more distinct utterances'),
        ('empty-speaker-census', 'Minor-speaker instance census is empty'),
        ('duplicate-speaker-identity', 'Duplicate minor-speaker instance identity'),
        ('omitted-speaker-instance', 'Minor-speaker instance census omitted bound utterances'),
        ('wrong-speaker-event', 'Minor-speaker consumer belongs to another scene identity'),
        ('swapped-speaker-bodies', 'Minor-speaker instance lacks matching message consumer'),
        ('forged-instance-deduplication', 'Minor-speaker instance duplicate accounting differs'),
        ('same-catalog-other-voice-evidence', 'Decision evidence differs from approved occurrence scope'),
        ('same-catalog-other-voice-case', 'Roster case differs from approved occurrence scope'),
        ('same-catalog-other-voice-binding', 'Approved voice binding differs from occurrence scope'),
    ]
    for name, expected in experiments:
        documents = json.loads(json.dumps(baseline))
        draft = {entry['id']: entry for entry in documents['source-draft.json']}
        roster = {row['label']: row for row in documents['roster-review.json']['labels']}
        proof = {row['id']: row for row in documents['entry-evidence.json']['entries']}
        policy = documents['owner-decisions.json']['regionalDecisions'][0]
        minor_policy = documents['owner-decisions.json']['minorSpeakerPolicies'][0]
        minor_mapping = minor_policy['mappings'][0]
        census_mapping = next(m for m in minor_policy['mappings'] if m['glossaryId'] == 'gardener-mole')
        if name == 'unapproved-individual-policy':
            draft['kim']['meaning'] += ' Owner-approved strategy: neutral constructions.'
        elif name == 'whole-stranger-label':
            roster['STRANGER']['glossaryId'] = 'stranger'
        elif name == 'outside-individual-catalog':
            proof['stranger']['sourceIds'].append(proof['kim']['sourceIds'][0])
        elif name == 'omitted-regional-policy':
            draft['aught']['meaning'] = draft['aught']['meaning'].replace('Owner-approved regional strategy:', 'Regional strategy:')
        elif name == 'outside-regional-map':
            policy['mappings'][0]['consumerIds'].append('data/Map301.KEL#["events",1,"pages",3,"list",6,"parameters",0]')
        elif name == 'whole-anonymous-label':
            roster['???']['glossaryId'] = 'map-of-truth-voice'
        elif name == 'erased-canonical-facts':
            draft['humphrey']['meaning'] = draft['humphrey']['meaning'].replace('Male; he/him.', 'Gender not established.', 1)
        elif name == 'unapproved-minor-policy':
            draft['kim']['meaning'] += ' Owner-approved minor-speaker strategy: neutral constructions.'
        elif name == 'changed-minor-threshold':
            minor_policy['maxDistinctUtterancesExclusive'] = 11
        elif name == 'omitted-minor-occurrence':
            minor_mapping = next(mapping for mapping in minor_policy['mappings'] if mapping['glossaryId'] == 'gibs')
            minor_mapping['sourceIds'].pop()
        elif name == 'forged-minor-deduplication':
            minor_mapping = next(mapping for mapping in minor_policy['mappings'] if mapping['glossaryId'] == 'gibs')
            minor_mapping['utteranceGroups'] = [minor_mapping['sourceIds']]
            minor_mapping['distinctUtterances'] = 1
        elif name == 'exactly-ten-utterances':
            # Test the counting guard, not the truth of an assigned gender strategy.
            # The baseline includes approved minor speakers below ten; use ten real
            # distinct indexed messages with complete namebox coverage for rejection.
            draft['meat-man']['meaning'] += ' Owner-approved minor-speaker strategy: guard fixture only.'
            proof['meat-man']['genderEvidence'] = 'owner-policy-P001'
            minor_policy['mappings'].append({'glossaryId': 'meat-man', 'labels': ['MEAT MAN'],
                                             'sourceIds': sorted(meat_ids), 'utteranceGroups': meat_groups,
                                             'distinctUtterances': 10})
        elif name == 'empty-speaker-census':
            census_mapping['speakerInstances'] = []
        elif name == 'duplicate-speaker-identity':
            census_mapping['speakerInstances'][1]['eventId'] = census_mapping['speakerInstances'][0]['eventId']
        elif name == 'omitted-speaker-instance':
            census_mapping['speakerInstances'].pop()
        elif name == 'wrong-speaker-event':
            census_mapping['speakerInstances'][0]['eventId'] = 999
        elif name == 'swapped-speaker-bodies':
            first, second = census_mapping['speakerInstances'][:2]
            first['sourceIds'], second['sourceIds'] = second['sourceIds'], first['sourceIds']
            first['utteranceGroups'], second['utteranceGroups'] = second['utteranceGroups'], first['utteranceGroups']
        elif name == 'forged-instance-deduplication':
            census_mapping['speakerInstances'][0]['utteranceGroups'] = []
        elif name == 'same-catalog-other-voice-evidence':
            proof['fear-guidance-voice']['sourceIds'].append('languages/en/xx_battle_text.HERO#["message_941","text"]')
        elif name == 'same-catalog-other-voice-case':
            roster['???']['caseScope']['sourceIds'].append('languages/en/xx_battle_text.HERO#["message_941","text"]')
        elif name == 'same-catalog-other-voice-binding':
            scope = next(s for s in roster['???']['resolvedOccurrenceScopes']
                         if s['glossaryId'] == 'fear-guidance-voice')
            scope['sourceIds'].append('languages/en/xx_battle_text.HERO#["message_941","text"]')
        else:
            draft['kim']['meaning'] += ' Guard experiment only.'
        memory = views(documents)
        draft_hash = digest(memory[GLOSSARY / 'source-draft.json'].encode())
        decision_hash = digest(memory[GLOSSARY / 'owner-decisions.json'].encode())
        if name != 'interrupted-refresh':
            for filename in ['entry-evidence.json', 'roster-review.json']:
                documents[filename]['sourceDraftRawSha256'] = draft_hash
                documents[filename]['ownerDecisionsRawSha256'] = decision_hash
            memory = views(documents)
        else:
            def fail_second_write(path, value, *args, **kwargs):
                if path == GLOSSARY / 'roster-review.json':
                    raise RuntimeError('simulated second-write failure')
                memory[path] = value
                return len(value)
            with patch.object(Path, 'read_text', read_text), patch.object(Path, 'read_bytes', read_bytes), \
                    patch.object(Path, 'write_text', fail_second_write), redirect_stdout(io.StringIO()):
                try:
                    refresh.main()
                except RuntimeError as error:
                    assert str(error) == 'simulated second-write failure'
                else:
                    raise AssertionError('Refresh did not reach simulated boundary')
            assert json.loads(memory[GLOSSARY / 'entry-evidence.json'])['sourceDraftRawSha256'] == draft_hash
            assert json.loads(memory[GLOSSARY / 'roster-review.json'])['sourceDraftRawSha256'] != draft_hash
        try:
            verify()
        except AssertionError as error:
            assert str(error) == expected, (name, str(error), expected)
            cases.append({'case': name, 'status': 'passed-intended-rejection', 'reason': expected})
        else:
            raise AssertionError((name, 'Invalid document was accepted'))
    # A positive structural result must not carry stale or partial editorial acceptance.
    memory = {GLOSSARY / name: original_text(GLOSSARY / name) for name in names}
    with patch.object(Path, 'read_text', read_text), patch.object(Path, 'read_bytes', read_bytes):
        assert validator.recorded_review_count(GLOSSARY, baseline['source-draft.json']) == 2
    review_cases = []
    for case in ['partial-review-ids', 'review-with-finding', 'wrong-reviewed-version', 'changed-evidence-after-review']:
        documents = json.loads(json.dumps(baseline))
        review = documents['editorial-audits.json']['passes'][-1]
        if case == 'partial-review-ids':
            review['reviewedEntryIds'].pop()
        elif case == 'review-with-finding':
            review['findings'].append({'entryId': 'omori', 'detail': 'Unresolved fixture issue'})
        elif case == 'wrong-reviewed-version':
            review['inputSourceDraftRawSha256'] = '0' * 64
        else:
            documents['entry-evidence.json']['entries'][0]['notes'].append('Changed fixture evidence')
        memory = views(documents)
        with patch.object(Path, 'read_text', read_text), patch.object(Path, 'read_bytes', read_bytes):
            assert validator.recorded_review_count(GLOSSARY, baseline['source-draft.json']) == 0, case
        review_cases.append({'case': case, 'status': 'passed-recorded-review-invalidation'})
    assert before == {name: digest(original_bytes(GLOSSARY / name)) for name in names}
    receipt = {
        'status': 'passed-positive-control-and-' + str(len(cases)) + '-intended-rejections',
        'sourceDraftRawSha256': before['source-draft.json'],
        'validatorRawSha256': digest(original_bytes(ROOT / 'tools/validate_glossary_draft.py')),
        'refreshRawSha256': digest(original_bytes(ROOT / 'tools/refresh_glossary_documents.py')),
        'editorialHelperRawSha256': digest(original_bytes(ROOT / 'tools/editorial_review_status.py')),
        'cases': cases,
        'editorialRecordCases': review_cases,
        'limits': ['Mocks replace document file views and write durability. The source index and validator run unchanged.',
                   'No real interrupted write, crash durability or transaction rollback is verified.',
                   'Structural guards do not establish semantic accuracy, complete regional inventory or runtime behavior.'],
        'originalDocumentsUnchanged': True,
    }
    (GLOSSARY / 'current-guard-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'cases': len(cases), 'originalDocumentsUnchanged': True}))


if __name__ == '__main__':
    main()
