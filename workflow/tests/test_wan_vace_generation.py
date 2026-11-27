"""VACE 입력 모드·서비스 계약·UI 복원·전문가 경계 검사."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.wan_vace.contracts import validate_vace_request, locate_expert_switch, VACE_DEFAULT_SETTINGS
from workflow.common.management_gateway import resolve_management_command


class VaceVideoContractTests(unittest.TestCase):
    def test_mode_guides_keep_api_values_and_show_pose_requirements(self):
        from generators.wan_vace.page.inputs import VACE_INPUT_CHOICES,VACE_MODE_HELP_TEXT
        self.assertEqual({mode for _,mode in VACE_INPUT_CHOICES},{'pose','reference','first_frame','text','video_edit','video_condition'})
        for phrase in ('DWPose','50','CFG','12'):
            self.assertIn(phrase,VACE_MODE_HELP_TEXT['pose'])
        self.assertIn('이미지',VACE_MODE_HELP_TEXT['text'])

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
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        current_service_instance = VaceVideoGenerationManager()
        with patch('workflow.domains.wan_vace.generation.validate_vace_assets') as current_assets_mock:
            with self.assertRaisesRegex(ValueError, 'Q4'):
                current_service_instance.validate_generation_runtime({'tag': 'wan22-vace'})
            current_assets_mock.assert_not_called()
            current_validated_record = validate_vace_request(self.current_request_record)
            self.assertEqual(current_validated_record['model_profile'], 'official-bf16-resident-v1')
            current_service_instance.validate_generation_runtime(current_validated_record)
            current_assets_mock.assert_called_once()

    def test_bf16_memory_profile_excludes_retired_q4_observations(self):
        import json
        from workflow.common.gpu_memory_history import identify_execution_command, estimate_required_memory
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_path = Path(current_temp_root)
            (current_job_path / 'request.json').write_text(json.dumps({'frames': 21, 'model_profile': 'official-bf16-resident-v1'}))
            current_profile_name = identify_execution_command(['python', 'generators/wan_vace/worker.py'], current_job_path, 'gtt')
            self.assertEqual(current_profile_name, 'wan-vace-bf16:frames=21:offload=none-v1:domain=gtt')
            with patch('workflow.common.gpu_memory_history.load_recent_observations', return_value=[]):
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
        from generators.wan_vace.page.inputs import build_vace_payload
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
        import hashlib, json
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application
        from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job='2026-11-15_12-00-00-12345678';jobdir=root/job;jobdir.mkdir()
            request={**VACE_DEFAULT_SETTINGS,'mode':'reference','prompt':'walk','negative_prompt':'','references':['reference-1.png']}
            Image.new('RGB',(832,480)).save(jobdir/'reference-1.png')
            image=(jobdir/'reference-1.png').read_bytes()
            request['reference_snapshots']=[{'path':'reference-1.png','order':1,'bytes':len(image),'sha256':hashlib.sha256(image).hexdigest()}]
            (jobdir/'request.json').write_text(json.dumps(request))
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with patch('generators.wan_vace.contracts.VACE_JOB_STORAGE',root),TestClient(app) as client:
                response=client.get(f'/management/assistant/vace-input/{job}/request')
                self.assertEqual(response.status_code,200);self.assertEqual(response.json()['attachments'],['reference'])
                self.assertEqual(response.json()['request']['mode'],'reference')
                request.update(model_profile='q8-gguf-resident-v1', lora_mode='fighting_lightning', fighting_strength=0.5)
                (jobdir/'request.json').write_text(json.dumps(request))
                restored=client.get(f'/management/assistant/vace-input/{job}/request')
                self.assertEqual(restored.status_code,200)
                self.assertEqual(restored.json()['request']['model_profile'],'q8-gguf-resident-v1')
                self.assertEqual(restored.json()['request']['fighting_strength'],0.5)
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/reference').status_code,200)
                self.assertEqual(client.get('/management/assistant/vace-input/invalid/request').status_code,404)
                missing_snapshot=dict(request);missing_snapshot.pop('reference_snapshots')
                (jobdir/'request.json').write_text(json.dumps(missing_snapshot))
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/request').status_code,422)
                (jobdir/'request.json').write_text('[]')
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/request').status_code,422)
                import imageio_ffmpeg, subprocess
                request['mode']='video_edit'
                for filename in ('edit-video.mp4','edit-mask.mp4'):
                    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-f','lavfi','-i','color=red:s=64x48:d=1','-c:v','mpeg4',str(jobdir/filename)],check=True)
                for part,filename in (('edit_video','edit-video.mp4'),('edit_mask','edit-mask.mp4')):
                    request[part+'_file']=filename;request[part+'_sha256']=hashlib.sha256((jobdir/filename).read_bytes()).hexdigest()
                (jobdir/'request.json').write_text(json.dumps(request))
                for part in ('edit_video','edit_mask'):
                    thumbnail=client.get(f'/management/assistant/vace-input/{job}/{part}-thumbnail')
                    self.assertEqual(thumbnail.status_code,200)
                    self.assertEqual(thumbnail.headers['content-type'],'image/png')
                    self.assertTrue(thumbnail.content.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/reference-thumbnail').status_code,404)
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/pose_video-thumbnail').status_code,404)
                (jobdir/'edit-video.mp4').write_bytes(b'changed')
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/request').status_code,422)
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/edit_video').status_code,422)
                request['mode']='reference';(jobdir/'request.json').write_text(json.dumps(request))
                (jobdir/'reference-1.png').write_bytes(image+b'changed')
                self.assertEqual(client.get(f'/management/assistant/vace-input/{job}/request').status_code,422)
                (jobdir/'reference-1.png').unlink()
                self.assertIn(client.get(f'/management/assistant/vace-input/{job}/request').status_code,(404,422))

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

    def test_history_connection_error_has_actionable_message(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        script="""import {requestErrorMessage} from './gui/requestError.mjs';
          const message=requestErrorMessage(new TypeError('Failed to fetch'));
          if(!message.includes('연결'))throw Error(message);"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_current_page_renders_without_generation_and_has_history(self):
        import os,subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'vace.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'VacePage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={search:'',pathname:'/management/frame/wan22-vace-generator/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server');const Page=require(process.argv[1]).default;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Page)));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('이력',markup);self.assertIn('모델',markup)

    def test_service_paths_and_required_commands(self):
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_service_instance=VaceVideoGenerationManager()
        self.assertEqual(current_service_instance.route_prefix_value,'/wan22-vace')
        self.assertEqual(current_service_instance.select_generation_runner(),'generators/wan_vace/worker.py')
        self.assertTrue({'history-delete','history-reset','prioritize','resume','cancel'} <= set(MANAGEMENT_SERVICE_COMMANDS['wan22-vace']))
