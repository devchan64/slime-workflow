"""Qwen 2511 Gradio 입력·이력 복원 계약을 검증한다."""
import unittest
import inspect
import io
import hashlib
from pathlib import Path
import tempfile
import gradio as gr
from PIL import Image

from tools.review.ui.gradio import qwen_2511_app


class Qwen2511GradioTests(unittest.TestCase):
    def test_vnccs_restore_rejects_unsupported_steps_before_loading(self):
        from unittest.mock import patch
        current_interface_blocks = qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, pose_transfer_enabled=True)
        current_restore_function = next(current_function.fn for current_function in current_interface_blocks.fns.values() if current_function.fn and current_function.fn.__name__ == 'restore_selected_inputs')
        current_restore_callback = inspect.getclosurevars(current_restore_function).nonlocals['restore_input_callback']
        with patch.object(qwen_2511_app, 'restore_reference_inputs') as current_reference_loader:
            for current_invalid_steps in (30, None, True, 25.0, '40'):
                with self.subTest(steps=current_invalid_steps), self.assertRaisesRegex(ValueError, 'VNCCS 스텝'):
                    current_restore_callback({'request': {'vnccs': {}, 'steps': current_invalid_steps}})
            current_reference_loader.assert_not_called()

    def test_expression_requires_at_least_one_reference(self):
        self.assertFalse(qwen_2511_app.check_expression_reference_readiness(None,None,None))
        for current_slot_number in range(3):
            current_reference_values=[None]*3
            current_reference_values[current_slot_number]=Image.new('RGB',(8,8))
            self.assertTrue(qwen_2511_app.check_expression_reference_readiness(*current_reference_values))
        current_interface_blocks=qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:8770',expression_mode_enabled=True)
        current_generate_button=next(current_component for current_component in current_interface_blocks.blocks.values() if isinstance(current_component,gr.Button) and current_component.value=='이미지 생성 시작')
        self.assertFalse(current_generate_button.interactive)
        current_readiness_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='refresh_generation_readiness')
        self.assertIs(inspect.getclosurevars(current_readiness_callback).nonlocals['generation_readiness_callback'],qwen_2511_app.check_expression_reference_readiness)

    def test_expression_restore_rejects_invalid_preset_without_mutation(self):
        from copy import deepcopy
        current_interface_blocks=qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:8770',expression_mode_enabled=True)
        current_restore_function=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='restore_selected_inputs')
        current_restore_callback=inspect.getclosurevars(current_restore_function).nonlocals['restore_input_callback']
        current_request_record={'prompt':'Saved prompt.','tag':'saved','width':512,'height':512,'steps':30,'seed':42}
        for current_expression_value in (None,[],{}, {'id':'removed-preset'},{'id':[]},{'id':1}):
            current_history_record={'request':{**current_request_record,'expression':current_expression_value}}
            current_original_record=deepcopy(current_history_record)
            with self.assertRaisesRegex(ValueError,'표정'):
                current_restore_callback(current_history_record)
            self.assertEqual(current_history_record,current_original_record)
        with self.assertRaisesRegex(ValueError,'표정'):
            current_restore_callback({'request':current_request_record})

    def test_circular_gui_validates_options_before_dispatch(self):
        from unittest.mock import patch
        current_interface_blocks=qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:8770',qwen21_mode_enabled=True,circular_mode_enabled=True)
        current_start_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='execute_confirmed_generation' and inspect.getclosurevars(current_function_value.fn).nonlocals['generation_callback_value'].__name__=='start_reference_generation')
        current_input_values=[None]*10+[512,512,40,42,12,True,True,False]
        with patch.object(qwen_2511_app,'execute_management_command',return_value={'id':'mock-id','status':'queued'}) as current_gateway_mock:
            list(current_start_callback({'inputs':('','',*current_input_values),'consumed':False}))
            current_request_record=current_gateway_mock.call_args.args[2]
            self.assertEqual(current_request_record['prompt'],'')
            self.assertTrue(current_request_record['pattern_view'])
            current_gateway_mock.reset_mock()
            with self.assertRaises(gr.Error):
                list(current_start_callback({'inputs':('word '*95,'',*current_input_values),'consumed':False}))
            current_gateway_mock.assert_not_called()
        self.assertFalse(qwen_2511_app.check_circular_prompt_readiness('',False,False))
        self.assertTrue(qwen_2511_app.check_circular_prompt_readiness('',True,True))
        self.assertFalse(qwen_2511_app.check_circular_prompt_readiness('word '*95,True,True))

    def test_circular_history_restores_saved_options_and_reference_order(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_workspace_root = Path(current_temp_directory)
            current_generation_identifier = '2026-10-16_00-00-00-12345678'
            current_job_directory = current_workspace_root / '.tmp/test/qwen-image-21-circular' / current_generation_identifier
            current_job_directory.mkdir(parents=True)
            current_snapshot_records = []
            for current_slot_number, current_color_name in enumerate(('red', 'blue'), 1):
                current_reference_path = current_job_directory / f'reference-{current_slot_number}.png'
                Image.new('RGB', (16, 16), current_color_name).save(current_reference_path)
                current_snapshot_records.append({'path': current_reference_path.name, 'sha256': hashlib.sha256(current_reference_path.read_bytes()).hexdigest()})
            with patch.object(qwen_2511_app, 'WORKFLOW_ROOT_DIRECTORY', current_workspace_root), patch.object(qwen_2511_app, 'execute_management_command') as current_gateway_mock:
                current_interface_blocks = qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, circular_mode_enabled=True)
                current_restore_function = next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__ == 'restore_selected_inputs')
                current_restore_callback = inspect.getclosurevars(current_restore_function.fn).nonlocals['restore_input_callback']
                for current_option_enabled in (True, False):
                    current_saved_record = {'id': current_generation_identifier, 'request': {
                        'prompt': 'Saved final prompt with additions.', 'user_prompt': '',
                        'tag': '순환 복원 검증', 'width': 768, 'height': 512, 'steps': 30, 'seed': 0,
                        'circular_vae': {'boundary_radius': 24, 'baseline_decode': current_option_enabled},
                        'soft_shading': current_option_enabled, 'pattern_view': current_option_enabled,
                        'references': [current_snapshot_record['path'] for current_snapshot_record in current_snapshot_records],
                        'reference_snapshots': current_snapshot_records}}
                    current_restored_values = current_restore_callback(current_saved_record)
                    self.assertEqual(current_restored_values[:6], ('', '순환 복원 검증', 768, 512, 30, 0))
                    self.assertEqual(current_restored_values[6].getpixel((0, 0)), (255, 0, 0))
                    self.assertEqual(current_restored_values[7].getpixel((0, 0)), (0, 0, 255))
                    self.assertTrue(all(current_reference_image is None for current_reference_image in current_restored_values[8:16]))
                    self.assertEqual(current_restored_values[-4:], (24, current_option_enabled, current_option_enabled, current_option_enabled))
                    self.assertEqual(len(current_restored_values), len(current_restore_function.outputs) - 1)
                current_gateway_mock.assert_not_called()

    def test_plain_prompt_readiness_matches_final_word_limit(self):
        self.assertFalse(qwen_2511_app.check_plain_prompt_readiness('  ',False,False))
        self.assertTrue(qwen_2511_app.check_plain_prompt_readiness('figure',False,False))
        self.assertTrue(qwen_2511_app.check_plain_prompt_readiness('',True,False))
        self.assertTrue(qwen_2511_app.check_plain_prompt_readiness('word '*99,False,False))
        self.assertFalse(qwen_2511_app.check_plain_prompt_readiness('word '*100,False,False))
        self.assertFalse(qwen_2511_app.check_plain_prompt_readiness('word '*99,False,True))
        current_interface_blocks=qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:8770',qwen21_mode_enabled=True)
        current_generate_button=next(current_component for current_component in current_interface_blocks.blocks.values() if isinstance(current_component,gr.Button) and current_component.value=='이미지 생성 시작')
        self.assertFalse(current_generate_button.interactive)

    def test_restore_rejects_cross_job_reference_links(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_storage_directory = Path(current_temporary_directory)
            current_generation_identifier = '2026-10-15_13-00-00-1234abcd'
            current_selected_directory = current_storage_directory/current_generation_identifier
            current_selected_directory.mkdir()
            current_other_directory = current_storage_directory/'other-job'
            current_other_directory.mkdir()
            current_other_reference = current_other_directory/'reference-1.png'
            Image.new('RGB', (8, 8), 'red').save(current_other_reference)
            current_reference_record = {'id': current_generation_identifier, 'request': {'reference_snapshots': [
                {'path': 'reference-1.png', 'sha256': hashlib.sha256(current_other_reference.read_bytes()).hexdigest()}
            ]}}
            current_selected_reference = current_selected_directory/'reference-1.png'
            current_selected_reference.symlink_to(current_other_reference)
            with self.assertRaisesRegex(gr.Error, '선택한 작업 폴더 밖'):
                qwen_2511_app.restore_reference_inputs(current_reference_record, current_storage_directory)
            current_selected_reference.unlink()
            current_selected_directory.rmdir()
            current_selected_directory.symlink_to(current_other_directory, target_is_directory=True)
            with self.assertRaisesRegex(gr.Error, '작업 폴더는 심볼릭 링크'):
                qwen_2511_app.restore_reference_inputs(current_reference_record, current_storage_directory)
            self.assertTrue(current_other_reference.is_file())

    def test_reference_request_trims_history_tag(self):
        request_payload_value=qwen_2511_app.build_reference_request('마을 입구',' 돌온재 ',[],512,768,4,10107)
        self.assertEqual(request_payload_value['tag'],'돌온재')

    def test_restore_rejects_incomplete_reference_metadata(self):
        import gradio as gr
        current_reference_names = ['reference-1.png', 'reference-2.png']
        for current_snapshot_records in ([], None, [{'path': 'reference-1.png'}], [{'path': 'reference-2.png'}, {'path': 'reference-1.png'}], ['invalid']):
            with self.subTest(snapshots=current_snapshot_records):
                with self.assertRaises(gr.Error):
                    qwen_2511_app.restore_reference_inputs({'request': {
                        'references': current_reference_names,
                        'reference_snapshots': current_snapshot_records,
                    }})

    def test_restore_rejects_malformed_records_before_file_read(self):
        from unittest.mock import patch
        current_invalid_records=[None,[],{'request':None},{'request':[]},
            {'request':{'references':'reference-1.png'}},
            {'request':{'references':[None]}},
            {'request':{'reference_snapshots':{}}},
            {'request':{'reference_snapshots':['invalid']}},
            {'request':{'reference_snapshots':[{}]}},
            {'request':{'reference_snapshots':[{'path':'reference-1.png','sha256':123}]}},
            {'request':{'reference_snapshots':[{'path':'reference-1.png','sha256':'bad'}]}},
            {'id':[], 'request':{'reference_snapshots':[{'path':'reference-1.png','sha256':'a'*64}]}}]
        with patch.object(Path,'read_bytes') as current_read_mock:
            for current_history_record in current_invalid_records:
                with self.subTest(record=current_history_record), self.assertRaises(gr.Error):
                    qwen_2511_app.restore_reference_inputs(current_history_record)
            current_read_mock.assert_not_called()

    def test_restore_rejects_invalid_setting_types_before_file_read(self):
        from copy import deepcopy
        from unittest.mock import patch
        for current_setting_name, current_invalid_values in (
            ('prompt', (None, [], 42)), ('tag', (None, {}, True)),
            *((current_setting_name, (None, '512', True, 1.5, float('nan'))) for current_setting_name in ('width', 'height', 'steps', 'seed')),
        ):
            for current_invalid_value in current_invalid_values:
                with self.subTest(setting=current_setting_name, value=current_invalid_value):
                    current_history_record = {'request': {current_setting_name: current_invalid_value}}
                    current_original_record = deepcopy(current_history_record)
                    with patch.object(Path, 'read_bytes') as current_file_reader, self.assertRaisesRegex(gr.Error, current_setting_name):
                        qwen_2511_app.restore_reference_inputs(current_history_record)
                    current_file_reader.assert_not_called()
                    self.assertEqual(current_history_record, current_original_record)

    def test_restore_reference_inputs_uses_saved_settings_without_files(self):
        restored_input_values=qwen_2511_app.restore_reference_inputs({'request':{'prompt':'마을 입구','tag':'돌온재','width':512,'height':768,'steps':30,'seed':42}})
        self.assertEqual(restored_input_values[:6],('마을 입구','돌온재',512,768,30,42))
        self.assertIn('참조 이미지',restored_input_values[-1])

    def test_invalid_reference_reports_slot_and_actual_dimensions(self):
        with self.assertRaisesRegex(gr.Error,'참조 이미지 2: 1024×768'):
            qwen_2511_app.prepare_reference_image_bytes((None,Image.new('L',(1024,768)),None))

    def test_transparent_reference_reports_actionable_error(self):
        with self.assertRaisesRegex(gr.Error,'투명 이미지는 배경을 합성'):
            qwen_2511_app.prepare_reference_image_bytes((Image.new('RGBA',(512,512),(0,0,0,0)),))

    def test_valid_reference_preserves_pixels_and_order(self):
        reference_bytes_values=qwen_2511_app.prepare_reference_image_bytes((Image.new('RGB',(464,455),'red'),None,Image.new('RGB',(512,512),'blue')))
        self.assertEqual(len(reference_bytes_values),2)
        self.assertEqual([Image.open(io.BytesIO(current_image_bytes)).getpixel((0,0)) for current_image_bytes in reference_bytes_values],[(255,0,0),(0,0,255)])
