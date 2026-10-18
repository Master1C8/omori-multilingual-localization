#!/usr/bin/env python3
"""Integrate reviewed OMORI EN/RU meanings into the canonical site checkout."""
import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path('/Users/antonkrutov/Desktop/SiteForMods')
BASE = ROOT / 'glossary/compact-public'
DEST = MASTER / 'data/games/omori'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(*args):
    return subprocess.check_output(args, cwd=MASTER, text=True).strip()


def main():
    baseline = read(ROOT / 'source/compact-public-publication-baseline-2026-10-13.json')
    assert run('git', 'status', '--porcelain') == '', 'Owner changes present; reconcile before integration'
    assert run('git', 'branch', '--show-current') == 'main'
    assert run('git', 'rev-parse', 'HEAD') == baseline['masterHead'], 'Master changed; reconcile baseline'
    assert run('git', 'remote', 'get-url', 'origin') == baseline['masterRemote']
    for relative, expected in baseline['masterFileHashes'].items():
        assert sha(MASTER / relative) == expected, f'Canonical input changed: {relative}'
    provenance = DEST / 'glossary-sources.md'
    old_provenance = provenance.read_text()
    heading = '# OMORI canonical source evidence\n\n'
    assert old_provenance.startswith(heading)
    old_source = read(DEST / 'glossary.json')
    old_translations = read(DEST / 'glossary-translations.json')
    assert old_source == read(ROOT / 'glossary/source-draft.json')
    assert old_translations['ru'] == read(ROOT / 'glossary/ru/approved.json')
    receipt = read(BASE / 'assembly.json')
    acceptance = read(BASE / 'acceptance.json')
    assert acceptance['status'] == 'accepted' and acceptance['entries'] == 699
    assert acceptance['assemblySha256'] == sha(BASE / 'assembly.json')
    for name, digest in receipt['outputs'].items():
        assert sha(BASE / name) == digest, 'Assembly output changed'
    source, ru = read(BASE / 'approved-source.json'), read(BASE / 'approved-ru.json')
    assert len(source) == len(ru) == 699
    assert [x['id'] for x in source] == [x['id'] for x in old_source]
    for old, new in zip(old_source, source):
        assert {k:v for k,v in old.items() if k != 'meaning'} == {k:v for k,v in new.items() if k != 'meaning'}
    assert set(ru) == set(old_translations['ru'])
    for key in ru:
        assert {k:v for k,v in ru[key].items() if k != 'meaning'} == {k:v for k,v in old_translations['ru'][key].items() if k != 'meaning'}
    translations = copy.deepcopy(old_translations)
    translations['ru'] = ru
    evidence = DEST / 'glossary-review/en-ru-compact-2026-10-13'
    assert not evidence.exists(), 'Existing integration must be reconciled, never overwritten'
    evidence.mkdir()
    for directory in ['parts', 'review']:
        shutil.copytree(BASE / directory, evidence / directory)
    for name in ['assembly.json', 'acceptance.json', 'README.md']:
        shutil.copy2(BASE / name, evidence / name)
    # Per-file replacement only. Verify both outputs before any commit/publication;
    # rerun after interruption requires explicit reconciliation of the partial state.
    for target, data in [(DEST / 'glossary.json', source), (DEST / 'glossary-translations.json', translations)]:
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)
    current = (
        heading + '## Compact English and Russian descriptions — October 13, 2026\n\n'
        'The owner authorized replacing English and Russian descriptions with compact\n'
        'translation-relevant text. All 699 stable IDs, terms and source metadata remain;\n'
        'the nine other active locale layers are unchanged. Two complete clean editorial\n'
        'layers cover the new EN/RU descriptions: GPT-6.1 Sol/high author self-review and\n'
        'independent coordinator review, each with fidelity and separate native reading.\n'
        'See `glossary-review/en-ru-compact-2026-10-13/acceptance.json` and its receipts.\n\n'
        'The prior complete descriptions remain in the source-restart evidence/history\n'
        'and the game project for detailed reference and existing batch provenance.\n'
        'Other locales have not been re-reviewed against the compact source. Their\n'
        'historical review receipts remain bound to their original source versions.\n'
        'Publication is recorded separately in the compact review packet; local acceptance\n'
        'alone does not establish production state.\n\n'
        f'Current English raw-file SHA-256: `{sha(DEST / "glossary.json")}`.\n\n'
        '## Historical source restart — October 12, 2026\n\n'
    )
    temporary = provenance.with_suffix('.md.tmp')
    temporary.write_text(current + old_provenance[len(heading):])
    temporary.replace(provenance)
    assert read(DEST / 'glossary.json') == source
    actual = read(DEST / 'glossary-translations.json')
    assert actual['ru'] == ru
    assert {k:v for k,v in actual.items() if k != 'ru'} == {k:v for k,v in old_translations.items() if k != 'ru'}
    result = {'baselineHead': baseline['masterHead'], 'sourceRawSha256': sha(DEST / 'glossary.json'),
              'translationsRawSha256': sha(DEST / 'glossary-translations.json'),
              'unchangedOtherLocales': [k for k in actual if k != 'ru'],
              'publication': 'not started', 'scope': '699 meaning-only source and Russian edits'}
    (evidence / 'integration-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
