"""Animate 고정 실험 입력 및 게이트웨이 계약."""
import base64,io,unittest
from PIL import Image
from generators.wan_animate.contracts import validate_animate_request
from tools.review.common.management_gateway import resolve_management_command
class AnimateGenerationContractTests(unittest.TestCase):
 def setUp(self):
  image_output_buffer=io.BytesIO()
  Image.new('RGB',(832,480),'white').save(image_output_buffer,format='PNG')
  self.request_input_record={'action':'generate','prompt':'걷는다.','images':[base64.b64encode(image_output_buffer.getvalue()).decode()]*22,'width':832,'height':480,'frames':21,'steps':20,'seed':42,'flow_shift':5.0,'guidance_scale':1.0}
 def test_rejects_wrong_model_and_frame_contract(self):
  for modified_request_record in [{**self.request_input_record,'model':'other'},{**self.request_input_record,'frames':35},{**self.request_input_record,'images':self.request_input_record['images'][:2]}]:
   with self.assertRaises(ValueError): validate_animate_request(modified_request_record)
 def test_accepts_reference_and_pose_frames(self):
  self.assertEqual(len(validate_animate_request(self.request_input_record)['images']),22)
 def test_accepts_reference_without_motion(self):
  current_request_record=validate_animate_request({**self.request_input_record,'images':self.request_input_record['images'][:1]})
  self.assertEqual(len(current_request_record['images']),1)
  self.assertEqual(current_request_record['tag'],'animate-q4-reference-only')
 def test_gateway_uses_common_job_route(self):
  current_method_name,current_route_path=resolve_management_command('wan22-animate','generate',self.request_input_record)
  self.assertEqual((current_method_name,current_route_path),('POST','/wan22-animate/jobs'))

