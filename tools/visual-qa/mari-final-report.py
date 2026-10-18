"""Reconcile all81 native frames, reviewed Mari evidence and the RU level repair."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--run',action='append',type=Path,required=True);p.add_argument('--catalog',action='append',type=Path,required=True);p.add_argument('--ru-fix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];images=root/'dist/screenshots/20261017-native';manual=root/'runtime/visual-qa/20261017-mari-manual-01';base=json.loads((root/'runtime/visual-qa/20261017-native/baseline.json').read_text());codes=base['requiredLocales'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
catalogs={}
for c in a.catalog:
 receipt=json.loads((c/'payload-receipt.json').read_text());h=sha(c/'catalog.json');assert h==receipt['catalogSha256'];catalog=json.loads((c/'catalog.json').read_text())
 if receipt.get('kind')=='selected-locale-native-QA-only':
  parent=Path(receipt['parentCatalog']);assert sha(parent/'catalog.json')==receipt['parentCatalogSha256'];full=json.loads((parent/'catalog.json').read_text())
  assert receipt['mandatoryLocales']==codes and receipt['notAReleaseCatalog']
  assert catalog['locales']==[next(row for row in full['locales'] if row['code']==code) for code in receipt['locales']]
  assert all(v==full['objects'][k] for k,v in catalog['objects'].items())
  assert all(v==full['originals'][k] for k,v in catalog['originals'].items())
 catalogs[h]=(c,catalog)
ru=json.loads((manual/'ru-third/visual-review.json').read_text());assert ru['status']=='pass';reviews={'ru':ru};evidence={'ru':str(manual.relative_to(root))};rejected=[]
for run in a.run:
 status=json.loads((run/'mari-status.json').read_text());restored=json.loads((run/'restoration.json').read_text());assert restored['status']=='verified'
 for code,r in json.loads((run/'mari-visual-reviews.json').read_text()).items():
  if r['status']=='fail':
   preserved=run/code/'rejected-mari-quests.png';assert sha(preserved)==r['sha256']
   rejected.append(dict(r,preservedEvidence=str(preserved)));continue
  assert code not in reviews and code in codes and r['status']=='pass'
  cap=json.loads((run/code/'mari-capture.json').read_text());install=json.loads((run/(code+'-installation.json')).read_text());stopped=json.loads((run/code/'stopped.json').read_text())
  assert stopped['stopped'] and stopped['protectedFiles']==base['saves']
  assert r['file']==cap['file'] and r['sha256']==cap['sha256'];assert cap['saveSlotLoaded']==1 and cap['saveSlotsWritten'] is False
  assert cap['automatedResult']=='pass' and cap['state']['scene']=='Scene_OmoriQuest' and cap['state']['language']=='en'
  assert cap['marker']['matched'] and cap['marker']['score']>=.94
  game=cap['gameplay'];assert game['scene']=='Scene_OmoriQuest' and (game['player']['x'],game['player']['y'])==(12,16)
  windows={w['type']:w for w in game['windows']};assert windows['Window_OmoriQuestTypes']['index']==0 and windows['Window_OmoriQuestList']['index']==0 and len(windows['Window_OmoriQuestList']['list'])==2 and windows['Window_OmoriQuestMessage']['openness']==255
  assert install['locale']==code and install['runtimeChannel']=='en';catalog_path,catalog=catalogs[install['catalogSha256']];row=next(v for v in catalog['locales'] if v['code']==code)
  assert row['archiveSha256']==install['packageArchiveSha256'] and install['fileHashes']=={k:v['sha256'] for k,v in row['files'].items()}
  reviews[code]=r;evidence[code]={'run':str(run),'catalog':str(catalog_path),'packageArchiveSha256':row['archiveSha256']}
assert set(reviews)==set(codes),'Missing third-frame reviews: '+str(set(codes)-set(reviews))
fix=json.loads(a.ru_fix.read_text());assert fix['status']=='verified' and fix['visualReview']=='pass'
old=json.loads((manual/'accepted-54.json').read_text());assert len(old)==54
for name,h in old.items():
 if name=='ru-02-load-game.png':
  assert h==fix['oldImageSha256'] and sha(Path(fix['preservedOldImage']))==h and sha(images/name)==fix['newImageSha256']
 else:assert sha(images/name)==h,'Previously accepted frame changed: '+name
expected=set(old)|{c+'-03-mari-quests.png' for c in codes};assert len(expected)==81 and {p.name for p in images.iterdir()}==expected
for c,r in reviews.items():assert r['file']==c+'-03-mari-quests.png' and sha(images/r['file'])==r['sha256']
for name in expected:
 with Image.open(images/name) as im:assert im.format=='PNG' and im.size==(1280,960);im.verify()
game=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
assert {str(p.relative_to(game/'save')):sha(p) for p in (game/'save').rglob('*') if p.is_file()}==base['saves']
assert all((sha(game/k) if (game/k).exists() else None)==h for k,h in fix['finalRussianAssets'].items())
assert not (game/'.vnrevival-omori').exists()
assert (game/'package.json').read_bytes()==(manual/'ru-04/package-before.json').read_bytes()
assert (game/'index.html').read_bytes()==(manual/'ru-04/index-before.html').read_bytes()
native=str(game.parents[1]/'MacOS/nwjs');assert not any(line.strip().startswith(native+' ') for line in subprocess.check_output(['ps','-axo','command='],text=True).splitlines())
audit=json.loads((root/'runtime/visual-qa/20261017-level-audit/review.json').read_text());assert len(audit['rows'])==27 and all(r['review']=='pass' for r in audit['rows'])
result={'status':'complete','imageCount':81,'reviewedAdditionalImages':27,'locales':codes,'thirdFrameReviews':reviews,'thirdFrameEvidence':evidence,'rejectedHistoricalFrames':rejected,'russianLevelRepair':fix,'levelFieldAudit':audit,'saveSlotLoadedPerLocale':1,'saveSlotsWritten':False,'protectedSaveAndSettingsFilesByteIdentical':8,'finalLocale':'ru','crossOverUsed':False,'temporaryBackgroundComponentsRemoved':True,'dimensions':[1280,960]}
a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# OMORI — 81 проверенный скриншот','','Получены и просмотрены три кадра для каждого из 27 языков: главное меню, список сохранений и советы Мари с выбранной первой невыполненной задачей. Нативная Mac-версия, Oculix, каждый PNG — 1280 × 960.','','Третий кадр получен загрузкой первого слота, двумя движениями к Мари и двумя разговорами. Диалоги проходились по состоянию текста, а не по фиксированному числу нажатий. Игра работала в фоне без вызовов активации окна. Временные компоненты фоновой работы удалены.','','| Язык | Главное меню | Загрузка | Задачи Мари | Результат |','|---|---|---|---|---|']
for c in codes:
 links=['['+c+'-'+suffix+'.png](<'+str(images/(c+'-'+suffix+'.png'))+'>)' for suffix in ['01-main-menu','02-load-game','03-mari-quests']]
 lines.append('| '+c+' | '+' | '.join(links)+' | Просмотрены; поле уровня проверено'+('; русский кадр загрузки переснят после исправления' if c=='ru' else '')+' |')
lines+=['','На всех 27 экранах загрузки проверены надпись уровня и число. В старой русской сборке подтверждено перекрытие из-за фиксированных координат; русский сборщик переведён на общий расчёт по фактической ширине с отдельным зазором. Исправление проверено в игре; прежний русский кадр сохранён отдельно. Остальные ранее принятые кадры неизменны.','','В третьих кадрах проверены язык, глифы, диакритика, пробелы, переносы и обрезание; для RTL — соединение букв и направление смешанных строк. Полная редактура перевода не выполнялась.','','Слоты не перезаписывались. Все восемь файлов сохранений/настроек совпадают побайтно. В игре оставлена русская локализация с исправлением поля уровня; остальные исходные настройки восстановлены. CrossOver и публикация не выполнялись. Подробные версии пакетов, контрольные суммы и замечания находятся в report.json.','']
(a.output/'report.md').write_text('\n'.join(lines));print('VERIFIED81 reviewed native PNGs;27 Mari frames; RU level repair;8 protected files unchanged')
