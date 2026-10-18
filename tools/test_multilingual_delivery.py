#!/usr/bin/env python3
"""Meaningful negative gates and real-data native delivery integration tests."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/multilingual/delivery'))
import native_delivery as nd


class Gates(unittest.TestCase):
    def test_explicit_locale_rejection_precedes_writes(self):
        for locale in ['en','zh','ja','ko','ru','unknown','../es','']:
            output=OUTPUT/('rejected-'+str(abs(hash(locale))))
            with self.assertRaisesRegex(ValueError,'excluded target locale'):
                nd.build(ROOT,locale,Path('/missing/plaintext'),output)
            self.assertFalse(output.exists())
        self.assertEqual(len(json.loads((nd.HERE/'locales.json').read_text())['locales']),26)

    def test_mapping_locale_and_completeness(self):
        expected=[{'id':'sample','source':'raw','target':'authored'}]
        receipt={'displayMappings':1,'displayMappingsSha256':'digest'}
        mapping={'siteLocale':'es','inventorySha256':nd.INVENTORY,'entries':expected}
        nd.mapping_gate('es',receipt,mapping,expected,'digest')
        with self.assertRaisesRegex(ValueError,'Wrong-locale'):
            nd.mapping_gate('fr',receipt,mapping,expected,'digest')
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            nd.mapping_gate('es',receipt,mapping,expected+expected,'digest')
        duplicate=dict(mapping,entries=expected+expected)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            nd.mapping_gate('es',receipt,duplicate,expected,'digest')

    def test_stale_author_binding(self):
        expected={'a':{'id':'a','source':'same','target':'current'}}
        nd.author_gate(expected,copy.deepcopy(expected))
        with self.assertRaisesRegex(ValueError,'Stale author receipt'):
            nd.author_gate(expected,{'a':{'id':'a','source':'same','target':'stale'}})

    def test_safe_paths_and_immutable_output(self):
        for path in ['../x','/x','a/../x','a//x','a\\x','C:x']:
            with self.assertRaisesRegex(ValueError,'Unsafe'):nd.safe_relative(path)
        p=OUTPUT/'immutable';p.mkdir()
        with self.assertRaisesRegex(ValueError,'immutable'):nd.inside(p,ROOT/'build/multilingual-delivery',new=True)
        link=OUTPUT/'symlink';link.symlink_to(p,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Symlink'):nd.inside(link/'new',ROOT/'build/multilingual-delivery',new=True)

    def test_native_codec_and_delivered_bytes(self):
        raw='Native Δ — authored text'.encode();encrypted=nd.crypt(raw)
        row={'path':'data/Test.KEL','sha256':nd.sha(encrypted),'plaintextSha256':nd.sha(raw),'encrypted':True}
        payload={'files/data/Test.KEL':encrypted}
        nd.verify_bytes(payload,[row],payload.__getitem__)
        damaged=encrypted[:-1]+bytes([encrypted[-1]^1])
        with self.assertRaisesRegex(ValueError,'delivered bytes'):
            nd.verify_bytes(payload,[row],lambda _:damaged)
        self.assertEqual(nd.crypt(encrypted,True),raw)
        # Native .PLUTO is encrypted just like KEL/HERO; JS config remains plaintext.
        self.assertNotEqual(encrypted,raw)

    def test_incomplete_revision_after_between_write_failure(self):
        output=OUTPUT/'incomplete'
        fake_ctx=type('Fake',(),{'units':[],'retained':[]})()
        payload={'files/a':b'a','files/b':b'b'}
        # Only failure injection is mocked. It tests the actual filesystem acceptance boundary.
        with patch.object(nd,'input_state',return_value=(fake_ctx,[],[],{},{})), patch.object(nd,'expected_payload',return_value=(payload,[],{},{})), patch.object(nd,'check_consumers',return_value={}):
            with self.assertRaisesRegex(ValueError,'between-write failure'):
                nd.build(ROOT,'es',Path('/unused'),output,fail_after=1)
        self.assertTrue((output/'INCOMPLETE.json').exists())
        self.assertTrue((output/'files/a').exists())
        self.assertFalse((output/'files/b').exists())
        self.assertFalse((output/'ACCEPTANCE.json').exists())

    def test_protected_logic_mutation(self):
        from verify_source_inventory import compare_protected
        original={'name':'RAW','switch':False,'event':{'code':122,'parameters':[1,1,0,4,'"RAW"']}}
        changed=copy.deepcopy(original);changed['name']='Authored'
        compare_protected(original,changed,{('name',):'visible'})
        changed['event']['parameters'][2]=1
        with self.assertRaisesRegex(ValueError,'protected value'):
            compare_protected(original,changed,{('name',):'visible'})


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=OUTPUT/'es-native'
        cls.plain=ROOT/'runtime/multilingual/locales/es/attempt-0043-plaintext-01'
        cls.result=nd.build(ROOT,'es',cls.plain,cls.build)

    def test_real_compile_readback_package_and_tamper(self):
        result=nd.verify(ROOT,'es',self.build)
        self.assertEqual(result['mappedTargets'],3505)
        self.assertEqual(result['status'],'passed-native-decrypted-readback')
        manifest=json.loads((self.build/'manifest.json').read_bytes())
        pluto=next(r for r in manifest['files'] if r['path']=='data/Quests.PLUTO')
        self.assertTrue(pluto['encrypted'])
        from prepare_source import native_parse
        pluto_raw=nd.crypt((self.build/'files/data/Quests.PLUTO').read_bytes(),True).decode()
        self.assertTrue(native_parse(nd.GAME/'js/libs/js-yaml-master',[{'asset':'data/Quests.PLUTO','text':pluto_raw}])[0]['value'])
        self.assertNotIn('data/Actors.KEL',[r['path'] for r in manifest['files']])
        archive=OUTPUT/'es-native.zip';nd.package(ROOT,'es',self.build,archive)
        nd.verify(ROOT,'es',self.build,archive)
        # The actual archive is decompressed/decrypted by the verifier; no substring search.
        with ZipFile(archive) as z:contents={name:z.read(name) for name in z.namelist()}
        extra=OUTPUT/'extra.zip'
        with ZipFile(extra,'x',compression=ZIP_DEFLATED) as z:
            for name,raw in contents.items():z.writestr(name,raw)
            z.writestr('files/unexpected.txt',b'extra')
        # Full positive controls above satisfy all earlier guards. Cache only the unchanged
        # deterministic input/compiler work for negative archive checks, never the readback.
        ctx,pairs,mapping,config,pinned=nd.input_state(ROOT,'es',self.plain,full=False)
        expected=nd.expected_payload(ctx,pairs,mapping,config)
        with patch.object(nd,'input_state',return_value=(ctx,pairs,mapping,config,pinned)),patch.object(nd,'expected_payload',return_value=expected):
            with self.assertRaisesRegex(ValueError,'Archive entry set'):
                nd.verify(ROOT,'es',self.build,extra)
            key=next(n for n in contents if n.endswith('.HERO'))
            modified=dict(contents);raw=modified[key];modified[key]=raw[:-1]+bytes([raw[-1]^1])
            tamper=OUTPUT/'tamper.zip'
            with ZipFile(tamper,'x',compression=ZIP_DEFLATED) as z:
                for name,raw in modified.items():z.writestr(name,raw)
            with self.assertRaisesRegex(ValueError,'delivered bytes'):
                nd.verify(ROOT,'es',self.build,tamper)
            # Re-sign the manifest fixture to get past the earlier receipt hash guard;
            # the intended dependency boundary must reject each stale input explicitly.
            stale=OUTPUT/'stale-source-build';shutil.copytree(self.build,stale)
            mp=stale/'manifest.json';ap=stale/'ACCEPTANCE.json';saved_m=mp.read_bytes();saved_a=ap.read_bytes()
            for field in ['inventorySha256','plaintextReceiptSha256']:
                doc=json.loads(saved_m);doc['inputs'][field]='0'*64;mp.write_bytes(nd.serialized(doc))
                accepted=json.loads(saved_a);accepted['manifestSha256']=nd.sha(mp.read_bytes());ap.write_bytes(nd.serialized(accepted))
                with self.assertRaisesRegex(ValueError,'Stale source/author receipt'):
                    nd.verify(ROOT,'es',stale)
            # Negative fixtures are separate revisions; preserve the accepted candidate.
            unwired=OUTPUT/'unwired-build';shutil.copytree(self.build,unwired)
            proof=unwired/'bindings.json';doc=json.loads(proof.read_bytes());doc['bindings'].pop();proof.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'Unwired|unwired'):
                nd.verify(ROOT,'es',unwired)
            damaged=OUTPUT/'mutated-native-build';shutil.copytree(self.build,damaged)
            destination=damaged/key;destination.write_bytes(nd.crypt(b'protected: mutated\n'))
            with self.assertRaisesRegex(ValueError,'delivered bytes'):
                nd.verify(ROOT,'es',damaged)
        receipt=OUTPUT/'real-data-result.json';receipt.write_bytes(nd.serialized(result|{'package':str(archive),'negativeCases':['archive-extra-entry','archive-ciphertext-tamper','unwired-mapping-proof','native-resource-mutation']}))

    def test_real_stale_german_receipt(self):
        with self.assertRaisesRegex(ValueError,'Stale author receipt'):
            nd.input_state(ROOT,'de',ROOT/'runtime/multilingual/locales/de/editorial-corrections-0029',full=False)

    def test_wrong_locale_before_build_write(self):
        with self.assertRaisesRegex(ValueError,'outside authorized'):
            nd.build(ROOT,'fr',self.plain,OUTPUT/'wrong-locale')
        self.assertFalse((OUTPUT/'wrong-locale').exists())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--unit-only',action='store_true')
    args=parser.parse_args();OUTPUT=nd.inside(args.output,ROOT/'build/multilingual-delivery',new=True);OUTPUT.mkdir(parents=True)
    loader=unittest.TestLoader();suite=loader.loadTestsFromTestCase(Gates)
    if not args.unit_only:suite.addTests(loader.loadTestsFromTestCase(RealData))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (OUTPUT/'test-result.json').write_bytes(nd.serialized({'status':'passed' if result.wasSuccessful() else 'failed','tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'realData':not args.unit_only,'usage':'unknown','runtime':'not-run','visual':'not-run'}))
    sys.exit(0 if result.wasSuccessful() else 1)
