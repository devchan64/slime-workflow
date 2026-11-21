"""용도별 FLUX 입력, 페이지와 이력 복원 계약."""
import base64
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
import gradio as gr
from PIL import Image
from workflow.domains.image.building_prompt import BUILDING_LAYOUT_PRESET_NAMES, BUILDING_STRUCTURE_RECORDS, load_building_layout_preset
from workflow.domains.image.flux_image_generation import FLUX_IMAGE_PROFILE_RECORDS, FluxImageGenerationManager
from workflow.domains.image.three_reference_generation import save_three_reference_inputs
from gui.ui.shared.flux_image_page import restore_flux_image_inputs
from workflow.common.management_gateway import resolve_management_command
from gui.ui.gradio.building_guide_gallery import (
    apply_selected_building_guide,
    render_building_guide_page,
    search_building_guide_catalog,
    select_building_guide_card,
)


class FluxImageGenerationTests(unittest.TestCase):
    def test_global_periodic_geometry_uses_shortest_unique_coordinates(self):
        import torch
        from diffusers.models.transformers.transformer_flux3 import Flux3PosEmbed
        from diffusers.modular_pipelines.flux3.before_denoise import _prepare_image_ids
        from generators.image.flux_global_periodic_attention import build_global_geometry, GLOBAL_PERIODIC_SHIFT_SEQUENCE
        current_entries_value=build_global_geometry(_prepare_image_ids(32,32,0.5),Flux3PosEmbed(10000,[2,2,2,2]))
        current_selection_count=torch.zeros((1024,1024),dtype=torch.int8)
        current_indices_value=torch.arange(1024)
        current_rows_value,current_columns_value=current_indices_value//32,current_indices_value%32
        for (current_y_shift,current_x_shift),current_mask_value,_ in current_entries_value:
            current_selection_count+=current_mask_value
            current_row_distance=(current_rows_value[:,None]-(current_rows_value[None,:]+current_y_shift*32)).abs()
            current_column_distance=(current_columns_value[:,None]-(current_columns_value[None,:]+current_x_shift*32)).abs()
            self.assertTrue(bool((current_row_distance[current_mask_value]<=16).all()))
            self.assertTrue(bool((current_column_distance[current_mask_value]<=16).all()))
        self.assertLessEqual(int(current_selection_count.max()),1)
        self.assertEqual(int(current_selection_count[0,31]),1)
        self.assertEqual(int(current_selection_count[0,16]),0)
        self.assertEqual(len(set(GLOBAL_PERIODIC_SHIFT_SEQUENCE)),16)

    def test_seamless_method_defaults_and_validation(self):
        current_manager_value=FluxImageGenerationManager('flux-seamless')
        current_request_record={'action':'generate','prompt':'grass','images':[],'width':512,'height':512,'steps':16,'seed':42}
        self.assertEqual(current_manager_value.validate_generation_request(current_request_record)['seamless_method'],'global-periodic-v1')
        with self.assertRaises(ValueError): current_manager_value.validate_generation_request({**current_request_record,'seamless_method':'circular-vae'})
        with self.assertRaises(ValueError): current_manager_value.validate_generation_request({**current_request_record,'seamless_method':'edge-blend'})
        with self.assertRaises(ValueError): current_manager_value.validate_generation_request({**current_request_record,'width':768})
        current_image_buffer=io.BytesIO(); Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        with self.assertRaises(ValueError): current_manager_value.validate_generation_request({**current_request_record,'images':[base64.b64encode(current_image_buffer.getvalue()).decode()]})
        with self.assertRaises(ValueError): current_manager_value.validate_generation_request({**current_request_record,'seamless_method':'unknown'})
        with self.assertRaises(ValueError): FluxImageGenerationManager('flux-image').validate_generation_request({**current_request_record,'seamless_method':'circular-vae'})

    def test_circular_preview_and_old_restore_method(self):
        from gui.ui.shared.flux_image_page import render_flux_seamless_comparison
        current_job_identifier='2026-11-16_18-54-49-49a54a00'
        current_result_path='/flux-seamless-generator/jobs/'+current_job_identifier+'/result.png'
        current_markup_value=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path,'seamless_method':'circular-vae'},'http://127.0.0.1:8770')
        self.assertIn('순환 VAE 타일',current_markup_value)
        self.assertIn('/blend-preview.png',current_markup_value)
        current_old_markup=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path},'http://127.0.0.1:8770')
        self.assertIn('경계 보간 타일',current_old_markup)
        self.assertNotIn('/blend-preview.png',current_old_markup)
        current_new_markup=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path,'seamless_method':'circular-vae-v2'},'http://127.0.0.1:8770')
        self.assertIn('순환 VAE 타일',current_new_markup)
        self.assertIn('/tiled-preview.png',current_new_markup)
        self.assertNotIn('/blend-preview.png',current_new_markup)
        self.assertNotIn('/raw-result.png',current_new_markup)
        current_global_markup=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path,'seamless_method':'global-periodic-v1'},'http://127.0.0.1:8770')
        self.assertIn('전역 주기 어텐션',current_global_markup)
        self.assertNotIn('/blend-preview.png',current_global_markup)

    def test_seamless_preview_uses_same_origin_and_checks_job(self):
        from gui.ui.shared.flux_image_page import render_flux_seamless_comparison
        current_job_identifier='2026-11-16_18-54-49-49a54a00'
        current_result_path='/flux-seamless-generator/jobs/'+current_job_identifier+'/result.png'
        current_markup_value=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path},'http://127.0.0.1:8770')
        for current_image_name in ('raw-result.png','result.png','tiled-preview.png'):
            self.assertIn('src="/flux-seamless-generator/jobs/'+current_job_identifier+'/'+current_image_name+'"',current_markup_value)
        self.assertNotIn('127.0.0.1',current_markup_value)
        self.assertIn('일치하지',render_flux_seamless_comparison(current_job_identifier,{'image':'/other/result.png'},'http://127.0.0.1:8770'))

    def test_legacy_seamless_resume_and_input_restore(self):
        import json
        from unittest.mock import patch
        from workflow.domains.image.flux_image_generation import WORKFLOW_ROOT_PATH
        current_manager_value=FluxImageGenerationManager('flux-seamless')
        current_request_value=current_manager_value.validate_generation_request({'action':'generate','prompt':'grass','images':[],'width':512,'height':512,'steps':16,'seed':42})
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_workspace_root=Path(current_directory_name).resolve()
            current_identifier_value='2026-11-16_18-54-49-49a54a00'
            current_job_path=current_workspace_root/'.tmp/test/flux-seamless-generator'/current_identifier_value
            current_job_path.mkdir(parents=True)
            current_saved_value=save_three_reference_inputs(current_job_path,current_request_value)
            for current_method_value in ('edge-blend','circular-vae','circular-vae-v2','global-periodic-v1'):
                current_saved_value['seamless_method']=current_method_value
                (current_job_path/'request.json').write_text(json.dumps(current_saved_value))
                (current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python',str(WORKFLOW_ROOT_PATH / 'generators/image/run_flux_image.py')]}))
                current_manager_value.validate_generation_resume(current_job_path)
                with patch('gui.ui.shared.flux_image_page.WORKFLOW_ROOT_DIRECTORY',current_workspace_root):
                    current_restored_value=restore_flux_image_inputs({'id':current_identifier_value,'request':current_saved_value},'flux-seamless')
                self.assertEqual(len(current_restored_value),9)
                self.assertEqual(current_restored_value[0],'grass')

    def test_transparent_reference_is_composited_on_white(self):
        current_image_buffer=io.BytesIO(); Image.new('RGBA',(16,16),(0,0,0,0)).save(current_image_buffer,format='PNG')
        current_request_record=FluxImageGenerationManager('flux-mannequin').validate_generation_request({'action':'generate','prompt':'A figure','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':768,'height':1152,'steps':16,'seed':42})
        with Image.open(io.BytesIO(base64.b64decode(current_request_record['images'][0]))) as current_image_value:
            self.assertEqual(current_image_value.convert('RGB').getpixel((0,0)),(255,255,255))
    def test_seamless_boundary_and_preview(self):
        import numpy as np
        from workflow.domains.image.flux_seamless_output import blend_opposite_tile_edges, build_repeated_tile_preview
        current_random_pixels=np.random.default_rng(42).integers(0,256,size=(64,64,3),dtype=np.uint8)
        current_result_image=blend_opposite_tile_edges(Image.fromarray(current_random_pixels))
        current_result_pixels=np.asarray(current_result_image)
        self.assertTrue(np.array_equal(current_result_pixels[0],current_result_pixels[-1]))
        self.assertTrue(np.array_equal(current_result_pixels[:,0],current_result_pixels[:,-1]))
        self.assertEqual(build_repeated_tile_preview(current_result_image).size,(192,192))

    def test_gpu_memory_identity_includes_image_settings(self):
        import json
        from workflow.common.gpu_memory_history import identify_execution_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)
            (current_job_root/'request.json').write_text(json.dumps({'action':'generate','width':768,'height':1152,'steps':16,'references':['reference-1.png','reference-2.png']}))
            current_identity_text=identify_execution_command(['python','generators/image/run_flux_image.py'],current_job_root)
            self.assertIn('768x1152:steps=16:references=2',current_identity_text)
            self.assertIn('offload=none-flux-resident-v1',current_identity_text)
    def test_profile_requests_and_pages(self):
        from workflow.common.management_asgi import build_management_blocks
        current_image_buffer=io.BytesIO(); Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        current_image_text=base64.b64encode(current_image_buffer.getvalue()).decode()
        for current_profile_name,current_profile_record in FLUX_IMAGE_PROFILE_RECORDS.items():
            with self.subTest(profile=current_profile_name):
                current_manager_value=FluxImageGenerationManager(current_profile_name)
                current_size_value=512 if current_profile_name=='flux-seamless' else 768
                current_request_record=current_manager_value.validate_generation_request({'action':'generate','prompt':'A small tree','images':[current_image_text] if current_profile_record[4] else [],'width':current_size_value,'height':current_size_value,'steps':16,'seed':42})
                self.assertEqual(current_request_record['profile'],current_profile_name)
                self.assertEqual(current_request_record['common_style']['version'],'1.5.0')
                self.assertEqual(resolve_management_command(current_profile_name,'history',{})[1],'/'+current_profile_name+'-generator/history')
                from unittest.mock import patch
                with tempfile.TemporaryDirectory() as current_directory_name:
                    current_source_path=Path(current_directory_name)/'menu.json'; current_source_path.write_text('{"pages": []}')
                    with patch.dict('os.environ',{'SLIME_MANAGEMENT_MENU_SOURCE':str(current_source_path)}):
                        current_page_blocks,_=build_management_blocks(current_profile_name+'-generator',8770,current_source_path)
                self.assertGreater(len(current_page_blocks.blocks),0)
                if current_profile_record[4]:
                    with self.assertRaises(ValueError):
                        current_manager_value.validate_generation_request({'action':'generate','prompt':'A tree','images':[],'width':768,'height':768,'steps':16,'seed':42})

    def test_restore_saved_reference_and_prompt(self):
        current_image_buffer=io.BytesIO(); Image.new('RGB',(16,16),'blue').save(current_image_buffer,format='PNG')
        current_profile_name='flux-image'; current_manager_value=FluxImageGenerationManager(current_profile_name)
        current_request_record=current_manager_value.validate_generation_request({'action':'generate','prompt':'A tree','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':768,'height':512,'steps':16,'seed':42})
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_identifier='2026-11-16_18-23-00-f1a2b3c4'; current_job_root=Path(current_directory_name)/'.tmp/test/flux-image-generator'/current_job_identifier; current_job_root.mkdir(parents=True)
            current_saved_record=save_three_reference_inputs(current_job_root,current_request_record)
            from unittest.mock import patch
            with patch('gui.ui.shared.flux_image_page.WORKFLOW_ROOT_DIRECTORY',Path(current_directory_name).resolve()):
                current_restored_values=restore_flux_image_inputs({'id':current_job_identifier,'request':current_saved_record},current_profile_name)
                self.assertEqual(current_restored_values[0],'A tree')
                self.assertEqual(current_restored_values[1].size,(16,16))
                self.assertIsNone(current_restored_values[2])
                self.assertEqual(current_restored_values[3:],(768,512,16,42,'',''))
                (current_job_root/'reference-1.png').write_bytes(b'changed')
                with self.assertRaises(Exception):
                    restore_flux_image_inputs({'id':current_job_identifier,'request':current_saved_record},current_profile_name)

    def test_character_step_range_and_history_restore(self):
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        current_manager_value=FluxImageGenerationManager('flux-character')
        current_request_value={'action':'generate','prompt':'A character','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':768,'height':512,'steps':32,'seed':42}
        current_valid_record=current_manager_value.validate_generation_request(current_request_value)
        self.assertEqual(current_valid_record['steps'],32)
        for current_step_value in (0,51,True,1.5):
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_request({**current_request_value,'steps':current_step_value})
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_identifier='2026-11-20_12-00-00-a1b2c3d4'
            current_job_root=Path(current_directory_name)/'.tmp/test/flux-character-generator'/current_job_identifier
            current_job_root.mkdir(parents=True)
            current_saved_record=save_three_reference_inputs(current_job_root,current_valid_record)
            from unittest.mock import patch
            with patch('gui.ui.shared.flux_image_page.WORKFLOW_ROOT_DIRECTORY',Path(current_directory_name)):
                current_restored_values=restore_flux_image_inputs({'id':current_job_identifier,'request':current_saved_record},'flux-character')
            self.assertEqual(current_restored_values[5],32)

    def test_character_output_size_limit_and_history_restore(self):
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        current_request_value={'action':'generate','prompt':'A character','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':2048,'height':2048,'steps':16,'seed':42}
        current_manager_value=FluxImageGenerationManager('flux-character')
        current_valid_record=current_manager_value.validate_generation_request(current_request_value)
        for current_invalid_width in (2064,2047,True):
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_request({**current_request_value,'width':current_invalid_width})
        with self.assertRaises(ValueError):
            FluxImageGenerationManager('flux-image').validate_generation_request(current_request_value)
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_identifier='2026-11-20_12-00-00-a1b2c3d4'
            current_job_root=Path(current_directory_name)/'.tmp/test/flux-character-generator'/current_job_identifier
            current_job_root.mkdir(parents=True)
            current_saved_record=save_three_reference_inputs(current_job_root,current_valid_record)
            from unittest.mock import patch
            with patch('gui.ui.shared.flux_image_page.WORKFLOW_ROOT_DIRECTORY',Path(current_directory_name)):
                current_restored_values=restore_flux_image_inputs({'id':current_job_identifier,'request':current_saved_record},'flux-character')
            self.assertEqual(current_restored_values[3:5],(2048,2048))
