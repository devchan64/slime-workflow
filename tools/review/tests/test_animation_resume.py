"""완료 프레임 보존과 중단 프레임 재생성을 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.animation.run_character_animation import generate_character_animation

class AnimationResumeContractTests(unittest.TestCase):
    def test_completed_frame_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            generation_job_path=Path(temporary_directory_name)
            generation_request_record={'directions':['down_left'],'frames':[{'direction':'down_left','frame':1},{'direction':'down_left','frame':2}],'fps':4,'motion':'test','source':'openpose','sampling':'target-fps'}
            (generation_job_path/'request.json').write_text(json.dumps(generation_request_record))
            for current_frame_number in (1,2):
                current_frame_directory=generation_job_path/'down_left'/f'frame-{current_frame_number:04d}'
                current_frame_directory.mkdir(parents=True)
                (current_frame_directory/'execution.log').write_text('이전 기록')
            completed_image_path=generation_job_path/'down_left/frame-0001/result.png'
            Image.new('RGB',(8,8)).save(completed_image_path)
            (completed_image_path.parent/'result.json').write_text('{"status":"completed"}')
            completed_image_bytes=completed_image_path.read_bytes()
            def execute_mock_frame(command_argument_list,check):
                self.assertEqual(command_argument_list[-1],'1')
                current_frame_directory=generation_job_path/'down_left/frame-0002'
                current_frame_directory.mkdir()
                Image.new('RGB',(8,8)).save(current_frame_directory/'result.png')
            with patch('generators.animation.run_character_animation.WORKFLOW_ROOT_DIRECTORY',generation_job_path),patch('generators.animation.run_character_animation.acquire_worker_lock'),patch('generators.animation.run_character_animation.subprocess.run',side_effect=execute_mock_frame) as mocked_frame_runner:
                generate_character_animation(generation_job_path)
            self.assertEqual(mocked_frame_runner.call_count,1)
            self.assertEqual(completed_image_path.read_bytes(),completed_image_bytes)
            self.assertEqual(len(list((generation_job_path/'down_left').glob('frame-0002-incomplete-*'))),1)
            self.assertEqual(json.loads((generation_job_path/'progress.json').read_text())['completed'],2)
