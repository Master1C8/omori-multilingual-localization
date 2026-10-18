"""Validate delivered native fifth frames, original108 preservation and restoration."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from PIL import Image,ImageChops
from wave_route import wave_ready,native_text_changed,TEXT_REGION
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];d=json.loads(a.inputs.read_text());images=root/'dist/screenshots/20261017-native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
base=read(root/'runtime/visual-qa/20261017-native/baseline.json');codes=base['requiredLocales']
protected=read(root/'runtime/visual-qa/20261018-equipment/completion.json')['nativePngHashesAfterEncoding'];assert len(protected)==108
reviews={};evidence={}
for entry in d['entries']:
 code=entry['locale'];run=Path(entry['run']);catalog=Path(entry['catalog']);assert code in codes and code not in reviews
 assert read(run/'wave-status.json')['status']=='complete'
 restored=read(run/'restoration.json');assert restored['status']=='verified' and restored['saveSlotsWritten'] is False
 assert restored['verifiedLoadedLocales']==[code] and not restored['loadEvidenceUnknownLocales']
 assert read(run/'russian-level-restoration.json')['levelRepairRestored']
 assert read(run/'protected-108.json')==protected
 assert all(sha(run/n)==h for n,h in read(run/'recipe-manifest.json').items())
 cap=read(run/code/'wave-capture.json');review=read(run/code/'visual-review.json')
 assert cap['automatedResult']=='pass' and review['status']=='pass' and review['locale']==code
 assert review['file']==cap['file']==code+'-05-joker-jash-wave.png'
 assert review['sha256']==cap['sha256']==sha(images/cap['file'])
 native=cap['nativeFocusAtCapture'];assert native['targetActive'] is False and native['frontmostPid']!=native['targetPid']
 policy=cap['state']['startupDiagnostics']['windowPolicy'];assert policy['hiddenRequested'] and not any(e['event']=='focus' for e in policy['events'])
 assert not cap['window'].get('kCGWindowIsOnscreen',False)
 settings=read(run/code/'launch-settings.json');assert settings['window']['show'] is False and settings['window']['focus'] is False
 assert settings['originalPackageSha256']==sha(run/code/'package-before.json')
 assert cap['state']['startupDiagnostics']['rendererInfo']['webgl'] is True
 assert cap['state'].get('language')=='en' or code=='ru' and cap['state'].get('language') is None
 if code!='ru':assert cap['state']['startupDiagnostics']['locale']==code
 assert cap['runtimeChannel']=='en' and cap['saveSlotLoaded']==1 and cap['saveSlotsWritten'] is False
 game=cap['gameplay'];assert game['scene']=='Scene_Map' and game['map']['id']==92 and game['map']['interpreter']['eventId']==18
 assert (game['player']['x'],game['player']['y'],game['player']['direction'])==(23,28,6)
 loaded=read(run/code/'load-first-save-semantic-result.json');assert loaded['map']['id']==92
 assert game['firstActor']==loaded['firstActor']
 wave=read(run/code/'wave-proof.json');samples=wave['samples'];assert len(samples)==3 and all(wave_ready(s) for s in samples)
 fixture=samples[0].get('fileAssets')
 if fixture:
  assert fixture['identity']=='omori-file-face-prefetch-v1' and fixture['phase']=='ready'
  assert {v['url'] for v in fixture['assets']}=={'img/faces/01_OMORI_BATTLE.png','img/faces/01_FA_OMORI_BATTLE.png'}
  assert len(fixture['assets'])==2 and all(v['state']=='loaded' and v['imageComplete'] and v['width']>0 and v['height']>0 for v in fixture['assets'])
 assert len({tuple(v['texts']) for v in samples})==1
 assert len({tuple(p['anchorY'] for p in v['sprites']) for v in samples})>1
 assert cap['frame']==wave['nativeFrames'][-1] and sha(Path(cap['frame']))==cap['sha256']
 with Image.open(wave['nativeFrames'][0]) as first_image,Image.open(wave['nativeFrames'][1]) as second_image:assert native_text_changed(first_image,second_image)
 native_attempts=[]
 for phase in wave['nativeFrames']:
  frame_path=Path(phase);rows=read(frame_path.with_name(frame_path.stem+'-native-capture-attempts.json'))
  assert 1<=len(rows)<=2
  final_attempt=rows[-1]
  assert final_attempt['returncode']==0 or (final_attempt.get('timedOut') and final_attempt['returncode'] is None and final_attempt.get('completeNativePngValidated') is True)
  assert final_attempt['pid']==native['targetPid'] and final_attempt['window']['kCGWindowOwnerPID']==native['targetPid']
  assert not final_attempt['window'].get('kCGWindowIsOnscreen',False)
  raw_path=Path(final_attempt['raw']);assert raw_path.is_relative_to(run/code) and not raw_path.is_symlink()
  with Image.open(raw_path) as im:assert im.format=='PNG' and im.size==(1280,1016);im.verify()
  with Image.open(raw_path) as im:im.load()
  native_attempts.extend(rows)
 inputs=list((run/code).glob('*-input.json'));assert inputs
 for proof in inputs:
  v=read(proof);assert v['inputMethod']=='game-thread-dom-bridge' and v['returncode']==0
  for f in ['native','nativeAfter']:assert v[f]['targetActive'] is False and v[f]['frontmostPid']!=v[f]['targetPid']
  bridge=v['bridge'];assert bridge['status']=='released' and bridge['trusted'] is False and bridge['error'] is None
  assert bridge['id']==v['request']['id'] and bridge['keyCode']==v['request']['keyCode']
  assert len(bridge['samples'])==3 and all(s['current'] for s in bridge['samples']) and [s['pressedTime'] for s in bridge['samples']]==[0,1,2]
 stopped=read(run/code/'stopped.json');assert stopped['stopped'] and stopped['protectedFiles']==base['saves']
 install=read(run/(code+'-installation.json'));raw=read(catalog/'catalog.json');row=next(v for v in raw['locales'] if v['code']==code)
 assert sha(catalog/'catalog.json')==install['catalogSha256']==entry['catalogSha256']
 assert install['locale']==code and install['packageArchiveSha256']==row['archiveSha256']
 assert install['fileHashes']=={n:v['sha256'] for n,v in row['files'].items()}
 assert raw['runtimeCode']==install['runtimeChannel']=='en'
 reviews[code]=review;evidence[code]=dict(run=str(run),catalog=str(catalog),inputProofs=len(inputs),waveProof=cap['waveProof'],nativeFocusAtCapture=native,cacheCondition='explicit-native-save-list-face-prefetch' if fixture else 'no-explicit-save-list-face-prefetch',nativePhaseReadAttempts=len(native_attempts),completedNativePngsAfterTimeout=sum(bool(v.get('completeNativePngValidated')) for v in native_attempts),spatialPhaseSpreads=[max(v['anchorY'] for v in sample['sprites'])-min(v['anchorY'] for v in sample['sprites']) for sample in samples])
assert set(reviews)==set(codes)
assert all(sha(images/n)==h for n,h in protected.items())
expected=set(protected)|{c+'-05-joker-jash-wave.png' for c in codes};assert len(expected)==135 and {f.name for f in images.iterdir()}==expected
for name in expected:
 f=images/name;assert f.is_file() and not f.is_symlink()
 with Image.open(f) as im:assert im.format=='PNG' and im.size==(1280,960);im.verify()
 with Image.open(f) as im:im.load()
game=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
fix=read(root/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json')
assert all((sha(game/n) if (game/n).exists() else None)==h for n,h in fix['finalRussianAssets'].items())
assert {str(f.relative_to(game/'save')):sha(f) for f in (game/'save').rglob('*') if f.is_file()}==base['saves']
assert not (game/'.vnrevival-omori').exists()
first=Path(d['entries'][0]['run'])/d['entries'][0]['locale']
for f,b in [('index.html','index-before.html'),('package.json','package-before.json')]:assert (game/f).read_bytes()==(first/b).read_bytes()
assert not any(line.strip().startswith(str(game.parents[2])+'/') for line in subprocess.check_output(['ps','-axo','command='],text=True,timeout=10).splitlines())
out=a.inputs.parent
report=dict(status='complete',images=135,locales=codes,reviewedFifthFrames=27,protectedEarlierImages=108,fifthFrameReviews=reviews,evidence=evidence,dimensions=[1280,960],wavePixelComparisonRegion=list(TEXT_REGION),gameStopped=True,saveSlotsWritten=False,finalLocale='ru',published=False,limitations=['Native macOS capture only. Temporary scheduling/input helpers are documented in immutable run recipes. PNGs are still frames; each has separate native phase images and passive original-SINV animation evidence. Russian runtime language field is unavailable; installed hashes and native review establish the locale. Canonical project has no Git metadata.'])
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('VERIFIED135 native PNGs;27 fifth-frame reviews and native wave proofs;108 originals unchanged;8 protected files unchanged; all input unfocused')
