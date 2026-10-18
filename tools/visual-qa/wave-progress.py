"""Compact current checkpoint from actual immutable run receipts; no game control."""
import json,hashlib,time
from pathlib import Path
root=Path(__file__).resolve().parents[2];qa=root/'runtime/visual-qa/20261018-wave'
read=lambda p:json.loads(p.read_text())
entries=read(qa/'final-inputs.json')['entries'];accepted=[]
for e in entries:
 p=Path(e['run'])/e['locale']/'visual-review.json'
 if p.exists():
  v=read(p)
  if v['status']=='pass':
   assert hashlib.sha256((root/'dist/screenshots/20261017-native'/v['file']).read_bytes()).hexdigest()==v['sha256']
   accepted.append(e['locale'])
status=read(qa/'status.json');status.update(acceptedLocales=accepted,acceptedNewImages=len(accepted))
series=Path(status.get('series') or str(qa/'series-03'));a=series/'active.json';result=dict(accepted=len(accepted),total=27)
if status.get('status','').endswith('-native-proof-running'):
 active=dict(locale=status['activeLocale'],run=str((root/status['activeRun']).resolve()),pid=None)
elif status.get('status')=='batch-running' and a.exists():active=read(a)
else:active=None
if active:
 run=Path(active['run']);code=active['locale'];directory=run/code
 status.update(activeRun=str(run),activeLocale=code,coordinatorChildPid=active['pid'])
 result.update(locale=code)
 p=directory/'state.json.mari.json'
 if p.exists():
  s=read(p);result.update(scene=s.get('scene'),player=s.get('player'),observerAgeSeconds=round(time.time()-s['time']/1000,2))
 if (directory/'wave-capture.json').exists() and not (directory/'visual-review.json').exists():result.update(reviewReady=True,image=read(directory/'wave-capture.json')['file'])
 if (run/'wave-status.json').exists():result['runStatus']=read(run/'wave-status.json')
else:result['seriesComplete']=(series/'complete.json').exists()
temp=qa/'status.json.new';temp.write_text(json.dumps(status,indent=2)+'\n');temp.replace(qa/'status.json')
print(json.dumps(result))
