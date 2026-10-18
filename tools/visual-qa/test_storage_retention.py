"""Real file-system checks for generated-artifact eviction boundaries."""
import gzip, hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import storage_retention as s


def h(b):return hashlib.sha256(b).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))


class StorageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
 def archive(self):
  r=self.root/'runtime/visual-qa/example/run-en';r.mkdir(parents=True);meta=r/'installer-metadata-final'
  write(r/'restoration.json',{'status':'verified'});write(r/'russian-level-restoration.json',{'levelRepairRestored':True});write(r/'owned-game.json',{'directory':str(r/'en')});write(r/'en/stopped.json',{'stopped':True})
  raw=b'known original resource';packed=gzip.compress(raw,mtime=0);key=h(raw)
  catalog={'locales':[{'files':{'data/example':{'sha256':key}}}],'objects':{key:{'bytes':len(packed),'sha256':h(packed),'unpackedBytes':len(raw)}}}
  data=json.dumps(catalog).encode();folder=meta/'packages'/h(data);folder.mkdir(parents=True);(folder/'catalog.json').write_bytes(data);(folder/'objects').mkdir();(folder/'objects'/key).write_bytes(packed)
  (meta/'backups').mkdir();(meta/'backups'/key).write_bytes(raw);(meta/'backups'/'unknown').write_bytes(b'unclassified')
  write(meta/'state.json',{'owned':{'data/example':key},'originals':{}})
  return r,key
 def test_closed_positive_first_postcondition_and_repeat(self):
  run,key=self.archive();plan=s.archive_plan(self.root,run);self.assertEqual(len(plan['delete']),2)
  out=run/'storage-eviction';result=s.apply(self.root,plan,out,opened=set());self.assertEqual(result['deletedFiles'],2)
  self.assertTrue(all(not (self.root/x['path']).exists() for x in plan['delete']))
  self.assertTrue((run/'installer-metadata-final/backups/unknown').exists());self.assertTrue(all((self.root/x['path']).exists() for x in plan['guards']))
  self.assertEqual(s.apply(self.root,{},out,opened=set()),result)
 def test_open_file_rejects_whole_selection(self):
  run,key=self.archive();plan=s.archive_plan(self.root,run)
  with self.assertRaisesRegex(ValueError,'is open'):s.apply(self.root,plan,run/'eviction',opened={str(self.root/plan['delete'][-1]['path'])})
  self.assertTrue(all((self.root/x['path']).exists() for x in plan['delete']))
 def test_changed_target_rejects_before_first_write(self):
  run,key=self.archive();plan=s.archive_plan(self.root,run);(self.root/plan['delete'][-1]['path']).write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'Preflight content/identity changed'):s.apply(self.root,plan,run/'eviction',opened=set())
  self.assertTrue(all((self.root/x['path']).exists() for x in plan['delete']))
 def test_unrestored_and_active_reject_at_their_own_guards(self):
  run,key=self.archive();write(run/'restoration.json',{'status':'unknown'})
  with self.assertRaisesRegex(ValueError,'not restored and stopped'):s.archive_plan(self.root,run)
  write(run/'restoration.json',{'status':'verified'});write(run.parent/'series-01/active.json',{'run':str(run)})
  with self.assertRaisesRegex(ValueError,'still active'):s.archive_plan(self.root,run)
 def test_failure_between_unlinks_is_explicit_partial_journal(self):
  run,key=self.archive();plan=s.archive_plan(self.root,run);original=Path.unlink;calls=[]
  def unlink(p,*a,**kw):
   calls.append(p)
   if len(calls)==2:raise OSError('injected second-unlink failure')
   return original(p,*a,**kw)
  out=run/'eviction'
  with patch.object(Path,'unlink',unlink):
   with self.assertRaisesRegex(OSError,'injected second'):s.apply(self.root,plan,out,opened=set())
  self.assertFalse((self.root/plan['delete'][0]['path']).exists());self.assertTrue((self.root/plan['delete'][1]['path']).exists())
  with self.assertRaisesRegex(ValueError,'Partial cleanup journal'):s.apply(self.root,plan,out,opened=set())
 def build(self,name,derivation=None):
  base=self.root/'build/multilingual-delivery/en'/name;blob=base/'files/data/test.KEL';blob.parent.mkdir(parents=True);blob.write_bytes(name.encode())
  write(base/'bindings.json',{});manifest={'files':[{'path':'data/test.KEL','sha256':s.digest(blob)}]}
  if derivation:manifest['derivation']=derivation
  write(base/'manifest.json',manifest);write(base/'INCOMPLETE.json',{});write(base/'ACCEPTANCE.json',{'status':'passed-technical-candidate','manifestSha256':s.digest(base/'manifest.json'),'bindingsSha256':s.digest(base/'bindings.json')})
  archive=base.parent/(name+'.zip');archive.write_bytes(name.encode());write(archive.with_name(archive.name+'.receipt.json'),{'archiveSha256':s.digest(archive),'buildManifestSha256':s.digest(base/'manifest.json')})
  return str(base.relative_to(self.root)),str(archive.relative_to(self.root))
 def catalog(self,name,archive):
  p=self.root/'build/installer'/name;write(p/'catalog.json',{'locales':[{'archiveSha256':s.digest(self.root/archive)}]});write(p/'payload-receipt.json',{'catalogSha256':s.digest(p/'catalog.json')});return str(p.relative_to(self.root))
 def test_registered_obsolete_only_and_derivative_parent_closure(self):
  old,oz=self.build('old');current,cz=self.build('current');unknown,uz=self.build('unregistered');cat=self.catalog('current',cz)
  policy={'knownBuilds':{old:s.digest(self.root/old/'manifest.json'),current:s.digest(self.root/current/'manifest.json')},'knownArchives':{oz:s.digest(self.root/oz),cz:s.digest(self.root/cz)},'workingCatalogs':{'en':cat}}
  plan=s.build_plan(self.root,policy);self.assertIn(old,plan['directories']);self.assertNotIn(current,plan['directories']);self.assertNotIn(unknown,plan['directories'])
  m=s.load(self.root/current/'manifest.json');m['derivation']={'parentBuild':old,'parentArchive':oz};write(self.root/current/'manifest.json',m);a=s.load(self.root/current/'ACCEPTANCE.json');a['manifestSha256']=s.digest(self.root/current/'manifest.json');write(self.root/current/'ACCEPTANCE.json',a)
  # The archive is the same fixture, with its manifest binding refreshed.
  receipt=self.root/cz;write(receipt.with_name(receipt.name+'.receipt.json'),{'archiveSha256':s.digest(receipt),'buildManifestSha256':s.digest(self.root/current/'manifest.json')})
  policy['knownBuilds'][current]=s.digest(self.root/current/'manifest.json');plan=s.build_plan(self.root,policy);self.assertNotIn(old,plan['directories'])

 def test_frozen_keeper_is_preserved(self):
  run,key=self.archive();backup=run/'installer-metadata-final/backups'/key
  write(self.root/'diagnostics/cleanup-20261018-01/plan.json',{'links':[{'keeper':{'path':str(backup.relative_to(self.root))}}]})
  plan=s.archive_plan(self.root,run);self.assertEqual(len(plan['delete']),1)
  s.apply(self.root,plan,run/'eviction',opened=set());self.assertTrue(backup.exists())
 def test_corrupt_gzip_rejects_before_any_deletion(self):
  run,key=self.archive();package=next((run/'installer-metadata-final/packages').iterdir());(package/'objects'/key).write_bytes(gzip.compress(b'other resource',mtime=0))
  with self.assertRaisesRegex(ValueError,'compressed object changed'):s.archive_plan(self.root,run)
  self.assertTrue((run/'installer-metadata-final/backups'/key).exists())
 def test_all_four_routes_use_real_archive_eviction(self):
  import retained_series
  for route in ['mari','equipment','wave','shop']:
   with self.subTest(route=route):
    run,key=self.archive();plan=run.parent/('series-'+route+'/plan.json');write(plan,{'route':route,'entries':[{'run':str(run)}]})
    # Only OS open-file inventory is replaced; restoration, hashes, gzip and unlink are real.
    with patch.object(s,'open_files',return_value=set()):results=retained_series.collect(self.root,plan,self.root/'control')
    self.assertEqual(results[0]['deletedFiles'],2);self.assertFalse((run/'installer-metadata-final/backups'/key).exists())
    import shutil
    shutil.rmtree(run)

 def test_actual_series_entry_cleans_every_route_without_game_launch(self):
  import os, shutil, subprocess, sys, textwrap
  canonical=Path(__file__).resolve().parent
  fake_worker=textwrap.dedent("""\
  import argparse,gzip,hashlib,json
  from pathlib import Path
  p=argparse.ArgumentParser();p.add_argument('--run',type=Path);p.add_argument('--catalog',type=Path);p.add_argument('--route');p.add_argument('locale');a=p.parse_args()
  def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
  catalog=(a.catalog/'catalog.json').read_bytes();data=json.loads(catalog);key=next(iter(data['objects']));blob=(a.catalog/'objects'/key).read_bytes();raw=gzip.decompress(blob)
  meta=a.run/'installer-metadata-final';folder=meta/'packages'/hashlib.sha256(catalog).hexdigest();(folder/'objects').mkdir(parents=True);(folder/'catalog.json').write_bytes(catalog);(folder/'objects'/key).write_bytes(blob)
  (meta/'backups').mkdir();(meta/'backups'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
  put(meta/'state.json',{'owned':{'data/test':hashlib.sha256(raw).hexdigest()},'originals':{}})
  put(a.run/'owned-game.json',{'directory':str(a.run/a.locale)});put(a.run/a.locale/'stopped.json',{'stopped':True})
  put(a.run/'restoration.json',{'status':'verified'});put(a.run/'russian-level-restoration.json',{'levelRepairRestored':True})
  put(a.run/'worker-ran.json',{'route':a.route})
  """)
  old_root=self.root
  for route in ['mari','equipment','wave','shop']:
   with self.subTest(route=route):
    self.root=old_root/route;self.root.mkdir();tools=self.root/'tools/visual-qa';tools.mkdir(parents=True)
    for name in ['mari-series.py','storage_retention.py','retained_series.py']:shutil.copy2(canonical/name,tools/name)
    (tools/'mari-session.py').write_text(fake_worker)
    build,archive=self.build('current');cat=self.catalog('current',archive);catalog=self.root/cat;data=s.load(catalog/'catalog.json');raw=b'fixture generated resource';key=h(raw);packed=gzip.compress(raw,mtime=0)
    data['locales'][0].update(code='en',files={'data/test':{'sha256':key}});data['objects']={key:{'bytes':len(packed),'sha256':h(packed),'unpackedBytes':len(raw)}}
    write(catalog/'catalog.json',data);write(catalog/'payload-receipt.json',{'catalogSha256':s.digest(catalog/'catalog.json')});(catalog/'objects').mkdir();(catalog/'objects'/key).write_bytes(packed)
    control=self.root/'runtime/storage-retention';control.mkdir(parents=True);write(control/'policy.json',{'knownBuilds':{},'knownArchives':{},'workingCatalogs':{'en':cat},'pendingPlans':[]})
    run=self.root/'runtime/visual-qa/test/series-01/run-en';run.mkdir(parents=True);plan=run.parent/'plan.json';names=['mari-series.py','storage_retention.py','retained_series.py','mari-session.py']
    write(plan,{'status':'ready','route':route,'entries':[{'locale':'en','run':str(run),'catalog':str(catalog),'catalogSha256':s.digest(catalog/'catalog.json')}],'driverInputs':{'tools/visual-qa/'+n:s.digest(tools/n) for n in names}})
    bins=self.root/'test-bin';bins.mkdir();(bins/'lsof').write_text('#!/bin/sh\nexit 0\n');(bins/'lsof').chmod(0o755)
    result=subprocess.run([sys.executable,'-B',str(tools/'mari-series.py'),str(plan),'--route',route],capture_output=True,text=True,env=dict(os.environ,PATH=str(bins)+os.pathsep+os.environ['PATH']),timeout=20)
    self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertTrue(plan.with_name('complete.json').exists());self.assertEqual(s.load(run/'worker-ran.json')['route'],route)
    self.assertEqual(s.load(run/'storage-eviction/result.json')['deletedFiles'],2);self.assertFalse(any((run/'installer-metadata-final/backups').iterdir()));self.assertEqual(s.load(control/'policy.json')['pendingPlans'],[])
  self.root=old_root

 def shared_fixture(self,count=2):
  policy={'knownBuilds':{},'knownArchives':{},'workingCatalogs':{}}
  for i in range(count):
   name,archive=self.build('version-'+str(i));base=self.root/name;payload=base/'files/data/test.KEL';payload.write_bytes(b'SHARED-DATA')
   m=s.load(base/'manifest.json');m['files'][0]['sha256']=s.digest(payload);write(base/'manifest.json',m);a=s.load(base/'ACCEPTANCE.json');a['manifestSha256']=s.digest(base/'manifest.json');write(base/'ACCEPTANCE.json',a)
   policy['knownBuilds'][name]=s.digest(base/'manifest.json')
  return policy
 def test_shared_immutable_first_postcondition_and_repeat(self):
  policy=self.shared_fixture();plan=s.share_plan(self.root,policy);self.assertEqual(len(plan['links']),1)
  result=s.apply_shared(self.root,plan,self.root/'diagnostics/share',opened=set());self.assertEqual(result['linkedFiles'],1)
  x=plan['links'][0];self.assertEqual((self.root/x['path']).stat().st_ino,(self.root/x['keeper']).stat().st_ino);self.assertEqual((self.root/x['path']).read_bytes(),b'SHARED-DATA')
  self.assertEqual(s.share_plan(self.root,policy)['links'],[])
  fresh=self.root/'build/new-version/payload';fresh.parent.mkdir();fresh.write_bytes(b'NEW VERSION');self.assertEqual((self.root/x['path']).read_bytes(),b'SHARED-DATA')
 def test_shared_content_rejection_with_same_identity_metadata(self):
  import os
  policy=self.shared_fixture();plan=s.share_plan(self.root,policy);x=plan['links'][0];p=self.root/x['path'];p.write_bytes(b'BROKEN-DATA');os.utime(p,ns=(p.stat().st_atime_ns,x['signature'][3]))
  self.assertEqual(s.signature(p),x['signature'])
  with self.assertRaisesRegex(ValueError,'Sharing content changed'):s.apply_shared(self.root,plan,self.root/'diagnostics/share',opened=set())
  self.assertFalse((self.root/'runtime/storage-retention/pending-share.json').exists())
 def test_shared_partial_publication_preserves_bytes_and_blocks_retry(self):
  import os
  policy=self.shared_fixture(3);plan=s.share_plan(self.root,policy);original=os.replace;calls=[]
  def replace(a,b):
   calls.append((a,b))
   if len(calls)==2:raise OSError('injected second publication failure')
   return original(a,b)
  with patch.object(s.os,'replace',replace):
   with self.assertRaisesRegex(OSError,'second publication'):s.apply_shared(self.root,plan,self.root/'diagnostics/share',opened=set())
  self.assertTrue(all((self.root/x['path']).read_bytes()==b'SHARED-DATA' for x in plan['links']))
  self.assertTrue((self.root/'runtime/storage-retention/pending-share.json').exists())
  with self.assertRaisesRegex(ValueError,'Partial sharing journal'):s.apply_shared(self.root,plan,self.root/'diagnostics/share-again',opened=set())

 def catalog_cache_fixture(self,name):
  base=self.root/'build/installer'/name;raw=b'PACKED-FIXTURE';key=h(raw);packed=gzip.compress(raw,mtime=0)
  write(base/'catalog.json',{'locales':[],'objects':{key:{'sha256':h(packed),'bytes':len(packed),'unpackedBytes':len(raw)}}})
  write(base/'payload-receipt.json',{'catalogSha256':s.digest(base/'catalog.json')});(base/'objects').mkdir();(base/'objects'/key).write_bytes(packed)
  return str(base.relative_to(self.root)),key
 def test_catalog_cache_pruning_preserves_current_and_unknown(self):
  current,key=self.catalog_cache_fixture('current');old,_=self.catalog_cache_fixture('old');unknown,_=self.catalog_cache_fixture('unregistered')
  policy={'workingCatalogs':{'en':current},'knownCatalogs':{n:s.digest(self.root/n/'catalog.json') for n in [current,old]}}
  plan=s.catalog_plan(self.root,policy);self.assertEqual(len(plan['delete']),1);self.assertTrue(plan['delete'][0]['path'].startswith(old+'/'))
  s.apply(self.root,plan,self.root/'diagnostics/catalog-prune',opened=set());s.mark_catalogs_evicted(self.root,plan,self.root/'diagnostics/catalog-prune');self.assertFalse((self.root/old/'objects'/key).exists());self.assertTrue((self.root/current/'objects'/key).exists());self.assertTrue((self.root/unknown/'objects'/key).exists());self.assertTrue((self.root/old/'catalog.json').exists())
  self.assertEqual(s.catalog_plan(self.root,policy)['delete'],[])
 def test_catalog_parent_and_pending_plan_are_protected(self):
  current,key=self.catalog_cache_fixture('current');old,_=self.catalog_cache_fixture('parent');pending,_=self.catalog_cache_fixture('pending')
  receipt=s.load(self.root/current/'payload-receipt.json');receipt.update(parentCatalog=str(self.root/old),parentCatalogSha256=s.digest(self.root/old/'catalog.json'));write(self.root/current/'payload-receipt.json',receipt)
  write(self.root/'runtime/visual-qa/test/series-01/plan.json',{'entries':[{'catalog':str(self.root/pending)}]})
  policy={'workingCatalogs':{'en':current},'pendingPlans':['runtime/visual-qa/test/series-01/plan.json'],'knownCatalogs':{n:s.digest(self.root/n/'catalog.json') for n in [current,old,pending]}}
  self.assertEqual(s.catalog_plan(self.root,policy)['delete'],[])


if __name__=='__main__':unittest.main()
