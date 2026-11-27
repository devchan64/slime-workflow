import json
import tempfile
import unittest
from pathlib import Path
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
            self.assertFalse((root/'candidates').exists())
