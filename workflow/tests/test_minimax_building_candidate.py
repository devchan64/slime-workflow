import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from workflow.domains.minimax_h3_image.building_candidates import send_candidate, read_candidate

class BuildingCandidateTest(unittest.TestCase):
    def test_completed_candidate_is_immutable_and_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'jobs'; target=root/'candidates'; job='2026-11-26_22-22-48-d42039d7'; folder=source/job; folder.mkdir(parents=True)
            (folder/'status.json').write_text(json.dumps({'status':'completed'}))
            Image.new('RGB', (2, 2), 'white').save(folder/'result.png')
            result=send_candidate(source,target,job)
            self.assertEqual(read_candidate(target,job,result['sha256'])['id'],job)
            self.assertTrue(send_candidate(source,target,job)['already_exists'])
            (folder/'result.png').unlink()
            self.assertEqual(read_candidate(target,job,result['sha256'])['id'],job)
            with self.assertRaises(ValueError): read_candidate(target,'../../outside',result['sha256'])
            file=next(target.glob('*.json')); file.write_text('{}')
            with self.assertRaises(ValueError): read_candidate(target,job,result['sha256'])
    def test_rejects_incomplete_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); job='2026-11-26_22-22-48-d42039d7'; folder=root/job; folder.mkdir()
            (folder/'status.json').write_text('{"status":"running"}')
            with self.assertRaises(ValueError): send_candidate(root,root/'candidates',job)
            self.assertEqual(list((root/'candidates').glob('*.json')), [])

    def test_expiration_rejects_and_resending_creates_new_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'jobs'; target=root/'candidates'; job='2026-11-26_22-22-48-d42039d7'; folder=source/job; folder.mkdir(parents=True)
            (folder/'status.json').write_text('{"status":"completed"}')
            Image.new('RGB', (2, 2), 'white').save(folder/'result.png')
            with patch('workflow.domains.minimax_h3_image.building_candidates.time.time', return_value=1000000000):
                result=send_candidate(source,target,job)
                self.assertEqual(result['expires_at'],1000000000+7*24*60*60)
            with patch('workflow.domains.minimax_h3_image.building_candidates.time.time', return_value=result['expires_at']):
                with self.assertRaisesRegex(ValueError,'만료'): read_candidate(target,job,result['sha256'])
                self.assertFalse(any(target.glob('*.json')))
                newer=send_candidate(source,target,job)
                self.assertGreater(newer['expires_at'],result['expires_at'])
                self.assertTrue((folder/'result.png').exists())
