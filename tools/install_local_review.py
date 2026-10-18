#!/usr/bin/env python3
"""Install the owner-authorized OMORI review ZIP with guarded backups and readback."""
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
VENDOR = ROOT / 'source/vendor/OneLoader-1.5/extracted/www'
ZIP = ROOT / 'dist/ru-text-8879120-2026-10-14-11/omori-ru-text-8879120.zip'
OUT = ROOT / 'diagnostics/ru-launch-2026-10-14'
EXPECTED_ZIP = 'a6fc962f793647e2006e97877a831fc56e8d797731dd9125592772d2fac2600e'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, indent=2) + '\n')

def plan():
    assert sha(ZIP) == EXPECTED_ZIP, 'Russian package changed'
    assert not (GAME/'mods').exists() and not (GAME/'modloader').exists(), 'Existing mod installation requires reconciliation'
    x = json.loads((ROOT/'source/research-8879120-02/manifest.json').read_text())
    for a in x['assets']:
        assert sha(GAME/a['asset']) == a.get('encryptedSha256', a.get('rawSha256')), a['asset']
    assert sha(GAME/'js/plugins.js') == x['pluginConfigurationSha256']
    rows = []
    for src in sorted(VENDOR.rglob('*')):
        if not src.is_file():
            continue
        rel = src.relative_to(VENDOR).as_posix(); dest = GAME/rel
        assert not src.is_symlink() and not dest.is_symlink()
        assert dest.resolve().is_relative_to(GAME.resolve())
        if dest.exists():
            assert rel == 'index.html', f'Unexpected existing destination {rel}'
        rows.append({'path': rel, 'source': str(src.relative_to(ROOT)), 'before': sha(dest) if dest.exists() else None, 'after': sha(src)})
    rows.append({'path':'mods/omori-ru-text-8879120.zip','source':str(ZIP.relative_to(ROOT)),'before':None,'after':EXPECTED_ZIP})
    p = {'gameRoot':str(GAME),'packageSha256':EXPECTED_ZIP,'verifiedOriginalAssets':len(x['assets']),'files':rows}
    p['fingerprint'] = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()
    return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--apply'); a=ap.parse_args()
    p=plan(); OUT.mkdir(parents=True,exist_ok=True)
    if not a.apply:
        save(OUT/'install-plan.json',p)
        print(json.dumps({'files':len(p['files']),'replacements':[r['path'] for r in p['files'] if r['before']],'fingerprint':p['fingerprint']}));return
    assert a.apply == p['fingerprint'], 'Plan changed'
    assert subprocess.run(['pgrep','-f','/OMORI.app/Contents/MacOS/nwjs'],stdout=subprocess.DEVNULL).returncode == 1, 'Close OMORI first'
    assert not (OUT/'install-result.json').exists(), 'Reconcile existing installation receipt first'
    changed=[]; made_dirs=[]
    save(OUT/'install-journal.json',{'status':'preparing','planFingerprint':p['fingerprint']})
    try:
        for r in p['files']:
            dest=GAME/r['path']; src=ROOT/r['source']; backup=OUT/'backup'/r['path']
            assert sha(src)==r['after']
            if r['before']:
                assert sha(dest)==r['before']
                assert not backup.exists()
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
                assert sha(backup)==r['before']
            else:
                assert not dest.exists()
            missing=[]; d=dest.parent
            while not d.exists(): missing.append(d);d=d.parent
            assert d.resolve().is_relative_to(GAME.resolve())
            for d in reversed(missing):d.mkdir();made_dirs.append(d)
            save(OUT/'install-journal.json',{'status':'writing','planFingerprint':p['fingerprint'],'current':r['path'],'completed':changed})
            temp=dest.with_name(dest.name+'.omori-local-install-staging');assert not temp.exists()
            shutil.copyfile(src,temp)
            assert sha(temp)==r['after']; os.replace(temp,dest);changed.append(r['path'])
            assert sha(dest)==r['after']
        assert all(sha(GAME/r['path'])==r['after'] for r in p['files'])
        save(OUT/'install-result.json',{'status':'installed-and-readback-verified','plan':p,'backupRoot':str(OUT/'backup'),'createdDirectories':[str(d) for d in made_dirs],'commitBoundary':'Each file replacement is atomic; the group uses rollback on caught exceptions. Unexpected interruption requires journal reconciliation.','saveFilesTouched':False})
        save(OUT/'install-journal.json',{'status':'complete','planFingerprint':p['fingerprint'],'completed':changed})
        print(json.dumps({'status':'installed-and-readback-verified','files':len(changed),'packageSha256':EXPECTED_ZIP}))
    except BaseException:
        by_path={r['path']:r for r in p['files']}
        for rel in reversed(changed):
            r=by_path[rel];dest=GAME/rel
            assert sha(dest)==r['after'], 'Concurrent change; do not overwrite during rollback'
            if r['before']:shutil.copy2(OUT/'backup'/rel,dest)
            else:dest.unlink()
        for d in reversed(made_dirs):
            if d.exists() and not any(d.iterdir()):d.rmdir()
        save(OUT/'install-journal.json',{'status':'rolled-back','planFingerprint':p['fingerprint']})
        raise

if __name__=='__main__':main()
