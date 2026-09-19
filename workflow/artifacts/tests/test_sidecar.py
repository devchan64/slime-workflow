"""합성 파일로 메타데이터와 경로 경계를 검사한다. 픽셀 품질 검사가 아니다."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from workflow.artifacts.sidecar import validate_pair


class PairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "artifacts"
        self.root.mkdir()
        self.image = self.root / 'tile.png'
        self.image.write_bytes(b'synthetic-file-for-contract-tests')
        self.sidecar = self.root / 'tile.json'
        self.data = dict(schemaVersion=1, artifactId='terrain.test', version='1.0.0',
            artifactType='TERRAIN_TILE', sourcePath='tile.png', sha256=sha256(self.image.read_bytes()).hexdigest(),
            createdBy='test', createdAt='2026-09-20T00:00:00+09:00', runId='run.test', sourceArtifacts=[],
            contractRefs=[dict(contractId='terrain', version='1')],
            generation=dict(profileId='test', profileVersion='1', pipelineVersion='1', seed=0, modelPreparationRef='test-model'),
            license=dict(source='synthetic-test', licenseId='test-only', rightsHolder='test', evidenceRef='test-record',
                         modificationAllowed=False, redistributionAllowed=False, attribution='test'),
            quality=dict(quality_warnings=['검수 필요'], reviewRequired=True, reviewRecordRef=None))
        self.write()

    def write(self):
        self.sidecar.write_text(json.dumps(self.data), encoding='utf-8')

    def test_valid_pair_preserves_warnings_and_does_not_grant_public_rights(self):
        before = deepcopy(self.data)
        self.assertEqual(validate_pair(self.root, self.sidecar), before)
        self.assertFalse(before['license']['redistributionAllowed'])

    def test_invalid_metadata(self):
        for mutate in [lambda d:d.update(schemaVersion=True), lambda d:d.update(extra=1),
                       lambda d:d.update(artifactType='UNKNOWN'), lambda d:d.update(artifactId='../x'),
                       lambda d:d.update(createdAt='2026-09-20'), lambda d:d.update(contractRefs=[]),
                       lambda d:d['generation'].update(seed=True), lambda d:d['license'].pop('evidenceRef'),
                       lambda d:d['license'].update(redistributionAllowed=1),
                       lambda d:d['quality'].update(reviewRequired='yes')]:
            with self.subTest(mutation=mutate):
                original = deepcopy(self.data)
                mutate(self.data); self.write()
                with self.assertRaises(ValueError): validate_pair(self.root, self.sidecar)
                self.data = original

    def test_paths_and_hash(self):
        for source in ['../tile.png', '/tile.png', './tile.png', 'dir/../tile.png', 'tile.json', 'missing.png']:
            with self.subTest(source=source):
                self.data['sourcePath'] = source; self.write()
                with self.assertRaises((ValueError, FileNotFoundError)): validate_pair(self.root, self.sidecar)
        self.data['sourcePath'] = 'tile.png'; self.write()
        self.image.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SHA-256'): validate_pair(self.root, self.sidecar)

    def test_duplicate_keys_and_nonfinite_json(self):
        for content in ['{"schemaVersion":1,"schemaVersion":1}', '{"schemaVersion":NaN}']:
            self.sidecar.write_text(content)
            with self.assertRaises(ValueError): validate_pair(self.root, self.sidecar)

    def test_symlink_and_basename_mismatch(self):
        self.image.rename(self.root / 'other.png')
        self.image.symlink_to(self.root / 'other.png')
        with self.assertRaises(ValueError): validate_pair(self.root, self.sidecar)
        self.data['sourcePath'] = 'other.png'; self.write()
        with self.assertRaisesRegex(ValueError, 'basename'): validate_pair(self.root, self.sidecar)

    def test_cli_records_success_warning_and_failure(self):
        command = [sys.executable, '-m', 'workflow.artifacts', '--root', str(self.root),
                   '--sidecar', str(self.sidecar), '--log', str(self.root.parent / 'validation.log')]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('/artifact-validate/WARN', result.stdout)
        self.assertIn('공개 승인 아님', result.stdout)
        self.image.unlink()
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertIn('/artifact-validate/failure', failed.stdout)
        self.assertIn('Traceback', (self.root.parent / 'validation.log').read_text())

    def test_log_cannot_overwrite_source_tree(self):
        before = self.sidecar.read_bytes()
        result = subprocess.run([sys.executable, '-m', 'workflow.artifacts', '--root', str(self.root),
            '--sidecar', str(self.sidecar), '--log', str(self.sidecar)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.sidecar.read_bytes(), before)
