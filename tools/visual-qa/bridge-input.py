"""One guarded game-thread DOM key pulse, with actual native focus evidence."""
import json,time,uuid,subprocess
from pathlib import Path
from runtime import RUN,state,save

ACK_TIMEOUT_SECONDS=60
def await_release(path,ident,timeout_seconds=ACK_TIMEOUT_SECONDS):
 deadline=time.monotonic()+timeout_seconds;reply=None
 while time.monotonic()<deadline:
  try:
   value=json.loads(path.read_text())
   if value.get('id')==ident:
    reply=value
    if reply['status'] in ['released','error']:break
  except (OSError,ValueError):pass
  time.sleep(.02)
 return reply

def pulse(pid,key,evidence,keys,focus_guard):
 native=RUN/'native-control';before=state();code,name=keys[key]
 def focus():return json.loads(subprocess.check_output([str(native),str(pid),'state']))
 first=focus()
 # Retain the boundary evidence even if no input can be dispatched.
 save(evidence,dict(key=key,inputMethod='game-thread-dom-bridge',before=before,native=first,returncode=None,requestSubmitted=False))
 focus_guard(first)
 own=json.loads((RUN/'owned-game.json').read_text());base=Path(own['statePath'])
 request=Path(str(base)+'.input-request.json');ack=Path(str(base)+'.input-ack.json');ident=uuid.uuid4().hex
 payload=dict(type='keyPulse',id=ident,keyCode=code,createdAt=time.time())
 temp=request.with_suffix('.json.new');assert not temp.exists();temp.write_text(json.dumps(payload));temp.replace(request)
 save(evidence,dict(key=key,inputMethod='game-thread-dom-bridge',before=before,native=first,request=payload,returncode=None))
 wait_started=time.monotonic();reply=await_release(ack,ident);wait_elapsed=time.monotonic()-wait_started
 success=bool(reply and reply['status']=='released' and len(reply['samples'])==3 and all(x['current'] for x in reply['samples']))
 last=focus()
 save(evidence,dict(key=key,inputMethod='game-thread-dom-bridge',before=before,native=first,nativeAfter=last,request=payload,bridge=reply,returncode=0 if success else 1,requestSubmitted=True,ackDeadlineSeconds=ACK_TIMEOUT_SECONDS,ackWaitElapsedSeconds=wait_elapsed))
 focus_guard(last)
 assert success,'Game-thread input was not sampled and released: '+str(reply)
 after=state()
 save(evidence,dict(key=key,inputMethod='game-thread-dom-bridge',before=before,afterRelease=after,native=first,nativeAfter=last,request=payload,bridge=reply,returncode=0,requestSubmitted=True,ackDeadlineSeconds=ACK_TIMEOUT_SECONDS,ackWaitElapsedSeconds=wait_elapsed,
  mode='Untrusted DOM key events sampled on three normal Input.update calls; no OS keyboard event, scene API, save API, or equipment API invoked'))
 return after
