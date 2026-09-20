"""다중 에셋의 원자적 공개·승인 게이트·동일 바이트 공유를 검증한다."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import test_exporter as fixtures
from workflow.artifacts.exporter import export_pack
from workflow.artifacts.registry import archive_register
from workflow.artifacts.reviews import record_review


class PackTests(unittest.TestCase):
    setUp = fixtures.ExportTests.setUp
    write = fixtures.ExportTests.write
    prepare = fixtures.ExportTests.prepare

    def second(self, approve=True, rights=True, same_bytes=False):
        data = deepcopy(self.data)
        data.update(artifactId='terrain.second', sourcePath='second.png')
        data['license'].update(modificationAllowed=rights, attribution='Second synthetic credit')
        source = self.root / 'second.png'
        source.write_bytes(self.image.read_bytes() if same_bytes else b'synthetic-second-file')
        data['sha256'] = sha256(source.read_bytes()).hexdigest()
        sidecar = source.with_suffix('.json')
        sidecar.write_text(json.dumps(data))
        entry = archive_register(self.db, self.root, sidecar)
        if approve:
            record_review(self.db, data['artifactId'], data['version'], **dict(self.review,
                review_id='review.second', content_hash=entry['content_hash'], metadata_hash=entry['metadata_hash']))
        return entry

    def export(self, assets=None, root=None):
        return export_pack(self.db, 'pack.test', '1', assets if assets is not None else
            [('terrain.test','1.0.0'), ('terrain.second','1.0.0')], root or self.releases)

    def test_multiple_assets_deterministic_bytes_and_private_records(self):
        self.prepare(); self.second()
        result = self.export()
        archive = Path(result['archive'])
        with ZipFile(archive) as pack:
            manifest = json.loads(pack.read('manifest.json'))
            self.assertEqual(set(manifest), {'packId','version','compatibleSchemaVersion','assets'})
            self.assertEqual([x['assetId'] for x in manifest['assets']], ['terrain.second','terrain.test'])
            self.assertEqual(len(pack.namelist()), 5)
            for asset in manifest['assets']:
                self.assertEqual(set(asset), {'assetId','version','assetType','files','hashes','licenseId','attribution','compatibleSchemaVersion'})
                for name in asset['files']:
                    self.assertEqual(sha256(pack.read(name)).hexdigest(), asset['hashes'][name])
            self.assertIn(b'Second synthetic credit', pack.read('ATTRIBUTION.txt'))
            for name in pack.namelist():
                self.assertNotIn(b'PRIVATE_', pack.read(name))
                self.assertNotIn(str(self.root).encode(), pack.read(name))
        receipt = json.loads(Path(result['privateRecord']).read_text())
        self.assertEqual({x['reviewId'] for x in receipt['assets']}, {'review.export','review.second'})
        reversed_result = self.export([('terrain.second','1.0.0'), ('terrain.test','1.0.0')])
        self.assertEqual(archive.read_bytes(), Path(reversed_result['archive']).read_bytes())

    def test_same_payload_is_written_once_but_keeps_both_credits(self):
        self.prepare(); self.second(same_bytes=True)
        with ZipFile(self.export()['archive']) as pack:
            self.assertEqual(len(pack.namelist()), 4)
            manifest = json.loads(pack.read('manifest.json'))
            self.assertEqual(manifest['assets'][0]['files'], manifest['assets'][1]['files'])
            self.assertEqual(len(manifest['assets']), 2)
            self.assertIn(b'Second synthetic credit', pack.read('ATTRIBUTION.txt'))

    def test_any_unapproved_restricted_or_changed_member_blocks_entire_pack(self):
        self.prepare(); entry = self.second(approve=False)
        with self.assertRaisesRegex(ValueError, '승인'): self.export()
        self.assertFalse(self.releases.exists())
        record_review(self.db, 'terrain.second', '1.0.0', **dict(self.review,
            review_id='review.second', content_hash=entry['content_hash'], metadata_hash=entry['metadata_hash']))
        source = Path(entry['root']) / 'second.png'
        source.chmod(0o644); source.write_bytes(b'changed')
        with self.assertRaises(ValueError): self.export()
        self.assertFalse(self.releases.exists())

    def test_one_restricted_member_blocks_pack(self):
        self.prepare(); self.second(rights=False)
        with self.assertRaisesRegex(ValueError, '라이선스'): self.export()
        self.assertFalse(self.releases.exists())

    def test_invalid_selection_and_all_member_path_boundaries(self):
        self.prepare(); entry = self.second()
        for assets in ([], [('terrain.test','1.0.0')]*2, ['terrain.test'], [('terrain.test', True)]):
            with self.subTest(assets=assets), self.assertRaises(ValueError): self.export(assets)
        with self.assertRaises(ValueError): self.export(root=Path(entry['root'])/'release')
        self.assertFalse(self.releases.exists())

    def test_failure_after_copy_leaves_no_partial_pack(self):
        from workflow.artifacts import exporter
        self.prepare(); self.second()
        original = exporter.resolve
        calls = 0
        def failing(*args):
            nonlocal calls
            calls += 1
            if calls == 3: raise ValueError('합성 후검사 실패')
            return original(*args)
        with patch.object(exporter, 'resolve', failing), self.assertRaisesRegex(ValueError, '후검사'):
            self.export()
        self.assertEqual(list(self.releases.iterdir()), [])

    def test_private_generation_input_is_verified_but_not_included(self):
        self.db = self.root.parent / 'registry.sqlite'
        source = deepcopy(self.data)
        source.update(artifactId='input.private', sourcePath='private.png')
        payload = self.root / 'private.png'
        payload.write_bytes(b'PRIVATE_GENERATION_INPUT')
        source['sha256'] = sha256(payload.read_bytes()).hexdigest()
        sidecar = payload.with_suffix('.json')
        sidecar.write_text(json.dumps(source))
        archive_register(self.db, self.root, sidecar)
        self.data['sourceArtifacts'] = [dict(artifactId='input.private', version='1.0.0', sha256=source['sha256'])]
        self.prepare(); self.second()
        with ZipFile(self.export()['archive']) as pack:
            self.assertEqual(len(pack.namelist()), 5)
            self.assertNotIn(source['sha256']+'.png', pack.namelist())
            for name in pack.namelist():
                self.assertNotIn(b'PRIVATE_GENERATION_INPUT', pack.read(name))

    def test_cli_exports_and_rejects_log_inside_any_source(self):
        self.prepare(); entry = self.second()
        args = [sys.executable, '-m', 'workflow.artifacts.pack_cli', '--registry', str(self.db),
            '--pack-id', 'pack.test', '--version', '1', '--asset', 'terrain.test', '1.0.0',
            '--asset', 'terrain.second', '1.0.0', '--release-root', str(self.releases), '--log']
        success = subprocess.run(args+[str(self.root.parent/'pack.log')], capture_output=True, text=True)
        self.assertEqual(success.returncode, 0, success.stdout+success.stderr)
        self.assertEqual(len(list(self.releases.glob('*/*.zip'))), 1)
        log = Path(entry['root'])/'invalid.log'
        failed = subprocess.run(args+[str(log)], capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse(log.exists())
