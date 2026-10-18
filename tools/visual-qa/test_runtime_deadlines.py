"""Fake process/clock boundaries; these tests do not establish native cleanup."""
import json,tempfile,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import runtime as r

with patch.object(r.subprocess,'check_output',return_value='') as query:
    assert r.processes()=={}
    assert query.call_args.kwargs['timeout']==10
with patch.object(r.subprocess,'check_output',side_effect=subprocess.TimeoutExpired('ps',10)):
    try:r.processes()
    except subprocess.TimeoutExpired:pass
    else:raise AssertionError('An unavailable process query was treated as an empty process list')

for closes in [False,True]:
    with tempfile.TemporaryDirectory() as folder:
        run=Path(folder);app=run/'OMORI.app';exe=str(app/'Contents/MacOS/nwjs')
        own=dict(pid=101,executable=exe,locale='fixture');(run/'owned-game.json').write_text(json.dumps(own))
        clock=[0.0];calls=[0];signals=[]
        rows={101:dict(ppid=1,state='S',command=exe+' --fixture')}
        def processes():
            calls[0]+=1;clock[0]+=10
            return {} if closes and calls[0]>1 else rows
        fake_time=SimpleNamespace(monotonic=lambda:clock[0],sleep=lambda seconds:None)
        with patch.multiple(r,RUN=run,APP=app,time=fake_time,processes=processes,check_saves=lambda:{}),patch.object(r.os,'kill',side_effect=lambda p,s:signals.append((p,s))):
            if closes:r.stop()
            else:
                try:r.stop()
                except RuntimeError as error:assert 'after30 real seconds' in str(error)
                else:raise AssertionError('A surviving game was credited as stopped')
        assert signals==[(101,r.signal.SIGTERM)]
        if closes:assert json.loads((run/'fixture/stopped.json').read_text())['stopped'] is True
        else:assert calls[0]==4 and clock[0]==40 and not (run/'fixture/stopped.json').exists()
with tempfile.TemporaryDirectory() as folder:
    run=Path(folder);app=run/'OMORI.app';exe=str(app/'Contents/MacOS/nwjs');child=str(app/'Contents/Versions/helper')+' --type=gpu-process'
    (run/'owned-game.json').write_text(json.dumps(dict(pid=101,executable=exe,locale='fixture',stoppingProcesses={'101':exe+' --fixture','102':child})))
    clock=[0.0];signals=[]
    def orphan_rows():clock[0]+=10;return {102:dict(ppid=1,state='S',command=child)}
    with patch.multiple(r,RUN=run,APP=app,time=SimpleNamespace(monotonic=lambda:clock[0],sleep=lambda seconds:None),processes=orphan_rows,check_saves=lambda:{}),patch.object(r.os,'kill',side_effect=lambda p,s:signals.append((p,s))):
        try:r.stop()
        except RuntimeError as error:assert 'after30 real seconds' in str(error)
        else:raise AssertionError('Exited root hid its surviving GPU child')
    assert signals==[] and not (run/'fixture/stopped.json').exists()
print('PASS bounded process query, unavailable-query rejection, real stop deadline, successful-close control and surviving-child rejection after root exit; native cleanup remains separate.')

# Exercise the actual startup wait: one unavailable query may recover, but it
# must neither reset the deadline nor hide positive evidence of game exit.
for mode in ['recover','persistent-timeout','exit','persistent-live']:
    with tempfile.TemporaryDirectory() as folder:
        directory=Path(folder);marker=directory/'state.json';clock=[0.];calls=[0]
        def query_startup():
            calls[0]+=1;clock[0]+=60
            if mode=='persistent-timeout' or (mode=='recover' and calls[0]==1):
                raise subprocess.TimeoutExpired('ps',10)
            if mode=='exit':return {}
            if mode=='recover':marker.write_text('{}')
            return {101:{'state':'S'}}
        fake_time=SimpleNamespace(monotonic=lambda:clock[0],time=lambda:clock[0],sleep=lambda seconds:None)
        with patch.multiple(r,time=fake_time,processes=query_startup,state=lambda **kwargs:{'observer':'omori-oculix-event-observer-v1','time':clock[0]*1000}):
            try:r.wait_for_observer(101,marker,directory)
            except subprocess.TimeoutExpired:assert mode=='persistent-timeout'
            except AssertionError as error:assert mode=='exit' and 'exited' in str(error)
            except RuntimeError as error:assert mode=='persistent-live' and '180 real seconds' in str(error)
            else:assert mode=='recover' and calls[0]==2
        if mode=='persistent-timeout':assert calls[0]==3 and clock[0]==180
        if mode=='exit':assert calls[0]==1
print('PASS native-startup observer wait: transient process query recovery, unchanged deadline, persistent query failure and positive game-exit rejection. Native startup is not mocked proof.')

for freshens in [True,False]:
 with tempfile.TemporaryDirectory() as folder:
  directory=Path(folder);marker=directory/'state.json';marker.write_text('{}');clock=[10.];queries=[0]
  def rows():queries[0]+=1;clock[0]+=60;return {101:{'state':'S'}}
  def observed(**kwargs):return {'observer':'omori-oculix-event-observer-v1','time':clock[0]*1000 if freshens and queries[0] else 0}
  with patch.multiple(r,time=SimpleNamespace(monotonic=lambda:clock[0],time=lambda:clock[0],sleep=lambda seconds:None),processes=rows,state=observed):
   try:r.wait_for_observer(101,marker,directory)
   except RuntimeError as error:assert not freshens and '180 real seconds' in str(error)
   else:assert freshens and queries[0]==1
  assert (directory/'startup-stale-observer.json').exists()
print('PASS stale first observer sample waits for actual freshness on the same process; persistent staleness retains the original180s bound.')
