"""Read-only startup diagnosis: no key, focus or gameplay command."""
import time
from runtime import RUN,launch,stop,state,save,check_desktop
from batch import apply,restore
from vision import Vision
pid=None;v=None
try:
 check_desktop();apply('es');pid=launch('es');v=Vision(RUN/'es');samples=[]
 for n in range(12):
  s=state(allow_stale=True);samples.append(s);save(RUN/'startup-samples.json',samples)
  if n in [0,11]:
   image,rgb,window=v.capture(pid,'startup-probe');marker=v.match(rgb,'title-logo.png');save(RUN/('startup-frame-'+str(n)+'.json'),{'state':s,'image':str(image),'window':window,'marker':marker})
  time.sleep(1)
 save(RUN/'mari-status.json',{'status':'complete-startup-diagnosis','gameInputSent':False,'saveSlotsLoaded':False,'saveSlotsWritten':False})
finally:
 if v:v.close()
 if pid:stop()
 restore()
