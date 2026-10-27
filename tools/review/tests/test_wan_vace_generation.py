"""VACE 입력 모드·서비스 계약·UI 복원·전문가 경계 검사."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.wan_vace.contracts import validate_vace_request, locate_expert_switch, VACE_DEFAULT_SETTINGS
from tools.review.common.management_gateway import resolve_management_command


class VaceVideoContractTests(unittest.TestCase):
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

    def test_boundary_is_sigma_not_step_ratio(self):
        self.assertEqual(locate_expert_switch([1,.95,.875,.8,.4,0]),3)
        self.assertEqual(locate_expert_switch([1,.1,0]),1)
        for current_sigma_values in ([1,.9,0],[.8,.4,0]):
            with self.assertRaises(ValueError):locate_expert_switch(current_sigma_values)

    def test_gui_payload_supports_pil_and_does_not_leak_tag(self):
        from tools.review.ui.gradio.wan_vace_app import build_vace_payload
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
        from tools.review.ui.gradio.wan_vace_app import restore_vace_inputs,check_vace_readiness
        with self.assertRaises(ValueError):restore_vace_inputs({'id':'../outside','request':{}})
        self.assertFalse(check_vace_readiness(False,'reference','image','walk'))
        self.assertFalse(check_vace_readiness(True,'text','image','walk'))
        self.assertTrue(check_vace_readiness(True,'text',None,'walk'))
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_root=Path(current_temp_root)/'job';current_job_root.mkdir()
            Image.new('RGB',(832,480)).save(current_job_root/'reference-1.png')
            with patch('tools.review.ui.gradio.wan_vace_app.VACE_JOB_STORAGE',Path(current_temp_root)):
                current_restored_values=restore_vace_inputs({'id':'job','request':{**self.current_request_record,'references':['reference-1.png']}})
            self.assertEqual(current_restored_values[0],'reference')
            self.assertEqual(current_restored_values[-1],'job')

    def test_gradio_builds_without_generation_and_has_history_actions(self):
        from tools.review.ui.gradio.wan_vace_app import build_vace_interface
        def reject_generation_command(current_command_name,current_payload_record):
            if current_command_name=='generate':raise AssertionError('검사 중 실제 생성 금지')
            return {'ready':False,'message':'격리 검사','items':[]}
        current_interface_blocks=build_vace_interface('http://localhost:8770',reject_generation_command)
        current_component_labels=[current_component_record.get('props',{}).get('value') for current_component_record in current_interface_blocks.config['components']]
        for expected_action_label in ('확인 후 대기열에 추가','추가하지 않기','선택 이력 삭제'):
            self.assertIn(expected_action_label,current_component_labels)
        current_interface_blocks.close()

    def test_service_paths_and_required_commands(self):
        from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_service_instance=VaceVideoGenerationManager()
        self.assertEqual(current_service_instance.route_prefix_value,'/wan22-vace')
        self.assertEqual(current_service_instance.select_generation_runner(),'generators/wan_vace/worker.py')
        self.assertTrue({'history-delete','history-reset','prioritize','resume','cancel'} <= set(MANAGEMENT_SERVICE_COMMANDS['wan22-vace']))
