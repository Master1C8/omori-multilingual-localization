"""Read capture progress and prepare a native-size stats crop; never issue gates."""
import argparse,json,time
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('series',type=Path,nargs='?');p.add_argument('--run',type=Path);p.add_argument('--locale');a=p.parse_args()
root=Path(__file__).resolve().parents[2]
if a.run:
 assert a.locale;run=a.run.resolve();code=a.locale
 own=run/'owned-game.json';entry=dict(run=str(run),locale=code,pid=json.loads(own.read_text())['pid'] if own.exists() else None)
else:
 assert a.series;active=a.series/'active.json'
 if not active.exists():
  print(json.dumps(dict(active=False,complete=(a.series/'complete.json').exists())));raise SystemExit
 entry=json.loads(active.read_text());run=Path(entry['run']);code=entry['locale']
directory=run/code
r=dict(active=True,locale=code,run=str(run),pid=entry['pid'])
capture=directory/'equipment-capture.json';gate=directory/'visual-review.json'
if gate.exists():r.update(review=json.loads(gate.read_text())['status'],awaitingRestoration=True)
elif capture.exists():
 c=json.loads(capture.read_text());image=root/'dist/screenshots/20261017-native'/c['file'];stats=directory/'review-stats.png'
 with Image.open(image) as im:im.crop((360,132,836,470)).save(stats)
 proofs=[json.loads(f.read_text()) for f in directory.glob('*-input.json')]
 r.update(readyForReview=True,image=str(image),stats=str(stats),domFocused=c['state']['focused'],nativeFocusAtCapture=c.get('nativeFocusAtCapture'),
          allNativeInputsInactive=bool(proofs) and all(q['native']['targetActive'] is False and q['native']['frontmostPid']!=q['native']['targetPid'] for q in proofs),
          inputProofs=len(proofs),marker=c['marker'],equipmentChanged=c['equipmentChanged'])
else:
 state=directory/'state.json'
 own=run/'owned-game.json'
 if own.exists():
  owner=json.loads(own.read_text());r.update(nativePid=owner['pid'],nativeAgeSeconds=round(time.time()-owner['startedAt'],1))
 if not state.exists():
  startup=directory/'state.json.startup.json'
  if startup.exists():
   start=json.loads(startup.read_text());r.update(startupReadyState=start.get('readyState'),startupGlobals=start.get('globals'))
  else:r['phase']='native-observer-pending' if own.exists() else 'locale-apply-or-launch-pending'
 if state.exists():
  s=json.loads(state.read_text());r.update(scene=s.get('scene'),focused=s.get('focused'),visibleError=s.get('visibleError'),stateAgeSeconds=round(time.time()-s['time']/1000,1),frameScheduler=s.get('startupDiagnostics',{}).get('frameScheduler'))
  assets=s.get('assetReadiness')
  if assets:
   r['assetReadiness']={k:assets.get(k) for k in ['queueLength','pendingCacheCount','requiredNextAtlases','allNextAtlasesLoaded']}
   for name in ['queue','pendingCache']:
    r['assetReadiness'][name+'Sample']=[{k:x.get('bitmap',{}).get(k) for k in ['url','state','naturalWidth']} for x in assets.get(name,[])[:8]]
 proofs=list(directory.glob('*semantic-result.json'))
 if proofs:r['lastAction']=max(proofs,key=lambda q:q.stat().st_mtime).stem
 status=run/'equipment-status.json'
 if status.exists():r['status']=json.loads(status.read_text())
print(json.dumps(r))