class AnimateMemoryPolicyTests(unittest.TestCase):
 def test_tiled_encoding_preserves_time_axis_without_gradients(self):
  import contextlib
  from types import SimpleNamespace
  from unittest.mock import patch
  from generators.wan_animate.memory import TiledAnimateVae
  inference_state_record={'enabled':False}
  @contextlib.contextmanager
  def enable_inference_context():
   inference_state_record['enabled']=True
   try: yield
   finally: inference_state_record['enabled']=False
  def encode_tiled_tensor(current_pixel_tensor,**current_tile_options):
   self.assertTrue(inference_state_record['enabled'])
   self.assertEqual(current_tile_options,{'tile_x':256,'tile_y':256,'overlap':64,'tile_t':9,'overlap_t':5})
   return SimpleNamespace(shape=(1,16,(current_pixel_tensor.shape[0]-1)//4+1,60,104))
  current_vae_model=SimpleNamespace(device=SimpleNamespace(type='cuda'),encode_tiled=encode_tiled_tensor)
  with patch.dict('sys.modules',{'torch':SimpleNamespace(inference_mode=enable_inference_context)}):
   for current_frame_count in (1,21):
    current_latent_tensor=TiledAnimateVae(current_vae_model).encode(SimpleNamespace(shape=(current_frame_count,480,832,3)))
    self.assertEqual(current_latent_tensor.shape[2],(current_frame_count-1)//4+1)
 def test_rejects_cpu_and_incorrect_latent_length(self):
  import contextlib
  from types import SimpleNamespace
  from unittest.mock import patch
  from generators.wan_animate.memory import TiledAnimateVae
  with self.assertRaises(ValueError):
   TiledAnimateVae(SimpleNamespace(device=SimpleNamespace(type='cpu')))
  current_vae_model=SimpleNamespace(device=SimpleNamespace(type='cuda'),encode_tiled=lambda *args,**kwargs:SimpleNamespace(shape=(1,16,5,60,104)))
  with patch.dict('sys.modules',{'torch':SimpleNamespace(inference_mode=contextlib.nullcontext)}):
   with self.assertRaises(ValueError):
    TiledAnimateVae(current_vae_model).encode(SimpleNamespace(shape=(21,480,832,3)))

class AnimateInterfaceContractTests(unittest.TestCase):
 def test_input_modes_and_confirmation_use_existing_gateway(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import Mock
  import gradio as gr
  from tools.review.ui.gradio.wan_animate_app import build_animate_interface, build_animate_payload, ANIMATE_INPUT_MODE_CHOICES
  with tempfile.TemporaryDirectory() as current_directory_name:
   current_reference_path=Path(current_directory_name)/'reference.png'
   Image.new('RGB',(832,480),'white').save(current_reference_path)
   current_input_values=(str(current_reference_path),[],ANIMATE_INPUT_MODE_CHOICES[1],'네 걸음을 걷는다.')
   current_expected_payload=build_animate_payload(*current_input_values)
   self.assertEqual(len(current_expected_payload['images']),1)
   self.assertEqual(len(build_animate_payload(str(current_reference_path),[str(current_reference_path)]*21,ANIMATE_INPUT_MODE_CHOICES[0],'걷는다.')['images']),22)
   for current_pose_paths,current_input_mode in [([],ANIMATE_INPUT_MODE_CHOICES[0]),([str(current_reference_path)],ANIMATE_INPUT_MODE_CHOICES[1])]:
    with self.assertRaises(ValueError):
     build_animate_payload(str(current_reference_path),current_pose_paths,current_input_mode,'걷는다.')
   from tools.review.ui.gradio.wan_animate_app import build_animation_video_payload
   current_input_values=(str(current_reference_path),str(current_reference_path),20,42,5.,1.,832,480)
   current_expected_payload=build_animation_video_payload(*current_input_values)
   current_command_mock=Mock(return_value={'id':'isolated-test-job'})
   current_interface_blocks=build_animate_interface('http://localhost:8770',current_command_mock)
   current_callback_functions={current_function_record.fn.__name__:current_function_record.fn for current_function_record in reversed(list(current_interface_blocks.fns.values())) if current_function_record.fn}
   current_pending_inputs=current_callback_functions['prepare_generation_confirmation'](*current_input_values)[0]
   current_callback_functions['cancel_generation_confirmation'](current_pending_inputs,*current_input_values)
   with self.assertRaises(gr.Error):
    list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs))
   current_command_mock.assert_not_called()
   current_pending_inputs=current_callback_functions['prepare_generation_confirmation'](*current_input_values)[0]
   self.assertEqual(list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs))[0][0],'isolated-test-job')
   current_command_mock.assert_called_once_with('generate',current_expected_payload)

 def test_history_restore_rejects_path_escape(self):
  from tools.review.ui.gradio.wan_animate_app import restore_animate_inputs
  with self.assertRaises(ValueError):
   restore_animate_inputs({'id':'../outside','request':{'references':[],'prompt':'걷는다.'}})

