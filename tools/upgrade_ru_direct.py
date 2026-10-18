#!/usr/bin/env python3
"""Upgrade only changed files from an exactly verified prior native overlay."""
import argparse,json,hashlib,subprocess,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GAME=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--previous',type=Path,required=True);ap.add_argument('--build',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--apply');a=ap.parse_args()
    old=json.loads((a.previous/'manifest.json').read_text());new=json.loads((a.build/'manifest.json').read_text());before={r['path']:r['sha256'] for r in old['files']};after={r['path']:r['sha256'] for r in new['files']};assert set(before)==set(after)
    for p,h in before.items():assert sha(GAME/p)==h,'Previous native overlay changed: '+p
    for p,h in after.items():assert sha(a.build/'files'/p)==h
    assert not (GAME/'mods').exists() and not (GAME/'modloader').exists()
    changes=[{'path':p,'before':before[p],'after':after[p]} for p in before if before[p]!=after[p]]
    plan={'previousManifestSha256':sha(a.previous/'manifest.json'),'buildManifestSha256':sha(a.build/'manifest.json'),'changes':changes}
    fingerprint=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest();a.output.mkdir(parents=True,exist_ok=True)
    if not a.apply:(a.output/'upgrade-plan.json').write_text(json.dumps({'fingerprint':fingerprint,**plan},indent=2)+'\n');print(json.dumps({'fingerprint':fingerprint,'changedFiles':[r['path'] for r in changes]}));return
    assert a.apply==fingerprint;assert not (a.output/'upgrade-result.json').exists();assert subprocess.run(['pgrep','-f','/OMORI.app/Contents/MacOS/nwjs'],stdout=subprocess.DEVNULL).returncode==1
    for r in changes:
        p=a.output/'backup'/r['path'];p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();shutil.copy2(GAME/r['path'],p);assert sha(p)==r['before']
    done=[]
    try:
        for r in changes:
            dest=GAME/r['path'];assert sha(dest)==r['before'];tmp=dest.with_name(dest.name+'.ru-direct-upgrade');assert not tmp.exists();shutil.copyfile(a.build/'files'/r['path'],tmp);assert sha(tmp)==r['after'];os.replace(tmp,dest);done.append(r)
        assert all(sha(GAME/p)==h for p,h in after.items())
        (a.output/'upgrade-result.json').write_text(json.dumps({'status':'installed-and-all-file-readback-verified','fingerprint':fingerprint,**plan},indent=2)+'\n');print('Native overlay upgrade verified.')
    except BaseException:
        for r in reversed(done):assert sha(GAME/r['path'])==r['after'];shutil.copy2(a.output/'backup'/r['path'],GAME/r['path'])
        raise
if __name__=='__main__':main()
