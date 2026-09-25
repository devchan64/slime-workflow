"""캐릭터 애니메이션 입력·공용 기록·취소·프레임 실행 계약 검증."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from tools.review import character_animation_assets as assets
from tools.review import character_animation_jobs as jobs
from tools.review import management_gateway as gateway
from tools.review.character_animation import CharacterAnimationManager

class CharacterAnimationTests(unittest.TestCase):
    def make_selection_record(self,**selection_override_values):
        return dict(motion='standing-v3',character='character-default',source='openpose',directions=['down_left'],**selection_override_values)

    def test_registered_sources_all_frames_integrity(self):
        for motion_identifier_value,expected_frame_count in [('standing-v3',16),('walking-v8',32),('stretch-v1',120)]:
            for source_kind_value in ('openpose','anny'):
                selection_request_record=self.make_selection_record()
                selection_request_record.update(motion=motion_identifier_value,source=source_kind_value,directions=list(assets.SUPPORTED_DIRECTION_NAMES))
                generation_request_record=assets.prepare_animation_request(selection_request_record)
                self.assertEqual(len(generation_request_record['frames']),expected_frame_count*4)
                self.assertEqual(generation_request_record['fps'],4)
                self.assertEqual(generation_request_record['frames'][-1]['frame'],expected_frame_count)
                self.assertLess(generation_request_record['prompt_words'],100)

    def test_reject_prompt_override_and_bad_selection(self):
        for invalid_selection_values in ({'prompt':'override'},{'motion':'../bad'},{'source':[]},{'directions':[]},{'directions':['down_left','down_left']},{'directions':['bad']},{'character':{}}):
            with self.assertRaises((ValueError,TypeError)):
                assets.prepare_animation_request({**self.make_selection_record(),**invalid_selection_values})

    def test_hash_mismatch_fails_before_launch(self):
        with patch.object(assets,'hash_asset_file',return_value='invalid'),self.assertRaisesRegex(ValueError,'무결성'):
            assets.prepare_animation_request(self.make_selection_record())

    def test_cli_and_http_envelope_have_same_selection(self):
        selection_request_record=self.make_selection_record()
        with patch.object(gateway,'execute_management_command',return_value={'id':'test'}) as command_execute_mock,contextlib.redirect_stdout(io.StringIO()):
            gateway.execute_gateway_cli(['command','character-animation','generate','--motion','standing-v3','--character','character-default','--directions','down_left','--detach'])
        self.assertEqual(command_execute_mock.call_args.args[:3],('character-animation','generate',selection_request_record))
        command_request_bytes=json.dumps({'service':'character-animation','command':'generate','payload':selection_request_record}).encode()
        http_request_handler=SimpleNamespace(command='POST',path='/management/command',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(command_request_bytes))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(command_request_bytes),wfile=io.BytesIO(),send_response=MagicMock(),send_header=MagicMock(),end_headers=MagicMock())
        with patch('tools.review.character_animation.execute_animation_command',return_value={'id':'test'}) as service_execute_mock:
            gateway.ManagementCommandGateway({'character-animation':CharacterAnimationManager().handle}).handle(http_request_handler)
        service_execute_mock.assert_called_once_with('generate',selection_request_record)

    def test_history_reset_retains_results_and_cancel_is_shared(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            with patch.object(jobs,'GENERATION_ROOT_DIRECTORY',temporary_root_path),patch.object(jobs,'GENERATION_HISTORY_DIRECTORY',temporary_root_path/'history'),patch.object(jobs,'GENERATION_LOCK_PATH',temporary_root_path/'generation.lock'),patch.object(jobs.subprocess,'Popen'):
                generation_start_record=jobs.start_animation_generation(self.make_selection_record())
                generation_job_identifier=generation_start_record['id']
                self.assertTrue(jobs.execute_animation_command('active',{})['running'])
                self.assertEqual(jobs.execute_animation_command('history',{})['records'][0]['id'],generation_job_identifier)
                jobs.execute_animation_command('cancel',{'id':generation_job_identifier})
                self.assertTrue((jobs.resolve_generation_directory(generation_job_identifier)/'cancel.request').exists())
                jobs.execute_animation_command('history-reset',{})
                jobs.write_record_atomically(jobs.resolve_generation_directory(generation_job_identifier)/'status.json',{'status':'completed'})
                self.assertEqual(jobs.execute_animation_command('history',{}),{'records':[]})
                self.assertTrue((jobs.resolve_generation_directory(generation_job_identifier)/'request.json').exists())

    def test_concurrent_generation_rejected(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            with patch.object(jobs,'GENERATION_ROOT_DIRECTORY',temporary_root_path),patch.object(jobs,'GENERATION_HISTORY_DIRECTORY',temporary_root_path/'history'),patch.object(jobs,'GENERATION_LOCK_PATH',temporary_root_path/'generation.lock'):
                with jobs.GENERATION_LOCK_PATH.open('a') as generation_lock_handle:
                    fcntl.flock(generation_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with self.assertRaisesRegex(ValueError,'이미 진행'):
                        jobs.start_animation_generation(self.make_selection_record())

    def test_missing_result_is_failed_and_manual_reset_not_restored(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            generation_job_identifier='2026-09-25_12-00-00-12345678'
            with patch.object(jobs,'GENERATION_ROOT_DIRECTORY',temporary_root_path),patch.object(jobs,'GENERATION_HISTORY_DIRECTORY',temporary_root_path/'history'),patch.object(jobs.subprocess,'Popen',return_value=SimpleNamespace(poll=lambda:0,returncode=0)),patch.object(jobs.os,'close'),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                generation_job_path=jobs.resolve_generation_directory(generation_job_identifier);generation_job_path.mkdir(parents=True)
                jobs.supervise_animation_generation(generation_job_identifier,99)
                self.assertEqual(json.loads((generation_job_path/'status.json').read_text())['status'],'failed')
                self.assertFalse(jobs.GENERATION_HISTORY_DIRECTORY.exists())


    def test_worker_normalizes_references_and_selects_adapters(self):
        from generators.animation.run_character_animation import generate_character_frame
        from PIL import Image
        for source_kind_value in ('openpose','anny'):
            generation_request_record=assets.prepare_animation_request({**self.make_selection_record(),'source':source_kind_value})
            with tempfile.TemporaryDirectory() as temporary_root_name:
                generation_job_path=Path(temporary_root_name)
                (generation_job_path/'request.json').write_text(json.dumps(generation_request_record))
                pose_execute_mock=MagicMock()
                with patch.dict(sys.modules,{'qwen_pose':SimpleNamespace(execute_pose_generation=pose_execute_mock)}):
                    generate_character_frame(generation_job_path,0)
                execution_keyword_values=pose_execute_mock.call_args.kwargs
                self.assertEqual(execution_keyword_values['enable_anypose_adapter'],source_kind_value=='anny')
                self.assertEqual(execution_keyword_values['enable_standalone_lightning_adapter'],source_kind_value=='openpose')
                for reference_path_field in ('character_image_path','pose_reference_path'):
                    with Image.open(execution_keyword_values[reference_path_field]) as image_reference_value:
                        self.assertEqual(image_reference_value.size,(512,512))
                        self.assertEqual(image_reference_value.mode,'RGB')

    def test_worker_batch_preserves_every_frame_and_fps(self):
        from generators.animation import run_character_animation as worker
        with tempfile.TemporaryDirectory() as temporary_root_name:
            generation_job_path=Path(temporary_root_name)
            generation_request_record=assets.prepare_animation_request(self.make_selection_record())
            (generation_job_path/'request.json').write_text(json.dumps(generation_request_record))
            def complete_mock_frame(command_argument_values,check):
                current_frame_index=int(command_argument_values[-1])
                result_image_path=generation_job_path/'down_left'/f'frame-{current_frame_index+1:04d}'/'result.png'
                result_image_path.parent.mkdir(parents=True);result_image_path.write_bytes(b'mocked')
            with patch.object(worker,'WORKFLOW_ROOT_DIRECTORY',generation_job_path),patch.object(worker.subprocess,'run',side_effect=complete_mock_frame) as subprocess_run_mock:
                worker.generate_character_animation(generation_job_path)
            result_record_value=json.loads((generation_job_path/'result.json').read_text())
            self.assertEqual(subprocess_run_mock.call_count,16)
            self.assertEqual(result_record_value['fps'],4)
            self.assertEqual(len(result_record_value['frames']['down_left']),16)

if __name__=='__main__':unittest.main()
