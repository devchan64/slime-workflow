"""얼굴 ON/OFF와 가림 정보 보존 계약."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.review.domains.momask.openpose_maps import generate_openpose_maps

class OpenposeFaceOptionTests(unittest.TestCase):
    def test_face_toggle_preserves_visibility(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            generation_job_path=Path(temporary_directory_name)
            (generation_job_path/'result/anny').mkdir(parents=True)
            (generation_job_path/'result.json').write_text(json.dumps({'directions':['down_left'],'frames':1}))
            (generation_job_path/'result/anny/openpose-keypoints.json').write_text(json.dumps({'frames':{'down_left':[[[100,100]]*14]}}))
            (generation_job_path/'result/anny/face-keypoints.json').write_text(json.dumps({'frames':{'down_left':[[[90,80,1],[0,0,0],[95,75,1],[0,0,0],[100,80,1]]]}}))
            generate_openpose_maps(generation_job_path,True)
            output_keypoint_record=json.loads((generation_job_path/'result/openpose-map/keypoints.json').read_text())
            current_pose_values=output_keypoint_record['frames']['down_left'][0]['pose_keypoints_2d']
            self.assertEqual(current_pose_values[:3],[90,80,1])
            self.assertEqual(current_pose_values[42:45],[0,0,0])
            generate_openpose_maps(generation_job_path,False)
            output_keypoint_record=json.loads((generation_job_path/'result/openpose-map/keypoints.json').read_text())
            self.assertEqual(output_keypoint_record['frames']['down_left'][0]['pose_keypoints_2d'][:3],[0,0,0])
            with self.assertRaises(ValueError):generate_openpose_maps(generation_job_path,'on')
