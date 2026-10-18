"""Canonical QA series entry with frozen, route-independent generated-file retention.

A watch-only attachment never launches/restarts/stops the existing game or queue.
All automatic deletion uses storage_retention's restoration and identity guards.
"""
import contextlib
import argparse, fcntl, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
import storage_retention as storage


@contextlib.contextmanager
def storage_lock(control):
    with (control/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield


def register_plan(root,policy,plan):
    name=str(plan.relative_to(root))
    if name not in policy['pendingPlans']:policy['pendingPlans'].append(name)
    inventory=storage.build_plan(root,policy)
    for n in inventory['protectedBuilds']:policy['knownBuilds'][n]=storage.digest(root/n/'manifest.json')
    for n in inventory['protectedArchives']:policy['knownArchives'][n]=storage.digest(root/n)
    for n in storage.protected_catalogs(root,policy):policy.setdefault('knownCatalogs',{})[n]=storage.digest(root/n/'catalog.json')
    return policy


def prune(root,policy,control):
    plan=storage.build_plan(root,policy)
    if not plan['delete']:return {'status':'unchanged','deletedFiles':0}
    output=control/('build-prune-'+str(time.time_ns()))
    result=storage.apply(root,plan,output)
    for n in plan['directories']:
        for folder,ds,fs in os.walk(root/n,topdown=False):
            if fs:raise ValueError('New file appeared in a retired build')
            Path(folder).rmdir()
    return result


def collect(root,plan,control):
    active=plan.with_name('active.json');active_run=storage.load(active).get('run') if active.exists() else None
    results=[]
    for entry in storage.load(plan)['entries']:
        run=storage.inside(root,entry['run'])
        if str(run)==active_run or not (run/'russian-level-restoration.json').exists():continue
        output=run/'storage-eviction'
        if (output/'result.json').exists():continue
        cache=storage.archive_plan(root,run)
        results.append(storage.apply(root,cache,output))
    return results


def finish_plan(root,policy_path,plan,control):
    data=storage.load(plan);complete=storage.load(plan.with_name('complete.json'))
    if complete.get('status')!='complete' or set(complete['locales'])!={e['locale'] for e in data['entries']}:
        raise ValueError('Series completion set mismatch')
    with storage_lock(control):
        policy=storage.load(policy_path)
        for entry in data['entries']:
            storage.closed(root,Path(entry['run']))
            policy['workingCatalogs'][entry['locale']]=str(Path(entry['catalog']).relative_to(root))
        policy['pendingPlans']=[n for n in policy['pendingPlans'] if n!=str(plan.relative_to(root))]
        storage.atomic_save(policy_path,policy)
        result=prune(root,policy,control)
        catalogs=storage.catalog_plan(root,policy)
        if catalogs['delete']:
            output=control/('catalog-prune-'+str(time.time_ns()));result['catalogCaches']=storage.apply(root,catalogs,output);storage.mark_catalogs_evicted(root,catalogs,output)
        shared=storage.share_plan(root,policy)
        if shared['links']:
            result['sharing']=storage.apply_shared(root,shared,control/('share-'+str(time.time_ns())))
        return result


def process_identity(pid):
    r=subprocess.run(['ps','-p',str(pid),'-o','lstart=,command='],capture_output=True,text=True,timeout=10)
    if r.returncode==1 and not r.stdout.strip():return None
    if r.returncode or not r.stdout.strip():raise RuntimeError('Process identity unavailable')
    return r.stdout.strip()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--policy',type=Path,required=True)
    ap.add_argument('--route',choices=['mari','equipment','wave','shop'],required=True);ap.add_argument('--watch-pid',type=int);ap.add_argument('--frozen',action='store_true');ap.add_argument('plan',type=Path)
    a=ap.parse_args();root=a.root.resolve();plan=storage.inside(root,a.plan);policy_path=storage.inside(root,a.policy)
    control=root/'runtime/storage-retention';control.mkdir(parents=True,exist_ok=True)
    if not a.frozen:
        snapshot=control/('controller-'+str(time.time_ns()));snapshot.mkdir()
        sources={}
        for source in [Path(__file__).resolve(),Path(storage.__file__).resolve()]:
            target=snapshot/source.name;shutil.copy2(source,target)
            if storage.digest(source)!=storage.digest(target):raise ValueError('Controller changed during snapshot')
            sources[source.name]=storage.digest(target)
        storage.save_new(snapshot/'sources.json',sources)
        args=[sys.executable,'-B',str(snapshot/Path(__file__).name),'--root',str(root),'--policy',str(policy_path),'--route',a.route,'--frozen']
        if a.watch_pid:args+=['--watch-pid',str(a.watch_pid)]
        os.execv(sys.executable,args+[str(plan)])
    lock_path=control/('series-'+hashlib.sha256(str(plan).encode()).hexdigest()+'.lock')
    with lock_path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=storage.load(plan)
        if data.get('route',a.route)!=a.route:raise ValueError('Wrong route for plan')
        for n,h in data['driverInputs'].items():
            if storage.digest(root/n)!=h:raise ValueError('Series input changed: '+n)
        with storage_lock(control):
            policy=register_plan(root,storage.load(policy_path),plan);storage.atomic_save(policy_path,policy)
        child=None;identity=None
        if a.watch_pid:
            identity=process_identity(a.watch_pid)
            if identity is None or 'mari-series.py' not in identity or str(plan.relative_to(root)) not in identity and str(plan) not in identity:
                raise ValueError('The requested existing coordinator identity does not match the plan')
        else:
            if plan.with_name('active.json').exists() or plan.with_name('complete.json').exists():raise ValueError('Reconcile existing series; never resubmit')
            child=subprocess.Popen([sys.executable,'-B',str(root/'tools/visual-qa/mari-series.py'),str(plan),'--route',a.route],cwd=root)
        state_path=Path(__file__).with_name('status.json')
        while True:
            with storage_lock(control):results=collect(root,plan,control)
            alive=child.poll() is None if child is not None else process_identity(a.watch_pid)==identity
            storage.atomic_save(state_path,{'status':'watching' if alive else 'coordinator-exited','plan':str(plan),'coordinatorPid':child.pid if child else a.watch_pid,'watchOnly':a.watch_pid is not None,'lastEvictions':results,'at':time.time()})
            if not alive:break
            time.sleep(5)
        # A coordinator exit is not proof of child exit. collect() requires actual
        # stopped/restored receipts; pending plans remain protected on every failure.
        with storage_lock(control):results=collect(root,plan,control)
        if (child is not None and child.returncode!=0) or not plan.with_name('complete.json').exists():
            storage.atomic_save(state_path,{'status':'needs-attention','plan':str(plan),'reason':'Series not complete; all pending inputs retained.'});return
        complete=storage.load(plan.with_name('complete.json'))
        if complete.get('status')!='complete' or set(complete['locales'])!={e['locale'] for e in data['entries']}:raise ValueError('Series completion set mismatch')
        result=finish_plan(root,policy_path,plan,control)
        storage.atomic_save(state_path,{'status':'complete','plan':str(plan),'buildPruning':result,'watchOnly':a.watch_pid is not None})


if __name__=='__main__':main()
