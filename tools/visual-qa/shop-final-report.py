"""Validate delivered native sixth frames, original135 preservation and restoration."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from PIL import Image
from shop_route import shop_ready
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];d=json.loads(a.inputs.read_text());images=root/'dist/screenshots/20261017-native'
owner_review=root/'runtime/visual-qa/20261018-sixth/thai-owner-review/status.json'
if owner_review.exists():
 resolved=json.loads(owner_review.read_text())
 assert resolved['status']=='resolved','Owner-reported Thai artifacts remain under review'
 assert resolved['sha256']==hashlib.sha256((images/resolved['file']).read_bytes()).hexdigest(),'Resolved Thai review belongs to different pixels'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
base=read(root/'runtime/visual-qa/20261017-native/baseline.json');codes=base['requiredLocales']
protected=read(root/'runtime/visual-qa/20261018-wave/completion.json')['nativePngHashes'];assert len(protected)==135
reviews={};evidence={}
for entry in d['entries']:
 code=entry['locale'];run=Path(entry['run']);catalog=Path(entry['catalog']);assert code in codes and code not in reviews
 producer=read(run/'shop-status.json')
 if producer['status']!='complete':
  correction=read(run/'review-reconciliation.json')
  assert producer==correction['originalProducerStatus']==dict(status='stopped',error="AssertionError('Shop review rejected or mismatched')")
  assert correction['status']=='verified' and correction['locale']==code
  assert correction['originalProducerStatusSha256']==sha(run/'shop-status.json')
  assert correction['originalReviewSha256']==sha(Path(correction['originalReview']))
  assert correction['supersedingReviewSha256']==sha(run/code/'visual-review.json')
  assert read(Path(correction['originalReview']))['status']=='fail'
 restored=read(run/'restoration.json');assert restored['status']=='verified' and restored['saveSlotsWritten'] is False
 assert restored['verifiedLoadedLocales']==[code] and not restored['loadEvidenceUnknownLocales']
 assert read(run/'russian-level-restoration.json')['levelRepairRestored']
 assert read(run/'protected-135.json')==protected
 assert all(sha(run/n)==h for n,h in read(run/'recipe-manifest.json').items())
 cap=read(run/code/'shop-capture.json');review=read(run/code/'visual-review.json')
 assert cap['automatedResult']=='pass' and review['status']=='pass' and review['locale']==code
 assert review['file']==cap['file']==code+'-06-mailbox-jacks.png'
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
 game=cap['gameplay'];assert game['scene']=='Scene_OmoriItemShop' and game['map']['id']==92 and game['map']['interpreter']['eventId']==24
 assert (game['player']['x'],game['player']['y'],game['player']['direction'])==(20,40,8)
 loaded=read(run/code/'load-first-save-semantic-result.json');assert loaded['map']['id']==92
 assert game['firstActor']==loaded['firstActor']
 shop=cap['shopEvidence'];assert shop_ready(shop)
 assert sha(Path(cap['frame']))==cap['sha256']
 assert cap['purchaseConfirmed'] is False and cap['inventoryChanged'] is False
 assert shop['inventory']==read(run/code/'loaded-inventory.json')
 assert shop['inventory']['gold']==72 and shop['shop']['price']==25 and shop['shop']['owned']==0
 assert cap['shopEvidence']['shop']['selected']['description']
 if code=='th':
  proof=shop['shop']['descriptionDrawProof'];assert proof['itemId']==78 and proof['newPages']==1 and proof['pages'][0]['fontSize']==26
  assert shop['shop']['message']['pause'] is False
 if code in ('ar','fa','he','hi'):
  proof=shop['shop']['descriptionDrawProof'];assert proof['itemId']==78 and proof['newPages']==1 and proof['pages'][0]['fontSize']==28
  assert shop['shop']['message']['pause'] is False
 fixture=shop.get('fileAssets')
 if fixture:
  assert fixture['phase']=='ready' and len(fixture['assets'])==2
  assert all(v['state']=='loaded' and v['imageComplete'] and v['width']>0 and v['height']>0 for v in fixture['assets'])
 native_attempts=[]
 for phase in [cap['frame']]:
  frame_path=Path(phase);rows=read(frame_path.with_name(frame_path.stem+'-native-capture-attempts.json'))
  assert 1<=len(rows)<=2
  final_attempt=rows[-1]
  assert final_attempt['returncode']==0 or (final_attempt.get('timedOut') and final_attempt['returncode'] is None and final_attempt.get('completeNativePngValidated') is True)
  assert final_attempt['pid']==native['targetPid'] and final_attempt['window']['kCGWindowOwnerPID']==native['targetPid']
  assert not final_attempt['window'].get('kCGWindowIsOnscreen',False)
  raw_path=Path(final_attempt['raw']);assert raw_path.is_relative_to(run/code) and not raw_path.is_symlink()
  with Image.open(raw_path) as im:assert im.format=='PNG' and im.size==(1280,1016);im.verify()
  with Image.open(raw_path) as im,Image.open(images/cap['file']) as delivered:
   assert im.crop((0,56,1280,1016)).convert('RGBA').tobytes()==delivered.convert('RGBA').tobytes(),'Delivered pixels differ from native content crop'
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
 reviews[code]=review;evidence[code]=dict(run=str(run),catalog=str(catalog),inputProofs=len(inputs),nativeFocusAtCapture=native,cacheCondition=dict(saveListFaces='explicit-native-reservation' if fixture else 'native-demand-load',mailbox='explicit-native-reservation' if shop.get('shopAssets') else 'native-demand-load'),nativeReadAttempts=len(native_attempts),selectedItemId=78,selectedIndex=2,gold=72,owned=0,price=25,purchaseConfirmed=False,inventoryChanged=False)
assert set(reviews)==set(codes)
assert all(sha(images/n)==h for n,h in protected.items())
expected=set(protected)|{c+'-06-mailbox-jacks.png' for c in codes};assert len(expected)==162 and {f.name for f in images.iterdir()}==expected
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
report=dict(status='complete',images=162,locales=codes,reviewedSixthFrames=27,protectedEarlierImages=135,sixthFrameReviews=reviews,evidence=evidence,dimensions=[1280,960],gameStopped=True,saveSlotsWritten=False,finalLocale='ru',published=False,limitations=['Native macOS capture only. Temporary scheduling/input helpers are documented in immutable run recipes. The target is the mailbox buy list with item78 selected and no purchase confirmation; inventory and gold remain unchanged. Russian runtime language field is unavailable; installed hashes and native review establish the locale. Canonical project has no Git metadata.'])
if owner_review.exists():report['ownerReportedReviewResolution']=resolved
report['siteValidation']=dict(status='not-run',reason='Automatic approval review rejected the earlier VN Revival screenshot dry-run network action. No upload or publication performed.')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('VERIFIED162 native PNGs;27 sixth-frame reviews/native mailbox shop proofs;135 originals unchanged;8 protected files unchanged; all input unfocused')
