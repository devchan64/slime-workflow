"""공개 ZIP의 명시적 필드·승인/권리 게이트·비공개 기록 분리."""
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile
import unittest
import test_sidecar as fixtures
from workflow.artifacts.registry import archive_register
from workflow.artifacts.reviews import record_review
from workflow.artifacts.exporter import export_asset


class ExportTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write

    def prepare(self, approve=True, rights=True):
        self.data['license'].update(licenseId='CC-BY-4.0', modificationAllowed=rights, redistributionAllowed=rights)
        self.data['generation']['modelPreparationRef'] = 'PRIVATE_MODEL_REF'
        self.write()
        self.db = self.root.parent / 'registry.sqlite'
        self.releases = self.root.parent / 'private-releases'
        self.entry = archive_register(self.db, self.root, self.sidecar)
        self.review = dict(review_id='review.export', decision='APPROVED', reviewer='synthetic',
            evidence_ref='PRIVATE_REVIEW_EVIDENCE', content_hash=self.entry['content_hash'], metadata_hash=self.entry['metadata_hash'])
        if approve:
            record_review(self.db, 'terrain.test', '1.0.0', **self.review)

    def export(self):
        return export_asset(self.db, 'terrain.test', '1.0.0', self.releases)

    def test_public_manifest_and_private_receipt_are_separate_and_repeatable(self):
        self.prepare()
        result = self.export()
        archive = Path(result['archive'])
        self.assertEqual(archive.stem, sha256(archive.read_bytes()).hexdigest())
        with ZipFile(archive) as pack:
            manifest = json.loads(pack.read('manifest.json'))
            self.assertEqual(set(manifest), {'assetId','version','assetType','files','hashes','licenseId','attribution','compatibleSchemaVersion'})
            self.assertEqual(set(pack.namelist()), {manifest['files'][0], 'manifest.json', 'LICENSE.txt', 'ATTRIBUTION.txt'})
            self.assertEqual(sha256(pack.read(manifest['files'][0])).hexdigest(), self.data['sha256'])
            for name in pack.namelist():
                content = pack.read(name)
                self.assertNotIn(b'PRIVATE_', content)
                self.assertNotIn(str(self.root).encode(), content)
        receipt = json.loads(Path(result['privateRecord']).read_text())
        self.assertEqual(receipt['metadataHash'], self.entry['metadata_hash'])
        self.assertEqual(receipt['reviewId'], 'review.export')
        again = self.export()
        self.assertEqual(archive.read_bytes(), Path(again['archive']).read_bytes())

    def test_unreviewed_and_later_rejected_assets_cannot_export(self):
        self.prepare(approve=False)
        with self.assertRaises(ValueError): self.export()
        record_review(self.db, 'terrain.test', '1.0.0', **self.review)
        record_review(self.db, 'terrain.test', '1.0.0', **dict(self.review, review_id='review.reject', decision='REJECTED', previous_review_id='review.export'))
        with self.assertRaises(ValueError): self.export()
        self.assertFalse(self.releases.exists())

    def test_approval_does_not_override_restricted_rights(self):
        self.prepare(rights=False)
        with self.assertRaises(ValueError): self.export()
        self.assertFalse(self.releases.exists())

    def test_changed_approved_file_is_rejected_without_release(self):
        self.prepare()
        file = Path(self.entry['root']) / 'tile.png'
        file.chmod(0o644); file.write_bytes(b'tampered')
        with self.assertRaises(ValueError): self.export()
        self.assertFalse(self.releases.exists())

    def test_export_cli_creates_local_package_only(self):
        import subprocess
        import sys
        self.prepare()
        result = subprocess.run([sys.executable, '-m', 'workflow.artifacts.review_cli',
            '--registry', str(self.db), '--artifact-id', 'terrain.test', '--version', '1.0.0',
            '--log', str(self.root.parent / 'export.log'), 'export', '--release-root', str(self.releases)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(self.releases.glob('*/*.zip'))), 1)

    def test_symlink_release_path_is_rejected(self):
        self.prepare()
        other = self.root.parent / 'other'
        other.mkdir(); self.releases.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError): self.export()
        self.assertEqual(list(other.iterdir()), [])
