#!/usr/bin/env python3
"""Validate draft structure and evidence bindings; never certify editorial readiness."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from editorial_review_status import recorded_review_count


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utterance_groups(records):
    """Conservatively count indexed messages, not runtime conversations.

    Deduplicate only explicit namebox/presentation differences and whitespace.
    Keep punctuation, wording, case, variables and unexpanded macros distinct.
    This deliberately cannot establish semantic identity or corpus completeness.
    """
    groups = {}
    for key in sorted(records):
        value = records[key]['source']
        value = re.sub(r'(?<!\\)\\n<[^>]*>', '', value)
        value = re.sub(r'(?<!\\)\\(?:[.!|{}^$<>]|(?:com|sinv|quake|c)\[[^\]]*\])', '', value, flags=re.I)
        value = re.sub(r'<br\s*/?>', ' ', value, flags=re.I)
        value = re.sub(r'\s+', ' ', value).strip()
        groups.setdefault(value, []).append(key)
    return sorted(groups.values(), key=lambda keys: keys[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--research', default='research-8879120-02')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    research = project / 'source' / args.research
    glossary = project / 'glossary'
    draft_file = glossary / 'source-draft.json'
    draft = json.loads(draft_file.read_text())
    evidence = json.loads((glossary / 'entry-evidence.json').read_text())
    roster = json.loads((glossary / 'roster-review.json').read_text())
    manifest = json.loads((research / 'manifest.json').read_text())
    index_hash = sha(research / 'strings.jsonl')
    draft_hash = sha(draft_file)
    assert index_hash == manifest['researchIndexSha256'], 'Research index changed'
    assert isinstance(draft, list) and draft, 'Empty or malformed draft'
    ids = [e['id'] for e in draft]
    assert len(ids) == len(set(ids)), 'Duplicate glossary ID'
    assert ids[0] == 'omori', 'Required player entry must remain first'
    allowed = {'id', 'priority', 'term', 'meaning', 'category', 'sourceTitle', 'sourceUrl'}
    for e in draft:
        assert not set(e) - allowed, (e['id'], 'Unexpected schema field')
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', e['id']), 'Invalid ID'
        assert e['priority'] in {'P0', 'P1', 'P2'}, 'Invalid priority'
        for key, value in e.items():
            assert isinstance(value, str) and value.strip(), (e['id'], key, 'Empty field')
            assert not any(0xD800 <= ord(c) <= 0xDFFF for c in value), 'Invalid Unicode'
        assert bool(e.get('sourceTitle')) == bool(e.get('sourceUrl')), 'Unpaired source metadata'
        if 'sourceUrl' in e:
            url = urlparse(e['sourceUrl'])
            assert url.scheme in {'http', 'https'} and url.netloc, 'Invalid supporting URL'
    for document in [evidence, roster]:
        assert document['researchIndexRawSha256'] == index_hash, 'Stale research binding'
        assert document['sourceDraftRawSha256'] == draft_hash, 'Stale draft binding'
    assert [e['id'] for e in evidence['entries']] == ids, 'Evidence ID/order mismatch'
    decisions_path = glossary / 'owner-decisions.json'
    decision_document = json.loads(decisions_path.read_text())
    decisions = decision_document['decisions']
    regional_decisions = decision_document.get('regionalDecisions', [])
    minor_policies = decision_document.get('minorSpeakerPolicies', [])
    decision_ids = [d['glossaryId'] for d in decisions]
    case_ids = [d['caseId'] for d in decisions]
    assert len(set(decision_ids)) == len(decision_ids), 'Duplicate individual decision'
    assert len(set(case_ids)) == len(case_ids), 'Duplicate case ID'
    assert set(decision_ids) <= set(ids), 'Decision entry missing'
    policy_ids = {e['id'] for e in draft if 'Owner-approved strategy:' in e['meaning']}
    assert policy_ids == set(decision_ids), 'Unapproved or omitted individual strategy'
    regional_ids = {m['glossaryId'] for policy in regional_decisions for m in policy['mappings']}
    regional_policy_ids = {e['id'] for e in draft if 'Owner-approved regional strategy:' in e['meaning']}
    assert regional_policy_ids == regional_ids, 'Unapproved or omitted regional strategy'
    assert regional_ids <= set(ids), 'Regional decision entry missing'
    assert len({p['caseId'] for p in regional_decisions}) == len(regional_decisions), 'Duplicate regional case'
    minor_ids = {m['glossaryId'] for policy in minor_policies for m in policy['mappings']}
    minor_marked_ids = {e['id'] for e in draft if 'Owner-approved minor-speaker strategy:' in e['meaning']}
    assert minor_marked_ids == minor_ids, 'Unapproved or omitted minor-speaker strategy'
    assert minor_ids <= set(ids), 'Minor-speaker entry missing'
    assert not minor_ids & set(decision_ids), 'Individual decision already owns minor-speaker entry'
    assert len({p['caseId'] for p in minor_policies}) == len(minor_policies), 'Duplicate minor-speaker policy'
    for document in [evidence, roster]:
        assert document['ownerDecisionsRawSha256'] == sha(decisions_path), 'Stale decision binding'
    proofs = {e['id']: e for e in evidence['entries']}
    for decision in decisions:
        assert proofs[decision['glossaryId']]['genderEvidence'] == 'owner-decision-' + decision['caseId'], 'Wrong decision attribution'
    source_ids = set()
    regional_reference_ids = {key for p in regional_decisions for m in p['mappings']
                              for key in m['sourceIds'] + m['consumerIds']}
    minor_reference_ids = {key for p in minor_policies for m in p['mappings'] for key in m['sourceIds']}
    minor_consumer_ids = {key for p in minor_policies for m in p['mappings']
                          for instance in m.get('speakerInstances', []) for key in instance['consumerIds']}
    regional_records = {}
    with (research / 'strings.jsonl').open() as source:
        for line in source:
            record = json.loads(line)
            key = record['id']
            assert key not in source_ids, 'Duplicate research scalar identity'
            source_ids.add(key)
            if key in regional_reference_ids | minor_reference_ids | minor_consumer_ids:
                regional_records[key] = record
    for e, proof in zip(draft, evidence['entries']):
        assert proof['sourceIds'] and set(proof['sourceIds']) <= source_ids, 'Missing primary reference'
        urls = [e['sourceUrl']] if 'sourceUrl' in e else []
        assert proof['supportingUrls'] == urls, 'Supporting source mismatch'
    original_labels = json.loads((research / 'speaker-labels.json').read_text())
    assert [r['label'] for r in roster['labels']] == [r['label'] for r in original_labels], 'Roster label loss/order change'
    for current, original in zip(roster['labels'], original_labels):
        assert current['sourceIds'] == original['sourceIds'], 'Roster occurrence loss'
        assert set(current['sourceIds']) <= source_ids, 'Roster source missing'
        if current['glossaryId']:
            assert current['glossaryId'] in ids, 'Roster refers to absent draft ID'
    labels_by_name = {r['label']: r for r in roster['labels']}
    entries_by_id = {e['id']: e for e in draft}
    for policy in minor_policies:
        assert policy['strategy'] == 'retain-name-and-neutral-constructions', 'Unsupported minor-speaker strategy'
        assert policy['maxDistinctUtterancesExclusive'] == 10, 'Owner minor-speaker threshold changed'
        assert len({m['glossaryId'] for m in policy['mappings']}) == len(policy['mappings']), 'Duplicate minor-speaker entry'
        for mapping in policy['mappings']:
            entry_id = mapping['glossaryId']
            expected = set()
            for row in roster['labels']:
                if row['glossaryId'] == entry_id:
                    expected.update(row['sourceIds'])
                else:
                    for scope in row.get('resolvedOccurrenceScopes', []):
                        if scope['glossaryId'] == entry_id:
                            expected.update(scope['sourceIds'])
            assert mapping['sourceIds'] and len(set(mapping['sourceIds'])) == len(mapping['sourceIds']), 'Empty or duplicate minor-speaker scope'
            assert set(mapping['sourceIds']) == expected, 'Minor-speaker count omitted or exceeded bound occurrences'
            records = {key: regional_records[key] for key in mapping['sourceIds']}
            assert all(record['asset'].startswith('languages/en/') and len(record['path']) == 2
                       and record['path'][1] == 'text' for record in records.values()), 'Minor-speaker count includes non-message record'
            groups = utterance_groups(records)
            assert mapping['utteranceGroups'] == groups, 'Minor-speaker duplicate accounting differs'
            count = len(groups)
            if mapping.get('countMode') == 'per-scene-speaker':
                instances = mapping.get('speakerInstances', [])
                assert instances, 'Minor-speaker instance census is empty'
                identities = [(i['mapAsset'], i['eventId']) for i in instances]
                assert len(set(identities)) == len(identities), 'Duplicate minor-speaker instance identity'
                assert set().union(*(set(i['sourceIds']) for i in instances)) == set(records), 'Minor-speaker instance census omitted bound utterances'
                counts = []
                for instance in instances:
                    assert instance['sourceIds'] and set(instance['sourceIds']) <= set(records), 'Invalid minor-speaker instance sources'
                    consumers = [regional_records[k] for k in instance['consumerIds']]
                    assert consumers and all(c['asset'] == instance['mapAsset']
                        and len(c['path']) == 8 and c['path'][:2] == ['events', instance['eventId']]
                        and c['path'][2] == 'pages' and c['path'][4] == 'list'
                        and c['path'][6:] == ['parameters', 0] for c in consumers), 'Minor-speaker consumer belongs to another scene identity'
                    for key in instance['sourceIds']:
                        record = records[key]
                        expected_call = 'ShowMessage ' + Path(record['asset']).stem + '.' + record['path'][0]
                        assert any(c['source'] == expected_call for c in consumers), 'Minor-speaker instance lacks matching message consumer'
                    instance_groups = utterance_groups({k: records[k] for k in instance['sourceIds']})
                    assert instance['utteranceGroups'] == instance_groups, 'Minor-speaker instance duplicate accounting differs'
                    counts.append(len(instance_groups))
                count = max(counts)
            else:
                assert mapping.get('countMode', 'all-bound-occurrences') == 'all-bound-occurrences', 'Unsupported minor-speaker count mode'
                assert not mapping.get('speakerInstances'), 'Unselected minor-speaker instance census'
            assert mapping['distinctUtterances'] == count, 'Minor-speaker count differs'
            assert count < policy['maxDistinctUtterancesExclusive'], 'Minor-speaker has ten or more distinct utterances'
            assert proofs[entry_id]['genderEvidence'] == 'owner-policy-' + policy['caseId'], 'Wrong minor-speaker policy attribution'
            assert set(proofs[entry_id]['sourceIds']) & expected, 'Minor-speaker proof lacks bound utterance'
    for policy in regional_decisions:
        assert policy['strategy'] == 'retain-name-and-neutral-constructions', 'Unsupported regional strategy'
        assert policy['mapAssets'] and len(set(policy['mapAssets'])) == len(policy['mapAssets']), 'Invalid regional maps'
        assert len({m['glossaryId'] for m in policy['mappings']}) == len(policy['mappings']), 'Duplicate regional entry'
        for mapping in policy['mappings']:
            entry = entries_by_id[mapping['glossaryId']]
            if 'preservedFactPrefix' in mapping:
                assert entry['meaning'].startswith(mapping['preservedFactPrefix']), 'Regional strategy erased canonical facts'
            row = labels_by_name[mapping['label']]
            assert mapping['sourceIds'] and set(mapping['sourceIds']) <= set(row['sourceIds']), 'Regional occurrence exceeds speaker scope'
            assert set(mapping['sourceIds'] + mapping['consumerIds']) <= set(regional_records), 'Regional reference missing'
            consumers = [regional_records[k] for k in mapping['consumerIds']]
            assert consumers and all(c['asset'] in policy['mapAssets'] for c in consumers), 'Regional consumer outside approved maps'
            for key in mapping['sourceIds']:
                record = regional_records[key]
                assert len(record['path']) == 2 and record['path'][1] == 'text', 'Invalid regional message path'
                expected = 'ShowMessage ' + Path(record['asset']).stem + '.' + record['path'][0]
                assert any(c['source'] == expected for c in consumers), 'Regional occurrence lacks matching consumer'
            scopes = [s for s in row.get('regionalAddressScopes', []) if s['caseId'] == policy['caseId']
                      and s['glossaryId'] == mapping['glossaryId']]
            assert len(scopes) == 1 and scopes[0]['sourceIds'] == mapping['sourceIds'], 'Regional roster scope mismatch'
            if row['label'] == '???':
                assert row['glossaryId'] is None, 'Regional identity was applied to the whole anonymous label'
            if row['glossaryId'] is None:
                assert any(s['glossaryId'] == mapping['glossaryId'] and s['sourceIds'] == mapping['sourceIds']
                           for s in row.get('resolvedOccurrenceScopes', [])), 'Anonymous regional identity lacks occurrence mapping'
    for decision in decisions:
        if 'catalogScope' in decision:
            prefix = decision['catalogScope'] + '#'
            proof = proofs[decision['glossaryId']]
            assert all(k.startswith(prefix) for k in proof['sourceIds']), 'Decision evidence exceeds catalog scope'
            row = labels_by_name[decision['label']]
            scope = row['caseScope']
            assert scope['catalog'] == decision['catalogScope'], 'Wrong roster decision scope'
            assert scope['glossaryId'] == decision['glossaryId'], 'Wrong scoped glossary ID'
            assert scope['sourceIds'] and all(k.startswith(prefix) for k in scope['sourceIds']), 'Roster approval exceeds catalog scope'
            if 'sourceIds' in decision:
                approved = decision['sourceIds']
                assert approved and len(set(approved)) == len(approved), 'Invalid approved occurrence scope'
                assert set(proof['sourceIds']) == set(approved), 'Decision evidence differs from approved occurrence scope'
                assert set(scope['sourceIds']) == set(approved), 'Roster case differs from approved occurrence scope'
                bound = {key for item in row.get('resolvedOccurrenceScopes', [])
                         if item['glossaryId'] == decision['glossaryId'] for key in item['sourceIds']}
                assert bound == set(approved), 'Approved voice binding differs from occurrence scope'
            if row['kind'] == 'multiple-referents-label':
                assert row['glossaryId'] is None, 'Scoped approval was applied to the whole mixed label'
    fixture_path = project / 'source' / 'macro-dispatch-verification.json'
    fixture = json.loads(fixture_path.read_text())
    expected = ['\x1bn<VANCE>Hello', '\x1bn<VANCE>Hello', '\x1bn<VAN>Hello', r'\\vanHello']
    expected_inputs = [r'\vanHello', r'\m[van]Hello', r'\m[203]Hello', r'\\vanHello']
    assert [c['input'] for c in fixture['cases']] == expected_inputs, 'Unexpected fixture input'
    assert [c['expanded'] for c in fixture['cases']] == expected, 'Exact dispatch result differs'
    assert fixture['pluginConfigurationSha256'] == manifest['pluginConfigurationSha256'], 'Fixture configuration differs'
    assert fixture['pluginHashes'] == manifest['macroDispatchPluginHashes'], 'Fixture plugin version differs'
    recorded_audits = recorded_review_count(glossary, draft)
    result = {
        'status': 'passed-structural-and-provenance-checks-only',
        'sourceDraftRawSha256': draft_hash,
        'researchIndexRawSha256': index_hash,
        'validatorRawSha256': sha(Path(__file__).resolve()),
        'draftEntries': len(ids),
        'evidenceEntries': len(evidence['entries']),
        'primaryReferences': sum(len(e['sourceIds']) for e in evidence['entries']),
        'individualOwnerDecisions': len(decisions),
        'regionalOwnerDecisions': len(regional_decisions),
        'regionalMappedEntries': len(regional_ids),
        'minorSpeakerPolicies': len(minor_policies),
        'minorSpeakerMappedEntries': len(minor_ids),
        'rosterLabels': len(roster['labels']),
        'rosterKindCounts': dict(Counter(r['kind'] for r in roster['labels'])),
        'macroDispatchCases': len(fixture['cases']),
        'recordedCleanFullEditorialAudits': recorded_audits,
        'editorialRecordRawSha256': sha(glossary / 'editorial-audits.json'),
        'sourceReadiness': ('reviewed-local-proposal; protected-integration-requires-owner-authorization'
                            if recorded_audits >= 2 else 'needs-full-editorial-review'),
        'limits': ['Does not validate the truth of definitions, pronoun antecedents or identities.',
                  'The review count reports authored evidence bound to current inputs; it is not an automated editorial judgment.',
                  'Does not prove exhaustive source inventory, reachability or reinsertion.',
                  'Fixture uses original macro code with rendering and storage replaced by stubs.',
                  'Does not run the master canonical-bundle CLI or validate historical locale layers.'],
    }
    if args.report:
        target = args.report.resolve()
        assert project in target.parents, 'Report must remain inside canonical project'
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
