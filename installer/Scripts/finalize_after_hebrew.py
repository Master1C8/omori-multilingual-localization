#!/usr/bin/env python3
"""Finish both installer archives once the running Hebrew lane delivers its ZIP.
Uses an immutable helper/binary snapshot; never launches a game or CrossOver.
"""
import argparse,datetime,fcntl,hashlib,json,os,pathlib,shutil,subprocess,sys,time,zipfile

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def write(p,j):
 tmp=p.with_suffix('.new');tmp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);ap.add_argument('--run',type=pathlib.Path,required=True);ap.add_argument('--snapshot',type=pathlib.Path,required=True);ap.add_argument('--status',type=pathlib.Path,required=True);a=ap.parse_args()
 root=a.root.resolve();run=a.run.resolve();snapshot=a.snapshot.resolve();status=a.status.resolve();lock=status.with_suffix('.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 manifest=load(snapshot/'manifest.json')
 def verify_snapshot():
  for path,digest in manifest['files'].items():
   if sha(snapshot/path)!=digest:raise ValueError('Frozen installer helper/binary changed: '+path)
 verify_snapshot()
 receipt={'status':'waiting-hebrew-package','pid':os.getpid(),'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Build archives only; Windows runtime testing remains paused; native Mac game untouched.','snapshot':str(snapshot)};write(status,receipt)
 try:
  previous=None
  while True:
   state=load(run/'state.json');he=state['locales']['he'];label=he['status']
   if label in ('packaged-awaiting-review','local-scope-complete'):break
   if label!=previous:
    receipt.update(hebrewStatus=label,hebrewTask=he['attempts'][-1]['taskId']);write(status,receipt);previous=label
   time.sleep(30)
  verify_snapshot();checkpoint=he['workflow']['machinePackageCheckpoint'];archive=root/checkpoint['deliveredArchive']
  if sha(archive)!=checkpoint['archive']['sha256']:raise ValueError('Hebrew archive checkpoint changed')
  payload=root/'build/installer/payload-v5';release=root/'dist/installer/1.0.0-r3'
  if payload.exists() or release.exists():raise ValueError('Preserve existing output; reconcile prior build identity before retry')
  receipt.update(status='building-complete-language-set',hebrewArchive=str(archive));write(status,receipt)
  with (status.parent/'final-payload-build.log').open('wb') as log:
   subprocess.run([sys.executable,str(snapshot/'prepare_payload.py'),'--root',str(root),'--output',str(payload),'--reuse',str(root/'build/installer/payload-v4')],check=True,stdout=log,stderr=log)
  prepared=load(payload/'payload-receipt.json');catalog=load(payload/'catalog.json')
  if prepared['pendingLocales'] or len(prepared['locales'])!=27 or 'he' not in prepared['locales']:raise ValueError('Final app must include Russian and all26 targets')
  if sha(payload/'catalog.json')!=prepared['catalogSha256']:raise ValueError('Prepared catalog changed')
  release.mkdir(parents=True)
  mac=release/'OMORI Translation Installer.app';win=release/'OMORI Installer Windows'
  shutil.copytree(snapshot/'mac',mac);shutil.copytree(snapshot/'windows',win)
  for resources in [mac/'Contents/Resources',win/'Resources']:
   resources.mkdir(parents=True,exist_ok=True);shutil.copytree(payload,resources/'Payload');write(resources/'PackageConfig.json',{'catalogSha256':prepared['catalogSha256']})
  (win/'Resources/languages.tsv').write_text(''.join(l['code']+'\t'+l['name']+'\n' for l in catalog['locales']))
  subprocess.run(['codesign','--force','--deep','--sign','-',str(mac)],check=True)
  subprocess.run(['codesign','--verify','--deep','--strict',str(mac)],check=True)
  mz=release/'OMORI-Installer-macOS-1.0.0.zip';wz=release/'OMORI-Installer-Windows-1.0.0.zip'
  subprocess.run(['ditto','-c','-k','--keepParent',str(mac),str(mz)],check=True)
  with zipfile.ZipFile(wz,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for p in sorted(win.rglob('*')):
    if p.is_file():z.write(p,str(p.relative_to(release)))
  reports=[]
  for zpath,stage in [(mz,mac),(wz,win)]:
   if zpath.stat().st_size>100_000_000:raise ValueError('Installer exceeds100MB target')
   count=0
   with zipfile.ZipFile(zpath) as z:
    if len(z.namelist())!=len(set(z.namelist())) or z.testzip() is not None:raise ValueError('Damaged archive')
    for p in stage.rglob('*'):
     if p.is_file():
      name=str(p.relative_to(release));raw=z.read(name)
      if hashlib.sha256(raw).hexdigest()!=sha(p):raise ValueError('Delivered ZIP readback differs: '+name)
      count+=1
   reports.append({'path':str(zpath),'sha256':sha(zpath),'bytes':zpath.stat().st_size,'filesReadback':count})
  receipt.update(status='complete',finishedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifacts=reports,locales=prepared['locales'],pendingLocales=[],catalogSha256=prepared['catalogSha256'],runtime='Existing unchanged app cores tested; newly included Hebrew runtime/visual not-run. Windows testing remains owner-paused.');write(status,receipt);write(release/'BUILD-RECEIPT.json',receipt)
 except BaseException as e:
  receipt.update(status='needs-attention',error=str(e));write(status,receipt);raise
if __name__=='__main__':main()
