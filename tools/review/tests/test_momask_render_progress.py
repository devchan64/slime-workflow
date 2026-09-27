import json
import tempfile
import unittest
from pathlib import Path
from tools.review.domains.momask.momask_jobs import read_render_progress
from tools.review.common.gradio_history import render_history_detail_cards


class MotionRenderProgressTests(unittest.TestCase):
    def test_source_frame_does_not_count_as_completed_render(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            render = root/'result/anny'
            render.mkdir(parents=True)
            (render/'retarget-contract.json').write_text(json.dumps({'frames': 2, 'directions': ['down_left', 'up_left']}))
            (render/'down_left').mkdir()
            (render/'down_left/preview-0001.png').touch()
            progress = read_render_progress(root, 'Fra:149 Sample 1/16\nFra:149 Sample 16/16')
            self.assertEqual(progress['percent'], 25)
            self.assertEqual(progress['current_source_frame'], 149)
            self.assertEqual(progress['total_frames'], 4)
            card = render_history_detail_cards([{'id': 'test', 'status': 'running', 'progress': progress}])
            self.assertIn('25%', card)
            self.assertIn('1/4프레임 저장', card)
            self.assertIn('Fra:149', card)
            # 다음 방향의 프레임 번호가 작아져도 완료 진행률은 줄지 않는다.
            (render/'up_left').mkdir()
            (render/'up_left/preview-0001.png').touch()
            self.assertEqual(read_render_progress(root, 'Fra:1')['percent'], 50)

    def test_inference_has_no_render_percentage(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(read_render_progress(Path(directory), 'loading model'))
