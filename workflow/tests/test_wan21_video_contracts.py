import unittest
from generators.wan21_video_contracts import validate_request


def request():
    return dict(action='generate', prompt=' a fight ', negative_prompt='', images=[], width=832, height=480, frames=73, steps=4, seed=42, flow_shift=5, guidance_scale=1, acceleration=True, action_lora=False, action_strength=1)


class Wan21VideoContractsTest(unittest.TestCase):
    def test_t2v_does_not_require_image_and_normalizes(self):
        actual=validate_request(request(),'t2v')
        self.assertEqual((actual['prompt'],actual['tag']),('a fight','wan21-t2v'))
    def test_i2v_requires_image(self):
        with self.assertRaises(ValueError): validate_request(request(),'i2v')
    def test_invalid_inputs_and_acceleration_are_rejected(self):
        for field,value in [('frames',72),('seed',True),('flow_shift',float('nan')),('steps',8),('guidance_scale',3.5),('acceleration',1),('images',['invalid'])]:
            data=request(); data[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): validate_request(data,'t2v')
    def test_action_adapter_requires_positive_weight(self):
        data=request(); data.update(action_lora=True,action_strength=0)
        with self.assertRaises(ValueError): validate_request(data,'t2v')
    def test_action_variant_is_fixed_to_allowed_modes(self):
        import base64,io
        from PIL import Image
        output=io.BytesIO();Image.new('RGB',(832,480)).save(output,format='PNG')
        data=request();data.update(images=[base64.b64encode(output.getvalue()).decode()],action_lora=True,action_variant='attack_high')
        self.assertEqual(validate_request(data,'i2v')['action_variant'],'attack_high')
        data['action_variant']='arbitrary-path'
        with self.assertRaises(ValueError): validate_request(data,'i2v')
        data=request();data['action_variant']='attack_high'
        with self.assertRaises(ValueError): validate_request(data,'t2v')

class Wan21ServiceIsolationTest(unittest.TestCase):
    def test_retired_asset_preparations_do_not_start_downloads(self):
        from generators.wan21_t2v import assets as t2v
        from generators.wan21_i2v import assets as i2v, attack_lora
        for module in (t2v, i2v, attack_lora):
            with self.subTest(module=module.__name__), self.assertRaisesRegex(ValueError, '폐기'):
                module.prepare_assets()

    def test_services_use_distinct_storage_and_execution_paths(self):
        from workflow.domains.wan21_t2v.generation import Wan21T2VGenerationManager
        from workflow.domains.wan21_i2v.generation import Wan21I2VGenerationManager
        text=Wan21T2VGenerationManager(); image=Wan21I2VGenerationManager()
        self.assertNotEqual(text.job_storage_root,image.job_storage_root)
        self.assertEqual(text.select_generation_service(),'wan21-t2v')
        self.assertEqual(image.select_generation_service(),'wan21-i2v')
        self.assertEqual(text.select_generation_runner(),'generators/wan21_t2v/worker.py')
        self.assertEqual(image.select_generation_runner(),'generators/wan21_i2v/worker.py')

    def test_missing_boss_lora_cannot_be_silently_skipped(self):
        from unittest.mock import patch
        from pathlib import Path
        from workflow.domains.wan21_t2v import generation
        manager=generation.Wan21T2VGenerationManager()
        with patch.object(generation,'validate_runtime'), patch.object(generation,'BOSS_LORA',Path('/nonexistent/kxsr.safetensors')):
            with self.assertRaisesRegex(ValueError,'폐기'):
                manager.validate_generation_runtime({'action_lora':True})

    def test_attack_adapter_must_be_present_before_submission(self):
        from unittest.mock import patch
        from pathlib import Path
        from workflow.domains.wan21_i2v import generation
        manager=generation.Wan21I2VGenerationManager()
        with patch.object(generation,'validate_runtime'), patch.object(generation,'DIRECTORY',Path('/nonexistent/wan21-i2v')):
            with self.assertRaisesRegex(ValueError,'폐기'):
                manager.validate_generation_runtime({'action_lora':True,'action_variant':'attack_high'})
            with self.assertRaisesRegex(ValueError,'폐기'):
                manager.validate_generation_runtime({'action_lora':False,'action_variant':'attack_high'})


class Wan21QueueIntegrationTest(unittest.TestCase):
    def test_gateway_and_dedicated_queue_paths(self):
        import tempfile
        from pathlib import Path
        from workflow.common.gpu_job_queue import GPU_MEMORY_REQUIREMENTS, GPU_EXCLUSIVE_SERVICES, identify_dedicated_gpu_reservation_source
        from workflow.common.management_gateway import resolve_management_command
        for mode in ('t2v','i2v'):
            service='wan21-'+mode
            self.assertIn(service,GPU_MEMORY_REQUIREMENTS)
            self.assertIn(service,GPU_EXCLUSIVE_SERVICES)
            payload=request()
            if mode=='i2v': payload['images']=['base64-input']
            with self.assertRaisesRegex(ValueError,'폐기'):
                resolve_management_command(service,'generate',payload)
            self.assertEqual(resolve_management_command(service,'history',{}),('GET','/'+service+'/history'))
            with tempfile.TemporaryDirectory() as root:
                path=Path(root)/'.tmp/test'/service/'2026-11-23_00-00-00-12345678'; path.mkdir(parents=True)
                self.assertEqual(identify_dedicated_gpu_reservation_source(str(path),service,root),service)
                other='wan21-i2v' if mode=='t2v' else 'wan21-t2v'
                self.assertIsNone(identify_dedicated_gpu_reservation_source(str(path),other,root))


if __name__ == '__main__': unittest.main()
