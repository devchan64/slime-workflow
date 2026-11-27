"""미디어 재시도 쿼리와 Range가 관리 경로 선택을 바꾸지 않는지 확인한다."""
import unittest
import tempfile
import hashlib
import json
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from types import SimpleNamespace
from unittest.mock import patch

from workflow.common.management_transport import is_management_runtime_request
from workflow.common.management_runtime import ManagementServiceRuntime


class MediaRetryRouteTests(unittest.TestCase):
    def write_saved_pose(self,job,content):
        (job/'pose-input.mp4').write_bytes(content)
        (job/'reference-1.png').write_bytes(b'png')
        (job/'request.json').write_text(json.dumps({'references':['reference-1.png'],
            'reference_snapshots':[{'path':'reference-1.png','order':1,'bytes':3,'sha256':hashlib.sha256(b'png').hexdigest()}],
            'pose_video_file':'pose-input.mp4','pose_video_sha256':hashlib.sha256(content).hexdigest()}))

    def test_saved_pose_retry_preserves_partial_response(self):
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/identifier;job.mkdir();self.write_saved_pose(job,b'fixture-video')
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with patch('workflow.domains.hermes_agent.video_operations.make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=root)),TestClient(app) as client:
                response=client.get('/management/assistant/fun-pose/'+identifier+'?retry=1',headers={'Range':'bytes=0-3'})
                self.assertEqual(response.status_code,206)
                self.assertEqual(response.content,b'fixt')

    def test_saved_pose_thumbnail_decodes_and_rejects_missing_job(self):
        import imageio_ffmpeg, subprocess
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/identifier;job.mkdir()
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-f','lavfi','-i','color=red:s=64x48:d=1','-c:v','mpeg4',str(job/'pose-input.mp4')],check=True)
            self.write_saved_pose(job,(job/'pose-input.mp4').read_bytes())
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with patch('workflow.domains.hermes_agent.video_operations.make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=root)),TestClient(app) as client:
                response=client.get('/management/assistant/fun-pose-thumbnail/'+identifier)
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.headers['content-type'],'image/png')
                self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(client.get('/management/assistant/fun-pose-thumbnail/invalid').status_code,404)

    def test_retry_query_routes_to_same_service_with_range(self):
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES
        for service,filename in [('kimodo','preview.mp4'),('music-heartmula','result.wav'),('sfx-dasheng-audiogen','result.wav')]:
            with self.subTest(service=service):
                route=MANAGEMENT_SERVICE_ROUTES[service]+'/jobs/test/'+filename+'?retry=1'
                self.assertTrue(is_management_runtime_request(route))
                seen=[]
                bindings={service:SimpleNamespace(request_handler_callback=lambda request:seen.append((request.path,request.headers['Range'])) or True)}
                runtime=ManagementServiceRuntime.__new__(ManagementServiceRuntime)
                runtime.runtime_closed_flag=False
                runtime.service_binding_records=bindings
                runtime.management_command_gateway=SimpleNamespace(handle=lambda request:False)
                request=SimpleNamespace(command='GET',path=route,headers={'Range':'bytes=0-3'})
                with patch.object(runtime.management_command_gateway,'handle',return_value=False):
                    self.assertTrue(runtime.dispatch_runtime_request(request))
                self.assertEqual(seen,[(route,'bytes=0-3')])
