import json,shutil
from runtime import RUN,ROOT,state,sha,save,stop
from vision import Vision
owned=json.loads((RUN/'owned-game.json').read_text());pid=owned['pid'];directory=RUN/'ru-observer';v=Vision(directory)
try:
 path,s,m,w=v.require(pid,'load-portrait','File',5);assert s['scene']=='Scene_OmoriFile';dest=ROOT/'dist/screenshots/20261017-native/ru-02-load-game.png';assert not dest.exists();shutil.copyfile(path,dest)
 save(directory/'capture.json',{'locale':'ru','mainMenuFile':'ru-01-main-menu.png','mainMenuReused':True,'mainMenuSha256':sha(ROOT/'dist/screenshots/20261017-native/ru-01-main-menu.png'),'loadGameFile':dest.name,'loadGameSha256':sha(dest),'dimensions':[1280,960],'scene':s,'oculixLoadMarker':m,'window':w,'captureResult':'pass','visualReview':'pass-with-legacy-save-metadata-note','saveSlotsLoaded':False,'saveSlotsWritten':False})
 print('RU_CAPTURE_COMPLETE',flush=True)
finally:v.close();stop()
