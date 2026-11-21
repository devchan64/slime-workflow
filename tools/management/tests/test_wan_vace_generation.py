"""VACE 입력 모드·서비스 계약·UI 복원·전문가 경계 검사."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.wan_vace.contracts import validate_vace_request, locate_expert_switch, VACE_DEFAULT_SETTINGS
from tools.management.common.management_gateway import resolve_management_command


class VaceVideoContractTests(unittest.TestCase):
    def test_mode_guides_keep_api_values_and_show_pose_requirements(self):
        from generators.wan_vace.page.interface import VACE_INPUT_CHOICES, describe_vace_mode
        self.assertEqual({current_mode for _,current_mode in VACE_INPUT_CHOICES}, {'pose','reference','first_frame','text','video_edit','video_condition'})
        current_pose_guide = describe_vace_mode('pose')[0]
        for current_required_phrase in ('DWPose', '50스텝', 'CFG 5', 'shift 12', '자동으로 바뀌지 않습니다'):
            self.assertIn(current_required_phrase, current_pose_guide)
        self.assertIn('이미지나 영상은 사용하지 않습니다', describe_vace_mode('text')[0])

    def setUp(self):
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (832,480), 'white').save(current_image_buffer, format='PNG')
        self.current_image_text = base64.b64encode(current_image_buffer.getvalue()).decode()
        self.current_request_record = dict(action='generate',mode='reference',prompt='The character walks.',negative_prompt='',images=[self.current_image_text],width=832,height=480,**{current_field_name:current_field_value for current_field_name,current_field_value in VACE_DEFAULT_SETTINGS.items() if current_field_name!='mode'})

    def test_modes_enforce_image_count_and_gateway(self):
        for current_input_mode in ('reference','first_frame','text'):
            current_request_record = {**self.current_request_record,'mode':current_input_mode,'images':[] if current_input_mode=='text' else [self.current_image_text]}
            self.assertEqual(validate_vace_request(current_request_record)['tag'],'wan22-vace')
            self.assertEqual(resolve_management_command('wan22-vace','generate',current_request_record),('POST','/wan22-vace/jobs'))
            for current_image_values in ([[self.current_image_text]] if current_input_mode=='text' else [[],[self.current_image_text]*2]):
                with self.assertRaises(ValueError):validate_vace_request({**current_request_record,'images':current_image_values})

    def test_invalid_inputs_fail_before_queue(self):
        for current_field_name,current_field_value in [('frames',6),('steps',True),('seed',-1),('flow_shift',float('nan')),('reference_strength',0),('mode','pose'),('width',512),('model','other'),('prompt',' ')]:
            with self.subTest(field=current_field_name),self.assertRaises(ValueError):
                validate_vace_request({**self.current_request_record,current_field_name:current_field_value})

    def test_seed_generator_boundaries(self):
        from generators.wan_vace.contracts import VACE_MAXIMUM_SEED_VALUE
        for current_seed_value in (0,VACE_MAXIMUM_SEED_VALUE):
            self.assertEqual(validate_vace_request({**self.current_request_record,'seed':current_seed_value})['seed'],current_seed_value)
        with self.assertRaisesRegex(ValueError,'seed'):
            validate_vace_request({**self.current_request_record,'seed':VACE_MAXIMUM_SEED_VALUE+1})

    def test_retired_q4_jobs_cannot_resume(self):
        from tools.management.domains.wan_vace.generation import VaceVideoGenerationManager
        current_service_instance = VaceVideoGenerationManager()
        with patch('tools.management.domains.wan_vace.generation.validate_vace_assets') as current_assets_mock:
            with self.assertRaisesRegex(ValueError, 'Q4'):
                current_service_instance.validate_generation_runtime({'tag': 'wan22-vace'})
            current_assets_mock.assert_not_called()
            current_validated_record = validate_vace_request(self.current_request_record)
            self.assertEqual(current_validated_record['model_profile'], 'official-bf16-resident-v1')
            current_service_instance.validate_generation_runtime(current_validated_record)
            current_assets_mock.assert_called_once()

    def test_bf16_memory_profile_excludes_retired_q4_observations(self):
        import json
        from tools.management.common.gpu_memory_history import identify_execution_command, estimate_required_memory
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_path = Path(current_temp_root)
            (current_job_path / 'request.json').write_text(json.dumps({'frames': 21, 'model_profile': 'official-bf16-resident-v1'}))
            current_profile_name = identify_execution_command(['python', 'generators/wan_vace/worker.py'], current_job_path, 'gtt')
            self.assertEqual(current_profile_name, 'wan-vace-bf16:frames=21:offload=none-v1:domain=gtt')
            with patch('tools.management.common.gpu_memory_history.load_recent_observations', return_value=[]):
                self.assertEqual(estimate_required_memory('image', 6144, current_profile_name)['required_memory_mib'], 81920)
            (current_job_path / 'request.json').write_text(json.dumps({'frames': 21}))
            with self.assertRaisesRegex(ValueError, 'Q4'):
                identify_execution_command(['python', 'generators/wan_vace/worker.py'], current_job_path, 'gtt')

    def test_boundary_is_sigma_not_step_ratio(self):
        self.assertEqual(locate_expert_switch([1,.95,.875,.8,.4,0]),3)
        self.assertEqual(locate_expert_switch([1,.1,0]),1)
        for current_sigma_values in ([1,.9,0],[.8,.4,0]):
            with self.assertRaises(ValueError):locate_expert_switch(current_sigma_values)

    def test_gui_payload_supports_pil_and_does_not_leak_tag(self):
        from tools.management.generators.wan_vace.page.inputs import build_vace_payload
        current_reference_image = Image.new('RGBA',(400,600),(255,0,0,128))
        current_common_values = ['walk','',21,42,50,12,5,1]
        current_request_record = build_vace_payload('reference',current_reference_image,*current_common_values)
        self.assertNotIn('tag',current_request_record)
        self.assertEqual(len(current_request_record['images']),1)
        self.assertEqual(build_vace_payload('text',None,*current_common_values)['images'],[])
        with self.assertRaises(ValueError):build_vace_payload('text',current_reference_image,*current_common_values)
        with self.assertRaises(ValueError):build_vace_payload('first_frame',None,*current_common_values)
        self.assertEqual(current_reference_image.size,(400,600))

    def test_restore_inputs_and_model_readiness(self):
        from tools.management.ui.gradio.wan_vace_app import restore_vace_inputs,check_vace_readiness
        with self.assertRaises(ValueError):restore_vace_inputs({'id':'../outside','request':{}})
        self.assertFalse(check_vace_readiness(False,'reference','image','walk'))
        self.assertFalse(check_vace_readiness(True,'text','image','walk'))
        self.assertTrue(check_vace_readiness(True,'text',None,'walk'))
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_root=Path(current_temp_root)/'job';current_job_root.mkdir()
            Image.new('RGB',(832,480)).save(current_job_root/'reference-1.png')
            with patch('tools.management.ui.gradio.wan_vace_app.VACE_JOB_STORAGE',Path(current_temp_root)):
                current_restored_values=restore_vace_inputs({'id':'job','request':{**self.current_request_record,'references':['reference-1.png']}})
            self.assertEqual(current_restored_values[0],'reference')
            self.assertEqual(current_restored_values[-1],'job')

    def test_pose_video_browser_copy_preserves_frames(self):
        import cv2
        import numpy as np
        from generators.wan_vace.page.video_preview import prepare_vace_browser_video
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_source_path = Path(current_temp_root)/'source.mp4'
            current_writer_object = cv2.VideoWriter(str(current_source_path), cv2.VideoWriter_fourcc(*'mp4v'), 16, (64, 64))
            self.assertTrue(current_writer_object.isOpened())
            for current_frame_index in range(5):
                current_writer_object.write(np.full((64, 64, 3), current_frame_index * 40, dtype=np.uint8))
            current_writer_object.release()
            with patch('generators.wan_vace.page.video_preview.VACE_WORKSPACE_ROOT', Path(current_temp_root)):
                current_result_path = prepare_vace_browser_video(current_source_path)
                self.assertEqual(current_result_path, prepare_vace_browser_video(current_source_path))
            current_source_video = cv2.VideoCapture(str(current_source_path))
            current_result_video = cv2.VideoCapture(current_result_path)
            self.assertAlmostEqual(current_result_video.get(cv2.CAP_PROP_FPS), 16)
            for current_frame_index in range(5):
                current_source_ok,current_source_frame = current_source_video.read()
                current_result_ok,current_result_frame = current_result_video.read()
                self.assertTrue(current_source_ok and current_result_ok)
                np.testing.assert_array_equal(current_source_frame, current_result_frame)
            self.assertFalse(current_result_video.read()[0])
            current_source_video.release()
            current_result_video.release()

    def test_initial_history_failure_is_actionable_and_not_queued(self):
        from tools.management.ui.gradio.wan_vace_app import build_vace_interface
        def execute_test_command(current_command_name,current_payload_record):
            if current_command_name == 'history':
                raise RuntimeError('게이트웨이 연결 실패')
            return {'ready': False, 'message': '검사', 'items': []}
        current_interface_blocks = build_vace_interface('http://localhost:8770', execute_test_command)
        current_history_binding = next(current_binding for current_binding in current_interface_blocks.fns.values()
                                       if current_binding.fn and current_binding.fn.__name__ == 'load_vace_history_initially')
        self.assertFalse(current_history_binding.queue)
        self.assertEqual(current_history_binding.show_progress, 'hidden')
        self.assertIn('게이트웨이 연결 실패', current_history_binding.fn()[1])
        self.assertIn('새로고침', current_history_binding.fn()[1])
        current_interface_blocks.close()

    def test_gradio_builds_without_generation_and_has_history_actions(self):
        from tools.management.ui.gradio.wan_vace_app import build_vace_interface
        def reject_generation_command(current_command_name,current_payload_record):
            if current_command_name=='generate':raise AssertionError('검사 중 실제 생성 금지')
            return {'ready':False,'message':'격리 검사','items':[]}
        current_interface_blocks=build_vace_interface('http://localhost:8770',reject_generation_command)
        current_component_labels=[current_component_record.get('props',{}).get('value') for current_component_record in current_interface_blocks.config['components']]
        for expected_action_label in ('확인 후 대기열에 추가','추가하지 않기','선택 이력 삭제'):
            self.assertIn(expected_action_label,current_component_labels)
        current_interface_blocks.close()

    def test_service_paths_and_required_commands(self):
        from tools.management.domains.wan_vace.generation import VaceVideoGenerationManager
        from tools.management.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_service_instance=VaceVideoGenerationManager()
        self.assertEqual(current_service_instance.route_prefix_value,'/wan22-vace')
        self.assertEqual(current_service_instance.select_generation_runner(),'generators/wan_vace/worker.py')
        self.assertTrue({'history-delete','history-reset','prioritize','resume','cancel'} <= set(MANAGEMENT_SERVICE_COMMANDS['wan22-vace']))
