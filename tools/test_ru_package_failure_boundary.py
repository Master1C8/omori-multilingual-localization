"""A failed new package leaves no completion receipt and preserves old delivery."""
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import package_ru_mod
from ru_static_inputs import current_inputs

ROOT=Path(__file__).resolve().parents[1]


class PackageFailureBoundaryTests(unittest.TestCase):
    def test_failure_between_copies_is_incomplete_not_a_transaction(self):
        fixture=current_inputs(ROOT)
        if not (fixture['display']/'receipt.json').exists():
            self.skipTest('Pinned rebuild required')
        previous=ROOT/'dist/ru-text-8879120-2026-10-14-05/omori-ru-text-8879120.zip'
        before=hashlib.sha256(previous.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='package-failure-',dir=ROOT/'build/ru') as temporary:
            out=Path(temporary)/'incomplete'
            argv=['package_ru_mod.py','--combined',str(fixture['combined']),
                  '--display',str(fixture['display']),
                  '--fonts',str(fixture['fonts']),
                  '--editorial',str(fixture['editorial']),
                  '--font-reproducibility',str(fixture['fontReproducibility']),
                  '--output',str(out)]
            real_copy=shutil.copyfile;calls=[]
            def interrupt(source,destination,*args,**kwargs):
                calls.append(str(destination))
                if len(calls)==2:raise OSError('injected failure between package copies')
                return real_copy(source,destination,*args,**kwargs)
            with patch.object(sys,'argv',argv),patch.object(package_ru_mod.shutil,'copyfile',side_effect=interrupt):
                with self.assertRaisesRegex(OSError,'injected failure between package copies'):
                    package_ru_mod.main()
            self.assertEqual(len(calls),2);self.assertTrue(Path(calls[0]).is_file())
            self.assertFalse((out/'receipt.json').exists());self.assertFalse((out/'omori-ru-text-8879120.zip').exists())
            with patch.object(sys,'argv',argv):
                with self.assertRaisesRegex(ValueError,'Preserve previous package'):
                    package_ru_mod.main()
        self.assertEqual(hashlib.sha256(previous.read_bytes()).hexdigest(),before)


if __name__=='__main__':unittest.main()
