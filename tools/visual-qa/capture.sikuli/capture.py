# Oculix/Jython 2.7. Native input/capture avoids the verified Java mouse failure.
from org.sikuli.script import Finder, Pattern
from java.io import File
from javax.imageio import ImageIO
import os,sys,time,json,subprocess,traceback
project=os.path.abspath(sys.argv[1]); run=os.path.abspath(sys.argv[2]); code=sys.argv[3]; pid=int(sys.argv[4]); output=os.path.abspath(sys.argv[5])
helper=os.path.join(run,'native-input'); templates=os.path.join(project,'tools/visual-qa/templates')
evidence=os.path.join(run,'evidence',code)
if not os.path.isdir(evidence):os.makedirs(evidence)
def window():
    ws=json.loads(subprocess.check_output([os.path.join(project,'build/installer/window-list'),'OMORI']))
    ws=[w for w in ws if int(w['kCGWindowOwnerPID'])==pid and w.get('kCGWindowIsOnscreen')]
    if len(ws)!=1:raise RuntimeError('Expected exactly one task-owned visible game window')
    b=ws[0]['kCGWindowBounds']
    if b['Width']!=640 or b['Height']!=508:raise RuntimeError('Window dimensions changed: '+str(b))
    return ws[0]
def capture(name):
    w=window();b=w['kCGWindowBounds'];path=os.path.join(evidence,name+'.png')
    subprocess.check_call(['/usr/sbin/screencapture','-x','-R%d,%d,640,480'%(b['X'],b['Y']+28),path])
    im=ImageIO.read(File(path))
    if im.getWidth()!=1280 or im.getHeight()!=960:raise RuntimeError('Native content dimensions changed')
    return path
counter=0
def matches(path,marker):
    global counter
    counter+=1; norm=os.path.join(evidence,'recognition-%04d.png'%counter)
    subprocess.check_call(['/opt/homebrew/bin/magick',path,'-alpha','off','-depth','8','PNG24:'+norm])
    finder=Finder(ImageIO.read(File(norm)))
    try:
        finder.find(Pattern(os.path.join(templates,marker+'.png')).similar(0.94))
        if finder.hasNext():
            m=finder.next();return {'x':m.x,'y':m.y,'score':m.getScore()}
        return None
    finally:finder.destroy()
def require(marker,timeout):
    end=time.time()+timeout
    while True:
        path=capture('state-%04d'%counter);m=matches(path,marker)
        if m:return path,m
        if time.time()>end:raise RuntimeError('Expected state marker not found: '+marker)
        time.sleep(1)
def publish(path,name):
    target=os.path.join(output,name)
    if os.path.exists(target):raise RuntimeError('Preserve existing screenshot: '+target)
    subprocess.check_call(['/bin/cp',path,target])
try:
    window();subprocess.check_call([helper,'focus',str(pid)]);time.sleep(5)
    title,tm=require('title-logo',90)
    # This representative Russian session was visually verified with Continue selected.
    # The source uses index 1 for Continue but does not guarantee that startup selects it.
    # Batch use requires its own selection guard and a working verified input path.
    title=capture('final-main-menu');require('title-logo',3)
    publish(title,code+'-01-main-menu.png')
    # Fresh visual guard immediately before the only gameplay input.
    require('title-logo',3)
    subprocess.check_call([helper,'key','6'])
    load,lm=require('load-portrait',20);time.sleep(2)
    load,lm=require('load-portrait',3)
    load=capture('final-load-game')
    publish(load,code+'-02-load-game.png')
    with open(os.path.join(evidence,'capture.json'),'w') as f:json.dump({'locale':code,'pid':pid,'window':window(),'dimensions':[1280,960],'titleMarker':tm,'loadMarker':lm,'input':'one Z press on guarded main menu; no slot selection/load/write','method':'Oculix Finder with native macOS content capture and input; Java mouse self-test incompatibility','automatedResult':'pass','visualReview':'pending'},f,indent=2)
    print('OCULIX_CAPTURE_PASS '+code)
except BaseException as error:
    traceback.print_exc()
    try:capture('failure')
    except:pass
    print('OCULIX_CAPTURE_FAIL '+code+': '+str(error));sys.exit(2)
