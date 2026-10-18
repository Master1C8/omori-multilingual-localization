#!/usr/bin/env python3
"""Integrate accepted assigned-model-authored data without generating wording."""
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
master = Path('/Users/antonkrutov/Desktop/SiteForMods')
local = root / 'glossary/ru'
source = master / 'data/games/omori/glossary.json'
translations = master / 'data/games/omori/glossary-translations.json'
review = master / 'data/games/omori/glossary-review/ru-2026-10-12'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source) == '11d48e714e6ba1652ca76ed45c4d7622e22312547410bc694c1f46181a18773b'
assert sha(local / 'approved.json') == '100e203e9ce6282bc2023e13f8b239dbcacdb552da24a05324d7789e952c8d15'
audits = json.loads((local / 'editorial-audits.json').read_text())
assert audits['status'] == 'accepted' and audits['cleanFullAudits'] == 2
for audit in audits['audits']:
    assert audit['status'] == 'complete-clean' and not audit['findings']
    assert [i for rr in audit['actualReadRanges'] for i in range(rr['start'], rr['end']+1)] == list(range(1,700))
layer = json.loads((local / 'approved.json').read_text())
assert list(layer) == [entry['id'] for entry in json.loads(source.read_text())]
existing = json.loads(translations.read_text())
assert 'ru' not in existing, 'An active Russian layer appeared; reconcile before replacing.'
assert not review.exists(), 'Review destination exists; reconcile before retrying.'
# Prepare the evidence first; the active-locale JSON is a single-file replacement.
# These separate evidence/content writes are not claimed to be a transaction.
review.mkdir(parents=True)
for name in ['approved.json','editorial-audits.json','terminology-decisions.md','draft-corrections.json','squizzard-name-evidence.json']:
    shutil.copyfile(local / name, review / name)
shutil.copyfile(root / 'glossary/process-binding.md', review / 'process-binding.md')
shutil.copyfile(source, review / 'source.json')
(review / 'README.md').write_text('''# OMORI Russian glossary acceptance\n\nStandard localization; 699 English-source entries translated directly into ru by the assigned Codex model. All stable IDs and order retained. Two consecutive full EN/RU term-and-meaning audits of unchanged content found no objective issue. Each pass inspected every concept occurrence, including inflections, compounds, abbreviations and cross-references. Actual read ranges and exact input hashes are in `editorial-audits.json`; scripts validate structure, not editorial quality. No independent reviewer, subagent, pivot translation or external text generator was used.\n\n`approved.json` is the complete accepted Russian layer, serialized byte-for-byte like the game-project snapshot. `source.json` is the unchanged protected English input. The original 144-entry source and 26 former locale layers remain in the pre-restart archive. This integration adds only the fresh Russian layer; it does not authorize CMS publication, deployment or game runtime changes.\n\nMaterial decisions: preserve hidden identities and player-name controls; use owner-approved R001/P001 and individual neutrality policies without inventing sex; keep DEEP WELL and DEEPER WELL distinct; preserve state tiers, ordered ROCK/PAPER/SCISSORS and password mappings, item target scopes and conditional effects. Genuine artist credits and quoted English evidence/code literals remain intentional exceptions. Renderer feasibility and in-game display are unverified under the owner's static-only scope. Measured token telemetry is unavailable.\n''')
existing['ru'] = layer
new_bytes = (json.dumps(existing, ensure_ascii=False, indent=2)+'\n').encode()
temp = translations.with_suffix('.json.ru-tmp')
temp.write_bytes(new_bytes)
temp.replace(translations)
assert json.loads(translations.read_text())['ru'] == layer
assert sha(review / 'approved.json') == sha(local / 'approved.json')
assert sha(source) == sha(review / 'source.json')
# Replace only the obsolete active-empty assertion, preserving archive/source guards.
test = master / 'tests/omori-glossary.test.ts'
t = test.read_text()
old = 'test("OMORI restart uses the reviewed source and starts active translations empty", () => {'
assert old in t
t = t.replace(old, 'test("OMORI restart preserves its reviewed source and accepts the fresh Russian layer", () => {', 1)
old_assert = '  assert.deepEqual(OMORI_GLOSSARY_TRANSLATIONS, {});'
assert old_assert in t
t = t.replace(old_assert, '''  const ru = OMORI_GLOSSARY_TRANSLATIONS.ru;
  assert.ok(ru);
  assert.deepEqual(Object.keys(ru), OMORI_GLOSSARY.map(({ id }) => id));
  const reviewedBytes = readFileSync(new URL(
    "../data/games/omori/glossary-review/ru-2026-10-12/approved.json", import.meta.url,
  ));
  assert.equal(createHash("sha256").update(reviewedBytes).digest("hex"),
    "100e203e9ce6282bc2023e13f8b239dbcacdb552da24a05324d7789e952c8d15");
  assert.deepEqual(ru, JSON.parse(reviewedBytes.toString("utf8")));''', 1)
test.write_text(t)
print(f'Integrated ru: {len(layer)} entries; exact snapshot/source parity; preserved {len(existing)-1} other active layers.')
