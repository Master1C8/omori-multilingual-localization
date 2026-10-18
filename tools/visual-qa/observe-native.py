"""Bounded native OMORI observation. No gameplay input or save actions."""
import subprocess,json,time,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; RUN=ROOT/'runtime/visual-qa/20261017-native'; APP=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app'); GAME=APP/'Contents/Resources/app.nw'
rows=subprocess.check_output(['ps','-axo','pid=,command='],text=True).splitlines()
assert not any(x.strip().split(None,1)[-1].startswith(str(APP/'Contents/MacOS/nwjs')) for x in rows),'OMORI already running'
assert any('/Steam.AppBundle/Steam/Contents/MacOS/steam_osx' in x for x in rows),'Native Steam must be running'
b=json.loads((RUN/'baseline.json').read_text());assert all(hashlib.sha256((GAME/'save'/k).read_bytes()).hexdigest()==v for k,v in b['saves'].items())
log=(RUN/'ru-game.log').open('wb');p=subprocess.Popen([str(APP/'Contents/MacOS/nwjs'),'--6bdb2e585882fbd48826ef9cffd4c511'],cwd=GAME,env=dict(os.environ,SteamAppId='1150690'),stdout=log,stderr=log,start_new_session=True);log.close()
(RUN/'owned-game.json').write_text(json.dumps({'pid':p.pid,'executable':str(APP/'Contents/MacOS/nwjs'),'locale':'ru','launchedBy':'OMORI Oculix screenshot task'},indent=2))
print('Owned native OMORI PID',p.pid,flush=True)
time.sleep(15)
ws=json.loads(subprocess.check_output([str(ROOT/'build/installer/window-list'),'OMORI']))
ws=[w for w in ws if w['kCGWindowOwnerPID']==p.pid and w.get('kCGWindowIsOnscreen')]
assert len(ws)==1,ws
w=ws[0];(RUN/'initial-window.json').write_text(json.dumps(w,indent=2));subprocess.check_call([str(RUN/'native-input'),'focus',str(p.pid)]);time.sleep(5)
subprocess.check_call(['/usr/sbin/screencapture','-x','-o','-l',str(w['kCGWindowNumber']),str(RUN/'evidence/ru-initial-window.png')])
print('Native initial window recorded; no keys pressed',flush=True)
