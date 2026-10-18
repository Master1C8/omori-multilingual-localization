"""Adopt only an exact verified Russian install into the existing adapter.
Original English bytes are recovered by their catalog hashes, never inferred.
"""
from runtime import ROOT,RUN,BASE,GAME,CATALOG,sha,save,processes,APP,check_saves,resource_baseline
import json,os
c=json.loads((CATALOG/'catalog.json').read_text());b=json.loads((BASE/'baseline.json').read_text());ru=next(l for l in c['locales'] if l['code']=='ru');meta=GAME/'.vnrevival-omori';assert not meta.exists()
b['assets'],resource_profile=resource_baseline(c)
assert not any(v['command'].startswith(str(APP/'Contents/MacOS/nwjs')) and not v['state'].startswith('Z') for v in processes().values())
check_saves();assert all((sha(GAME/k) if (GAME/k).exists() else None)==v for k,v in b['assets'].items())
originals={};sources={};blobs={}
for k,f in ru['files'].items():
 assert sha(GAME/k)==f['sha256'],k
 h=c['originals'].get(k,'-');originals[k]=h
 if h!='-':
  candidates=list(ROOT.glob('diagnostics/*/backup/'+k));p=next((p for p in candidates if p.is_file() and sha(p)==h),None);assert p,'Missing exact English original '+k;sources[k]=str(p);blobs[h]=p.read_bytes()
 # Current files are also retained so an interrupted future apply can roll back.
 blobs[f['sha256']]=(GAME/k).read_bytes()
plan={'kind':'hash-verified-install-adoption','locale':'ru','resourceProfile':resource_profile,'catalog':sha(CATALOG/'catalog.json'),'files':len(ru['files']),'originalSources':sources,'originals':originals,'baselineSha256':sha(BASE/'baseline.json'),'saveWrites':False}
save(RUN/'adoption-plan.json',plan)
(meta/'backups').mkdir(parents=True)
for h,d in blobs.items():
 p=meta/'backups'/h;p.write_bytes(d);assert sha(p)==h
save(meta/'state.json',{'schemaVersion':1,'gameRoot':str(GAME),'locale':'ru','runtimeCode':'en','catalog':sha(CATALOG/'catalog.json'),'originals':originals,'owned':{k:f['sha256'] for k,f in ru['files'].items()}})
save(RUN/'adoption.json',{'status':'verified','files':len(ru['files']),'originalEnglishFiles':len(sources),'metadataCreated':str(meta),'gameResourcesChanged':False,'saveWrites':False})
print('ADOPTED exact ru files with',len(sources),'hash-proven English originals',flush=True)
