import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("provenance", Path(__file__).parents[1] / "Scripts/build-provenance.py")
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)


class ProvenanceTests(unittest.TestCase):
    def test_archive_matches_stage_and_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "App"
            stage.mkdir()
            (stage / "file").write_bytes(b"accepted")
            archive = root / "release.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.write(stage / "file", "App/file")
            self.assertEqual(provenance.verify_archive(archive, stage), 1)
            (stage / "file").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "bytes differ"):
                provenance.verify_archive(archive, stage)

    def test_archive_rejects_missing_material(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "App"
            stage.mkdir()
            (stage / "file").write_bytes(b"accepted")
            archive = root / "release.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("App/other", b"accepted")
            with self.assertRaisesRegex(ValueError, "paths differ"):
                provenance.verify_archive(archive, stage)

    def test_materials_reject_symlinks_and_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "file"
            source.write_bytes(b"first")
            before = provenance.fingerprint(provenance.inventory(root))
            source.write_bytes(b"second")
            self.assertNotEqual(before, provenance.fingerprint(provenance.inventory(root)))
            (root / "link").symlink_to(source)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                provenance.inventory(root)


if __name__ == "__main__":
    unittest.main()
