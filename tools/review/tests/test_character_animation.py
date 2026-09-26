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
from tools.review.domains.character_animation import character_animation_assets as assets
from tools.review.domains.character_animation import character_animation_jobs as jobs
from tools.review.common import management_gateway as gateway
from tools.review.domains.character_animation.character_animation import CharacterAnimationManager

class CharacterAnimationTests(unittest.TestCase):
    def make_selection_record(self,**selection_override_values):
        return dict(motion='standing-v8',character='character-default',source='openpose',directions=['down_left'],**selection_override_values)

    def test_catalog_skips_missing_asset_and_reports_reason(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            (temporary_root_path/'prompts').mkdir()
            for prompt_file_name in ('base.txt','front.txt','rear.txt'):
                (temporary_root_path/'prompts'/prompt_file_name).write_text('short prompt')
            (temporary_root_path/'assets/motions/available').mkdir(parents=True)
            (temporary_root_path/'assets/motions/available/manifest.yaml').write_text('frames: 8\nfps: 4\n')
            (temporary_root_path/'assets/characters/default').mkdir(parents=True)
            (temporary_root_path/'assets/characters/default/manifest.yaml').write_text('baseline_crops: {}\n')
            temporary_config_path=temporary_root_path/'character-animation.yaml'
            temporary_config_path.write_text('''schema_version: 1
prompts:
  base: prompts/base.txt
  auxiliary: prompts/front.txt
  auxiliary_rear: prompts/rear.txt
motions:
  available:
    label: 사용 가능
    root: assets/motions/available
    manifest: manifest.yaml
    openpose: openpose/{direction}/frame-{frame:04d}.png
    anny: anny/{direction}/frame-{frame:04d}.png
    target_fps: 4
  removed:
    label: 제거됨
    root: assets/motions/removed
    manifest: manifest.yaml
    openpose: openpose/{direction}/frame-{frame:04d}.png
    anny: anny/{direction}/frame-{frame:04d}.png
    target_fps: 4
characters:
  default:
    label: 기본 캐릭터
    root: assets/characters/default
    manifest: manifest.yaml
''')
            with patch.object(assets,'WORKFLOW_ROOT_DIRECTORY',temporary_root_path),patch.object(assets,'ANIMATION_CONFIG_PATH',temporary_config_path):
                catalog_record_value=assets.build_animation_catalog()
            self.assertEqual([record['id'] for record in catalog_record_value['motions']],['available'])
            self.assertEqual(catalog_record_value['characters'][0]['id'],'default')
            self.assertEqual(catalog_record_value['unavailable_assets'][0]['id'],'removed')
            self.assertIn('등록 파일을 찾을 수 없습니다',catalog_record_value['unavailable_assets'][0]['reason'])

    def test_output_resolution_validation(self):
        for selected_resolution_value in (512,768,1024,1280):
            request_record_value=assets.prepare_animation_request(self.make_selection_record(resolution=selected_resolution_value))
            self.assertEqual(request_record_value['resolution'],selected_resolution_value)
        for invalid_resolution_value in (True,'512',512.0,0,2048):
            with self.assertRaises(ValueError):
                assets.prepare_animation_request(self.make_selection_record(resolution=invalid_resolution_value))

    def test_target_fps_sampling_and_validation(self):
        for target_frame_rate, expected_frame_numbers in [(1,[1,5,9,13]),(2,list(range(1,17,2))),(3,[1,2,3,5,6,7,9,10,11,13,14,15]),(4,list(range(1,17)))]:
            request_record_value=assets.prepare_animation_request(self.make_selection_record(target_fps=target_frame_rate))
            self.assertEqual(request_record_value['selected_frame_numbers'],expected_frame_numbers)
            self.assertEqual(request_record_value['fps'],target_frame_rate)
            self.assertEqual(request_record_value['frames_per_direction']/target_frame_rate,4)
        for invalid_frame_rate in (0,5,True,'2',2.5):
            with self.assertRaises(ValueError):assets.prepare_animation_request(self.make_selection_record(target_fps=invalid_frame_rate))
        with self.assertRaises(ValueError):assets.prepare_animation_request(self.make_selection_record(target_fps=2,frame_step=2))

    def test_generation_speed_changes_sampling_not_fps(self):
        for selected_speed_value, expected_frame_numbers in [(1,list(range(1,17))),(1.5,[1,2,4,5,7,8,10,11,13,14,16]),(2,list(range(1,17,2))),(4,[1,5,9,13])]:
            request_record_value=assets.prepare_animation_request(self.make_selection_record(target_fps=4,speed=selected_speed_value))
            self.assertEqual(request_record_value['selected_frame_numbers'],expected_frame_numbers)
            self.assertEqual(request_record_value['fps'],4)
            self.assertEqual(request_record_value['speed'],selected_speed_value)
        for invalid_speed_value in (0,-1,0.5,True,'2',float('nan')):
            with self.assertRaises(ValueError):assets.prepare_animation_request(self.make_selection_record(speed=invalid_speed_value))
        with self.assertRaises(ValueError):assets.prepare_animation_request(self.make_selection_record(speed=2,frame_step=2))

    def test_registered_sources_all_frames_integrity(self):
        for motion_identifier_value,expected_frame_count in [('standing-v8',120),('walking-v10',60)]:
            for source_kind_value in ('openpose','anny'):
                selection_request_record=self.make_selection_record(resolution=512)
                selection_request_record.update(motion=motion_identifier_value,source=source_kind_value,frame_step=1,directions=list(assets.SUPPORTED_DIRECTION_NAMES))
                generation_request_record=assets.prepare_animation_request(selection_request_record)
                self.assertEqual(len(generation_request_record['frames']),expected_frame_count*4)
                self.assertEqual(generation_request_record['fps'],4)
                self.assertEqual(generation_request_record['frames'][-1]['frame'],expected_frame_count)
                self.assertLess(generation_request_record['prompt_words'],100)

    def test_frame_step_defaults_and_direction_prompts(self):
        request_record_value=assets.prepare_animation_request(self.make_selection_record())
        self.assertEqual(request_record_value['selected_frame_numbers'],list(range(1,17)))
        self.assertEqual(request_record_value['frames_per_direction'],16)
        for direction_name_value,prompt_record_value in request_record_value['direction_prompts'].items():
            self.assertIn(assets.DIRECTION_PROMPT_LABELS[direction_name_value],prompt_record_value['text'])
            self.assertLess(prompt_record_value['words'],100)
        for invalid_step_value in (0,3,True,'2'):
            with self.assertRaises(ValueError):assets.prepare_animation_request({**self.make_selection_record(),'frame_step':invalid_step_value})
        for frame_step_value in (1,2,4,8):
            self.assertEqual(assets.prepare_animation_request({**self.make_selection_record(),'frame_step':frame_step_value})['selected_frame_numbers'],list(range(1,17,frame_step_value)))

    def test_progress_separates_images_source_frames_and_inference(self):
        request_record_value=assets.prepare_animation_request({**self.make_selection_record(),'directions':['down_left','up_right'],'target_fps':2,'steps':30})
        with tempfile.TemporaryDirectory() as temporary_root_name:
            generation_job_path=Path(temporary_root_name)
            frame_log_path=generation_job_path/'down_left/frame-0003/execution.log'
            frame_log_path.parent.mkdir(parents=True)
            frame_log_path.write_text('date/qwen-pose/load model=x\ndate/qwen-pose/inference steps=30\ndate/qwen-pose/denoise step=7/30\n')
            status_record_value={'status':'running','progress':{'completed':1,'total':999}}
            result_record_value=jobs.describe_generation_progress(generation_job_path,request_record_value,status_record_value)
            self.assertEqual((result_record_value['completed'],result_record_value['total']),(1,16))
            self.assertEqual((result_record_value['direction_index'],result_record_value['direction_total'],result_record_value['frame']),(2,8,3))
            self.assertEqual((result_record_value['inference_completed'],result_record_value['inference_steps']),(7,30))
            for final_status_name in ('cancelled','failed'):
                result_record_value=jobs.describe_generation_progress(generation_job_path,request_record_value,{**status_record_value,'status':final_status_name})
                self.assertEqual(result_record_value['stage'],final_status_name)
                self.assertEqual(result_record_value['completed'],1)
                self.assertNotIn('direction',result_record_value)

    def test_remaining_time_uses_completed_images(self):
        request_record_value=assets.prepare_animation_request(self.make_selection_record(target_fps=2))
        with tempfile.TemporaryDirectory() as temporary_root_name:
            job_path=Path(temporary_root_name)
            state={'status':'running','progress':{'completed':0}}
            self.assertIsNone(jobs.estimate_generation_remaining(job_path,request_record_value,state)['remaining_seconds'])
            result_path=job_path/'down_left/frame-0001/result.json';result_path.parent.mkdir(parents=True);result_path.write_text('{"elapsed_seconds":120}')
            state['progress']['completed']=1
            estimate=jobs.estimate_generation_remaining(job_path,request_record_value,state)
            self.assertEqual(estimate['remaining_seconds'],840)
            self.assertEqual(estimate['samples'],1)
            state['status']='cancelled'
            self.assertIsNone(jobs.estimate_generation_remaining(job_path,request_record_value,state)['remaining_seconds'])

    def test_rear_auxiliary_selection_keeps_common_base(self):
        prompt_values={'base':'Common base.','auxiliary':'Front {direction}.','auxiliary_rear':'Rear head {direction}.'}
        result_values=assets.compose_direction_prompts(prompt_values)
        for direction_name,record_value in result_values.items():
            self.assertTrue(record_value['text'].startswith('Common base.\n\n'))
            self.assertEqual(record_value['auxiliary'].startswith('Rear head'),direction_name.startswith('up_'))
            self.assertEqual(record_value['words'],len(record_value['text'].split()))

    def test_inference_steps_contract(self):
        for step_count_value in (4,30):
            request_record_value=assets.prepare_animation_request({**self.make_selection_record(),'steps':step_count_value})
            self.assertEqual(request_record_value['steps'],step_count_value)
            self.assertEqual(request_record_value['lightning'],step_count_value==4)
            with patch.object(gateway,'execute_management_command',return_value={'id':'test'}) as execute_mock,contextlib.redirect_stdout(io.StringIO()):
                gateway.execute_gateway_cli(['command','character-animation','generate','--motion','standing-v8','--character','character-default','--steps',str(step_count_value),'--detach'])
            self.assertEqual(execute_mock.call_args.args[2]['steps'],step_count_value)
        for step_count_value in (0,10,True,'30'):
            with self.assertRaises(ValueError):assets.prepare_animation_request({**self.make_selection_record(),'steps':step_count_value})

    def test_original_asset_preview_bounds_and_sources(self):
        for motion_identifier_value,frame_count_value in [('standing-v8',120),('walking-v10',60)]:
            for source_kind_value in ('openpose','anny'):
                for direction_name_value in assets.SUPPORTED_DIRECTION_NAMES:
                    self.assertTrue(assets.resolve_motion_preview(motion_identifier_value,source_kind_value,direction_name_value,frame_count_value).is_file())
            for invalid_frame_number in (0,-1,frame_count_value+1,True):
                with self.assertRaises(ValueError):assets.resolve_motion_preview(motion_identifier_value,'anny','down_left',invalid_frame_number)
        with self.assertRaises(ValueError):assets.resolve_motion_preview('../bad','anny','down_left',1)

    def test_reject_prompt_override_and_bad_selection(self):
        for invalid_selection_values in ({'prompt':'override'},{'motion':'../bad'},{'source':[]},{'directions':[]},{'directions':['down_left','down_left']},{'directions':['bad']},{'character':{}}):
            with self.assertRaises((ValueError,TypeError)):
                assets.prepare_animation_request({**self.make_selection_record(),**invalid_selection_values})

    def test_hash_mismatch_fails_before_launch(self):
        with patch.object(assets,'hash_asset_file',return_value='invalid'),self.assertRaisesRegex(ValueError,'무결성'):
            assets.prepare_animation_request(self.make_selection_record(target_fps=2))

    def test_cli_and_http_envelope_have_same_selection(self):
        selection_request_record=self.make_selection_record(resolution=512)
        with patch.object(gateway,'execute_management_command',return_value={'id':'test'}) as command_execute_mock,contextlib.redirect_stdout(io.StringIO()):
            gateway.execute_gateway_cli(['command','character-animation','generate','--motion','standing-v8','--character','character-default','--directions','down_left','--detach'])
        self.assertEqual(command_execute_mock.call_args.args[:3],('character-animation','generate',selection_request_record))
        command_request_bytes=json.dumps({'service':'character-animation','command':'generate','payload':selection_request_record}).encode()
        http_request_handler=SimpleNamespace(command='POST',path='/management/command',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(command_request_bytes))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(command_request_bytes),wfile=io.BytesIO(),send_response=MagicMock(),send_header=MagicMock(),end_headers=MagicMock())
        with patch('tools.review.domains.character_animation.character_animation.execute_animation_command',return_value={'id':'test'}) as service_execute_mock:
            gateway.ManagementCommandGateway({'character-animation':CharacterAnimationManager().handle}).handle(http_request_handler)
        service_execute_mock.assert_called_once_with('generate',selection_request_record)

    def test_retired_page_returns_gone(self):
        response_status_values=[]
        current_http_handler=SimpleNamespace(command='GET',path='/character-animation/',headers={},server=SimpleNamespace(server_port=8770),wfile=io.BytesIO(),send_response=response_status_values.append,send_header=lambda *current_header_values:None,end_headers=lambda:None)
        self.assertTrue(CharacterAnimationManager().handle(current_http_handler))
        self.assertEqual(response_status_values,[410])
        self.assertIn('이전 관리 화면은 폐기되었습니다.',json.loads(current_http_handler.wfile.getvalue())['error'])

    def test_history_reset_retains_results_and_cancel_is_shared(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            with patch.object(jobs,'GENERATION_ROOT_DIRECTORY',temporary_root_path),patch.object(jobs,'GENERATION_HISTORY_DIRECTORY',temporary_root_path/'history'),patch.object(jobs,'GENERATION_LOCK_PATH',temporary_root_path/'generation.lock'),patch.object(jobs.subprocess,'Popen'):
                generation_start_record=jobs.start_animation_generation(self.make_selection_record(target_fps=2))
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
                        jobs.start_animation_generation(self.make_selection_record(target_fps=2))

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
        for source_kind_value,selected_step_count in [('openpose',4),('openpose',30),('anny',4),('anny',30)]:
            generation_request_record=assets.prepare_animation_request({**self.make_selection_record(),'source':source_kind_value,'steps':selected_step_count,'resolution':1280})
            with tempfile.TemporaryDirectory() as temporary_root_name:
                generation_job_path=Path(temporary_root_name)
                (generation_job_path/'request.json').write_text(json.dumps(generation_request_record))
                pose_execute_mock=MagicMock()
                with patch.dict(sys.modules,{'qwen_pose':SimpleNamespace(execute_pose_generation=pose_execute_mock)}):
                    generate_character_frame(generation_job_path,0)
                execution_keyword_values=pose_execute_mock.call_args.kwargs
                self.assertEqual(execution_keyword_values['selected_output_width'],1280)
                self.assertEqual(execution_keyword_values['selected_output_height'],1280)
                self.assertEqual(execution_keyword_values['enable_anypose_adapter'],source_kind_value=='anny')
                self.assertEqual(execution_keyword_values['enable_standalone_lightning_adapter'],source_kind_value=='openpose' and selected_step_count==4)
                self.assertEqual(execution_keyword_values['enable_lightning_adapter'],selected_step_count==4)
                self.assertEqual(execution_keyword_values['selected_inference_steps'],selected_step_count)
                for reference_path_field in ('character_image_path','pose_reference_path'):
                    with Image.open(execution_keyword_values[reference_path_field]) as image_reference_value:
                        self.assertEqual(image_reference_value.size,(512,512))
                        self.assertEqual(image_reference_value.mode,'RGB')

    def test_worker_batch_preserves_every_frame_and_fps(self):
        from generators.animation import run_character_animation as worker
        with tempfile.TemporaryDirectory() as temporary_root_name:
            generation_job_path=Path(temporary_root_name)
            generation_request_record=assets.prepare_animation_request(self.make_selection_record(target_fps=2))
            (generation_job_path/'request.json').write_text(json.dumps(generation_request_record))
            def complete_mock_frame(command_argument_values,check):
                current_frame_index=int(command_argument_values[-1])
                source_frame_number=generation_request_record['frames'][current_frame_index]['frame']
                result_image_path=generation_job_path/'down_left'/f'frame-{source_frame_number:04d}'/'result.png'
                result_image_path.parent.mkdir(parents=True);result_image_path.write_bytes(b'mocked')
            with patch.object(worker,'WORKFLOW_ROOT_DIRECTORY',generation_job_path),patch.object(worker.subprocess,'run',side_effect=complete_mock_frame) as subprocess_run_mock:
                worker.generate_character_animation(generation_job_path)
            result_record_value=json.loads((generation_job_path/'result.json').read_text())
            self.assertEqual(subprocess_run_mock.call_count,8)
            self.assertEqual(result_record_value['fps'],2)
            self.assertEqual(len(result_record_value['frames']['down_left']),8)

if __name__=='__main__':unittest.main()
