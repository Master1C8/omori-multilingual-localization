#!/usr/bin/env python3
"""Refresh derived draft documentation without choosing identities or gender."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from editorial_review_status import recorded_review_count


ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / 'glossary'


def write_json(path, value):
    # Separate document writes, not a transaction. The validator rejects mixed
    # versions through source/index/decision hash bindings before acceptance.
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    draft_path = GLOSSARY / 'source-draft.json'
    draft = json.loads(draft_path.read_text())
    evidence_path = GLOSSARY / 'entry-evidence.json'
    evidence = json.loads(evidence_path.read_text())
    roster_path = GLOSSARY / 'roster-review.json'
    roster = json.loads(roster_path.read_text())
    decisions_path = GLOSSARY / 'owner-decisions.json'
    decision_document = json.loads(decisions_path.read_text())
    decisions = decision_document['decisions']
    regional_decisions = decision_document.get('regionalDecisions', [])
    minor_policies = decision_document.get('minorSpeakerPolicies', [])
    assert [e['id'] for e in draft] == [e['id'] for e in evidence['entries']], 'Author exact evidence before refresh'
    draft_hash = hashlib.sha256(draft_path.read_bytes()).hexdigest()
    decisions_hash = hashlib.sha256(decisions_path.read_bytes()).hexdigest()
    evidence['sourceDraftRawSha256'] = draft_hash
    evidence['ownerDecisionsRawSha256'] = decisions_hash
    roster['sourceDraftRawSha256'] = draft_hash
    roster['ownerDecisionsRawSha256'] = decisions_hash
    roster['kindCounts'] = dict(Counter(r['kind'] for r in roster['labels']))
    write_json(evidence_path, evidence)
    write_json(roster_path, roster)
    recorded_audits = recorded_review_count(GLOSSARY, draft)

    lines = ['# OMORI source-glossary evidence', '',
             'Date: 2026-10-12. English Steam build 8879120. Standard localization.', '',
             'Status: ' + ('reviewed local proposal; protected canonical integration awaits owner authorization.'
                          if recorded_audits >= 2 else 'editorial preparation incomplete.'),
             'Recorded clean full-entry audits bound to these exact inputs: ' + str(recorded_audits) + '.',
             'The structure/provenance report is `draft-validation.json`; it does not certify semantic accuracy.', '',
             '## Primary references', '',
             'This table mechanically renders authored selections from `entry-evidence.json`.',
             'References establish provenance. Authored all-entry reviews are recorded separately in editorial-audits.json.',
             'Research statuses and pending-review notes below describe their collection checkpoints, not the later full-review result.', '',
             '| Draft ID | Primary asset/key references | Gender/pronoun evidence class |',
             '| --- | --- | --- |']
    for proof in evidence['entries']:
        refs = '<br>'.join('`' + key + '`' for key in proof['sourceIds'])
        lines.append('| ' + proof['id'] + ' | ' + refs + ' | ' + proof['genderEvidence'] + ' |')
    lines += ['', '## Entry-specific evidence notes', '']
    boilerplate = 'Name and term selection is not final. Complete roster and two clean full audits remain required.'
    for proof in evidence['entries']:
        notes = [n for n in proof['notes'] if n != boilerplate]
        if notes:
            lines.append('- `' + proof['id'] + '`: ' + ' '.join(notes))
    lines += ['', '## Supporting pages', '',
              'These are secondary sources read on 2026-10-12, including readable indexed article content',
              'where direct page retrieval was unavailable. A failed fetch is not a successful page read.',
              'Explicit community gender assertions are distinguished from primary game evidence in the table.',
              'Unknown, hidden, variable and ambiguous remain distinct categories; appearance is not evidence.', '']
    for entry in draft:
        if 'sourceUrl' in entry:
            lines.append('- [' + entry['sourceTitle'] + '](' + entry['sourceUrl'] + ') — `' + entry['id'] + '`.')
    lines += ['', '## Individual owner decisions', '',
              'Exact answers are in `owner-decisions.json`; context and open cases are in `owner-cases.md`.',
              'An accepted strategy preserves uncertainty and does not establish canonical sex or a nonbinary identity.', '']
    for decision in decisions:
        lines.append('- `' + decision['caseId'] + '` / `' + decision['glossaryId'] + '`: owner approved ' +
                     'name and neutral constructions on ' + decision['date'] + '. Applies to this case only.' +
                     (' Catalog scope: `' + decision['catalogScope'] + '`.' if 'catalogScope' in decision else ''))
    lines += ['', '## Regional owner decisions', '']
    for policy in regional_decisions:
        lines.append('- `' + policy['caseId'] + '` / ' + policy['region'] + ': ' + policy['scope'])
        lines.append('  Recorded ' + policy['date'] + '; current static mapping covers ' +
                     str(len(policy['mappings'])) + ' entries. Full inventory and runtime remain unaccepted.')
    lines += ['', '## Minor-speaker owner policy', '']
    for policy in minor_policies:
        lines.append('- `' + policy['caseId'] + '`: ' + policy['scope'])
        lines.append('  Distinct indexed messages are counted conservatively; identical namebox/presentation')
        lines.append('  differences do not create another utterance. Edited wording and unresolved macros stay distinct.')
        lines.append('  Exact groups and all bound occurrences are recorded in owner-decisions.json.')
        lines.append('  Collective roles use individual counts only with an authored, complete scene-speaker census')
        lines.append('  and exact event-to-message consumers. A shared label alone cannot establish separate individuals.')
        lines.append('  Current mapping covers ' + str(len(policy['mappings'])) + ' entries; this is not a runtime or editorial gate.')
    lines += ['', '## Scope and integration', '',
              'A label is not necessarily one individual. STRANGER has multiple separately scoped scene referents;',
              'the U006 decision concerns only the BASIL-associated speaking shadow in bs_basils_shadow.',
              'Collective nameboxes retain their individual members and participant number.', '',
              'The historical master source and 26 locale layers have not been replaced. Preserve matching',
              'stable IDs, assess meaning/ID changes and retranslate affected layers before canonical acceptance.',
              'New individual SLIME SISTER and clone entries do not silently remove historical collective entries.', '',
              'The 585-label static roster has authored coverage. Dynamic reachability, the accepted reinsertion inventory,',
              'runtime rendering and publication remain separate uncompleted gates.', '']
    (GLOSSARY / 'glossary-sources.md').write_text('\n'.join(lines))
    print(json.dumps({'draftEntries': len(draft), 'characterEntries': sum(e['category'] == 'Character' for e in draft),
                      'ownerDecisions': len(decisions), 'regionalOwnerDecisions': len(regional_decisions),
                      'minorSpeakerPolicies': len(minor_policies),
                      'sourceDraftRawSha256': draft_hash}, indent=2))


if __name__ == '__main__':
    main()
