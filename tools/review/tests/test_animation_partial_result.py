"""미완료 프레임을 제외한 부분 결과 조회 계약."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.review.domains.character_animation.character_animation_jobs import collect_partial_result

class AnimationPartialResultTests(unittest.TestCase):
    def test_only_saved_completed_frames_are_playable(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            generation_job_path=Path(temporary_directory_name)
            request_record_value={'fps':4,'frames':[{'direction':'down_left','frame':1},{'direction':'up_left','frame':3}]}
            self.assertIsNone(collect_partial_result(generation_job_path,request_record_value))
            for direction_name_value,frame_number_value in [('down_left',1),('up_left',3)]:
                frame_output_directory=generation_job_path/direction_name_value/f'frame-{frame_number_value:04d}'
                frame_output_directory.mkdir(parents=True)
                (frame_output_directory/'result.png').write_bytes(b'fixture')
            (generation_job_path/'down_left/frame-0001/result.json').write_text(json.dumps({'status':'completed'}))
            result_record_value=collect_partial_result(generation_job_path,request_record_value)
            self.assertEqual(result_record_value['completed'],1)
            self.assertEqual(result_record_value['total'],2)
            self.assertEqual(result_record_value['source_frame_numbers'],{'down_left':[1]})
