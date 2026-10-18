# Oculix/Jython adapter of the canonical Stardew guarded capture runner.
from sikuli import *
from java.io import File
from javax.imageio import ImageIO
import os,sys,json,subprocess,time
root=sys.argv[1];title=sys.argv[2];output=sys.argv[3]
if os.path.exists(output): raise RuntimeError('Preserve existing capture')
windows=json.loads(subprocess.check_output([os.path.join(root,'window-list'),title]))
if len(windows)!=1: raise RuntimeError('Expected one identified visible window: '+title)
w=windows[0];wid=str(w['kCGWindowNumber'])
# Capture the exact native window, without resizing or annotations.
subprocess.check_call(['/usr/sbin/screencapture','-x','-l',wid,output])
frame=ImageIO.read(File(output))
if frame is None or frame.getWidth()<400 or frame.getHeight()<300: raise RuntimeError('Invalid captured frame')
screen=Screen()
with open(output+'.json','w') as f:json.dump({'window':w,'width':frame.getWidth(),'height':frame.getHeight(),'screenLogical':{'width':screen.w,'height':screen.h},'method':'Oculix guarded native window capture; canonical Stardew adapter pattern','visualReview':'pending'},f)
print('CAPTURE_PASS '+output)