class FluxBuildingGuideGalleryTests(unittest.TestCase):
    def test_korean_translation_request_across_image_profiles(self):
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        current_encoded_image=base64.b64encode(current_image_buffer.getvalue()).decode()
        for current_profile_name,current_profile_record in FLUX_IMAGE_PROFILE_RECORDS.items():
            if current_profile_name=='flux-building':
                continue
            with self.subTest(profile=current_profile_name):
                current_size_value=512 if current_profile_name=='flux-seamless' else 768
                current_payload_record={'action':'generate','prompt':'A prepared guide.', 'translation_source_ko':'따뜻한 녹색 풀',
                    'images':[current_encoded_image] if current_profile_record[4] else [],'width':current_size_value,'height':current_size_value,'steps':16,'seed':42}
                current_result_record=FluxImageGenerationManager(current_profile_name).validate_generation_request(current_payload_record)
                self.assertEqual(current_result_record['translation_source_ko'],'따뜻한 녹색 풀')
                self.assertEqual(current_result_record['translation_base_prompt'],'A prepared guide.')
                self.assertNotIn('따뜻한',current_result_record['prompt'])
                self.assertEqual(current_result_record['common_style']['version'],'1.5.0')
                current_payload_record.pop('translation_source_ko')
                current_payload_record['prompt']='따뜻한 녹색 풀'
                current_auto_record=FluxImageGenerationManager(current_profile_name).validate_generation_request(current_payload_record)
                self.assertEqual(current_auto_record['translation_source_ko'],'따뜻한 녹색 풀')
                self.assertEqual(current_auto_record['translation_base_prompt'],'')

    def test_general_translation_pipeline_routes_profile_and_style(self):
        import json
        from unittest.mock import patch,MagicMock
        from generators.image import run_flux_translation_pipeline as current_pipeline_module
        for current_profile_name in ('flux-image','flux-seamless','flux-expression'):
            with self.subTest(profile=current_profile_name), tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
                current_root_path=Path(current_directory_name).resolve()
                current_job_path=current_root_path/'.tmp/test'/(current_profile_name+'-generator')/'2026-11-17_00-00-00-12345678'
                current_job_path.mkdir(parents=True)
                (current_job_path/'request.json').write_text(json.dumps({'translation_source_ko':'녹색 풀','translation_base_prompt':'A prepared guide.'},ensure_ascii=False))
                current_fake_manager=MagicMock()
                current_translation_record={'request':{'text':'녹색 풀','target_language':'en'},'status':{'status':'completed'},'result':{'text':'Green grass.','model_id':'model','revision':'rev'}}
                current_fake_manager.execute_translation_command.side_effect=lambda current_command_name,current_payload_value: {'id':'2026-11-17_00-00-00-abcdef12'} if current_command_name=='translation-submit' else current_translation_record
                with patch.object(current_pipeline_module,'WORKFLOW_ROOT_DIRECTORY',current_root_path), patch.object(current_pipeline_module,'TranslationServiceManager',return_value=current_fake_manager), patch.object(current_pipeline_module,'launch_gpu_process') as current_launch_mock:
                    current_launch_mock.return_value.wait.return_value=0
                    current_pipeline_module.execute_flux_translation_pipeline(current_job_path)
                current_saved_record=json.loads((current_job_path/'request.json').read_text())
                self.assertIn('A prepared guide. Green grass.',current_saved_record['prompt'])
                self.assertEqual(current_saved_record['translated_design'],'Green grass.')
                current_command_values=current_launch_mock.call_args.args
                self.assertEqual(current_command_values[2],'flux-expression' if current_profile_name=='flux-expression' else 'flux-image')
                self.assertEqual('common_style' in current_saved_record,current_profile_name!='flux-expression')

    def test_translated_image_history_restores_base_and_korean_without_duplication(self):
        import hashlib
        from unittest.mock import patch
        from generators.image.common_art_style import compose_common_style_prompt
        current_manager_value=FluxImageGenerationManager('flux-image')
        current_request_record=current_manager_value.validate_generation_request({'action':'generate','prompt':'A small cottage.',
            'translation_source_ko':'파란 지붕','images':[],'width':512,'height':512,'steps':16,'seed':42})
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name).resolve()
            current_identifier_value='2026-11-17_08-00-00-12345678'
            current_job_path=current_root_path/'.tmp/test/flux-image-generator'/current_identifier_value
            current_job_path.mkdir(parents=True)
            current_saved_record=save_three_reference_inputs(current_job_path,current_request_record)
            current_final_prompt,current_style_record=compose_common_style_prompt('A small cottage. Blue roof.')
            current_saved_record.update(user_prompt='A small cottage. Blue roof.',prompt=current_final_prompt,common_style=current_style_record,
                prompt_sha256=hashlib.sha256(current_final_prompt.encode()).hexdigest(),translated_design='Blue roof.')
            with patch('gui.ui.shared.flux_image_page.WORKFLOW_ROOT_DIRECTORY',current_root_path):
                current_restored_values=restore_flux_image_inputs({'id':current_identifier_value,'request':current_saved_record},'flux-image')
            self.assertEqual(current_restored_values[0],'A small cottage.')
            self.assertEqual(current_restored_values[-1],'파란 지붕')
            self.assertNotIn('Blue roof.',current_restored_values[0])

    def test_parallel_untranslated_resume_starts_only_once(self):
        import json
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            current_launch_entered=threading.Event()
            current_launch_release=threading.Event()
            current_second_started=threading.Event()
            def launch_mocked_worker(*current_arguments):
                current_launch_entered.set()
                if not current_launch_release.wait(5):raise RuntimeError('모의 실행 동기화 실패')
            def resume_second_request():
                current_second_started.set()
                return current_manager.resume_generation_job(current_job_path,current_request_record,None)
            with patch.object(current_manager,'validate_generation_resume'),patch.object(current_manager,'launch_generation_worker',side_effect=launch_mocked_worker) as current_launch_mock,ThreadPoolExecutor(max_workers=2) as current_executor:
                current_first_future=current_executor.submit(current_manager.resume_generation_job,current_job_path,current_request_record,None)
                self.assertTrue(current_launch_entered.wait(5))
                current_second_future=current_executor.submit(resume_second_request)
                self.assertTrue(current_second_started.wait(5))
                current_launch_release.set()
                self.assertEqual(current_first_future.result(timeout=5)['status'],'queued')
                with self.assertRaisesRegex(ValueError,'실패·취소·일시정지'):
                    current_second_future.result(timeout=5)
                self.assertEqual(current_launch_mock.call_count,1)

    def test_untranslated_resume_waits_for_shared_resume_lock(self):
        import fcntl
        import json
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        from workflow.common import gpu_job_queue
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            current_open_called=threading.Event()
            current_launch_called=threading.Event()
            current_original_open=gpu_job_queue.open_gpu_resume_lock
            def observe_resume_lock_open(current_directory_value):
                current_handle_value=current_original_open(current_directory_value)
                current_open_called.set()
                return current_handle_value
            with current_original_open(current_job_path) as current_held_lock:
                fcntl.flock(current_held_lock,fcntl.LOCK_EX)
                with patch.object(current_manager,'validate_generation_resume'),patch.object(gpu_job_queue,'open_gpu_resume_lock',side_effect=observe_resume_lock_open),patch.object(
                        current_manager,'launch_generation_worker',side_effect=lambda *current_values:current_launch_called.set()),ThreadPoolExecutor(max_workers=1) as current_executor:
                    current_resume_future=current_executor.submit(current_manager.resume_generation_job,current_job_path,current_request_record,None)
                    self.assertTrue(current_open_called.wait(5))
                    self.assertFalse(current_launch_called.wait(.25))
                    self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')
                    fcntl.flock(current_held_lock,fcntl.LOCK_UN)
                    self.assertEqual(current_resume_future.result(timeout=5)['status'],'queued')
                    self.assertTrue(current_launch_called.is_set())

    def test_untranslated_resume_rejects_symlinked_pipeline_lock(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            (current_job_path/'building-pipeline.lock').symlink_to(current_job_path/'outside')
            with patch.object(current_manager,'validate_generation_resume'),patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                with self.assertRaises(OSError):
                    current_manager.resume_generation_job(current_job_path,current_request_record,None)
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')

    def test_untranslated_resume_rejects_changed_request_before_launch(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'request.json').write_text(json.dumps({**current_request_record,'translation_source_ko':'변경됨'}))
            with patch.object(current_manager,'validate_generation_resume') as current_validation_mock,patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'요청이 변경'):
                    current_manager.resume_generation_job(current_job_path,current_request_record,None)
                current_validation_mock.assert_not_called()
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')

    def test_untranslated_resume_rejects_request_changed_during_validation(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            current_request_path=current_job_path/'request.json'
            current_request_path.write_text(json.dumps(current_request_record))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            def mutate_request_during_validation(current_job_directory):
                current_request_path.write_text(json.dumps({**current_request_record,'translation_source_ko':'변경됨'}))
            with patch.object(current_manager,'validate_generation_resume',side_effect=mutate_request_during_validation),patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'검증 중 변경'):
                    current_manager.resume_generation_job(current_job_path,current_request_record,None)
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')

    def test_reviewed_flux_resume_rechecks_reference_before_mock_launch(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager.job_storage_root=current_root_path
            current_job_path=current_root_path/'2026-11-20_10-00-00-abcdef12'
            current_job_path.mkdir()
            current_request_value={'profile':'flux-character','references':['reference-1.png']}
            (current_job_path/'request.json').write_text(json.dumps(current_request_value))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            current_reference_path=current_job_path/'reference-1.png'
            current_reference_path.write_bytes(b'original')
            current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
            with patch.object(current_manager,'inspect_flux_resume_availability',return_value='available'),patch('workflow.common.model_prepare_process.hold_registered_preparation_guard',return_value=contextlib.nullcontext()),patch.object(current_manager,'validate_generation_runtime'),patch.object(current_manager,'validate_generation_resume'),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                current_reference_path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'변경'):
                    current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)
                current_launch_mock.assert_not_called()
                current_reference_path.write_bytes(b'original')
                current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
                current_result_value=current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)
                self.assertEqual(current_result_value['status'],'queued')
                current_launch_mock.assert_called_once()

    def test_reviewed_flux_resume_rejects_changes_during_locked_validation(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager.job_storage_root=current_root_path
            current_job_path=current_root_path/'2026-11-20_10-00-00-abcdef12'
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'profile':'flux-character','references':['reference-1.png']}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            current_reference_path=current_job_path/'reference-1.png'
            current_reference_path.write_bytes(b'original')
            current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
            with patch.object(current_manager,'inspect_flux_resume_availability',return_value='available'),patch('workflow.common.model_prepare_process.hold_registered_preparation_guard',return_value=contextlib.nullcontext()),patch.object(current_manager,'validate_generation_runtime'),patch.object(current_manager,'validate_generation_resume',side_effect=lambda _:current_reference_path.write_bytes(b'changed')),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'검증 중 입력이 변경'):
                    current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')

    def test_reviewed_flux_resume_holds_model_guard_until_worker_launch(self):
        import json
        from unittest.mock import patch
        from workflow.common.model_prepare_process import start_registered_preparation
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager.job_storage_root=current_root_path
            current_job_path=current_root_path/'2026-11-20_10-00-00-abcdef12'
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'profile':'flux-character','references':[]}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
            def verify_preparation_guard(*current_arguments,**current_options):
                self.assertEqual(start_registered_preparation(current_root_path,'flux-image')['preparation_status'],'running')
            with patch('workflow.common.model_prepare_process.resolve_model_preparation_root',return_value=current_root_path/'model-prep'),patch.object(current_manager,'inspect_flux_resume_availability',return_value='available'),patch.object(current_manager,'validate_generation_runtime'),patch.object(current_manager,'validate_generation_resume'),patch('workflow.common.gpu_job_queue.launch_gpu_process',side_effect=verify_preparation_guard) as current_launch_mock,patch('workflow.common.model_prepare_process.subprocess.Popen') as current_prepare_mock:
                self.assertEqual(current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)['status'],'queued')
                current_launch_mock.assert_called_once()
                current_prepare_mock.assert_not_called()

    def test_reviewed_flux_resume_blocks_model_preparation(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager.job_storage_root=current_root_path
            for current_translation_value in (False,True):
                with self.subTest(untranslated=current_translation_value):
                    current_job_path=current_root_path/('2026-11-20_10-00-0'+str(int(current_translation_value))+'-abcdef12')
                    current_job_path.mkdir()
                    current_request_value={'profile':'flux-character','references':[]}
                    if current_translation_value:current_request_value['translation_source_ko']='검증'
                    (current_job_path/'request.json').write_text(json.dumps(current_request_value))
                    (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
                    current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
                    with patch.object(current_manager,'validate_generation_runtime'),patch.object(current_manager,'validate_generation_resume'),patch.object(current_manager,'inspect_flux_resume_availability',return_value='download_running'),patch.object(current_manager,'launch_generation_worker') as current_worker_mock,patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_queue_mock:
                        with self.assertRaisesRegex(ValueError,'모델 준비 충돌'):
                            current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)
                        current_worker_mock.assert_not_called()
                        current_queue_mock.assert_not_called()
                        self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')

    def test_reviewed_flux_resume_rechecks_unfinished_translation(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager.job_storage_root=current_root_path
            current_job_path=current_root_path/'2026-11-20_10-00-00-abcdef12'
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'profile':'flux-character','references':['reference-1.png'],'translation_source_ko':'검증'}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            current_reference_path=current_job_path/'reference-1.png'
            current_reference_path.write_bytes(b'original')
            current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
            with patch.object(current_manager,'inspect_flux_resume_availability',return_value='available'),patch('workflow.common.model_prepare_process.hold_registered_preparation_guard',return_value=contextlib.nullcontext()),patch.object(current_manager,'validate_generation_runtime'),patch.object(current_manager,'validate_generation_resume',side_effect=lambda _:current_reference_path.write_bytes(b'changed')),patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'검증 중 입력이 변경'):
                    current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')
            current_reference_path.write_bytes(b'original')
            current_fingerprint_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint']
            with patch.object(current_manager,'inspect_flux_resume_availability',return_value='available'),patch('workflow.common.model_prepare_process.hold_registered_preparation_guard',return_value=contextlib.nullcontext()),patch.object(current_manager,'validate_generation_runtime'),patch.object(current_manager,'validate_generation_resume'),patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                current_result_value=current_manager.resume_reviewed_generation_job(current_job_path,current_fingerprint_value)
                self.assertEqual(current_result_value['status'],'queued')
                current_launch_mock.assert_called_once()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['stage'],'translation')

    def test_flux_reviewed_resume_http_requires_exact_target_and_fingerprint(self):
        import json
        from unittest.mock import patch
        from workflow.tests.test_image_generation import ImageGenerationTests
        from workflow.common.management_gateway import resolve_management_command
        current_manager=FluxImageGenerationManager('flux-character')
        current_job_identifier='2026-11-20_10-00-00-abcdef12'
        current_request_value={'id':current_job_identifier,'expected_resume_fingerprint':'a'*64}
        self.assertEqual(resolve_management_command('flux-character','resume-reviewed',current_request_value)[:2],('POST','/flux-character-generator/resume/reviewed'))
        for current_payload_value,current_success_value in ((current_request_value,True),({**current_request_value,'extra':True},False),({**current_request_value,'expected_resume_fingerprint':'bad'},False),({'id':'../bad','expected_resume_fingerprint':'a'*64},False)):
            with self.subTest(payload=current_payload_value):
                current_handler_value=ImageGenerationTests().make_http_handler(current_manager.route_prefix_value+'/resume/reviewed','POST')
                current_request_bytes=json.dumps(current_payload_value).encode()
                current_handler_value.rfile=io.BytesIO(current_request_bytes)
                current_handler_value.headers['Content-Length']=str(len(current_request_bytes))
                with patch.object(current_manager,'resume_reviewed_generation_job',return_value={'id':current_job_identifier,'status':'queued'}) as current_resume_mock:
                    self.assertTrue(current_manager.handle_image_request(current_handler_value))
                    if current_success_value:
                        self.assertEqual(current_handler_value.status,200)
                        current_resume_mock.assert_called_once_with(current_manager.job_storage_root/current_job_identifier,'a'*64)
                    else:
                        self.assertEqual(current_handler_value.status,400)
                        current_resume_mock.assert_not_called()

    def test_flux_resume_preview_gateway_route_and_http_contract(self):
        import json
        from unittest.mock import patch
        from workflow.tests.test_image_generation import ImageGenerationTests
        from workflow.common.management_gateway import resolve_management_command
        current_manager=FluxImageGenerationManager('flux-character')
        current_job_identifier='2026-11-20_10-00-00-abcdef12'
        current_expected_value={'service':'flux-character','id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64}
        self.assertEqual(resolve_management_command('flux-character','resume-preview',{'id':current_job_identifier})[:2],('POST','/flux-character-generator/resume/preview'))
        current_test_helper=ImageGenerationTests()
        current_handler_value=current_test_helper.make_http_handler(current_manager.route_prefix_value+'/resume/preview','POST')
        current_request_bytes=json.dumps({'id':current_job_identifier}).encode()
        current_handler_value.rfile=io.BytesIO(current_request_bytes)
        current_handler_value.headers['Content-Length']=str(len(current_request_bytes))
        with patch.object(current_manager,'preview_generation_resume',return_value=current_expected_value) as current_preview_mock,patch.object(current_manager,'resume_generation_job') as current_submit_mock:
            self.assertTrue(current_manager.handle_image_request(current_handler_value))
            self.assertEqual(current_handler_value.status,200)
            self.assertEqual(json.loads(current_handler_value.wfile.getvalue()),current_expected_value)
            current_preview_mock.assert_called_once_with(current_manager.job_storage_root/current_job_identifier)
            current_submit_mock.assert_not_called()

    def test_flux_resume_preview_checks_locks_and_mutation_without_launch(self):
        import fcntl
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager.job_storage_root=current_root_path
            current_job_path=current_root_path/'2026-11-20_10-00-00-abcdef12'
            with self.assertRaisesRegex(ValueError,'작업이 없습니다'):
                current_manager.preview_generation_resume(current_job_path)
            self.assertFalse(current_job_path.exists())
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'profile':'flux-character','references':['reference-1.png']}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            current_reference_path=current_job_path/'reference-1.png'
            current_reference_path.write_bytes(b'original')
            with patch.object(current_manager,'validate_generation_runtime') as current_runtime_mock,patch.object(current_manager,'validate_generation_resume') as current_validation_mock,patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                current_review_value=current_manager.preview_generation_resume(current_job_path)
                self.assertEqual(current_review_value['service'],'flux-character')
                self.assertEqual(current_review_value['status'],'failed')
                self.assertEqual(len(current_review_value['expected_resume_fingerprint']),64)
                current_runtime_mock.assert_called_once()
                current_validation_mock.assert_called_once()
                current_launch_mock.assert_not_called()
                with (current_job_path/'execution.lock').open('a') as current_external_lock:
                    fcntl.flock(current_external_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with self.assertRaisesRegex(ValueError,'이전 FLUX 실행'):
                        current_manager.preview_generation_resume(current_job_path)
                current_validation_mock.side_effect=lambda _:current_reference_path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'검토 중 입력이 변경'):
                    current_manager.preview_generation_resume(current_job_path)
                current_launch_mock.assert_not_called()

    def test_flux_resume_fingerprint_covers_records_and_reference_bytes(self):
        import json
        import os
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'request.json').write_text(json.dumps({'profile':'flux-character','references':['reference-1.png']}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            current_reference_path=current_job_path/'reference-1.png'
            current_reference_path.write_bytes(b'first')
            current_first_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)
            self.assertEqual(current_first_value['status'],'failed')
            self.assertEqual(len(current_first_value['fingerprint']),64)
            current_reference_path.write_bytes(b'second')
            current_second_value=current_manager.fingerprint_generation_resume_inputs(current_job_path)
            self.assertNotEqual(current_first_value['fingerprint'],current_second_value['fingerprint'])
            (current_job_path/'translation-pipeline.json').write_text('{}')
            self.assertNotEqual(current_second_value['fingerprint'],current_manager.fingerprint_generation_resume_inputs(current_job_path)['fingerprint'])
            current_reference_path.unlink()
            os.mkfifo(current_reference_path)
            with self.assertRaises(ValueError):current_manager.fingerprint_generation_resume_inputs(current_job_path)
            current_reference_path.unlink()
            current_reference_path.symlink_to(current_job_path/'request.json')
            with self.assertRaises(ValueError):current_manager.fingerprint_generation_resume_inputs(current_job_path)

    def test_flux_resume_rejects_missing_legacy_reference(self):
        import json
        current_manager=FluxImageGenerationManager('flux-character')
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'request.json').write_text(json.dumps({'references':['reference-1.png']}))
            with self.assertRaisesRegex(ValueError,'참조 사본 일반 파일'):
                current_manager.validate_generation_resume(current_job_path)

    def test_untranslated_resume_rejects_unsafe_log_without_changing_state(self):
        import json
        import os
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            current_status_record={'status':'failed','error':'기존 실패'}
            (current_job_path/'status.json').write_text(json.dumps(current_status_record))
            (current_job_path/'cancel.request').write_text('기존 취소')
            current_outside_path=current_job_path/'outside.log'
            current_outside_path.write_text('변경 없음')
            current_log_path=current_job_path/'worker.log'
            for current_log_kind in ('symlink','fifo'):
                with self.subTest(kind=current_log_kind):
                    if current_log_kind=='symlink':current_log_path.symlink_to(current_outside_path.resolve())
                    else:os.mkfifo(current_log_path)
                    with patch.object(current_manager,'validate_generation_resume'),patch.object(current_manager,'launch_generation_worker') as current_launch_mock:
                        with self.assertRaises((OSError,ValueError)):
                            current_manager.resume_generation_job(current_job_path,current_request_record,None)
                        current_launch_mock.assert_not_called()
                    self.assertEqual(json.loads((current_job_path/'status.json').read_text()),current_status_record)
                    self.assertEqual((current_job_path/'cancel.request').read_text(),'기존 취소')
                    self.assertEqual(current_outside_path.read_text(),'변경 없음')
                    current_log_path.unlink()

    def test_untranslated_resume_launch_failure_records_failed_state(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용','translation_base_prompt':'test'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            for current_start_error in (OSError('모의 시작 실패'),ValueError('모의 인자 오류')):
                (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
                with self.subTest(error=type(current_start_error).__name__),patch.object(current_manager,'validate_generation_resume'),patch.object(current_manager,'launch_generation_worker',side_effect=current_start_error):
                    with self.assertRaises(type(current_start_error)):
                        current_manager.resume_generation_job(current_job_path,current_request_record,None)
                current_status_record=json.loads((current_job_path/'status.json').read_text())
                self.assertEqual(current_status_record['status'],'failed')
                self.assertEqual(current_status_record['stage'],'translation')
                self.assertIn('시작하지 못했습니다',current_status_record['error'])

    def test_initial_translation_launch_failure_records_failed_state(self):
        import json
        from unittest.mock import patch
        current_manager=FluxImageGenerationManager('flux-seamless')
        current_request_record={'translation_source_ko':'검증용'}
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            with (current_job_path/'worker.log').open('w') as current_log_handle,patch('workflow.domains.image.flux_translation_queue.subprocess.Popen',side_effect=OSError('모의 시작 실패')):
                with self.assertRaises(OSError):
                    current_manager.launch_generation_worker(current_job_path,current_request_record,current_log_handle)
            current_status_record=json.loads((current_job_path/'status.json').read_text())
            self.assertEqual(current_status_record['status'],'failed')
            self.assertEqual(current_status_record['stage'],'translation')

    def test_untranslated_job_resume_requeues_translation(self):
        import json
        from unittest.mock import patch
        current_manager_value=FluxImageGenerationManager('flux-seamless')
        current_request_record=current_manager_value.validate_generation_request({'action':'generate','prompt':'풀잎',
            'images':[],'width':512,'height':512,'steps':16,'seed':42})
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_path=Path(current_directory_name)
            current_saved_record=save_three_reference_inputs(current_job_path,current_request_record)
            (current_job_path/'request.json').write_text(json.dumps(current_saved_record,ensure_ascii=False))
            (current_job_path/'status.json').write_text('{"status":"cancelled"}')
            (current_job_path/'cancel.request').touch()
            current_manager_value.validate_generation_resume(current_job_path)
            with patch.object(current_manager_value,'launch_generation_worker') as current_launch_mock:
                current_resume_record=current_manager_value.resume_generation_job(current_job_path,current_saved_record,None)
            current_launch_mock.assert_called_once()
            self.assertEqual(current_resume_record['status'],'queued')
            self.assertFalse((current_job_path/'cancel.request').exists())
            self.assertEqual(json.loads((current_job_path/'status.json').read_text())['stage'],'translation')


    def test_korean_building_request_keeps_source_and_prepared_prompt(self):
        current_guide_image = load_building_layout_preset(BUILDING_LAYOUT_PRESET_NAMES[0])
        current_image_buffer = io.BytesIO()
        current_guide_image.save(current_image_buffer, format='PNG')
        current_request_record = FluxImageGenerationManager('flux-building').validate_generation_request({
            'action':'generate','prompt':'나무 집','building_design_ko':'나무 집',
            'images':[base64.b64encode(current_image_buffer.getvalue()).decode()],
            'width':768,'height':768,'steps':16,'seed':42,
        })
        self.assertEqual(current_request_record['building_design_ko'],'나무 집')
        self.assertIn('Match image 1',current_request_record['building_base_prompt'])
        self.assertIn(current_request_record['building_base_prompt'],current_request_record['prompt'])
        self.assertNotIn('나무 집',current_request_record['prompt'])
        self.assertNotIn('translated_design',current_request_record)
        current_implicit_record=FluxImageGenerationManager('flux-building').validate_generation_request({
            'action':'generate','prompt':'나무 집','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],
            'width':768,'height':768,'steps':16,'seed':42,
        })
        self.assertEqual(current_implicit_record['building_design_ko'],'나무 집')
        self.assertEqual(current_implicit_record['prompt'],current_request_record['prompt'])

    def test_translation_pipeline_combines_and_queues_or_stops_on_failure(self):
        import json
        from unittest.mock import patch, MagicMock
        from generators.image import run_flux_translation_pipeline as building_pipeline
        from generators.image.common_art_style import load_common_style_record
        current_translation_id='2026-11-16_23-01-00-12345678'
        for current_failure_value in (False,True):
            with self.subTest(failure=current_failure_value), tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
                current_root_path=Path(current_directory_name).resolve()
                current_job_path=current_root_path/'.tmp/test/flux-building-generator/2026-11-16_23-00-00-12345678'
                current_job_path.mkdir(parents=True)
                (current_job_path/'request.json').write_text(json.dumps({'building_design_ko':'나무 집','building_base_prompt':'A complete building.'},ensure_ascii=False))
                current_fake_manager=MagicMock()
                current_translation_record={'id':current_translation_id,'request':{'text':'나무 집','target_language':'en'},'status':{'status':'failed' if current_failure_value else 'completed','error':'모델 오류'},'result':{'text':'A wooden house.','model_id':'translation-model','revision':'revision-1','quality_checks':[],'term_checks':[]}}
                current_fake_manager.execute_translation_command.side_effect=lambda current_command_name,current_payload_value: {'id':current_translation_id} if current_command_name=='translation-submit' else current_translation_record
                with patch.object(building_pipeline,'WORKFLOW_ROOT_DIRECTORY',current_root_path), patch.object(building_pipeline,'TranslationServiceManager',return_value=current_fake_manager), patch.object(building_pipeline,'launch_gpu_process') as current_launch_mock:
                    current_launch_mock.return_value.wait.return_value=0
                    if current_failure_value:
                        with self.assertRaisesRegex(ValueError,'번역 실패'):
                            building_pipeline.execute_flux_translation_pipeline(current_job_path)
                        current_launch_mock.assert_not_called()
                        self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')
                    else:
                        building_pipeline.execute_flux_translation_pipeline(current_job_path)
                        current_launch_mock.assert_called_once()
                        current_saved_record=json.loads((current_job_path/'request.json').read_text())
                        self.assertEqual(current_saved_record['translated_design'],'A wooden house.')
                        self.assertEqual(current_saved_record['translation']['id'],current_translation_id)
                        self.assertIn('A complete building. A wooden house.',current_saved_record['prompt'])
                        self.assertEqual(current_saved_record['prompt'].count(load_common_style_record()['prompt']),1)

    def test_translation_pipeline_cancel_does_not_enqueue_work(self):
        import json
        from unittest.mock import patch, MagicMock
        from generators.image import run_flux_translation_pipeline as building_pipeline
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_root_path=Path(current_directory_name).resolve()
            current_job_path=current_root_path/'.tmp/test/flux-building-generator/2026-11-16_23-00-00-87654321'
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps({'building_design_ko':'나무 집','building_base_prompt':'A complete building.'},ensure_ascii=False))
            (current_job_path/'cancel.request').touch()
            current_fake_manager=MagicMock()
            with patch.object(building_pipeline,'WORKFLOW_ROOT_DIRECTORY',current_root_path), patch.object(building_pipeline,'TranslationServiceManager',return_value=current_fake_manager), patch.object(building_pipeline,'launch_gpu_process') as current_launch_mock:
                building_pipeline.execute_flux_translation_pipeline(current_job_path)
                current_fake_manager.execute_translation_command.assert_not_called()
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'cancelled')

    def test_building_history_reads_completed_translation_from_job(self):
        import json
        from unittest.mock import patch
        from workflow.domains.image.image_generation import ImageGenerationManager
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_root=Path(current_directory_name)
            current_identifier_value='2026-11-16_23-00-00-12345678'
            current_job_path=current_job_root/current_identifier_value
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'building_design_ko':'나무 집','translated_design':'A wooden house.'},ensure_ascii=False))
            current_manager_value=FluxImageGenerationManager('flux-building')
            current_manager_value.job_storage_root=current_job_root
            with patch.object(ImageGenerationManager,'list_generation_history',return_value=[{'id':current_identifier_value,'request':{'building_design_ko':'나무 집'}}]):
                current_history_value=current_manager_value.list_generation_history()
            self.assertEqual(current_history_value[0]['request']['translated_design'],'A wooden house.')

    def test_building_history_displays_translation_and_pending_state(self):
        from workflow.common.gradio_history_inputs import collect_saved_input_view, collect_saved_stage_prompts, describe_saved_prompt_counts
        current_request_record={'building_design_ko':'나무 집','building_base_prompt':'A building.',
            'common_style':{'version':'1.5.0','prompt':'Soft shading.'},'prompt':'A building. Soft shading.'}
        self.assertIn('최종 입력 미확정',describe_saved_prompt_counts({'request':current_request_record}))
        self.assertIn('최종 모델 입력이 확정되지 않습니다',collect_saved_input_view({'request':current_request_record})[0])
        self.assertNotIn('최종 모델 입력',collect_saved_stage_prompts({'request':current_request_record}))
        current_request_record.update(translated_design='A wooden house.',prompt='A building. A wooden house. Soft shading.')
        current_stage_text=collect_saved_stage_prompts({'request':current_request_record})
        for current_expected_value in ('한국어 디자인\n나무 집','영어 번역\nA wooden house.','건물 기본 문구\nA building.','공용 화풍 v1.5.0','최종 모델 입력'):
            self.assertIn(current_expected_value,current_stage_text)
        self.assertIn('영어 번역 3단어',describe_saved_prompt_counts({'request':current_request_record}))

    def test_building_request_applies_common_style_once_and_displays_final_prompt(self):
        import hashlib
        from generators.image.common_art_style import load_common_style_record
        from gui.ui.shared.flux_image_page import describe_flux_image_prompt
        current_guide_image = load_building_layout_preset(BUILDING_LAYOUT_PRESET_NAMES[0])
        current_image_buffer = io.BytesIO()
        current_guide_image.save(current_image_buffer, format='PNG')
        current_user_prompt = 'A timber guild hall.'
        current_request_record = FluxImageGenerationManager('flux-building').validate_generation_request({
            'action': 'generate', 'prompt': current_user_prompt,
            'images': [base64.b64encode(current_image_buffer.getvalue()).decode()],
            'width': 768, 'height': 768, 'steps': 16, 'seed': 42,
        })
        current_style_record = load_common_style_record()
        self.assertEqual(current_request_record['common_style']['version'], '1.5.0')
        self.assertEqual(current_request_record['common_style']['sha256'], current_style_record['sha256'])
        self.assertEqual(current_request_record['prompt'].count(current_style_record['prompt']), 1)
        self.assertEqual(current_request_record['prompt_sha256'], hashlib.sha256(current_request_record['prompt'].encode()).hexdigest())
        current_display_text = describe_flux_image_prompt(current_user_prompt)
        self.assertIn('공용 화풍 v1.5.0 41단어 (자동 적용)', current_display_text)
        self.assertIn(current_request_record['prompt'], current_display_text)
        self.assertIn(f'최종 {len(current_request_record["prompt"].split())}단어', current_display_text)
        self.assertIn('입력에 포함됨', describe_flux_image_prompt(current_request_record['prompt']))

    def test_catalog_search_pagination_and_empty_result(self):
        self.assertEqual(search_building_guide_catalog(''), list(BUILDING_LAYOUT_PRESET_NAMES))
        current_matching_names = search_building_guide_catalog('박공 2층')
        self.assertTrue(current_matching_names)
        self.assertTrue(all(BUILDING_STRUCTURE_RECORDS[current_name]['roof'] == 'gable' and BUILDING_STRUCTURE_RECORDS[current_name]['floors'] == 2 for current_name in current_matching_names))
        current_first_page = render_building_guide_page('', 1)
        current_second_page = render_building_guide_page('', 2)
        self.assertEqual(len(current_first_page[2]), 8)
        self.assertFalse(set(current_first_page[2]) & set(current_second_page[2]))
        self.assertIn('총 50건', current_first_page[3])
        self.assertIn('없습니다', render_building_guide_page('없는가이드', 1)[3])
        current_four_page = render_building_guide_page('', 2, 4)
        self.assertEqual(current_four_page[2], list(BUILDING_LAYOUT_PRESET_NAMES[4:8]))
        self.assertEqual(current_four_page[1]['value'], 2)
        current_final_page = render_building_guide_page('', 99, 16)
        self.assertEqual(current_final_page[1]['value'], 4)
        self.assertEqual(len(current_final_page[2]), 2)
        self.assertFalse(current_final_page[5]['interactive'])
        self.assertEqual(len(render_building_guide_page('', 1, 32)[2]), 32)

    def test_selection_identity_and_full_size_application(self):
        current_first_page = render_building_guide_page('', 1)
        current_selected_name = current_first_page[2][0]
        current_selected_event = gr.SelectData(None, {'index': 0, 'value': {'caption': f'건물\nID: {current_selected_name}'}})
        current_selected_result = select_building_guide_card('', 1, 8, current_first_page[2], current_selected_event)
        self.assertEqual(current_selected_result[0], current_selected_name)
        self.assertIn(current_selected_name, current_selected_result[1])
        self.assertTrue(current_selected_result[2]['interactive'])
        self.assertEqual(apply_selected_building_guide(current_selected_name).tobytes(), load_building_layout_preset(current_selected_name).tobytes())
        with self.assertRaises(gr.Error):
            select_building_guide_card('없는가이드', 1, 8, current_first_page[2], current_selected_event)
        with self.assertRaises(gr.Error):
            select_building_guide_card('', 1, 8, current_first_page[2], gr.SelectData(None, {'index': 0, 'value': {'caption': 'ID: wrong'}}))
        with self.assertRaises(gr.Error):
            select_building_guide_card('', 1, 4, current_first_page[2], current_selected_event)
        with self.assertRaises(gr.Error):
            apply_selected_building_guide(None)

    def test_flux_building_page_has_gallery_and_no_guide_dropdown(self):
        from gui.ui.shared.flux_image_page import build_flux_image_page
        current_page_blocks = build_flux_image_page('flux-building', 'http://127.0.0.1:8770', 8770)
        current_component_values = current_page_blocks.config['components']
        self.assertTrue(any(current_component_value['props'].get('label') == '건물 가이드 카드' for current_component_value in current_component_values))
        self.assertFalse(any(current_component_value['props'].get('label') == '건물 가이드 미리보기' for current_component_value in current_component_values))
        self.assertFalse(any(current_component_value['props'].get('label') == '건물 배치 가이드 검색·선택' for current_component_value in current_component_values))

    def test_building_and_history_share_panel_and_pagination_controls(self):
        from gui.ui.shared.flux_image_page import build_flux_image_page
        current_page_blocks=build_flux_image_page('flux-building','http://127.0.0.1:8770',8770)
        current_page_config=current_page_blocks.config
        current_component_lookup={current_component_value['id']:current_component_value for current_component_value in current_page_config['components']}
        current_gallery_panels={}

        def find_gallery_panels(current_layout_node, current_panel_stack):
            current_component_record=current_component_lookup.get(current_layout_node['id'],{})
            current_component_props=current_component_record.get('props',{})
            if current_component_record.get('type')=='column' and current_component_props.get('variant')=='panel':
                current_panel_stack=[*current_panel_stack,current_layout_node]
            if current_component_props.get('label')=='건물 가이드 카드':
                current_gallery_panels['building']=current_panel_stack[-1]
            if current_component_props.get('elem_id')=='generation-history-cards':
                current_gallery_panels['history']=current_panel_stack[-1]
            for current_child_node in current_layout_node.get('children',[]):
                find_gallery_panels(current_child_node,current_panel_stack)

        def collect_panel_controls(current_layout_node):
            current_component_record=current_component_lookup.get(current_layout_node['id'],{})
            current_component_props=current_component_record.get('props',{})
            current_controls_value=[]
            if current_component_props.get('label') in ('페이지당 항목','페이지 이동 (입력 후 Enter)') or current_component_props.get('value') in ('새로고침','← 이전','다음 →'):
                current_controls_value.append((current_component_record.get('type'),current_component_props.get('label'),current_component_props.get('value'),current_component_props.get('size'),current_component_props.get('min_width')))
            for current_child_node in current_layout_node.get('children',[]):
                current_controls_value.extend(collect_panel_controls(current_child_node))
            return current_controls_value

        find_gallery_panels(current_page_config['layout'],[])
        self.assertEqual(set(current_gallery_panels),{'building','history'})
        self.assertEqual(collect_panel_controls(current_gallery_panels['building']),collect_panel_controls(current_gallery_panels['history']))
        current_refresh_functions=[current_function_value for current_function_value in current_page_blocks.fns.values() if current_function_value.fn is render_building_guide_page]
        self.assertGreaterEqual(len(current_refresh_functions),2)
