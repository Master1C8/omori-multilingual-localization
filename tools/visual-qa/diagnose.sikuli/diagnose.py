from org.sikuli.script import Finder,Pattern
from java.io import File
from javax.imageio import ImageIO
import os,sys,json,subprocess,time,traceback
root=os.path.abspath(sys.argv[1]);run=os.path.join(root,'runtime/visual-qa/20261017-native-r2');owned=json.load(open(os.path.join(run,'owned-game.json')));pid=owned['pid'];directory=owned['directory'];statepath=owned['statePath'];counter=0;receipts=[]
def state():
 s=json.load(open(statepath));assert time.time()*1000-s['time']<3000;return s
def observe(label):
 global counter
 ws=json.loads(subprocess.check_output([os.path.join(root,'build/installer/window-list'),'OMORI']));ws=[w for w in ws if w['kCGWindowOwnerPID']==pid and w.get('kCGWindowIsOnscreen')];assert len(ws)==1
 b=ws[0]['kCGWindowBounds'];assert b['Width']==640 and b['Height']==508
 path=os.path.join(directory,label+'.png');subprocess.check_call(['/usr/sbin/screencapture','-x','-R%d,%d,640,480'%(b['X'],b['Y']+28),path]);rgb=path+'.rgb.png';subprocess.check_call(['/opt/homebrew/bin/magick',path,'-alpha','off','-depth','8','PNG24:'+rgb]);return path,rgb
def is_title(rgb):
 f=Finder(ImageIO.read(File(rgb)))
 try:
  f.find(Pattern(os.path.join(root,'tools/visual-qa/templates/title-logo.png')).similar(.94));return f.hasNext()
 finally:f.destroy()
def guarded_title():
 global counter
 for _ in range(100):
  counter+=1;path,rgb=observe('title-%03d'%counter);s=state()
  if is_title(rgb) and s.get('active') and 'Title' in s.get('scene',''):return s
  time.sleep(1)
 raise RuntimeError('Title state not reached')
try:
 subprocess.check_call([os.path.join(run,'native-control'),str(pid),'focus']);time.sleep(5)
 s=guarded_title();assert s['index']==1, s
 before={'label':'before-old-input','runtime':s,'native':json.loads(subprocess.check_output([os.path.join(run,'native-control'),str(pid),'state']))};receipts.append(before)
 subprocess.check_call([os.path.join(root,'runtime/visual-qa/20261017-native/native-input'),'key','6']);time.sleep(2);s=state();receipts.append({'label':'after-old-input','runtime':s});observe('after-old-input')
 if 'Title' in s.get('scene',''):
  guarded_title();assert state()['index']==1
  subprocess.check_call([os.path.join(run,'native-control'),str(pid),'key','6']);time.sleep(2);s=state();receipts.append({'label':'after-targeted-input','runtime':s});observe('after-targeted-input')
 with open(os.path.join(directory,'input-diagnosis.json'),'w') as f:json.dump(receipts,f,indent=2)
 print('DIAGNOSIS_RESULT '+json.dumps(s))
except:
 with open(os.path.join(directory,'input-diagnosis.json'),'w') as f:json.dump(receipts,f,indent=2)
 observe('diagnosis-failure');traceback.print_exc();sys.exit(2)
