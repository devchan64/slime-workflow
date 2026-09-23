"""Qwen 타일 생성 기록을 관리도구 검수 화면으로 묶는 계약을 확인한다."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools.review.collect_tile_reviews import collect_tile_reviews


class TileReviewCollectionTests(unittest.TestCase):
    def test_empty_tile_review_is_listed(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            workflow_root_path = Path(temporary_directory_name)
            (workflow_root_path/'.tmp').mkdir()
            output_directory_path = workflow_root_path/'.tmp'/'review-output'
            output_directory_path.mkdir()
            page_records = collect_tile_reviews(workflow_root_path, output_directory_path, lambda *unused_trace_values: None)
            self.assertEqual(page_records, [])

    def make_tile_run(self, workflow_root_path):
        run_directory_path = workflow_root_path/'.tmp'/'2026-09-21_12-00-00'
        run_directory_path.mkdir(parents=True)
        tile_path = run_directory_path/'ground.png'
        Image.new('RGBA', (32, 32), (45, 110, 65, 255)).save(tile_path)
        ticket_path = run_directory_path/'ticket.yaml'
        ticket_path.write_text('asset_id: field.grass-v1\n')
        map_path = run_directory_path/'map-preview.yaml'
        map_path.write_text('schemaVersion: 1\nmapId: meadow\ndisplayNameKo: 이슬 초원\ncolumns: 2\nrows: 1\nterrainRows: [gg]\nterrainCodes:\n  g:\n    labelKo: 풀밭\n    color: "#39754a"\ntargetCells:\n  - column: 1\n    row: 0\n')
        hash_file = lambda current_file_path: hashlib.sha256(current_file_path.read_bytes()).hexdigest()
        record_value = {'schemaVersion': 1, 'kind': 'qwen-terrain-tile-review', 'assetId': 'field.grass-v1', 'status': 'candidate-needs-user-review', 'modelId': 'Qwen/Qwen-Image-Edit-2511', 'modelRevision': 'a'*40, 'tileSize': [32, 32], 'tileability': 'repeat-both', 'heightSteps': 1, 'ticket': {'file': 'ticket.yaml', 'sha256': hash_file(ticket_path)}, 'variants': [{'role': 'ground', 'file': 'ground.png', 'sha256': hash_file(tile_path)}], 'preview': None, 'mapPreview': {'file': 'map-preview.yaml', 'sha256': hash_file(map_path), 'mapId': 'meadow', 'targetCells': [{'column': 1, 'row': 0}]}, 'qualityWarnings': ['검수 필요']}
        (run_directory_path/'tile-review.json').write_text(json.dumps(record_value, ensure_ascii=False))
        return run_directory_path

    def test_collects_tile_run_and_map_target_preview(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            workflow_root_path = Path(temporary_directory_name)
            self.make_tile_run(workflow_root_path)
            output_directory_path = workflow_root_path/'.tmp'/'review-output'
            output_directory_path.mkdir()
            page_records = collect_tile_reviews(workflow_root_path, output_directory_path, lambda *unused_trace_values: None)
            self.assertEqual(page_records[0]['category'], 'tile-review')
            page_path = output_directory_path/page_records[0]['path']
            self.assertIn('지정 타일', page_path.read_text())
            self.assertTrue((page_path.parent/'ground.png').is_file())

    def test_rejects_changed_tile_after_recording_hash(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            workflow_root_path = Path(temporary_directory_name)
            run_directory_path = self.make_tile_run(workflow_root_path)
            (run_directory_path/'ground.png').write_bytes(b'changed')
            output_directory_path = workflow_root_path/'.tmp'/'review-output'
            output_directory_path.mkdir()
            with self.assertRaisesRegex(ValueError, '해시'):
                collect_tile_reviews(workflow_root_path, output_directory_path, lambda *unused_trace_values: None)


if __name__ == '__main__':
    unittest.main()
