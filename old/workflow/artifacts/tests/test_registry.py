"""등록 경쟁·동일 버전 변경 거절·조회 시 원본 재검증."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import sqlite3
import unittest
import test_sidecar as fixtures
from workflow.artifacts.registry import register, resolve


class RegistryTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write
    def db(self):
        return self.root.parent / 'registry.sqlite'

    def test_registration_is_idempotent_under_concurrency(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(lambda _: register(self.db(), self.root, self.sidecar), range(8)))
        self.assertTrue(all(entry == entries[0] for entry in entries))
        with sqlite3.connect(self.db()) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM artifacts').fetchone()[0], 1)
        self.assertEqual(resolve(self.db(), 'terrain.test', '1.0.0'), self.data)

    def test_metadata_change_is_not_silently_registered(self):
        register(self.db(), self.root, self.sidecar)
        self.data['quality']['quality_warnings'].append('새 경고')
        self.write()
        with self.assertRaises(ValueError): register(self.db(), self.root, self.sidecar)
        with self.assertRaises(ValueError): resolve(self.db(), 'terrain.test', '1.0.0')

    def test_content_with_updated_hash_still_requires_new_version(self):
        register(self.db(), self.root, self.sidecar)
        self.image.write_bytes(b'new-version')
        self.data['sha256'] = sha256(self.image.read_bytes()).hexdigest()
        self.write()
        with self.assertRaises(ValueError): register(self.db(), self.root, self.sidecar)
        with self.assertRaises(ValueError): resolve(self.db(), 'terrain.test', '1.0.0')
        self.data['version'] = '2.0.0'; self.write()
        register(self.db(), self.root, self.sidecar)
        self.assertEqual(resolve(self.db(), 'terrain.test', '2.0.0'), self.data)

    def test_invalid_pair_does_not_create_registry(self):
        self.db().unlink()
        self.image.unlink()
        with self.assertRaises(FileNotFoundError): register(self.db(), self.root, self.sidecar)
        self.assertFalse(self.db().exists())

    def test_unknown_lookup_does_not_create_database(self):
        self.db().unlink()
        with self.assertRaises(FileNotFoundError): resolve(self.db(), 'terrain.test', '1')
        self.assertFalse(self.db().exists())

    def test_unrelated_database_is_preserved(self):
        self.db().unlink()
        with sqlite3.connect(self.db()) as connection:
            connection.execute('CREATE TABLE unrelated(id INTEGER)')
        with self.assertRaises(ValueError): register(self.db(), self.root, self.sidecar)
        with sqlite3.connect(self.db()) as connection:
            self.assertEqual(connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [('unrelated',)])

    def test_cli_registration(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-m', 'workflow.artifacts', '--root', str(self.root),
            '--sidecar', str(self.sidecar), '--registry', str(self.db()),
            '--log', str(self.root.parent / 'validation.log')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('/artifact-validate/registered', result.stdout)
        self.assertEqual(resolve(self.db(), 'terrain.test', '1.0.0'), self.data)
