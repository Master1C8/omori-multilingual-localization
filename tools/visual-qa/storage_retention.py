"""Exact, journaled retention of generated OMORI artifacts and restored QA caches.

Unknown files, source, translations, screenshots, live/queued inputs and hash pins
are protected. No game launch, save write, review gate or server action occurs.
"""
import argparse, collections, fcntl, gzip, hashlib, json, os, stat, subprocess, sys, time, uuid
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()


def inside(root, name):
    p=Path(name);p=p if p.is_absolute() else root/p
    if not p.is_relative_to(root) or p.resolve()!=p:
        raise ValueError('Path outside project or through symlink: '+str(p))
    return p


def signature(p):
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or p.resolve()!=p:
        raise ValueError('Not a regular non-symlink file: '+str(p))
    return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_mode,s.st_uid,s.st_gid]


def row(root,p,expected=None):
    s=signature(p);h=digest(p)
    if expected is not None and h!=expected: raise ValueError('Changed content: '+str(p))
    if signature(p)!=s: raise ValueError('Changed during inventory: '+str(p))
    return {'path':str(p.relative_to(root)),'signature':s,'sha256':h}


def save_new(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')


def atomic_save(p,d):
    tmp=p.with_name(p.name+'.new');tmp.write_text(json.dumps(d,indent=2)+'\n');os.replace(tmp,p)


def open_files():
    r=subprocess.run(['lsof','-nP','-F','n'],capture_output=True,text=True,timeout=30)
    if r.returncode not in (0,1) or r.stderr.strip():
        raise RuntimeError('Open-file inventory unavailable: '+r.stderr[:300])
    return {l[1:] for l in r.stdout.splitlines() if l.startswith('n/')}


def closed(root,run):
    run=inside(root,run)
    if not run.is_relative_to(root/'runtime/visual-qa'): raise ValueError('Not a QA run')
    restore=load(run/'restoration.json');level=load(run/'russian-level-restoration.json')
    owned=load(run/'owned-game.json');directory=inside(root,owned['directory'])
    if not directory.is_relative_to(run): raise ValueError('Owned process directory outside run')
    stopped=load(directory/'stopped.json')
    if restore.get('status')!='verified' or not level.get('levelRepairRestored') or not stopped.get('stopped'):
        raise ValueError('Run is not restored and stopped: '+str(run))
    guards=[run/'restoration.json',run/'russian-level-restoration.json',run/'owned-game.json',directory/'stopped.json']
    # A queued/running entry stays protected even if it contains old receipts.
    for active in (root/'runtime/visual-qa').glob('*/series-*/active.json'):
        if load(active).get('run')==str(run):raise ValueError('Run is still active: '+str(run))
    return guards


def keeper_paths(root):
    # The live legacy coordinator loads this exact keeper inventory between runs.
    proof=root/'diagnostics/cleanup-20261018-01/plan.json'
    if not proof.exists(): return set()
    return {x['keeper']['path'] for x in load(proof)['links']}


def archive_plan(root,run):
    run=inside(root,run);guards=closed(root,run);meta=run/'installer-metadata-final'
    if not meta.is_dir():return {'guards':[], 'delete':[], 'kind':'closed-qa-cache'}
    guards.append(meta/'state.json');state=load(meta/'state.json')
    allowed=set(state.get('owned',{}).values())|set(state.get('originals',{}).values())
    packages=[]
    for folder in sorted((meta/'packages').glob('*')):
        catalog=folder/'catalog.json'
        if not catalog.is_file():raise ValueError('Unknown archived package directory '+str(folder))
        d=load(catalog)
        if digest(catalog)!=folder.name:raise ValueError('Archived catalog hash mismatch')
        guards.append(catalog);allowed.update(d.get('originals',{}).values())
        for locale in d['locales']:allowed.update(x['sha256'] for x in locale['files'].values())
        for p in (folder/'objects').glob('*'):
            metadata=d['objects'].get(p.name)
            if metadata is None:raise ValueError('Unknown archived object '+str(p))
            packed=p.read_bytes();plain=gzip.decompress(packed)
            if len(packed)!=metadata['bytes'] or hashlib.sha256(packed).hexdigest()!=metadata['sha256'] or len(plain)!=metadata['unpackedBytes'] or hashlib.sha256(plain).hexdigest()!=p.name:
                raise ValueError('Archived compressed object changed '+str(p))
            packages.append(row(root,p,metadata['sha256']))
    protected=keeper_paths(root);backups=[]
    for p in sorted((meta/'backups').glob('*')):
        n=str(p.relative_to(root))
        if n in protected:continue
        if p.name not in allowed:continue  # Unique, unclassified evidence is retained.
        backups.append(row(root,p,p.name))
    return {'kind':'closed-qa-cache','run':str(run.relative_to(root)), 'guards':[row(root,p) for p in guards], 'delete':backups+packages}


def apply(root,plan,output,opened=None):
    output=inside(root,output);output.mkdir(parents=True,exist_ok=True)
    # Unknown/partial prior outcomes must be reconciled; never repeat a deletion blindly.
    if (output/'journal.jsonl').exists() and not (output/'result.json').exists():
        raise ValueError('Partial cleanup journal requires reconciliation: '+str(output))
    if (output/'result.json').exists():
        previous=load(output/'plan.json')
        if any((root/x['path']).exists() for x in previous['delete']):raise ValueError('Previously evicted file reappeared')
        return load(output/'result.json')
    opened=open_files() if opened is None else opened
    for x in plan['guards']+plan['delete']:
        p=inside(root,x['path'])
        if str(p) in opened:raise ValueError('Selected or guarded file is open: '+str(p))
        if signature(p)!=x['signature'] or digest(p)!=x['sha256']:raise ValueError('Preflight content/identity changed: '+str(p))
    inodes={}
    for x in plan['delete']:
        s=(root/x['path']).stat();v=inodes.setdefault((s.st_dev,s.st_ino),[s.st_blocks*512,s.st_nlink,0]);v[2]+=1
    save_new(output/'plan.json',plan)
    with (output/'journal.jsonl').open('x') as log:
        for x in plan['delete']:
            p=root/x['path']
            if signature(p)!=x['signature']:raise ValueError('Identity changed before unlink')
            p.unlink();log.write(json.dumps({'deleted':x['path'],'sha256':x['sha256']})+'\n');log.flush()
    for x in plan['guards']:
        if digest(root/x['path'])!=x['sha256']:raise ValueError('Guarded evidence changed')
    if any((root/x['path']).exists() for x in plan['delete']):raise ValueError('Eviction postcondition failed')
    result={'status':'verified','deletedFiles':len(plan['delete']),'allocatedBytesEligible':sum(b for b,n,c in inodes.values() if n==c),'boundary':'Whole-plan preflight, then journaled per-file deletion; not a multi-file transaction.'}
    save_new(output/'result.json',result);return result


def build_inventory(root):
    builds={};archives={}
    parent=root/'build/multilingual-delivery'
    if not parent.is_dir():return builds,archives
    for locale in parent.iterdir():
        if not locale.is_dir() or locale.name.startswith('tests-'):continue
        for p in locale.iterdir():
            if p.is_dir() and (p/'manifest.json').is_file() and (p/'ACCEPTANCE.json').is_file():
                m=load(p/'manifest.json');a=load(p/'ACCEPTANCE.json')
                if a.get('status')=='passed-technical-candidate' and a.get('manifestSha256')==digest(p/'manifest.json') and a.get('bindingsSha256')==digest(p/'bindings.json'):
                    builds[str(p.relative_to(root))]=m
            elif p.name.endswith('.zip.receipt.json'):
                z=p.with_name(p.name[:-len('.receipt.json')]);d=load(p)
                if z.exists() and d.get('archiveSha256') and d.get('buildManifestSha256'):
                    archives[str(z.relative_to(root))]=d
    return builds,archives


def build_plan(root,policy):
    builds,archives=build_inventory(root);keep_b=set();keep_a=set();guard_paths=set();known_b=policy['knownBuilds'];known_a=policy['knownArchives']
    by_manifest=collections.defaultdict(list);by_archive=collections.defaultdict(list)
    for n,m in builds.items():by_manifest[digest(root/n/'manifest.json')].append(n)
    for n,d in archives.items():by_archive[d['archiveSha256']].append(n)
    def pin(n):
        p=inside(root,n);n=str(p.relative_to(root))
        if not p.exists():raise ValueError('Missing protected dependency: '+n)
        if n in builds:keep_b.add(n)
        if n in archives:
            keep_a.add(n);keep_b.update(by_manifest[archives[n]['buildManifestSha256']])
        if p.name=='manifest.json' and str(p.parent.relative_to(root)) in builds:keep_b.add(str(p.parent.relative_to(root)))
    def catalog(n):
        p=inside(root,n);d=load(p/'catalog.json');receipt=load(p/'payload-receipt.json')
        if digest(p/'catalog.json')!=receipt['catalogSha256']:raise ValueError('Protected catalog changed')
        guard_paths.update([p/'catalog.json',p/'payload-receipt.json'])
        for locale in d['locales']:
            matches=by_archive[locale['archiveSha256']]
            if locale.get('code')!='ru' and not matches:raise ValueError('Protected locale archive unavailable')
            for z in matches:pin(z)
    for n in set(policy['workingCatalogs'].values())|set(policy.get('protectedCatalogs',[])):catalog(n)
    for name in policy.get('pendingPlans',[]):
        p=inside(root,name);guard_paths.add(p)
        for entry in load(p)['entries']:catalog(entry['catalog'])
    current=root/'runtime/cli-localization/current.json'
    if current.exists():
        state_path=Path(load(current)['run'])/'state.json';state=load(state_path)
        for locale in state['locales'].values():
            cp=locale.get('workflow',{}).get('machinePackageCheckpoint',{})
            for k in ('manifest','archive'):
                if k in cp:pin(cp[k]['path'])
    for name in policy.get('requiredBuilds',[]):pin(name)
    previous=None
    while previous!=(len(keep_b),len(keep_a)):
        previous=(len(keep_b),len(keep_a))
        for name in list(keep_b):
            d=builds[name].get('derivation',{})
            for key in ('parentBuild','parentArchive'):
                if key in d:pin(d[key])
    deletes=[];directories=[]
    for n,m in builds.items():
        if n not in known_b or n in keep_b:continue  # Unregistered new work is never disposable.
        base=root/n
        if digest(base/'manifest.json')!=known_b[n]:raise ValueError('Registered build changed: '+n)
        wanted={k:None for k in ['manifest.json','bindings.json','ACCEPTANCE.json','INCOMPLETE.json']}
        wanted.update({'files/'+r['path']:r['sha256'] for r in m['files']})
        actual={str(p.relative_to(base)):p for p in base.rglob('*') if p.is_file() or p.is_symlink()}
        if set(actual)!=set(wanted):raise ValueError('Unknown build files: '+n)
        deletes.extend(row(root,p,wanted[name]) for name,p in actual.items());directories.append(n)
    for n,d in archives.items():
        if n not in known_a or n in keep_a:continue
        if d['archiveSha256']!=known_a[n]:raise ValueError('Registered archive changed: '+n)
        deletes.extend([row(root,root/n,d['archiveSha256']),row(root,(root/n).with_name(Path(n).name+'.receipt.json'))])
    if not deletes:
        return {'kind':'obsolete-registered-builds','guards':[],'delete':[],'directories':[],'protectedBuilds':sorted(keep_b),'protectedArchives':sorted(keep_a),'evictedManifests':{}}
    for n in keep_a:
        archive=root/n
        if digest(archive)!=archives[n]['archiveSha256']:raise ValueError('Retained archive changed: '+n)
        guard_paths.update([archive,archive.with_name(archive.name+'.receipt.json')])
    for n in keep_b:
        base=root/n;guard_paths.update([base/'manifest.json',base/'ACCEPTANCE.json',base/'bindings.json'])
        for r in builds[n]['files']:guard_paths.add(base/'files'/r['path'])
    # Metadata retained in the plan makes eviction explicit without rewriting old receipts.
    return {'kind':'obsolete-registered-builds','guards':[row(root,p) for p in sorted(guard_paths)],'delete':deletes,'directories':directories,'protectedBuilds':sorted(keep_b),'protectedArchives':sorted(keep_a),'evictedManifests':{n:builds[n] for n in directories}}


def protected_catalogs(root,policy):
    keep=set(policy['workingCatalogs'].values())|set(policy.get('protectedCatalogs',[]))
    for name in policy.get('pendingPlans',[]):
        keep.update(str(inside(root,e['catalog']).relative_to(root)) for e in load(root/name)['entries'])
    todo=list(keep)
    while todo:
        n=todo.pop();p=inside(root,n);receipt=load(p/'payload-receipt.json')
        if digest(p/'catalog.json')!=receipt['catalogSha256']:raise ValueError('Catalog identity changed')
        if receipt.get('parentCatalog'):
            parent=inside(root,receipt['parentCatalog']);name=str(parent.relative_to(root))
            if digest(parent/'catalog.json')!=receipt['parentCatalogSha256']:raise ValueError('Catalog parent identity changed')
            if name not in keep:keep.add(name);todo.append(name)
    return keep


def catalog_plan(root,policy):
    keep=protected_catalogs(root,policy);deletes=[];guards=[];evicted=[]
    for name,expected in policy.get('knownCatalogs',{}).items():
        p=inside(root,name);catalog=p/'catalog.json'
        if not catalog.exists():continue
        if digest(catalog)!=expected or load(p/'payload-receipt.json')['catalogSha256']!=expected:raise ValueError('Registered catalog changed: '+name)
        if name in keep:continue
        d=load(catalog);objects=p/'objects'
        if not objects.is_dir():continue
        actual={x.name for x in objects.iterdir()}
        # An already evicted cache is harmless; a partially missing cache is not
        # silently retried or reported as verified continuation.
        if not actual:continue
        if (p/'STORAGE_EVICTED.json').exists():raise ValueError('Evicted catalog cache was regenerated in place: '+name)
        if actual!=set(d['objects']):raise ValueError('Unknown or partially missing catalog objects: '+name)
        guards.extend([row(root,catalog,expected),row(root,p/'payload-receipt.json')])
        deletes.extend(row(root,objects/k,m['sha256']) for k,m in d['objects'].items());evicted.append(name)
    return {'kind':'obsolete-registered-catalog-caches','delete':deletes,'guards':guards,'evictedCatalogCaches':evicted}


def mark_catalogs_evicted(root,plan,output):
    for name in plan.get('evictedCatalogCaches',[]):
        base=inside(root,name)
        if any((base/'objects').iterdir()):raise ValueError('Catalog eviction postcondition changed')
        marker=base/'STORAGE_EVICTED.json'
        if marker.exists():
            if load(marker).get('status')!='generated-catalog-objects-evicted':raise ValueError('Unknown eviction marker')
            continue
        save_new(marker,{'status':'generated-catalog-objects-evicted','objectsAvailable':False,'historicalCatalogPreserved':True,'receipt':str(output.relative_to(root)),'recovery':'Use the registered working catalogs or prepare a fresh output revision; never treat this historical catalog as an available object store.'})


def share_plan(root,policy):
    """Share immutable registered native outputs; public ZIP writer uses exclusive create."""
    builds,archives=build_inventory(root);groups=collections.defaultdict(list);guards=[]
    for n,expected in policy['knownBuilds'].items():
        if n not in builds:continue
        base=root/n
        if digest(base/'manifest.json')!=expected:raise ValueError('Registered build changed: '+n)
        guards.append(row(root,base/'manifest.json',expected))
        for r in builds[n]['files']:
            p=base/'files'/r['path'];sig=signature(p)
            groups[(r['sha256'],sig[2],*sig[4:])].append((p,sig))
    for n,expected in policy['knownArchives'].items():
        p=root/n
        if p.exists():
            sig=signature(p);groups[(expected,sig[2],*sig[4:])].append((p,sig))
    for name in protected_catalogs(root,policy):
        base=inside(root,name);d=load(base/'catalog.json');guards.extend([row(root,base/'catalog.json'),row(root,base/'payload-receipt.json')])
        for key,metadata in d.get('objects',{}).items():
            p=base/'objects'/key;sig=signature(p)
            groups[(metadata['sha256'],sig[2],*sig[4:])].append((p,sig))
    current=root/'runtime/cli-localization/current.json'
    if current.exists():
        state=load(Path(load(current)['run'])/'state.json')
        for locale in state['locales'].values():
            cp=locale.get('workflow',{}).get('machinePackageCheckpoint',{})
            if cp.get('deliveredArchive') and cp.get('archive'):
                p=inside(root,cp['deliveredArchive']);sig=signature(p)
                groups[(cp['archive']['sha256'],sig[2],*sig[4:])].append((p,sig))
    selected=[];hashed={}
    for (h,*_),rows in groups.items():
        # Path duplicates are metadata aliases, never two deletion selections.
        rows=list({str(p):(p,sig) for p,sig in rows}.values())
        if len({tuple(sig[:2]) for p,sig in rows})<2:continue
        keeper,ks=min(rows,key=lambda r:(-r[0].stat().st_nlink,str(r[0])))
        for p,sig in rows:
            if sig[:2]==ks[:2]:continue
            for f,fs in [(p,sig),(keeper,ks)]:
                key=tuple(fs[:2])
                if key not in hashed:
                    if digest(f)!=h or signature(f)!=fs:raise ValueError('Immutable duplicate changed: '+str(f))
                    hashed[key]=h
            selected.append({'path':str(p.relative_to(root)),'signature':sig,'keeper':str(keeper.relative_to(root)),'keeperSignature':ks,'sha256':h})
    return {'kind':'share-immutable-registered-artifacts','links':selected,'guards':guards}


def apply_shared(root,plan,output,opened=None):
    output=inside(root,output);output.mkdir(parents=True,exist_ok=True);control=root/'runtime/storage-retention';control.mkdir(parents=True,exist_ok=True);pending=control/'pending-share.json'
    if pending.exists():raise ValueError('Partial sharing journal requires reconciliation: '+str(pending))
    opened=open_files() if opened is None else opened;checked=set();inodes={}
    for x in plan['guards']:
        if signature(root/x['path'])!=x['signature'] or digest(root/x['path'])!=x['sha256']:raise ValueError('Sharing metadata changed')
    for x in plan['links']:
        for name,sig in [(x['path'],x['signature']),(x['keeper'],x['keeperSignature'])]:
            p=inside(root,name)
            if str(p) in opened:raise ValueError('Sharing input is open: '+name)
            if signature(p)!=sig:raise ValueError('Sharing identity changed: '+name)
            key=tuple(sig[:2])
            if key not in checked:
                if digest(p)!=x['sha256']:raise ValueError('Sharing content changed: '+name)
                checked.add(key)
        st=(root/x['path']).stat();v=inodes.setdefault((st.st_dev,st.st_ino),[st.st_blocks*512,st.st_nlink,0]);v[2]+=1
    save_new(output/'plan.json',plan);save_new(pending,{'plan':str((output/'plan.json').relative_to(root))})
    with (output/'journal.jsonl').open('x') as log:
        for x in plan['links']:
            p=root/x['path'];keeper=root/x['keeper'];sig=x['signature'];ks=x['keeperSignature']
            if signature(p)!=sig or signature(keeper)!=ks or digest(p)!=x['sha256'] or digest(keeper)!=x['sha256']:raise ValueError('Sharing inputs changed before publication')
            temp=p.with_name('.storage-share-'+uuid.uuid4().hex)
            try:
                os.link(keeper,temp)
                if signature(p)!=sig or signature(keeper)!=ks:raise ValueError('Sharing identity changed during publication')
                os.replace(temp,p)
            finally:
                if temp.exists():temp.unlink()
            if p.stat().st_ino!=keeper.stat().st_ino or digest(p)!=x['sha256']:raise ValueError('Sharing postcondition failed')
            log.write(json.dumps({'linked':x['path'],'keeper':x['keeper'],'sha256':x['sha256']})+'\n');log.flush()
    result={'status':'verified','linkedFiles':len(plan['links']),'allocatedBytesEligible':sum(b for b,n,c in inodes.values() if n==c),'boundary':'Per-file atomic hardlink replacement, not a multi-file transaction. All registered output paths and bytes survive.'}
    save_new(output/'result.json',result);pending.unlink();return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True)
    sub=ap.add_subparsers(dest='command',required=True)
    archive=sub.add_parser('close-archive');archive.add_argument('--run',type=Path,required=True)
    prune=sub.add_parser('prune-builds');prune.add_argument('--policy',type=Path,required=True)
    catalog=sub.add_parser('prune-catalogs');catalog.add_argument('--policy',type=Path,required=True)
    share=sub.add_parser('share-artifacts');share.add_argument('--policy',type=Path,required=True)
    args=ap.parse_args();root=args.root.resolve();control=root/'runtime/storage-retention';control.mkdir(exist_ok=True)
    with (control/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.command=='close-archive':
            run=inside(root,args.run);output=run/'storage-eviction'
            if (output/'result.json').exists():
                print(json.dumps(apply(root,{},output)));return
            plan=archive_plan(root,run);result=apply(root,plan,output)
        elif args.command=='prune-catalogs':
            plan=catalog_plan(root,load(args.policy));output=control/('catalog-prune-'+str(time.time_ns()));result=apply(root,plan,output);mark_catalogs_evicted(root,plan,output)
        elif args.command=='share-artifacts':
            plan=share_plan(root,load(args.policy));result=apply_shared(root,plan,control/('share-'+str(time.time_ns())))
        else:
            policy=load(args.policy);plan=build_plan(root,policy)
            output=control/('prune-'+str(time.time_ns()));result=apply(root,plan,output)
            for n in plan['directories']:
                base=root/n
                for folder,ds,fs in os.walk(base,topdown=False):
                    if fs:raise ValueError('Unexpected file after pruning')
                    Path(folder).rmdir()
        print(json.dumps(result))


if __name__=='__main__':main()
