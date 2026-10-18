#!/usr/bin/env python3
"""Exercise actual filesystem operations on disposable synthetic QA artifacts."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).with_name('cleanup_qa_storage.py'))
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        c.ROOT = Path(self.temp.name).resolve()
        c.EVIDENCE = c.ROOT / 'evidence'; c.EVIDENCE.mkdir()
        (c.EVIDENCE / 'open-files.txt').write_text('')
        c.FRAMES = c.ROOT / 'source/movie-cache'
        frames = c.FRAMES / 'movie-00/frames'; frames.mkdir(parents=True)
        self.frame = frames / 'frame-000001.png'; self.frame.write_bytes(b'generated-cache')
        self.original = c.ROOT / 'original.webm'; self.original.write_bytes(b'original-video')
        self.backups = []
        for name in ['20261017-one', '20261017-two']:
            base = c.ROOT / 'runtime/visual-qa' / name / 'installer-metadata-final/backups'
            base.mkdir(parents=True)
            p = base / c.sha(self.original); p.write_bytes(self.original.read_bytes())
            self.backups.append(p)
        a, b = self.backups
        self.plan = c.EVIDENCE / 'plan.json'
        self.data = {'root': str(c.ROOT), 'links': [dict(c.row(b,c.sha(b)), keeper=c.row(a,c.sha(a)))],
                     'deleteFrames':[c.row(self.frame,c.sha(self.frame))],
                     'protected':[c.row(self.original,c.sha(self.original))],
                     'allocatedBytesEligible':0,'freeBefore':0}
        c.save(self.plan,self.data)

    def tearDown(self): self.temp.cleanup()

    def test_positive_preserves_backup_paths_bytes_and_original(self):
        previous = Path.cwd()
        try:
            os.chdir(c.ROOT)
            result=c.apply(self.plan.relative_to(c.ROOT))
        finally:
            os.chdir(previous)
        a,b=self.backups
        self.assertEqual(a.stat().st_ino,b.stat().st_ino)
        self.assertEqual(b.read_bytes(),b'original-video')
        self.assertEqual(self.original.read_bytes(),b'original-video')
        self.assertFalse(self.frame.exists())
        self.assertEqual(result['deletedReproducibleFrames'],1)
        self.assertEqual(c.read(c.FRAMES/'STORAGE_EVICTED.json')['receipt'], 'evidence/plan.result.json')

    def test_changed_frame_rejects_before_any_backup_mutation(self):
        before=[p.stat().st_ino for p in self.backups]
        self.frame.write_bytes(b'owner-edit')
        with self.assertRaises(AssertionError): c.apply(self.plan)
        self.assertEqual(before,[p.stat().st_ino for p in self.backups])
        self.assertEqual(self.frame.read_bytes(),b'owner-edit')

    def test_open_file_rejects_before_mutation(self):
        (c.EVIDENCE / 'open-files.txt').write_text('n'+str(self.frame)+'\n')
        with self.assertRaisesRegex(AssertionError,'Open file'): c.apply(self.plan)
        self.assertTrue(self.frame.exists())
        self.assertNotEqual(self.backups[0].stat().st_ino,self.backups[1].stat().st_ino)

    def test_changed_original_rejects_before_mutation(self):
        self.original.write_bytes(b'changed-source')
        with self.assertRaises(AssertionError): c.apply(self.plan)
        self.assertTrue(self.frame.exists())
        self.assertNotEqual(self.backups[0].stat().st_ino,self.backups[1].stat().st_ino)

if __name__ == '__main__': unittest.main()
