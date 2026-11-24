"""걷기 비교 생성물이 공통 검수 템플릿을 반영하는지 확인한다."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from workflow.build_walk_review import build_walk_review
from workflow.build_frame_manager import build_frame_manager


class WalkReviewBuildUiTests(unittest.TestCase):
    def test_generated_page_contains_current_controls_and_review_assets(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=root/'.tmp') as directory:
            run = Path(directory)
            directions = ('down_left', 'down_right', 'up_left', 'up_right')
            outputs = []
            for direction in directions:
                image = f'walk-{direction}.png'
                (run/image).write_bytes(b'fixture')
                (run/f'rig-{direction}.png').write_bytes(b'fixture')
                outputs.append({'direction':direction, 'image':image, 'size':[256, 256]})
            (run/'result.json').write_text(json.dumps({'outputs':outputs}))
            build_walk_review(run)
            page = (run/'preview.html').read_text()
            self.assertNotIn('__ASSET_RECORDS__', page)
            self.assertIn('walk-down_left.png', page)
            self.assertIn('걷기 비교 다시 불러오기', page)
            self.assertIn('reviewImagesReady', page)
            self.assertIn('검수·관리 셸 배치', page)

    def test_manager_regenerates_walking_page_from_current_template(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=root/'.tmp') as directory:
            fake_root = Path(directory)
            walking = fake_root/'.tmp'/'walking'
            standing = fake_root/'.tmp'/'standing'
            walking.mkdir(parents=True)
            standing.mkdir()
            records = [{'direction':'down_left', 'image':'walk.png', 'size':[256, 256]}]
            (walking/'preview.html').write_text('const reviewAssetRecords='+json.dumps(records)+';')
            anchor = 'const reviewFrameRecords=[];const reviewSourceMetadata={};'
            (walking/'anchors.html').write_text(anchor)
            (standing/'preview.html').write_text(anchor)
            with patch('workflow.build_frame_manager.WORKFLOW_REPO_ROOT',fake_root):
                output = build_frame_manager(SimpleNamespace(walking=walking,standing=standing))
            page = (output/'walking'/'preview.html').read_text()
            self.assertIn('walk.png', page)
            self.assertIn('걷기 비교 다시 불러오기', page)
            self.assertIn('reviewImagesReady', page)
            manager = json.loads((output/'manager-source.json').read_text())
            self.assertTrue(any(item['id']=='walk-review' and item['path']=='walking/preview.html' for item in manager['pages']))
