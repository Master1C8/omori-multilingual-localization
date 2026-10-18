"""Oculix Finder state guards using exact native window captures."""
import json,subprocess,time,struct,os
from pathlib import Path
from runtime import ROOT,RUN,state,save,check_desktop
JAVA='/opt/homebrew/opt/openjdk@17/bin/java';JAR='/Users/antonkrutov/Applications/Oculix/oculixide-4.0.0-macos.jar'
TEMPLATES=RUN/'templates' if (RUN/'templates').is_dir() else ROOT/'tools/visual-qa/templates'
def native_candidates(windows,pid,background=False):
 return [w for w in windows if w['kCGWindowOwnerPID']==pid and (background or w.get('kCGWindowIsOnscreen')) and w['kCGWindowBounds']['Width']==640 and w['kCGWindowBounds']['Height']==508]
def native_capture(pid,directory,label,counter):
 check_desktop();attempts=[]
 for attempt in range(2):
  deadline=time.monotonic()+6;all_windows=[]
  while True:
   all_windows=json.loads(subprocess.check_output([str(RUN/'native-window'),str(pid)]))
   ws=native_candidates(all_windows,pid,os.environ.get('OMORI_QA_BACKGROUND')=='1')
   if len(ws)==1:
    w=ws[0];break
   if time.monotonic()>deadline:
    try:native=json.loads(subprocess.check_output([str(RUN/'native-control'),str(pid),'state']))
    except Exception:native=None
    save(directory/'window-boundary.json',{'allWindows':all_windows,'pid':pid,'nativeState':native})
    raise RuntimeError('Task-owned window did not settle at native dimensions: '+str(all_windows))
   time.sleep(.2)
  suffix='' if attempt==0 else '-retry-1'
  raw=directory/('%04d-%s%s-window.png'%(counter,label,suffix))
  try:
   result=subprocess.run(['/usr/sbin/screencapture','-x','-o','-T','0','-l',str(w['kCGWindowNumber']),str(raw)],capture_output=True,text=True,timeout=10)
  except subprocess.TimeoutExpired as error:
   # subprocess.run has killed/waited its exact capture child. Reconcile the
   # unique output before another read: WindowServer can finish the PNG while
   # the command itself is still exiting. Never invent a zero exit code.
   valid=False;validation=None
   try:
    import io
    from PIL import Image
    payload=raw.read_bytes()
    with Image.open(io.BytesIO(payload)) as im:
     assert im.format=='PNG' and im.size==(1280,1016);im.verify()
    with Image.open(io.BytesIO(payload)) as im:im.load()
    valid=True
   except Exception as reason:validation=repr(reason)
   attempts.append(dict(attempt=attempt+1,pid=pid,window=w,raw=str(raw),returncode=None,timedOut=True,timeoutSeconds=10,completeNativePngValidated=valid,validationError=validation,time=time.time()))
   save(directory/('%04d-%s-native-capture-attempts.json'%(counter,label)),attempts)
   if valid:return raw,w
   if attempt==1:raise
   check_desktop();time.sleep(.2);continue
  attempts.append({'attempt':attempt+1,'pid':pid,'window':w,'raw':str(raw),'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'time':time.time()})
  save(directory/('%04d-%s-native-capture-attempts.json'%(counter,label)),attempts)
  if result.returncode==0:return raw,w
  # WindowServer can reject a single read while the same hidden game remains
  # healthy. Re-enumerate the owned window once; never replay any game input.
  if attempt==1 or result.returncode!=1 or result.stderr.strip()!='could not create image from window':result.check_returncode()
  check_desktop();time.sleep(.2)
 raise AssertionError('Native capture exhausted without a result')

class Vision:
 def __init__(self,directory):
  self.directory=Path(directory);self.counter=0;self.log=(self.directory/'oculix-engine.log').open('a');self.p=subprocess.Popen([JAVA,'-Djava.awt.headless=true','-cp',JAR+':'+str(RUN),'OculixMatch','--serve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True)
 def match(self,image,template):
  self.p.stdin.write(str(image)+'\t'+str(TEMPLATES/template)+'\t0.94\n');self.p.stdin.flush()
  while True:
   line=self.p.stdout.readline();assert line,'Oculix matcher exited';self.log.write(line);self.log.flush()
   if line.startswith('OCULIX_RESULT '):
    r=json.loads(line[len('OCULIX_RESULT '):]);assert 'error' not in r,r;return r
 def capture(self,pid,label):
  self.counter+=1;raw,w=native_capture(pid,self.directory,label,self.counter);path=self.directory/('%04d-%s.png'%(self.counter,label))
  subprocess.check_call(['/opt/homebrew/bin/magick',str(raw),'-crop','1280x960+0+56','+repage',str(path)])
  assert struct.unpack('>II',path.read_bytes()[16:24])==(1280,960)
  rgb=path.with_suffix('.rgb.png');subprocess.check_call(['/opt/homebrew/bin/magick',str(path),'-alpha','off','-depth','8','PNG24:'+str(rgb)],stderr=subprocess.DEVNULL)
  return path,rgb,w
 def require(self,pid,marker,scene=None,timeout=90):
  end=time.monotonic()+timeout;refocused=False
  while True:
   s=state(allow_stale=True)
   # Boot loads encrypted resources synchronously. Repeated native capture and
   # image matching add needless contention before the title can exist. Wait
   # through known startup states, then still require the real native marker.
   if scene=='Title' and (s.get('scene') in (None,'Scene_Boot','Scene_SplashScreens') or (s.get('scene')=='Scene_OmoriTitleScreen' and not s.get('startupDiagnostics',{}).get('sceneStarted'))) and not s.get('engineStopped') and not s.get('visibleError') and time.monotonic()<end:
    save(self.directory/'startup-wait.json',{'state':s,'waitingFor':scene,'remainingSeconds':round(end-time.monotonic(),1)})
    time.sleep(.5)
    continue
   native=json.loads(subprocess.check_output([str(RUN/'native-control'),str(pid),'state']))
   if scene=='Title' and not native['targetActive'] and os.environ.get('OMORI_QA_BACKGROUND')!='1':
    check_desktop();assert not refocused,'Native startup lost focus again; stop before input'
    focus=json.loads(subprocess.check_output([str(RUN/'native-control'),str(pid),'focus']))
    save(self.directory/'startup-refocus.json',{'before':s,'nativeBefore':native,'focus':focus})
    assert focus['targetActive'] and focus['frontmostPid']==pid,'Startup focus unavailable'
    refocused=True;time.sleep(3)
   path,rgb,w=self.capture(pid,marker);m=self.match(rgb,marker+'.png');s=state(allow_stale=True)
   if m['matched'] and time.time()*1000-s['time']<3000 and (not scene or scene in s.get('scene','')):return path,s,m,w
   if time.monotonic()>end:
    save(self.directory/'failure.json',{'marker':marker,'state':s,'frame':str(path)});raise RuntimeError('Unknown screen; expected '+marker+'; observed '+str(s))
   time.sleep(1)
 def close(self):
  self.p.stdin.close();self.p.wait(timeout=10);self.log.close()
