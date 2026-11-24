import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.generators.minimax_h3_ref2va.contracts import save_video_input, validate_request
from workflow.common.video_attachment_verification import verify_saved_video_attachments


class Ref2VAContractTest(unittest.TestCase):
    def setUp(self):
        self.data = b'\x00\x00\x00\x18ftypisom' + b'test video'
        self.request = dict(action='generate', prompt='  Remove the trail.  ', images=[],
                            edit_video=base64.b64encode(self.data).decode(), width=832,
                            height=480, frames=124, steps=8, seed=45)

    def test_validate_and_verify_saved_video(self):
        with patch('workflow.generators.minimax_h3_ref2va.contracts.validate_video_content') as inspect:
            validated = validate_request(self.request)
        inspect.assert_called_once_with(self.data)
        self.assertEqual(validated['prompt'], 'Remove the trail.')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saved = save_video_input(root, validated)
            self.assertNotIn('edit_video', saved)
            verify_saved_video_attachments(root, saved, ('edit_video',))
            (root / 'edit-video.mp4').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                verify_saved_video_attachments(root, saved, ('edit_video',))

    def test_saved_input_restore_rejects_tampering(self):
        from workflow.domains.minimax_h3_ref2va.input_restore import load_saved_input
        import json
        job = '2026-11-24_22-18-44-dd9b846b'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / job; target.mkdir()
            saved = save_video_input(target, self.request)
            (target / 'request.json').write_text(json.dumps(saved))
            with patch('workflow.generators.minimax_h3_ref2va.contracts.validate_video_content'):
                restored = load_saved_input(root, job)
                self.assertEqual(restored['request']['edit_video'], self.request['edit_video'])
                (target / 'edit-video.mp4').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    load_saved_input(root, job)

    def test_rejects_wrong_settings_and_bad_video(self):
        for key, value in [('frames', 123), ('seed', True), ('images', ['image']),
                           ('edit_video', 'not-base64')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_request({**self.request, key: value})


class Ref2VAIntegrationTest(unittest.TestCase):
    def test_gateway_and_gpu_queue_route(self):
        from workflow.common.management_gateway import resolve_management_command
        from workflow.common.gpu_job_queue import (
            GPU_EXCLUSIVE_SERVICES, GPU_MEMORY_REQUIREMENTS,
            identify_dedicated_gpu_reservation_source, is_dedicated_gpu_source_verifiable,
        )
        from workflow.domains.minimax_h3_ref2va.generation import MiniMaxH3Ref2VAManager
        self.assertEqual(resolve_management_command('minimax-h3-ref2va', 'generate', {}),
                         ('POST', '/minimax-h3-ref2va/jobs'))
        self.assertEqual(MiniMaxH3Ref2VAManager().select_generation_service(), 'minimax-h3-ref2va')
        self.assertIn('minimax-h3-ref2va', GPU_EXCLUSIVE_SERVICES)
        self.assertEqual(GPU_MEMORY_REQUIREMENTS['minimax-h3-ref2va'], 81920)
        self.assertTrue(is_dedicated_gpu_source_verifiable('minimax-h3-ref2va'))
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / '.tmp/test/minimax-h3-ref2va/2026-11-24_22-18-44-dd9b846b'
            job.mkdir(parents=True)
            self.assertIsNotNone(identify_dedicated_gpu_reservation_source(str(job), 'minimax-h3-ref2va', directory))


    def test_contiguous_attention_accepts_prompt_length_variation_only_in_bounded_shape(self):
        from workflow.generators.minimax_h3_ref2va.contiguous_attention import is_supported_self_attention_shape
        for length in (1, 2751, 29999, 31965, 32025, 32768):
            self.assertTrue(is_supported_self_attention_shape((1,length,56,128)))
        for shape in ((1,0,56,128),(1,32769,56,128),(2,32025,56,128),
                      (1,32025,55,128),(1,32025,56,64),(32025,56,128)):
            self.assertFalse(is_supported_self_attention_shape(shape))

    def test_pipeline_config_reuses_only_matching_fixed_snapshot(self):
        from workflow.generators.minimax_h3_ref2va import assets
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); snapshot=root/'snapshot'; ref=root/'ref'; output=root/'cache/pipeline-config'
            snapshot.mkdir()
            for name in ('modular_model_index.json','model_index.json'):
                (snapshot/name).write_text('{}')
            for name in ('text_encoder','tokenizer','processor','transformer','scheduler','audio_scheduler','vae','audio_vae'):
                target=snapshot/name;target.mkdir();(target/'config.json').write_text('{}')
            (ref/'transformer_ref').mkdir(parents=True)
            (ref/'transformer_ref/config.json').write_text('{"value":1}')
            with patch.object(assets,'SNAPSHOT',snapshot),patch.object(assets,'REF',ref),patch.object(assets,'PIPELINE',output):
                self.assertEqual(assets.prepare_pipeline_config(),output)
                self.assertEqual(assets.prepare_pipeline_config(),output)
                (output/'transformer_ref/config.json').write_text('{"value":2}')
                with self.assertRaises(ValueError):
                    assets.prepare_pipeline_config()

    def test_hermes_proposal_and_catalog_resolve_to_video_editor(self):
        import json
        from workflow.common.management_catalog import DEFAULT_PAGE_RECORDS
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal
        from workflow.domains.hermes_agent.video_operations import make_hermes_video_manager, HERMES_VIDEO_SERVICES
        from workflow.domains.hermes_agent.video_selection import select_video_proposal
        service = 'minimax-h3-ref2va'
        proposal = {'service': service, 'mode': 'video_edit', 'prompt': 'Remove the blue trail', 'explicit_service': True}
        answer = 'HERMES_VIDEO_PROPOSAL\n' + json.dumps(proposal) + '\nEND_HERMES_VIDEO_PROPOSAL'
        parsed = parse_hermes_video_proposal(answer)
        selected = select_video_proposal(parsed, {'prompt': 'MiniMax Ref2VA 영상 편집', 'minimax_preferred': True})
        self.assertEqual(selected['service'], service)
        self.assertIn(service, HERMES_VIDEO_SERVICES)
        self.assertEqual(make_hermes_video_manager(service).route_prefix_value, '/' + service)
        self.assertTrue(any(page['id'] == service + '-generator' and page['uiMode'] == 'react' for page in DEFAULT_PAGE_RECORDS))


    def test_gateway_submission_saves_verified_video_before_launch(self):
        import io
        import json
        from types import SimpleNamespace
        from unittest.mock import Mock
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.domains.minimax_h3_ref2va.generation import MiniMaxH3Ref2VAManager
        service = 'minimax-h3-ref2va'
        video = b'\x00\x00\x00\x18ftypisom' + b'decoder is mocked'
        payload = {'action':'generate', 'prompt':'Remove the trail', 'images':[],
                   'edit_video':base64.b64encode(video).decode(), 'width':832, 'height':480,
                   'frames':124, 'steps':8, 'seed':45}
        body = json.dumps({'service':service,'command':'generate','payload':payload}).encode()
        handler = SimpleNamespace(path='/management/command', command='POST',
            headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770',
                     'Content-Type':'application/json','Content-Length':str(len(body))},
            server=SimpleNamespace(server_port=8770), rfile=io.BytesIO(body), wfile=io.BytesIO(), responses=[])
        handler.send_response=handler.responses.append
        handler.send_header=lambda *args: None
        handler.end_headers=lambda: None
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); manager=MiniMaxH3Ref2VAManager(); manager.job_storage_root=root/'jobs'; manager.job_storage_root.mkdir()
            with patch.object(manager,'history_storage_path',return_value=root/'history'), \
                 patch.object(manager,'validate_generation_runtime'), \
                 patch.object(manager,'launch_generation_worker',return_value=Mock()) as launch, \
                 patch('workflow.generators.minimax_h3_ref2va.contracts.validate_video_content'), \
                 patch('workflow.domains.image.image_generation.threading.Thread'):
                ManagementCommandGateway({service:manager.handle_image_request}).handle(handler)
            self.assertEqual(handler.responses,[202])
            job=json.loads(handler.wfile.getvalue())['id']; directory=manager.job_storage_root/job
            saved=json.loads((directory/'request.json').read_text())
            self.assertEqual((directory/'edit-video.mp4').read_bytes(),video)
            self.assertNotIn('edit_video',saved)
            verify_saved_video_attachments(directory,saved,('edit_video',))
            self.assertEqual(launch.call_count,1)


    def test_hermes_duplicate_submission_only_dispatches_once(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.video_operations import submit_hermes_video_request
        from unittest.mock import Mock
        service = 'minimax-h3-ref2va'; job = '2026-11-24_22-38-58-ec4f928e'
        video = base64.b64encode(b'\x00\x00\x00\x18ftypisom' + b'video').decode()
        request = dict(action='generate', prompt='remove trail', images=[], edit_video=video,
                       width=832, height=480, frames=124, steps=8, seed=45)
        with tempfile.TemporaryDirectory() as directory:
            store = HermesDelegationStore(Path(directory))
            dispatch = Mock(return_value={'id':job})
            with patch('workflow.domains.hermes_agent.video_operations.HermesDelegationStore',return_value=store), \
                 patch('workflow.domains.hermes_agent.video_operations.call_hermes_video_service',dispatch), \
                 patch('workflow.generators.minimax_h3_ref2va.contracts.validate_video_content'):
                first=submit_hermes_video_request('ref2va_request_123',service,request)
                second=submit_hermes_video_request('ref2va_request_123',service,request)
                self.assertEqual(first['job_id'],job)
                self.assertTrue(second['duplicate'])
                self.assertEqual(dispatch.call_count,1)
                with self.assertRaises(ValueError):
                    submit_hermes_video_request('ref2va_request_123',service,{**request,'seed':46})



if __name__ == '__main__':
    unittest.main()
