# -*- coding: utf-8 -*-
"""Reconcile reviewed native evidence; refuse an incomplete 54-frame report."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from PIL import Image

p=argparse.ArgumentParser();p.add_argument('--run',action='append',type=Path,required=True);p.add_argument('--catalog',action='append',type=Path,required=True);p.add_argument('--restoration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];images=root/'dist/screenshots/20261017-native';base=root/'runtime/visual-qa/20261017-native';baseline=json.loads((base/'baseline.json').read_text());required=baseline['requiredLocales']
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
game=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
catalogs={}
for path in a.catalog:
 path=path.resolve();receipt=json.loads((path/'payload-receipt.json').read_text());h=sha(path/'catalog.json');assert h==receipt['catalogSha256'];catalogs[h]={'path':str(path),'catalog':json.loads((path/'catalog.json').read_text())}
ru=json.loads((root/'runtime/visual-qa/20261017-native-r3/visual-reviews.json').read_text())['ru'];assert ru['mainMenu']=='pass' and ru['loadGame']=='pass-with-legacy-metadata-note'
reviews={'ru':{'locale':'ru','status':'pass','files':ru['files'],'findings':ru['findings'],'evidence':'runtime/visual-qa/20261017-native-r3/visual-reviews.json'}}
rejected_reviews=[]
for run in a.run:
 run=run.resolve();assert run.is_relative_to(root)
 for code,review in json.loads((run/'visual-reviews.json').read_text()).items():
  if review['status']=='fail':
   rejected_reviews.append(dict(review,evidence=str(run.relative_to(root))));continue
  assert code in required and code not in reviews and review['status']=='pass'
  capture=json.loads((run/code/'capture.json').read_text());install=json.loads((run/(code+'-installation.json')).read_text());stopped=json.loads((run/code/'stopped.json').read_text())
  assert stopped['stopped'] and stopped['protectedFiles']==baseline['saves']
  assert install['locale']==code and install['runtimeChannel']=='en'
  catalog=catalogs[install['catalogSha256']];row=next(v for v in catalog['catalog']['locales'] if v['code']==code)
  assert row['archiveSha256']==install['packageArchiveSha256'] and install['fileHashes']=={k:v['sha256'] for k,v in row['files'].items()}
  assert capture['automatedResult']=='pass' and not capture['saveSlotsLoaded'] and not capture['saveSlotsWritten']
  title=capture['mainMenu']['state'];assert title['index']==1 and title['active'] and title['focused'] and title['canContinue']
  assert all(capture[k]['state']['language']=='en' and capture[k]['marker']['matched'] and capture[k]['marker']['score']>=.94 for k in ['mainMenu','loadGame'])
  assert capture['dimensions']==[1280,960] and capture['window']['kCGWindowBounds']['Width']==640 and capture['window']['kCGWindowBounds']['Height']==508
  assert capture['loadGame']['state']['scene']=='Scene_OmoriFile'
  assert review['files']=={capture[k]['file']:capture[k]['sha256'] for k in ['mainMenu','loadGame']}
  font_probe=None
  if code in ['ar','he','fa']:
   font_probe=json.loads((run/code/'actual-font-probe.json').read_text())
   assert font_probe['status']=='passed' and font_probe['locale']==code
   assert font_probe['actual']['sha256']==font_probe['derived']['sha256']
   assert font_probe['actual']['sha256']!=font_probe['uncontrolledFallback']['sha256']
   assert font_probe['originalLatin']['sha256']==font_probe['nativeLatin']['sha256']
  reviews[code]=dict(review,evidence=str(run.relative_to(root)),installation=install,catalogPath=catalog['path'],actualFontProbe=font_probe)
assert set(reviews)==set(required),'Missing locale review: '+str(set(required)-set(reviews))
expected={code+'-'+suffix+'.png' for code in required for suffix in ['01-main-menu','02-load-game']};assert {v.name for v in images.iterdir()}==expected and len(expected)==54
for code,review in reviews.items():
 assert set(review['files'])=={code+'-01-main-menu.png',code+'-02-load-game.png'}
 for name,digest in review['files'].items():
  path=images/name;assert path.is_file() and not path.is_symlink() and sha(path)==digest
  with Image.open(path) as im:assert im.format=='PNG' and im.size==(1280,960);im.verify()
restored=json.loads(a.restoration.read_text());assert restored['status']=='verified' and restored['locale']=='ru'
assert all((sha(game/k) if (game/k).exists() else None)==v for k,v in baseline['assets'].items())
assert {str(v.relative_to(game/'save')):sha(v) for v in (game/'save').rglob('*') if v.is_file()}==baseline['saves']
assert not (game/'.vnrevival-omori').exists(),'Temporary installer state remains in game'
for run in a.run:
 for code in json.loads((run/'visual-reviews.json').read_text()):assert sha(game/'index.html')==sha(run/code/'index-before.html')
introduced={name for item in catalogs.values() for loc in item['catalog']['locales'] for name in loc['files'] if name.startswith('fonts/Locale-') and ('-Primary.' in name or '-Secondary.' in name) and name not in baseline['assets']}
assert all(not (game/name).exists() for name in introduced),'Temporary locale fonts remain in game'
native=str(game.parents[1]/'MacOS/nwjs')
assert not any(line.strip().startswith(native+' ') for line in subprocess.check_output(['ps','-axo','command='],text=True).splitlines()),'Native game still running'
result={'status':'complete','locales':required,'imageCount':54,'reviewedImages':54,'dimensions':[1280,960],'output':str(images),'reviews':reviews,'rejectedEarlierReviews':rejected_reviews,'restoration':restored,'crossOverUsed':False,'editorialScope':'Only the two requested screens','pendingLocales':[]}
a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# OMORI — 54 проверенных скриншота','', 'Получены и просмотрены оба экрана для всех 27 языков. Нативная Mac-версия, Oculix, размер каждого PNG — 1280 × 960.','', 'На главном меню выбран пункт продолжения; на втором экране открыт список сохранений. Слоты не загружались и не перезаписывались. Русская локализация и настройки восстановлены, все восемь файлов сохранений/настроек побайтно совпадают с исходными.','', '| Язык | Главное меню | Загрузка | Проверка | Замечания |','|---|---|---|---|---|']
notes={'ru':'Сохранены ранее принятые кадры и их исходные байты.','es':'Исправлены обрезание нового пункта игры, масштаб акцента и перекрытие полей.','es-419':'Региональный пакет проверен отдельно; прежние обрезания и перекрытия устранены.','pt-BR':'Исправлены масштаб Ç/Õ/Í и перекрытие заголовков.','hi':'Проверены кластеры деванагари и гласные знаки.','th':'Проверены надстрочные знаки и гласные.','zh-TW':'Проверены традиционные иероглифы и плотные знаки.','vi':'Проверены составные акценты, рожки и нижние точки.','ar':'Исправлены границы RTL-подписей; проверены соединение букв, имена и цифры.','he':'Проверены RTL, границы подписей и смешанные строки.','fa':'Проверены персидские формы, RTL, границы подписей и цифры.'}
notes['fa']='Исправлено обрезание команды загрузки в узкой левой панели; проверены персидские формы, RTL и цифры.'
for code in required:
 links=['['+code+'-'+s+'.png](<'+str(images/(code+'-'+s+'.png'))+'>)' for s in ['01-main-menu','02-load-game']]
 lines.append('| '+code+' | '+links[0]+' | '+links[1]+' | Оба кадра просмотрены | '+notes.get(code,'Дефектов на этих двух экранах не обнаружено.')+' |')
lines+=['','Примечания: сохранённые названия карт и PROLOGUE оставлены как в пользовательских данных. Компактное вписывание левой команды загрузки соответствует нативному интерфейсу. Четвёртая строка списка продолжается ниже границы экрана одинаково для всех языков.','', 'Проверены язык, глифы, пробелы, диакритика, пересечения и обрезание. Для RTL отдельно проверены соединение букв, направление, латинские имена и порядок цифр. Подробные замечания, хеши изображений и привязки к установленным пакетам — в report.json. Полная редактура переводов не выполнялась.','']
lines += [
 'Переход через «Продолжить»: прежние события нажатия и отпускания приходили с интервалом 7 мс, но экран не менялся. Вероятная причина — пропуск короткого импульса между обновлениями игры. Управление исправлено: отдельный источник событий, сброшенные модификаторы, адресация проверенному процессу и удержание клавиши. Успех подтверждался распознаванием списка сохранений и фактической сменой сцены после одного нажатия.',
 '',
 'Артефакты: нормализованы метрики дополнительных шрифтов, измерение пунктов меню и размещение полей сохранений. Для RTL учитывается фактическая граница штрихов, включая узкую команду загрузки в персидском. Отклонённые кадры сохранены отдельно. Ранее принятые русские изображения не изменены.',
 '',
 'Исправленные пакеты и рецепты находятся в этом проекте; прежние релизные архивы сохранены. Публикация и CrossOver не выполнялись. Каноническая папка не является Git-репозиторием, поэтому коммит создать невозможно.',
 ''
]
(a.output/'report.md').write_text('\n'.join(lines));print('VERIFIED 54/54 reviewed PNGs; original native game assets and saves restored')
