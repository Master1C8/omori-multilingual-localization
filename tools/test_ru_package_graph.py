"""Exercise real package pre-output guards using verified positive inputs."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from ru_static_inputs import current_inputs
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class PackageGraphTests(unittest.TestCase):
    def test_changed_graph_and_outputs_fail_before_creation(self):
        fixture=current_inputs(ROOT)
        combined=fixture['combined'];display=fixture['display'];fonts=fixture['fonts']
        if not (display/'receipt.json').exists():
            self.skipTest('This regression requires the pinned independent-review rebuild')
        with tempfile.TemporaryDirectory(prefix='package-graph-',dir=ROOT/'build/ru') as temporary:
            scratch=Path(temporary)
            def run(c,d,out,independent=None):
                args=[sys.executable,'-B',str(ROOT/'tools/package_ru_mod.py'),
                      '--combined',str(c),'--display',str(d),'--fonts',str(fonts),
                      '--editorial',str(fixture['editorial']),
                      '--font-reproducibility',str(fixture['fontReproducibility']),
                      '--output',str(out)]
                if independent:args+=['--independent',str(independent)]
                return subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
            positive=run(combined,display,scratch/'positive')
            self.assertEqual(positive.returncode,0,positive.stderr)
            self.assertTrue((scratch/'positive/receipt.json').exists())
            record=json.loads((display/'receipt.json').read_text())
            plugin=next(p for p in record['compiledOutputs'] if p.startswith('plugins/') and 'OmoriRu' not in p)
            override=next(p for p in record['compiledOutputs'] if p.startswith('data/'))
            edits=[('native-plugin',plugin),('bootstrap','plugins/OmoriRu_Bootstrap.js'),
                   ('install','plugins/OmoriRu_Install.js'),('structured-override',override)]
            for name,path in edits:
                with self.subTest(name=name):
                    changed=scratch/name;shutil.copytree(display,changed)
                    with (changed/path).open('ab') as f:f.write(b' ')
                    out=scratch/(name+'-out');result=run(combined,changed,out)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('Display output bytes changed: '+path,result.stderr)
                    self.assertFalse(out.exists())
            for name,change in [('missing',lambda d:(d/plugin).unlink()),
                                ('extra',lambda d:(d/'plugins/unreviewed.js').write_text('// extra'))]:
                changed=scratch/name;shutil.copytree(display,changed);change(changed)
                out=scratch/(name+'-out');result=run(combined,changed,out)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Display output inventory changed',result.stderr);self.assertFalse(out.exists())
            stale=scratch/'stale-combined';shutil.copytree(combined,stale)
            receipt=json.loads((stale/'receipt.json').read_text())
            key=next(k for k in receipt['dependencies'] if k.startswith('translation/ru/batches/'))
            receipt['dependencies'][key]='0'*64;(stale/'receipt.json').write_text(json.dumps(receipt))
            out=scratch/'stale-out';result=run(stale,display,out)
            self.assertNotEqual(result.returncode,0);self.assertIn('Combined current dependency graph changed',result.stderr);self.assertFalse(out.exists())
            invalid=scratch/'unclean-review.json';invalid.write_text(json.dumps({'passStatus':'pending','findings':[]}))
            out=scratch/'unclean-out';result=run(combined,display,out,invalid)
            self.assertNotEqual(result.returncode,0);self.assertIn('Clean independent delta receipt required',result.stderr);self.assertFalse(out.exists())
            from package_ru_mod import verify_independent
            from source_prepare import sha
            prior=ROOT/'translation/ru/audits/2026-10-14-independent-01/reviewer/report-01.json'
            old_manifest=ROOT/'translation/ru/audits/2026-10-14-independent-01/manifest.json'
            previous=json.loads((old_manifest.parent/'closure-ids.json').read_text());review_ids=previous[:1]
            changed=json.loads(fixture['caseReview'].read_text())['allTaskChangedIds']
            current=list(dict.fromkeys(previous+changed))
            review_ids=list(dict.fromkeys(changed+[i for i in current if i not in previous]+review_ids))
            authors=json.loads(fixture['editorial'].read_text())['authorDependencies']
            manifest={'inputs':{str((p/'receipt.json').relative_to(ROOT)):sha((p/'receipt.json').read_bytes()) for p in [combined,display,fonts]},
                      'authorDependencies':authors,'previousManifest':str(old_manifest.relative_to(ROOT)),
                      'currentClosureIds':current,'changedIds':changed,'invalidatedIds':previous[:1],'reviewIds':review_ids}
            manifest_path=scratch/'synthetic-manifest.json';manifest_path.write_text(json.dumps(manifest))
            review={'passStatus':'passed-clean-delta','findings':[],
                    'reviewer':{'taskIdentity':'/root/omori_independent_review','model':'gpt-6.1-sol','reasoning':'high'},
                    'inputManifest':str(manifest_path.relative_to(ROOT)),'inputManifestSha256':sha(manifest_path.read_bytes()),
                    'priorReport':str(prior.relative_to(ROOT)),'priorReportSha256':sha(prior.read_bytes()),
                    'resolvedFindingIds':[f['id'] for f in json.loads(prior.read_text())['findings']],
                    'mandatoryRegressionStatus':'passed-static','reviewedIds':review_ids}
            review_path=scratch/'synthetic-review.json';review_path.write_text(json.dumps(review))
            # Synthetic metadata positive exercises the guard only, never certifies semantics.
            self.assertEqual(verify_independent(ROOT,review_path,combined,display,fonts)['reviewedIds'],review_ids)
            # Current text cannot inherit the real old clean receipt.
            old_clean=ROOT/'translation/ru/audits/2026-10-14-independent-03/reviewer/report-03.json'
            out=scratch/'old-clean-out';result=run(combined,display,out,old_clean)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Independent graph changed:',result.stderr);self.assertFalse(out.exists())
            mutations=[('manifest-hash',lambda j:j.update(inputManifestSha256='0'*64),'Independent manifest changed'),
                       ('coverage',lambda j:j.update(reviewedIds=[]),'Independent delta coverage mismatch')]
            for name,change,reason in mutations:
                bad=json.loads(json.dumps(review));change(bad);review_path.write_text(json.dumps(bad))
                out=scratch/(name+'-out');result=run(combined,display,out,review_path)
                self.assertNotEqual(result.returncode,0);self.assertIn(reason,result.stderr);self.assertFalse(out.exists())
            manifest['inputs'][str((display/'receipt.json').relative_to(ROOT))]='0'*64
            manifest_path.write_text(json.dumps(manifest));review['inputManifestSha256']=sha(manifest_path.read_bytes());review_path.write_text(json.dumps(review))
            out=scratch/'review-graph-out';result=run(combined,display,out,review_path)
            self.assertNotEqual(result.returncode,0);self.assertIn('Independent graph changed:',result.stderr);self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
