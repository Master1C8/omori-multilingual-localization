#!/usr/bin/env python3
"""Restore checksummed private editing sources without replacing existing work."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def relative(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p)!=name or '\\' in name:
        raise ValueError('Unsafe source path')
    return Path(*p.parts)
def safe_target(root,name):
    p=root/relative(name)
    cursor=root
    if cursor.is_symlink():raise ValueError('Symlink destination')
    for part in relative(name).parts:
        cursor=cursor/part
        if cursor.is_symlink():raise ValueError('Symlink in source destination')
    p.parent.resolve().relative_to(ROOT)
    return p
def restore(root,archive,locator,groups):
    if sha(archive)!=locator['archiveSha256']:raise ValueError('Private source archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        members={}
        for member in z.infolist():
            if member.filename in members:raise ValueError('Duplicate source archive member')
            members[member.filename]=member
        raw=z.read(locator['inventoryMember'])
        if hashlib.sha256(raw).hexdigest()!=locator['inventorySha256']:raise ValueError('Source inventory checksum mismatch')
        inventory=json.loads(raw)
        selected=inventory['groups'] if groups==['all'] else {k:inventory['groups'][k] for k in groups}
        files={}
        for group in selected.values():
            for name,pin in group.items():
                relative(name)
                if name in files and files[name]!=pin:raise ValueError('Conflicting source inventory')
                files[name]=pin
        missing=[]
        # Validate every existing preimage before publishing even the first file.
        # Other files in mixed source/input directories are deliberately preserved.
        for name,pin in files.items():
            p=safe_target(root,name)
            if os.path.lexists(p):
                if not p.is_file() or sha(p)!=pin['sha256']:raise ValueError('Existing edited source preserved: '+name)
            else:missing.append(name)
        cache=ROOT/'.build/private-source-recovery';cache.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='staged-',dir=cache) as work:
            staged=Path(work)
            for name in missing:
                member=members.get(name)
                if member is None or stat.S_ISLNK(member.external_attr>>16):raise ValueError('Missing or symlink source member')
                data=z.read(member);pin=files[name]
                if len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']:raise ValueError('Source member checksum mismatch: '+name)
                p=staged/relative(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            published=0
            for name in missing:
                target=safe_target(root,name);target.parent.mkdir(parents=True,exist_ok=True)
                # Same-project hardlink publication is atomic and refuses EEXIST.
                # Each file commits independently; a later failure leaves the
                # earlier complete files resumable, never overwritten/rolled back.
                os.link(staged/relative(name),target)
                published+=1
    return {'status':'restored' if missing else 'already-present','files':len(files),'published':published,'groups':list(selected)}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--group',action='append',default=[])
    p.add_argument('--rehearse',help='New project-relative generated rehearsal root')
    a=p.parse_args();locator=json.loads((ROOT/'archival-sources.json').read_text())
    cache=ROOT/'.build/private-source-recovery'/locator['archiveSha256'][:16];cache.mkdir(parents=True,exist_ok=True)
    archive=cache/relative(locator['asset']);assert archive.parent==cache
    if not archive.exists():
        status=subprocess.run(['gh','auth','status','--hostname','github.com'],capture_output=True)
        if status.returncode:raise RuntimeError('GitHub authentication required')
        account=subprocess.check_output(['gh','api','user','--jq','.login'],text=True).strip()
        if account!='Master1C8':raise RuntimeError('Use the canonical GitHub account Master1C8')
        subprocess.run(['gh','release','download',locator['releaseTag'],'--repo',locator['repository'],'--pattern',locator['asset'],'--dir',str(cache)],check=True)
    root=ROOT/relative(a.rehearse) if a.rehearse else ROOT
    root.mkdir(parents=True,exist_ok=True)
    print(json.dumps(restore(root,archive,locator,a.group or ['all']),ensure_ascii=False))
if __name__=='__main__':main()
