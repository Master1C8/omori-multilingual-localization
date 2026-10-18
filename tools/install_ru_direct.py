#!/usr/bin/env python3
"""Guarded local native-file installation; preserve originals and owned loader files."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
from research_source import decrypt
ROOT=Path(__file__).resolve().parents[1]
GAME=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
BUILD=ROOT/'dist/ru-direct-8879120-2026-10-14-01'
OUT=ROOT/'diagnostics/ru-direct-launch-2026-10-14'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def make_plan():
    manifest=json.loads((BUILD/'manifest.json').read_text());rows=[]
    research=json.loads((ROOT/'source/research-8879120-02/manifest.json').read_text())
    for a in research['assets']:assert sha(GAME/a['asset'])==a['encryptedSha256'],a['asset']
    assert sha(GAME/'js/plugins.js')==research['pluginConfigurationSha256']
    for r in manifest['files']:
        src=BUILD/'files'/r['path'];dest=GAME/r['path'];assert sha(src)==r['sha256']
        if r['plaintextSha256']:assert hashlib.sha256(decrypt(src)[0].encode()).hexdigest()==r['plaintextSha256']
        assert dest.resolve().is_relative_to(GAME.resolve()) and not dest.is_symlink()
        rows.append({'path':r['path'],'before':sha(dest) if dest.exists() else None,'after':r['sha256']})
    installed=json.loads((ROOT/'diagnostics/ru-launch-2026-10-14/install-result.json').read_text())['plan']['files']
    owned={r['path']:r['after'] for r in installed if r['path'].startswith(('mods/','modloader/'))}
    actual={str(p.relative_to(GAME)):sha(p) for d in ['mods','modloader'] for p in (GAME/d).rglob('*') if p.is_file()}
    assert owned==actual,'Loader directories changed; preserve and reconcile before moving'
    p={'gameRoot':str(GAME),'buildManifestSha256':sha(BUILD/'manifest.json'),'files':rows,'preserveLoaderDirectories':['mods','modloader'],'loaderOwnership':actual}
    p['fingerprint']=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest();return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply');a=ap.parse_args();p=make_plan();OUT.mkdir(parents=True,exist_ok=True)
    if not a.apply:save(OUT/'install-plan.json',p);print(json.dumps({'files':len(p['files']),'fingerprint':p['fingerprint'],'newFiles':sum(r['before'] is None for r in p['files'])}));return
    assert a.apply==p['fingerprint'];assert not (OUT/'install-result.json').exists()
    assert subprocess.run(['pgrep','-f','/OMORI.app/Contents/MacOS/nwjs'],stdout=subprocess.DEVNULL).returncode==1,'Close game first'
    # Complete backups before the first replacement, including exact readback.
    for r in p['files']:
        if r['before']:
            dest=OUT/'backup'/r['path'];assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(GAME/r['path'],dest);assert sha(dest)==r['before']
    changed=[];moved=[]
    try:
        for r in sorted(p['files'],key=lambda r:r['path']=='index.html'):
            dest=GAME/r['path'];assert (sha(dest) if dest.exists() else None)==r['before']
            dest.parent.mkdir(parents=True,exist_ok=True)
            save(OUT/'install-journal.json',{'status':'writing','current':r['path'],'completed':changed,'fingerprint':p['fingerprint']})
            tmp=dest.with_name(dest.name+'.ru-direct-staging');assert not tmp.exists();shutil.copyfile(BUILD/'files'/r['path'],tmp);assert sha(tmp)==r['after'];os.replace(tmp,dest);changed.append(r['path'])
        for directory in p['preserveLoaderDirectories']:
            target=OUT/'preserved-oneloader'/directory;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(GAME/directory),str(target));moved.append(directory)
        assert all(sha(GAME/r['path'])==r['after'] for r in p['files'])
        save(OUT/'install-result.json',{'status':'installed-and-readback-verified','plan':p,'backupRoot':str(OUT/'backup'),'preservedLoader':str(OUT/'preserved-oneloader'),'saveFilesModified':False,'boundary':'Per-file atomic replacement with caught-failure rollback. index.html is activated last. Unexpected interruption requires journal reconciliation.'})
        save(OUT/'install-journal.json',{'status':'complete','fingerprint':p['fingerprint'],'completed':changed,'movedDirectories':moved})
        print(json.dumps({'status':'installed-and-readback-verified','files':len(changed),'activeLoader':'none'}))
    except BaseException:
        for d in reversed(moved):shutil.move(str(OUT/'preserved-oneloader'/d),str(GAME/d))
        by_path={r['path']:r for r in p['files']}
        for rel in reversed(changed):
            r=by_path[rel];dest=GAME/rel;assert sha(dest)==r['after'],'Concurrent modification; rollback stopped'
            if r['before']:shutil.copy2(OUT/'backup'/rel,dest)
            else:dest.unlink()
        save(OUT/'install-journal.json',{'status':'rolled-back','fingerprint':p['fingerprint']});raise
if __name__=='__main__':main()
