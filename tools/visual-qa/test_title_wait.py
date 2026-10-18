import sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path('tools/visual-qa').resolve()))
import vision
from time import time
states=iter([{'scene':'Scene_OmoriTitleScreen','startupDiagnostics':{'sceneStarted':False}}, {'scene':'Scene_OmoriTitleScreen','startupDiagnostics':{'sceneStarted':True},'time':time()*1000}, {'scene':'Scene_OmoriTitleScreen','startupDiagnostics':{'sceneStarted':True},'time':time()*1000}])
v=object.__new__(vision.Vision);v.directory=Path(tempfile.mkdtemp());calls=[]
v.capture=lambda *args:(calls.append(args) or ('image','rgb',{}))
v.match=lambda *args:{'matched':True}
with patch.object(vision,'state',side_effect=lambda **kwargs:next(states)),patch.object(vision.time,'sleep'),patch.object(vision.subprocess,'check_output',return_value='{"targetActive":false}'),patch.dict(vision.os.environ,{'OMORI_QA_BACKGROUND':'1'}):
 v.require(1,'title-logo',scene='Title')
assert len(calls)==1
print('PASS unstarted Title waits; started Title requires native matching')
