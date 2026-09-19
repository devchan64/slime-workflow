"""보관본의 작업 원본 독립성·등록 경쟁·실패 격리."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import unittest
import test_sidecar as fixtures
from workflow.artifacts.registry import archive_register, resolve


class ArchiveTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write

    def db(self):
        return self.root.parent / 'registry.sqlite'

    def test_archived_pair_survives_deleted_working_source(self):
        saved = archive_register(self.db(), self.root, self.sidecar)
        self.image.unlink(); self.sidecar.unlink()
        self.assertEqual(resolve(self.db(), 'terrain.test', '1.0.0'), self.data)
        self.assertEqual((Path(saved['root']) / 'tile.png').stat().st_mode & 0o222, 0)

    def test_concurrent_archive_registration_is_idempotent(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(lambda _: archive_register(self.db(), self.root, self.sidecar), range(8)))
        self.assertTrue(all(entry == entries[0] for entry in entries))
        self.assertEqual(resolve(self.db(), 'terrain.test', '1.0.0'), self.data)

    def test_copy_failure_never_registers_partial_pair(self):
        with patch('shutil.copyfile', side_effect=OSError('복사 실패')):
            with self.assertRaises(OSError): archive_register(self.db(), self.root, self.sidecar)
        self.assertFalse((self.db().with_suffix('.artifacts') / 'terrain.test' / '1.0.0').exists())
        saved = archive_register(self.db(), self.root, self.sidecar)
        self.assertEqual(resolve(self.db(), saved['artifact_id'], saved['version']), self.data)

    def test_changed_archive_is_not_overwritten(self):
        saved = archive_register(self.db(), self.root, self.sidecar)
        archived = Path(saved['root']) / 'tile.png'
        archived.chmod(0o644); archived.write_bytes(b'tampered')
        with self.assertRaises(ValueError): resolve(self.db(), 'terrain.test', '1.0.0')
        with self.assertRaises(ValueError): archive_register(self.db(), self.root, self.sidecar)
        self.assertEqual(archived.read_bytes(), b'tampered')

    def test_deleted_archive_is_not_silently_recreated(self):
        import shutil
        saved = archive_register(self.db(), self.root, self.sidecar)
        shutil.rmtree(saved['root'])
        with self.assertRaises(ValueError): archive_register(self.db(), self.root, self.sidecar)

    def test_database_failure_leaves_verified_pair_for_same_request_retry(self):
        from contextlib import contextmanager
        from workflow.artifacts import registry
        original = registry.database
        @contextmanager
        def failing(*args):
            with original(*args) as connection:
                yield connection
                raise OSError('커밋 이전 실패')
        with patch.object(registry, 'database', failing):
            with self.assertRaises(OSError): archive_register(self.db(), self.root, self.sidecar)
        self.assertTrue((self.db().with_suffix('.artifacts') / 'terrain.test' / '1.0.0' / 'tile.png').exists())
        archive_register(self.db(), self.root, self.sidecar)
        self.assertEqual(resolve(self.db(), 'terrain.test', '1.0.0'), self.data)

    def test_archive_cli(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-m', 'workflow.artifacts', '--archive',
            '--root', str(self.root), '--sidecar', str(self.sidecar), '--registry', str(self.db()),
            '--log', str(self.root.parent / 'archive.log')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.image.unlink()
        self.assertEqual(resolve(self.db(), 'terrain.test', '1.0.0'), self.data)
