"""명시적 3D 골반 시험의 출력 경로와 출처를 검증한다."""
import json
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

from generators.kimodo.dwpose_export import export_kimodo_dwpose


class KimodoProjectedHipExportTests(unittest.TestCase):
    def test_generation_review_requires_reviewed_skeleton_for_projected_hip(self):
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                inputs=client.get('/management/assistant/kimodo-generation-template').json()['inputs']
                inputs['prompt']='stand'
                response=client.post('/management/assistant/kimodo-generation-review',json={**inputs,'proportion_projected_hip':True})
                self.assertEqual(response.status_code,422)
                self.assertIn('검수 3D 골격',response.json()['detail'])
                self.assertEqual(client.post('/management/assistant/kimodo-generation-review',json=inputs).status_code,200)

    def test_opt_in_projects_only_matching_attempt_and_records_source(self):
        current_keypoint_type = namedtuple('Keypoint', 'x y')
        current_body_type = namedtuple('Body', 'keypoints')
        current_pose_type = namedtuple('Pose', 'body')
        current_points = [current_keypoint_type(5, 5) for _ in range(18)]
        for current_index, current_xy in {2:(4,1),5:(6,1),8:(4.9,6),11:(5.1,6),9:(4,8),10:(4,10),12:(6,8),13:(6,10)}.items():
            current_points[current_index] = current_keypoint_type(*current_xy)
        current_frames = [[current_pose_type(current_body_type(current_points))]]
        current_projection = [[current_point.x,current_point.y,1] for current_point in current_points]
        current_projection[8] = [4,6,1]
        current_projection[11] = [6,6,1]
        current_candidate = {'candidate':'bound'}
        with tempfile.TemporaryDirectory() as current_directory:
            current_root=Path(current_directory)
            current_attempt=current_root/'attempt';current_attempt.mkdir()
            (current_root/'request.json').write_text(json.dumps({'frames':1,'directions':['left'],'proportion_projected_hip':True,'proportion_reviewed_multiview':{'skeleton':current_candidate}}))
            (current_attempt/'reference-proportions.json').write_text(json.dumps({'weighted_body_face_candidate':current_candidate}))
            (current_attempt/'soma-render-left.mp4').write_bytes(b'video')
            (current_attempt/'soma-direct-pose.json').write_text(json.dumps({'fps':30,'size':[832,480],'directions':{'left':{'source_frames':[0],'body_points_832x480':[current_projection]}}}))
            def run_fake_pose(current_work,current_output,current_request,current_transform,current_output_fps,current_soma_foreground_fallback):
                self.assertTrue(current_soma_foreground_fallback)
                current_transform(current_frames,(480,832))
                (current_output/'pose.mp4').write_bytes(b'pose')
                (current_output/'pose-preprocess.json').write_text(json.dumps({'soma_foreground_fallback_frames':[]}))
            with patch('generators.kimodo.dwpose_export.prepare_fun_pose_frames',side_effect=run_fake_pose), patch('generators.kimodo.dwpose_export.calculate_projected_segment_gains',return_value={}) as current_gain_mock, patch('generators.kimodo.dwpose_export.adjust_detected_pose_frames',side_effect=lambda *current_args:current_args[0]) as current_adjust_mock:
                export_kimodo_dwpose(current_root,current_attempt)
            self.assertEqual(current_gain_mock.call_args.args[-1],('hip_width',))
            current_adjusted=current_adjust_mock.call_args.args[0][0][0].body.keypoints
            self.assertLess(current_adjusted[8].x,current_points[8].x)
            self.assertGreater(current_adjusted[11].x,current_points[11].x)
            current_record=json.loads((current_attempt/'dwpose-export.json').read_text())
            self.assertTrue(current_record['hip_projection_enabled'])
            self.assertEqual(current_record['body_axis']['left']['hip_reconstruction']['frames'],1)
            self.assertEqual(len(current_record['body_axis']['left']['hip_reconstruction']['source_sha256']),64)
            (current_attempt/'reference-proportions.json').write_text(json.dumps({'weighted_body_face_candidate':{'other':True}}))
            with self.assertRaisesRegex(ValueError,'다릅니다'):
                export_kimodo_dwpose(current_root,current_attempt)


if __name__ == '__main__':
    unittest.main()
