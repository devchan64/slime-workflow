"""포즈 비교 공통 템플릿의 세 생성 경로를 임시 리포트로 확인한다."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
with patch.object(sys, 'path', [str(ROOT/'workflow'), *sys.path]):
    import build_pose_transfer_review as pose
    import build_openpose_review as openpose
    import build_two_reference_review as two_reference


class PoseReviewBuildUiTests(unittest.TestCase):
    def test_all_builders_preserve_their_image_roles(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as directory:
            root = Path(directory)
            report = root/'report'/'fixture'
            for direction in pose.SUPPORTED_DIRECTIONS:
                for number in pose.FRAME_NUMBERS:
                    frame = report/direction/f'frame-{number:02d}'
                    frame.mkdir(parents=True)
                    for filename in ('result.png', 'rig-reference.png', 'openpose-reference.png'):
                        (frame/filename).write_bytes(filename.encode())
                    hashes = {name:hashlib.sha256((frame/name).read_bytes()).hexdigest() for name in ('rig-reference.png','openpose-reference.png')}
                    metadata = {'status':'completed','size':[256,256], 'input_order':['character-reference.png','rig-reference.png','openpose-reference.png'], 'input_sha256':hashes,'output':'result.png','revision':'v1'}
                    (frame/'result.json').write_text(json.dumps(metadata))
            output = root/'.tmp'
            with patch.object(pose,'WORKFLOW_REPOSITORY_ROOT',root), patch.object(openpose,'ROOT',root), patch.object(two_reference,'WORKFLOW_REPOSITORY_ROOT',root):
                paths = [pose.build_pose_transfer_review(report,output/'pose'), openpose.build_openpose_review(report,output/'openpose'), two_reference.build_two_reference_review(report,report,output/'two')]
            for path, roles in zip(paths, ({'result','rig','openpose'}, {'result','rig'}, {'result','rig','openpose'})):
                page = (path/'preview.html').read_text()
                data, _ = json.JSONDecoder().raw_decode(page.split('const poseTransferData=',1)[1])
                self.assertEqual(len(data['directions']),4)
                self.assertEqual(set(data['directions'][0]['frames'][0]['files']),roles)
                self.assertIn('겹치기 다시 불러오기',page)
                self.assertIn('검수·관리 셸 배치',page)
                self.assertNotIn('__POSE_TRANSFER_DATA__',page)
