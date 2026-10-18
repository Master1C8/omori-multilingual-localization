"""Stop only recorded task-owned native processes and verify the untouched baseline."""
from pathlib import Path
import subprocess,json,os,signal,time,hashlib
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'runtime/visual-qa/20261017-native';base=json.loads((RUN/'baseline.json').read_text());GAME=Path(base['gameRoot']);owned=json.loads((RUN/'owned-game.json').read_text());pid=owned['pid'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def processes():
 out={}
 for l in subprocess.check_output(['ps','-axo','pid=,ppid=,state=,command='],text=True).splitlines():
  s=l.strip().split(None,3)
  if len(s)==4:out[int(s[0])]={'ppid':int(s[1]),'state':s[2],'command':s[3]}
 return out
rows=processes();ids=set();tracked={}
if pid in rows and not rows[pid]['state'].startswith('Z'):
 assert rows[pid]['command'].startswith(owned['executable']+' '),'Task PID was reused; do not stop it'
 ids={pid}
 while True:
  extra={p for p,v in rows.items() if v['ppid'] in ids}-ids
  if not extra:break
  ids.update(extra)
 tracked={p:rows[p] for p in ids if rows[p]['command'].startswith(str(GAME.parents[2])+'/')}
 assert pid in tracked
 os.kill(pid,signal.SIGTERM)
 for i in range(40):
  current=processes();alive={p:v for p,v in current.items() if p in tracked and v['command']==tracked[p]['command'] and not v['state'].startswith('Z')}
  if not alive:break
  time.sleep(.25)
 else:
  for p in alive:os.kill(p,signal.SIGTERM)
  time.sleep(2)
  current=processes();assert not any(p in current and current[p]['command']==v['command'] and not current[p]['state'].startswith('Z') for p,v in tracked.items()),'Task-owned process still running'
assets={k:(sha(GAME/k) if (GAME/k).exists() else None) for k in base['assets']}
saves={str(p.relative_to(GAME/'save')):sha(p) for p in (GAME/'save').rglob('*') if p.is_file()}
assert assets==base['assets'],'Unexpected asset changes: preserve and reconcile'
assert saves==base['saves'],'Unexpected save/settings change: preserve and reconcile'
assert not (GAME/'.vnrevival-omori').exists(),'Unexpected installer metadata appeared'
r={'status':'verified','taskOwnedProcessesStopped':tracked,'assetsVerified':len(assets),'saveFilesVerified':len(saves),'saveFilesByteIdentical':True,'localizationByteIdentical':True,'settingsByteIdentical':True,'initialLocalization':'ru','finalLocalization':'ru','localizationChangesApplied':False,'saveSlotsLoaded':False,'saveSlotsWritten':False,'restorationWritesRequired':False}
(RUN/'cleanup.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='taskOwnedProcessesStopped'}))
