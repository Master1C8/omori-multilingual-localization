#!/usr/bin/env python3
"""Bind an actual coordinator case read to current authored text, never certify humor.

Known-regression checks complement recorded semantic reading. They are not an
independent review, a general rhyme detector, or game/rendering acceptance.
"""
import argparse
import json
import re
from pathlib import Path
from source_prepare import strict_json, sha


POEM = 'languages/en/Bestiary.HERO#["Information",129,"text"]'
BOTTLES = [
    'languages/en/dreamworld_npc_dialogue_otherworld.HERO#["message_162","text"]',
    'languages/en/dreamworld_npc_dialogue_frozenforest.HERO#["message_31","text"]',
]
BED_DEFINITIONS = [
    'data/Items.KEL#[163,"description"]',
    'languages/en/dw_flavor_text.HERO#["message_512","text"]',
    'languages/en/sidequest_dreamworld_bed.HERO#["message_24","text"]',
]
REDACTED_EARLY = {
    'languages/en/hidden_library.HERO#["message_2","text"]': 'Первым задремал',
    'languages/en/hidden_library.HERO#["message_40","text"]': '☐ думал',
    'languages/en/hidden_library.HERO#["message_43","text"]': '☐ наблюдал',
    'languages/en/hidden_library.HERO#["message_21","text"]': 'не кто иной',
    'languages/en/hidden_library.HERO#["message_70","text"]': 'ему досталась',
    'languages/en/hidden_library.HERO#["message_71","text"]': '☐ безучастно смотрел',
}


def registry_contract(registry):
    fields = ['id', 'title', 'category', 'unitIds', 'evidence', 'observed',
              'invariants', 'dependencyLimits', 'analysisStatus']
    cases = [{**{key: case[key] for key in fields},
              'adaptationRoute': case['ru']['adaptationRoute'],
              'acceptanceScenarios': case['ru']['acceptanceScenarios']}
             for case in registry['cases']]
    return sha(json.dumps({'sourceBindings': registry['sourceBindings'], 'cases': cases},
                          ensure_ascii=False, sort_keys=True).encode())


def check_contracts(targets):
    for identifier, early_marker in REDACTED_EARLY.items():
        if early_marker in targets[identifier]:
            raise ValueError('SP013: premature redacted-participant gender marker')
    poem = targets[POEM]
    if 'грустит...\nНо вечным сном не спит.' in poem:
        raise ValueError('SP008: known rhyming verse contradicts the no-rhyme reaction')
    if not all(x in poem for x in ['не мёртвый', '- ОМОРИ', 'Тут даже рифмы нет', '- ОБРИ']):
        raise ValueError('SP008: non-death, attribution or criticism missing')
    lyrics = []
    for identifier in BOTTLES:
        text = targets[identifier]
        if 'аморе' not in text:
            raise ValueError('SP016: name/song phonetic cue missing')
        match = re.search(r'Когда луна.*почти как «аморе»!', text.replace('<br>', ' '))
        if not match:
            raise ValueError('SP016: complete shared lyric missing')
        lyrics.append(re.sub(r'_{5,8}', '<blank>', match.group()))
    if lyrics[0] != lyrics[1]:
        raise ValueError('SP016: bottle variants diverge')
    for identifier in BED_DEFINITIONS:
        text = targets[identifier]
        if 'B.E.D.' not in text or 'кровать' not in text.lower():
            raise ValueError('SP018: approved name/ordinary-bed link missing')
    for identifier in BED_DEFINITIONS[:2]:
        text = re.sub(r'\\c\[\d+\]|<br>', ' ', targets[identifier])
        if 'УЛУЧШЕННЫЙ УНИЧТОЖИТЕЛЬ УСТАЛОСТИ' not in ' '.join(text.split()):
            raise ValueError('SP018: approved expansion missing')


def verify_review(root, path):
    from assemble_ru_resources import read_pairs
    from special_scene_registry import validate
    proof = strict_json(path.read_bytes())
    if proof.get('status') != 'complete coordinator actual paired case review; independent pending':
        raise ValueError('Actual coordinator special-scene review required')
    registry, known = validate(root / 'source/special-scenes-8879120.json')
    if proof['registryContractSha256'] != registry_contract(registry):
        raise ValueError('Special-scene source/adaptation contract changed')
    membership = {c['id']: c['unitIds'] for c in registry['cases']}
    expected = set().union(*(set(v) for v in membership.values()))
    if proof['caseMembership'] != membership or not expected <= known:
        raise ValueError('Special-scene membership changed')
    pairs, corpus, dependencies = read_pairs(root)
    ordered = [u['id'] for u, _ in pairs if u['id'] in expected]
    if proof['reviewedIds'] != ordered or proof['caseCount'] != len(membership):
        raise ValueError('Actual special-scene reading coverage incomplete')
    authors = {p: h for p, h in dependencies.items() if p.startswith('translation/ru/batches/')}
    if proof['authorDependencies'] != authors or proof['corpusManifestRawSha256'] != corpus:
        raise ValueError('Special-scene reviewed author graph changed')
    for file, digest in proof['inputDependencies'].items():
        target = (root / file).resolve()
        if not target.is_relative_to(root) or sha(target.read_bytes()) != digest:
            raise ValueError('Special-scene review input changed: ' + file)
    rows = [strict_json(line) for line in (root / proof['rows']).read_bytes().splitlines()]
    actual = {u['id']: (u, e) for u, e in pairs}
    if [r['id'] for r in rows] != ordered:
        raise ValueError('Special-scene review rows incomplete')
    for row in rows:
        unit, entry = actual[row['id']]
        if (row['source'], row['serializedTarget'], row['target']) != (
            unit['source'], entry['target'], entry.get('encodedPayload', {}).get('decodedTarget', entry['target'])
        ):
            raise ValueError('Special-scene actual reviewed text changed: ' + row['id'])
    decisions = strict_json((root / proof['decisions']).read_bytes())
    if [c['id'] for c in decisions['cases']] != list(membership):
        raise ValueError('Special-scene actual decisions incomplete')
    for decision in decisions['cases']:
        if decision['sourceUnitIds'] != membership[decision['id']] or not decision['decision']:
            raise ValueError('Special-scene decision group incomplete')
    check_contracts({identifier: actual[identifier][1]['target'] for identifier in expected})
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    proof = verify_review(root, args.review.resolve())
    print({'binding': 'passed', 'cases': proof['caseCount'], 'actualPairedIds': len(proof['reviewedIds']),
           'independent': 'pending', 'runtime': 'not-run'})


if __name__ == '__main__':
    main()
