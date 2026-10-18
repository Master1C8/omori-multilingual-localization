"""Native OMORI capture ownership, byte protection and read-only runtime inspection."""
import json,subprocess,time,os,signal,hashlib,urllib.request,plistlib,re
from pathlib import Path
from websockets.sync.client import connect
ROOT=Path(os.environ.get('OMORI_QA_PROJECT',str(Path(__file__).resolve().parents[2])));RUN=Path(os.environ.get('OMORI_QA_RUN',str(ROOT/'runtime/visual-qa/20261017-native-r2')));BASE=ROOT/'runtime/visual-qa/20261017-native';APP=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app');GAME=APP/'Contents/Resources/app.nw';CATALOG=Path(os.environ.get('OMORI_QA_CATALOG',str(ROOT/'build/installer/payload-v5')));PORT=9238
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def resource_baseline(catalog=None):
 original=json.loads((BASE/'baseline.json').read_text())['assets']
 catalog=catalog or json.loads((CATALOG/'catalog.json').read_text());ru=next(v for v in catalog['locales'] if v['code']=='ru')
 owned={k:v['sha256'] for k,v in ru['files'].items()}
 fix=json.loads((ROOT/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json').read_text())
 legacy=ROOT/fix['oldNativeBuild'];old_manifest=json.loads((legacy/'manifest.json').read_text());old_owned={r['path']:r['sha256'] for r in old_manifest['files']}
 if owned==old_owned:
  assert ru['archiveSha256']==sha(legacy/'omori-ru-direct-8879120.zip'),'Russian baseline archive identity changed'
  assert all(original[k]==h for k,h in owned.items())
  return original,'historical-russian'
 build=ROOT/fix['newNativeBuild'];manifest=json.loads((build/'manifest.json').read_text());expected={r['path']:r['sha256'] for r in manifest['files']}
 assert fix['status']=='verified' and owned==expected,'Unrecognized Russian catalog baseline'
 assert ru['archiveSha256']==sha(build/'omori-ru-direct-8879120.zip'),'Russian baseline archive identity changed'
 repaired=fix['finalRussianAssets'];assert set(repaired)==set(original)
 assert {k for k in original if original[k]!=repaired[k]}==set(fix['changedResourceFiles'])
 assert all(repaired[k]==h for k,h in owned.items())
 return repaired,'russian-level-repaired'
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')
def processes():
 rows={}
 for line in subprocess.check_output(['ps','-axo','pid=,ppid=,state=,command='],text=True,timeout=10).splitlines():
  v=line.strip().split(None,3)
  if len(v)==4:rows[int(v[0])]={'ppid':int(v[1]),'state':v[2],'command':v[3]}
 return rows
def check_saves():
 b=json.loads((BASE/'baseline.json').read_text());now={str(p.relative_to(GAME/'save')):sha(p) for p in (GAME/'save').rglob('*') if p.is_file()};assert now==b['saves'],'Protected save/settings files changed';return now
def check_desktop():
 value=plistlib.loads(subprocess.check_output(['/usr/sbin/ioreg','-n','Root','-d1','-a']))
 root=value[0] if isinstance(value,list) else value
 sessions=root.get('IOConsoleUsers',[])
 evidence={'consoleLocked':root.get('IOConsoleLocked'),'sessions':[{'screenLocked':s.get('CGSSessionScreenIsLocked'),'onConsole':s.get('CGSSessionOnConsoleKey')} for s in sessions]}
 save(RUN/'desktop-state.json',evidence)
 assert evidence['consoleLocked'] is False and sessions and not any(s.get('CGSSessionScreenIsLocked') is True for s in sessions),'macOS desktop locked or unavailable; no locale switch or game input permitted'
 return evidence
def state(allow_stale=False):
 owned=json.loads((RUN/'owned-game.json').read_text());p=Path(owned['statePath']);s=json.loads(p.read_text());assert allow_stale or time.time()*1000-s['time']<3000,'Stale runtime state';return s

def wait_for_observer(pid,state_path,directory):
 observer_deadline=time.monotonic()+180
 while True:
  if state_path.exists():
   sample=state(allow_stale=True)
   assert sample['observer']=='omori-oculix-event-observer-v1'
   if time.time()*1000-sample['time']<3000:break
   # Startup can write its first sample, then synchronously load resources.
   # A stale initial file is not readiness or a reason to launch again. Keep
   # this process and the original deadline until a genuinely fresh sample.
   save(directory/'startup-stale-observer.json',{'pid':pid,'time':time.time(),'sampleTime':sample['time'],'deadlineRetained':True})
  try:rows=processes()
  except subprocess.TimeoutExpired:
   # An unavailable read-only process query is not evidence of game exit.
   # Keep the same launch and original startup deadline; never infer an empty list.
   save(directory/'startup-process-query-timeout.json',{'pid':pid,'time':time.time(),'deadlineRetained':True})
   if time.monotonic()>=observer_deadline:raise
   continue
  assert pid in rows and not rows[pid]['state'].startswith('Z'),'Game exited during startup'
  if time.monotonic()>=observer_deadline:raise RuntimeError('Runtime observer unavailable after180 real seconds')
  time.sleep(.5)

def launch(code, attempt=None):
 assert not any(v['command'].startswith(str(APP)+'/') and not v['state'].startswith('Z') for v in processes().values()),'Existing game or surviving helper must be preserved'
 check_saves();directory=RUN/(attempt or code);assert not directory.exists();directory.mkdir(parents=True)
 index=GAME/'index.html';raw=index.read_bytes();backup=directory/'index-before.html';backup.write_bytes(raw)
 state_path=directory/'state.json';bridge=directory/'observer.js'
 package=GAME/'package.json';package_raw=package.read_bytes();package_instrumented=None
 if os.environ.get('OMORI_QA_BACKGROUND')=='1':
  (directory/'package-before.json').write_bytes(package_raw)
  config=json.loads(package_raw);flags='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows --disable-features=MacWebContentsOcclusion'
  # Keep the same hardware WebGL renderer but isolate GPU submission from NW's
  # browser process. The stalled VI native sample waited in Metal submission.
  original_args=config.get('chromium-args','').split()
  gpu_overrides={'--in-process-gpu','--enable-gpu-rasterization','--enable-gpu-memory-buffer-video-frames',
   '--enable-native-gpu-memory-buffers','--enable-zero-copy','--enable-gpu-async-worker-context','--disable-direct-composition'}
  config['chromium-args']=' '.join(x for x in original_args if x not in gpu_overrides)
  config['chromium-args']=config.get('chromium-args','')+' '+flags
  config.setdefault('window',{})['focus']=False
  config['window']['show']=False
  package_instrumented=(json.dumps(config,indent=2)+'\n').encode()
  save(directory/'launch-settings.json',{'temporary':True,'window':config['window'],'chromiumArgs':config['chromium-args'],
   'gpuMode':'separate-process','removedGpuOverrides':[x for x in original_args if x in gpu_overrides],
   'originalPackageSha256':hashlib.sha256(package_raw).hexdigest(),'instrumentedPackageSha256':hashlib.sha256(package_instrumented).hexdigest()})
 source=Path(__file__).with_name('runtime-observer.js').read_text().replace('__STATE_PATH__',json.dumps(str(state_path)));bridge.write_text(source)
 startup=directory/'startup-observer.js';startup.write_text(Path(__file__).with_name('startup-observer.js').read_text().replace('__STATE_PATH__',json.dumps(str(state_path))))
 marker=('<script src="'+bridge.as_uri()+'"></script>\n').encode();early=('<script src="'+startup.as_uri()+'"></script>\n').encode()
 assert raw.count(b'<head>')==1 and raw.count(b'</body>')==1,'Unknown native entry-point layout'
 instrumented=raw.replace(b'<head>',b'<head>\n'+early).replace(b'</body>',marker+b'</body>');assert instrumented!=raw
 index.write_bytes(instrumented)
 try:
  if package_instrumented is not None:package.write_bytes(package_instrumented)
  if os.environ.get('OMORI_QA_BACKGROUND')=='1':
   proof=ROOT/'runtime/visual-qa/20261018-equipment/run-pt-BR-02/owned-game.json'
   old=json.loads(proof.read_text());command=old['stoppingProcesses'][str(old['pid'])]
   prefix=str(APP/'Contents/MacOS/nwjs')+' ';assert command.startswith(prefix)
   argument=command[len(prefix):];assert re.fullmatch(r'--[0-9a-f]{32}',argument)
   assert (GAME/'steam_appid.txt').read_text().strip()=='1150690'
   save(directory/'steam-launch-request.json',{'method':'direct native app via LaunchServices open -g',
    'submittedAt':time.time(),'priorNativeGameProcesses':[],'argumentProof':str(proof),'argumentProofSha256':sha(proof)})
   subprocess.check_call(['/usr/bin/open','-g','-a',str(APP),'--args',argument])
  else:
   save(directory/'steam-launch-request.json',{'uri':'steam://rungameid/1150690','submittedAt':time.time(),'priorNativeGameProcesses':[]})
   subprocess.check_call(['/usr/bin/open','-g','steam://rungameid/1150690'])
  pid=None
  for _ in range(120):
   matches=[p for p,v in processes().items() if v['command'].startswith(str(APP/'Contents/MacOS/nwjs')+' ') and not v['state'].startswith('Z')]
   assert len(matches)<=1,'Ambiguous native game launch'
   if matches:pid=matches[0];break
   time.sleep(.25)
  assert pid is not None,'Steam request submitted but native game readiness unknown; reconcile before retry'
  save(RUN/'owned-game.json',{'pid':pid,'locale':code,'executable':str(APP/'Contents/MacOS/nwjs'),'startedAt':time.time(),'statePath':str(state_path),'directory':str(directory),'launchMethod':'native background LaunchServices with verified Steam argument' if os.environ.get('OMORI_QA_BACKGROUND')=='1' else 'native Steam URI with reconciled unique process'})
  # A verified background cold start previously needed128s. Keep a real-clock
  # bound without rejecting that known valid startup condition.
  wait_for_observer(pid,state_path,directory)
 finally:
  try:
   assert index.read_bytes()==instrumented,'Concurrent game index change';index.write_bytes(raw);assert index.read_bytes()==raw
  finally:
   if package_instrumented is not None:
    assert package.read_bytes()==package_instrumented,'Concurrent game package change'
    package.write_bytes(package_raw);assert package.read_bytes()==package_raw
 if os.environ.get('OMORI_QA_BACKGROUND')=='1':
  rows=processes()
  gpu=[{'pid':p,'ppid':v['ppid'],'command':v['command']} for p,v in rows.items()
       if v['ppid']==pid and v['command'].startswith(str(APP)+'/') and '--type=gpu-process' in v['command'] and not v['state'].startswith('Z')]
  save(RUN/'gpu-process-proof.json',{'ownerPid':pid,'gpuProcesses':gpu})
 print('LAUNCHED',code,pid,flush=True);return pid
def stop():
 owned=json.loads((RUN/'owned-game.json').read_text());rows=processes();pid=owned['pid'];ids={pid}
 if pid in rows and not rows[pid]['state'].startswith('Z'):
  assert rows[pid]['command'].startswith(owned['executable']+' '),'PID reused'
  while True:
   extra={p for p,v in rows.items() if v['ppid'] in ids}-ids
   if not extra:break
   ids.update(extra)
  tracked={p:rows[p] for p in ids if rows[p]['command'].startswith(str(APP)+'/')}
  owned['stoppingProcesses']={str(p):v['command'] for p,v in tracked.items()};save(RUN/'owned-game.json',owned)
  os.kill(pid,signal.SIGTERM)
 else:
  tracked={int(p):{'command':command} for p,command in owned.get('stoppingProcesses',{}).items()}
 if tracked:
  stop_deadline=time.monotonic()+30
  while True:
   now=processes();alive={p:v for p,v in tracked.items() if p in now and now[p]['command']==v['command'] and not now[p]['state'].startswith('Z')}
   if not alive:break
   if time.monotonic()>=stop_deadline:raise RuntimeError('Task-owned child still active after30 real seconds; do not change locale')
   time.sleep(.2)
 save(Path(owned.get('directory',str(RUN/owned['locale'])))/'stopped.json',{'pid':pid,'stopped':True,'protectedFiles':check_saves()})
if __name__=='__main__':
 import sys
 if sys.argv[1]=='launch':launch(sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
 elif sys.argv[1]=='state':print(json.dumps(state(),indent=2))
 elif sys.argv[1]=='stop':stop()
