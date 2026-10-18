"""Verify 108 native PNGs, package lineage, unfocused input and full restoration."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from PIL import Image
from equipment_route import equipment_ready
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];d=json.loads(a.inputs.read_text());images=root/'dist/screenshots/20261017-native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((root/'runtime/visual-qa/20261017-native/baseline.json').read_text());codes=base['requiredLocales']
reviews={};evidence={};protected=None
for entry in d['entries']:
    code=entry['locale'];run=Path(entry['run']);catalog=Path(entry['catalog']);assert code not in reviews and code in codes
    status=json.loads((run/'equipment-status.json').read_text());assert status['status']=='complete'
    restored=json.loads((run/'restoration.json').read_text());assert restored['status']=='verified' and restored['saveSlotsWritten'] is False
    assert restored['verifiedLoadedLocales']==[code] and not restored['loadEvidenceUnknownLocales']
    assert json.loads((run/'russian-level-restoration.json').read_text())['levelRepairRestored']
    keep=json.loads((run/'protected-81.json').read_text());assert len(keep)==81 and (protected is None or protected==keep);protected=keep
    manifest=json.loads((run/'recipe-manifest.json').read_text());assert all(sha(run/n)==h for n,h in manifest.items())
    review=json.loads((run/code/'visual-review.json').read_text());assert review['status']=='pass' and review['locale']==code
    cap=json.loads((run/code/'equipment-capture.json').read_text());assert cap['automatedResult']=='pass' and cap['equipmentChanged'] is False
    final_focus=cap.get('nativeFocusAtCapture')
    if final_focus is not None:
        assert final_focus['targetActive'] is False and final_focus['frontmostPid']!=final_focus['targetPid']
    if cap.get('inputMethod')=='game-thread-dom-bridge':assert final_focus is not None
    window_policy=cap['state']['startupDiagnostics'].get('windowPolicy')
    asset_fixture=cap['state'].get('equipmentAssets')
    if asset_fixture:
        assert asset_fixture['identity']=='omori-equipment-asset-prefetch-v1' and asset_fixture['phase']=='ready'
        assert {x['url'] for x in asset_fixture['assets']}=={'img/atlases/itemCharms.png','img/atlases/itemWeapon.png'}
        assert len(asset_fixture['assets'])==2 and all(x['state']=='loaded' and x['imageComplete'] and x['width']>0 and x['height']>0 for x in asset_fixture['assets'])
    if window_policy:
        assert window_policy['identity']=='omori-hidden-native-window-v1' and window_policy['hiddenRequested'] is True
        assert not any(e['event']=='focus' for e in window_policy['events'])
        assert not cap['window'].get('kCGWindowIsOnscreen',False)
    launch_settings=run/code/'launch-settings.json'
    if launch_settings.exists():
        settings=json.loads(launch_settings.read_text());gpu=json.loads((run/'gpu-process-proof.json').read_text())
        assert settings['temporary'] and settings['gpuMode']=='separate-process'
        assert '--in-process-gpu' not in settings['chromiumArgs'].split()
        assert settings['window']['show'] is False and settings['window']['focus'] is False
        assert settings['originalPackageSha256']==sha(run/code/'package-before.json')
        assert final_focus and gpu['ownerPid']==final_focus['targetPid'] and len(gpu['gpuProcesses'])==1
        assert gpu['gpuProcesses'][0]['ppid']==gpu['ownerPid'] and '--type=gpu-process' in gpu['gpuProcesses'][0]['command']
        assert cap['state']['startupDiagnostics']['rendererInfo']['webgl'] is True
    assert review['file']==cap['file']==code+'-04-omori-equipment.png' and review['sha256']==cap['sha256']==sha(images/cap['file'])
    runtime_language=cap['state'].get('language')
    assert runtime_language=='en' or (code=='ru' and runtime_language is None)
    assert cap['runtimeChannel']=='en' and cap['marker']['matched'] and cap['marker']['score']>=.94
    if code!='ru':assert cap['state']['startupDiagnostics']['locale']==code
    assert cap['saveSlotLoaded']==1 and cap['saveSlotsWritten'] is False and cap['menuOpeningKey']=='X'
    game=cap['gameplay'];assert equipment_ready(game) and game['equipment']['item']['id']==2
    loaded=json.loads((run/code/'load-first-save-semantic-result.json').read_text())
    assert loaded['scene']=='Scene_Map' and loaded['map']['id']==92 and (loaded['player']['x'],loaded['player']['y'])==(11,15)
    assert game['firstActor']==loaded['firstActor'] and (game['player']['x'],game['player']['y'])==(11,15)
    actions=json.loads((run/code/'route.json').read_text());assert actions[-1]['action']=='select-omori'
    assert any(s['action']=='open-character-menu-x' and s['key']==7 for s in actions)
    inputs=list((run/code).glob('*-input.json'));assert inputs
    for proof in inputs:
        x=json.loads(proof.read_text());assert x['native']['targetActive'] is False and x['native']['frontmostPid']!=x['native']['targetPid']
        if x.get('inputMethod')=='game-thread-dom-bridge':
            assert x['returncode']==0
            native_after=x['nativeAfter'];assert native_after['targetActive'] is False and native_after['frontmostPid']!=native_after['targetPid']
            bridge=x['bridge'];request=x['request'];samples=bridge['samples']
            assert bridge['status']=='released' and bridge['trusted'] is False and bridge['error'] is None
            assert bridge['id']==request['id'] and bridge['keyCode']==request['keyCode']
            assert len(samples)==3 and all(s['current'] is True for s in samples)
            assert [s['pressedTime'] for s in samples]==[0,1,2]
            # SceneManager may process multiple input updates before rendering.
            # Graphics.frameCount is diagnostic, not an input-update serial.
        else:
            assert x['native']['acknowledged']
            if 'returncode' in x:assert x['returncode']==0
            else:
                # Historical successful receipts overwrote the numeric code.
                # Preserve that limitation; require their actual final success
                # state and acknowledgement rather than inventing a saved code.
                assert x['mode']=='One native process holds down until observed engine-frame consumption, then releases without another helper launch'
                assert x['afterRelease']['observer']=='omori-oculix-event-observer-v1'
    stopped=json.loads((run/code/'stopped.json').read_text());assert stopped['stopped'] and stopped['protectedFiles']==base['saves']
    install=json.loads((run/(code+'-installation.json')).read_text());raw=json.loads((catalog/'catalog.json').read_text())
    catalog_hash=sha(catalog/'catalog.json');receipt=json.loads((catalog/'payload-receipt.json').read_text())
    assert catalog_hash==install['catalogSha256']==receipt['catalogSha256']
    if 'catalogSha256' in entry:assert entry['catalogSha256']==catalog_hash
    row=next(x for x in raw['locales'] if x['code']==code)
    assert install['locale']==code and install['packageArchiveSha256']==row['archiveSha256']
    assert install['runtimeChannel']==raw['runtimeCode']==cap['runtimeChannel']=='en'
    if code=='ru':
        ru_fix=json.loads((root/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json').read_text())
        assert ru_fix['status']=='verified'
        assert row['archiveSha256']==sha(root/ru_fix['newNativeBuild']/'omori-ru-direct-8879120.zip')
    assert install['fileHashes']=={n:v['sha256'] for n,v in row['files'].items()}
    if receipt.get('kind')=='selected-locale-native-QA-only':
        parent=Path(receipt['parentCatalog']);assert sha(parent/'catalog.json')==receipt['parentCatalogSha256']
        full=json.loads((parent/'catalog.json').read_text());assert row==next(x for x in full['locales'] if x['code']==code)
        assert receipt['mandatoryLocales']==codes and receipt['notAReleaseCatalog']
    reviews[code]=review;evidence[code]=dict(run=str(run),catalog=str(catalog),packageArchiveSha256=row['archiveSha256'],inputProofs=len(inputs),
      inputMethods=sorted({json.loads(f.read_text()).get('inputMethod','native-pid-targeted-keyboard') for f in inputs}),
      hiddenNativeWindow=bool(window_policy),
      cacheCondition='explicit-native-equipment-asset-prefetch' if asset_fixture else 'no-explicit-QA-prefetch',
      runtimeLanguageObserved=runtime_language,
      localeVerification='canonical repaired-Russian archive and installed file hashes plus native visual review' if code=='ru' else 'native locale diagnostic and channel plus installed file hashes and native visual review',
      inputDriverResultCodesRecorded=sum('returncode' in json.loads(f.read_text()) for f in inputs),
      finalDomFocus=cap['state']['focused'],nativeFocusAtCapture=cap.get('nativeFocusAtCapture'),frameScheduler=cap['state']['startupDiagnostics'].get('frameScheduler'))
assert set(reviews)==set(codes)
assert all(sha(images/n)==h for n,h in protected.items()),'An accepted original frame changed'
expected=set(protected)|{c+'-04-omori-equipment.png' for c in codes};assert len(expected)==108
assert {f.name for f in images.iterdir()}==expected
for name in expected:
    f=images/name;assert f.is_file() and not f.is_symlink()
    with Image.open(f) as im:assert im.format=='PNG' and im.size==(1280,960);im.verify()
game=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
fix=json.loads((root/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json').read_text())
assert all((sha(game/n) if (game/n).exists() else None)==h for n,h in fix['finalRussianAssets'].items())
assert {str(f.relative_to(game/'save')):sha(f) for f in (game/'save').rglob('*') if f.is_file()}==base['saves']
assert not (game/'.vnrevival-omori').exists()
first=Path(d['entries'][0]['run'])/d['entries'][0]['locale']
assert (game/'index.html').read_bytes()==(first/'index-before.html').read_bytes()
assert (game/'package.json').read_bytes()==(first/'package-before.json').read_bytes()
app_prefix=str(game.parents[2])+'/'
assert not any(line.strip().startswith(app_prefix) for line in subprocess.check_output(['ps','-axo','command='],text=True,timeout=10).splitlines())
out=a.inputs.parent
preference=out/'app-nap-preference.json'
if preference.exists():assert json.loads(preference.read_text())['status']=='restored'
git_probe=subprocess.run(['git','-C',str(root),'rev-parse','--show-toplevel'],capture_output=True,text=True,timeout=10)
assert git_probe.returncode==128 and 'not a git repository' in git_probe.stderr.lower(),'Reconcile current Git delivery before reporting the historical no-repository limitation'
result=dict(status='complete',images=108,locales=codes,reviewedFourthFrames=27,protectedEarlierImages=81,fourthFrameReviews=reviews,evidence=evidence,
            dimensions=[1280,960],backgroundCaptureRequested=True,allInputProofsUnfocused=True,equipmentChanged=False,saveSlotsWritten=False,
            protectedFilesByteIdentical=8,finalLocale='ru',gameStopped=True,published=False,gitDelivery='Unavailable: canonical project has no .git metadata')
result['limitations']=[
    'Accepted capture/input evidence is distinct from failed attempts. The owner confirmed spontaneous foreground activation in rejected series07; later captures use a hidden native window.',
    'Native reserved-cache atlas prefetch, where recorded per locale, does not verify cold equipment loading or diagnose the earlier on-demand atlas stall.',
    'Historical native-keyboard receipts retain acknowledgements and success state but not numeric driver exit codes; recorded-code counts are reported per locale.',
    'The legacy Russian runtime does not emit ConfigManager.language. Its locale is bound to the exact verified repaired-Russian archive, installed file hashes and reviewed native Russian image; no missing runtime measurement was invented.',
    'Evidence covers the native macOS game and temporary background QA helpers; no Windows runtime verification is claimed.'
]
(out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# OMORI native screenshot evidence: 108 frames','','Four native frames per locale: title, load list, Mari quest advice, and OMORI equipment. All previous81 PNGs remain byte-identical.','','The fourth frame starts from save slot1, opens the character menu with X, selects Equip and the first actor, and stops before weapon confirmation. Native state, Oculix recognition and human review are separate evidence gates. All input proofs show the game was unfocused.','','| Locale | Fourth frame | Review |','|---|---|---|']
for c in codes:lines.append('| '+c+' | ['+reviews[c]['file']+'](<'+str(images/reviews[c]['file'])+'>) | pass |')
lines+=['','All108 files are regular1280x960 PNGs. No equipment was changed or save slot written. All8 protected files and the repaired Russian resource baseline were restored. Native game and temporary components were stopped/removed. No publication was applied.','']
lines.extend(result['limitations'])
lines+=['','The canonical project has no .git metadata, so no commit was created.','']
(out/'report.md').write_text('\n'.join(lines))
print('VERIFIED108 native PNGs;27 fourth-frame reviews;81 originals unchanged;8 protected files unchanged; all input unfocused')
