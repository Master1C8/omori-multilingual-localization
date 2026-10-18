"""Hash/ZIP checkpoint regressions; no model, compiler or game execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import native_checkpoint as cp

class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.build=self.root/'build/multilingual-delivery/de/native';self.plain='runtime/multilingual/locales/de/plain'
        self.put('source/multilingual/shared-8879120-03/units.json',[])
        self.put('source/input.json',{'source':'unchanged'})
        self.put('source/multilingual/shared-8879120-03/verification.json',{'files':{},'inputHashes':{'source/input.json':cp.digest(self.root/'source/input.json')}})
        self.put('translation/de/batches/one.json',{'authored':'fixture'})
        self.put(self.plain+'/receipt.json',{'files':[]});self.put(self.plain+'/display-mappings.json',{})
        self.build.mkdir(parents=True);(self.build/'files').mkdir();(self.build/'files/test.dat').write_bytes(b'verified compiled fixture')
        self.put(str((self.build/'bindings.json').relative_to(self.root)),{})
        self.put(str((self.build/'INCOMPLETE.json').relative_to(self.root)),{'historical':'acceptance written last'})
        manifest={'siteLocale':'de','files':[{'path':'test.dat','sha256':cp.digest(self.build/'files/test.dat')}],
            'displayMappings':1,'authoredEntries':3,'bindingsSha256':cp.digest(self.build/'bindings.json'),'recipeDependencies':{},
            'inputs':{'plaintext':self.plain,'plaintextReceiptSha256':cp.digest(self.root/self.plain/'receipt.json'),
                'mappingSha256':cp.digest(self.root/self.plain/'display-mappings.json'),
                'inventorySha256':cp.digest(self.root/'source/multilingual/shared-8879120-03/units.json'),
                'sourceVerificationSha256':cp.digest(self.root/'source/multilingual/shared-8879120-03/verification.json'),
                'authorFiles':{'translation/de/batches/one.json':cp.digest(self.root/'translation/de/batches/one.json')}}}
        self.put(str((self.build/'manifest.json').relative_to(self.root)),manifest)
        self.put(str((self.build/'ACCEPTANCE.json').relative_to(self.root)),{'siteLocale':'de','status':'passed-technical-candidate','manifestSha256':cp.digest(self.build/'manifest.json'),'bindingsSha256':cp.digest(self.build/'bindings.json')})
        self.output=self.build.parent/'mod.zip'
    def put(self,path,obj):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj))
    def test_one_zip_readback_then_reuse_no_recompilation(self):
        result=cp.package_once(self.root,'de',self.build,self.output)
        self.assertEqual(result['status'],cp.STATUS);before=self.output.read_bytes()
        with patch.object(cp,'archive_readback',side_effect=AssertionError('unchanged ZIP reread')):
            reused=cp.package_once(self.root,'de',self.build,self.output)
        self.assertEqual(reused['verificationMode'],'reuse-native-checkpoint-with-current-input-and-byte-hashes')
        self.assertEqual(self.output.read_bytes(),before)
    def test_interrupted_zip_creation_resumes_actual_existing_bytes(self):
        with patch.object(cp,'archive_readback',side_effect=InterruptedError('after ZIP write')):
            with self.assertRaises(InterruptedError):cp.package_once(self.root,'de',self.build,self.output)
        before=self.output.read_bytes();self.assertFalse(self.output.with_name('mod.zip.receipt.json').exists())
        cp.package_once(self.root,'de',self.build,self.output);self.assertEqual(self.output.read_bytes(),before)
    def test_changed_author_native_source_and_added_batch_reject(self):
        for target in ['translation/de/batches/one.json','source/input.json',str((self.build/'files/test.dat').relative_to(self.root))]:
            p=self.root/target;old=p.read_bytes();p.write_bytes(old+b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):cp.build_checkpoint(self.root,'de',self.build)
            p.write_bytes(old)
        self.put('translation/de/batches/extra.json',{})
        with self.assertRaisesRegex(ValueError,'file set changed'):cp.build_checkpoint(self.root,'de',self.build)
    def test_changed_zip_and_receipt_are_not_reused(self):
        cp.package_once(self.root,'de',self.build,self.output);self.output.write_bytes(self.output.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'ZIP checkpoint'):cp.package_once(self.root,'de',self.build,self.output)
    def test_missing_build_acceptance_cannot_grant_package(self):
        (self.build/'ACCEPTANCE.json').unlink()
        with self.assertRaises(FileNotFoundError):cp.package_once(self.root,'de',self.build,self.output)
        self.assertFalse(self.output.exists())
    def test_queue_packages_and_delivers_without_a_model_job(self):
        import localization_pipeline as pipeline
        run=self.root/'runtime/cli-localization/runs/test';run.mkdir(parents=True)
        task=self.root/'translation/de/pipeline/tasks/resources/task.json';receipt=task.with_name('receipt.json')
        self.put(str(task.relative_to(self.root)),{'receiptPath':str(receipt)})
        manifest=self.build/'manifest.json'
        self.put(str(receipt.relative_to(self.root)),{'work':{'buildManifest':{'path':str(manifest.relative_to(self.root)),'sha256':cp.digest(manifest)}}})
        state={'locales':{'de':{'status':'queued','workflow':{'role':'package'},'attempts':[
            {'role':'resources','status':'stage-complete','validation':{'roleComplete':True},'taskPath':str(task)}]}}}
        fake=type('Acceptance',(),{'_owner_checkpoint_reuse':staticmethod(lambda *args:True),
            'inspect_locale':staticmethod(lambda *args:dict(inventorySha256='inventory',glossarySha256='glossary',corpusSha256='corpus'))})()
        with patch.object(pipeline,'acceptance',return_value=fake):
            self.assertTrue(pipeline.package_locale_checkpoint(self.root,run,state,'de'))
        package=state['locales']['de']['workflow']['machinePackageCheckpoint']
        self.assertEqual(cp.digest(self.root/package['deliveredArchive']),package['archive']['sha256'])
        self.assertEqual(len(state['locales']['de']['attempts']),1)
        self.assertEqual(state['locales']['de']['workflow']['role'],'delivery')

if __name__=='__main__':unittest.main()