class AnimateExpandedInputTests(unittest.TestCase):
 def test_face_frames_and_parameter_ranges(self):
  current_image_buffer=io.BytesIO()
  Image.new('RGB',(832,480)).save(current_image_buffer,format='PNG')
  current_body_base64=base64.b64encode(current_image_buffer.getvalue()).decode()
  current_image_buffer=io.BytesIO()
  Image.new('RGB',(512,512)).save(current_image_buffer,format='PNG')
  current_face_base64=base64.b64encode(current_image_buffer.getvalue()).decode()
  current_input_record={'action':'generate','prompt':'动作','images':[current_body_base64]*46+[current_face_base64]*45,'width':832,'height':480,'frames':45,'steps':30,'seed':123,'flow_shift':5.0,'guidance_scale':1.0,'fps':16}
  current_valid_record=validate_animate_request(current_input_record)
  self.assertEqual(current_valid_record['tag'],'animate-q4-pose-face')
  for current_changed_values in ({'images':current_input_record['images'][:-1]},{'images':[current_body_base64]*91},{'fps':0},{'frames':44},{'flow_shift':float('nan')},{'width':831},{'seed':-1}):
   with self.assertRaises(ValueError):
    validate_animate_request({**current_input_record,**current_changed_values})

 def test_expanded_history_roundtrip(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from tools.review.ui.gradio.wan_animate_app import restore_animate_inputs,build_animate_payload
  with tempfile.TemporaryDirectory() as current_temp_directory:
   current_storage_root=Path(current_temp_directory)
   current_job_directory=current_storage_root/'test-job'
   current_job_directory.mkdir()
   Image.new('RGB',(832,480)).save(current_job_directory/'body.png')
   Image.new('RGB',(512,512)).save(current_job_directory/'face.png')
   current_request_record={'references':['body.png']*46+['face.png']*45,'prompt':'动作','width':832,'height':480,'frames':45,'steps':30,'seed':12,'flow_shift':5.,'guidance_scale':1.,'fps':16}
   with patch('tools.review.ui.gradio.wan_animate_app.ANIMATE_JOB_STORAGE',current_storage_root):
    current_restored_values=restore_animate_inputs({'id':'test-job','request':current_request_record})
   current_restored_payload=build_animate_payload(*current_restored_values[:-1])
   self.assertEqual(len(current_restored_payload['images']),91)
   for current_field_name in ('frames','steps','seed','flow_shift','guidance_scale','fps','width','height'):
    self.assertEqual(current_restored_payload[current_field_name],current_request_record[current_field_name])


class AnimateVideoInputTests(unittest.TestCase):
 def test_video_metadata_and_default_prompt(self):
  import tempfile,subprocess
  from pathlib import Path
  from tools.review.ui.gradio.wan_animate_app import build_animation_video_payload
  with tempfile.TemporaryDirectory() as current_directory_name:
   current_directory_path=Path(current_directory_name)
   current_reference_path=current_directory_path/'reference.png'
   current_video_path=current_directory_path/'motion.mp4'
   Image.new('RGB',(120,180),'white').save(current_reference_path)
   current_ffmpeg_path=next(Path('.venv/lib').glob('python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux*'))
   subprocess.run([str(current_ffmpeg_path),'-v','error','-f','lavfi','-i','color=black:s=64x64:r=24','-frames:v','6','-c:v','libx264','-pix_fmt','yuv420p',str(current_video_path)],check=True)
   current_video_payload=build_animation_video_payload(str(current_reference_path),str(current_video_path))
   current_valid_record=validate_animate_request(current_video_payload)
   self.assertEqual((current_valid_record['source_frames'],current_valid_record['frames'],current_valid_record['fps']),(6,9,24))
   self.assertEqual(current_valid_record['prompt'],'视频中的人在做动作')
   for current_changed_values in ({'mode':'replacement'},{'driving_video':'invalid'},{'width':100000},{'prompt':'unexpected'}):
    with self.assertRaises((ValueError,TypeError)):
     validate_animate_request({**current_video_payload,**current_changed_values})

class AnimateExternalWeightTests(unittest.TestCase):
 def test_external_weight_missing_truncated_and_escape(self):
  import tempfile
  from pathlib import Path
  from generators.wan_animate.model_validation import validate_external_tensor_files
  with tempfile.TemporaryDirectory() as current_directory_name:
   current_model_path=Path(current_directory_name)/'end2end.onnx'
   current_weight_path=Path(current_directory_name)/'tensor.bin'
   current_weight_path.write_bytes(b'12345678')
   validate_external_tensor_files(current_model_path,[{'location':'tensor.bin','offset':'2','length':'6'}])
   for current_external_record in ({'location':'missing'},{'location':'tensor.bin','length':'9'},{'location':'../outside'},{'location':'tensor.bin','offset':'-1'}):
    with self.assertRaises(ValueError):
     validate_external_tensor_files(current_model_path,[current_external_record])
