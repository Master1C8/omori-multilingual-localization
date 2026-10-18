"""Baseline-selection boundary only; the native installer is exercised separately."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/visual-qa'))
from runtime import resource_baseline,sha
catalog=json.loads((ROOT/'build/installer/payload-visual-repaired-20261017-02/catalog.json').read_text())
original,profile=resource_baseline(catalog);assert profile=='historical-russian'
fix=json.loads((ROOT/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json').read_text());build=ROOT/fix['newNativeBuild'];manifest=json.loads((build/'manifest.json').read_text())
repaired=copy.deepcopy(catalog);ru=next(row for row in repaired['locales'] if row['code']=='ru')
ru['files']={row['path']:{'sha256':row['sha256']} for row in manifest['files']};ru['archiveSha256']=sha(build/'omori-ru-direct-8879120.zip')
assets,profile=resource_baseline(repaired);assert profile=='russian-level-repaired' and assets==fix['finalRussianAssets']
assert {k for k in original if original[k]!=assets[k]}==set(fix['changedResourceFiles'])
bad=copy.deepcopy(repaired);next(iter(next(r for r in bad['locales'] if r['code']=='ru')['files'].values()))['sha256']='0'*64
try:resource_baseline(bad)
except AssertionError as e:assert str(e)=='Unrecognized Russian catalog baseline'
else:raise AssertionError('Unknown baseline was accepted')
print('PASS actual legacy/repaired RU catalog profiles, exact three-file delta, and unknown-profile rejection. No installed file was written.')
