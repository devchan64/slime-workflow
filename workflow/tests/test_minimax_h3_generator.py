"""MiniMax H3 등록과 입력·작업 계약."""
import base64
import io
import unittest
from unittest.mock import patch
from PIL import Image
from generators.minimax_h3.contracts import validate_request
from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_SERVICE_ROUTES
from workflow.common.gpu_job_queue import GPU_EXCLUSIVE_SERVICES, GPU_MEMORY_REQUIREMENTS, is_dedicated_gpu_source_verifiable
from workflow.domains.hermes_agent.video_operations import make_hermes_video_source_manager, validate_hermes_video_service


def png(width=832,height=480):
    buffer=io.BytesIO();Image.new('RGB',(width,height),'white').save(buffer,format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


class MiniMaxH3GeneratorTests(unittest.TestCase):
    def test_encoder_path_conflict_reports_not_ready_for_all_consumers(self):
        from generators.minimax_h3 import contracts as video
        from generators.minimax_h3_image import contracts as image
        from workflow.generators.minimax_h3_ref2va import assets as ref
        for module in (video, image, ref):
            with self.subTest(module=module.__name__), patch.object(module, 'current_files', side_effect=ValueError('경로 충돌')):
                result = module.inspect_runtime()
                self.assertFalse(result['ready'])
                self.assertIn('경로 충돌', result['message'])
                if module is image:
                    self.assertFalse(result['generation_ready'])

    def setUp(self):
        self.request={'action':'generate','prompt':'  Step and slash.  ','images':[png()],'width':832,'height':480,'frames':124,'steps':8,'seed':42}

    def test_request_preserves_validated_fixed_settings(self):
        result=validate_request(self.request)
        self.assertEqual(result['prompt'],'Step and slash.')
        self.assertEqual(result['tag'],'minimax-h3-i2v')
        self.assertEqual(validate_request({**self.request,'width':768,'height':448})['width'],768)
        for name,value in (('width',800),('height',432),('frames',73),('steps',7),('seed',True)):
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_request({**self.request,name:value})
        with self.assertRaises(ValueError):validate_request({**self.request,'images':[png(640,480)]})
        with self.assertRaises(ValueError):validate_request({**self.request,'prompt':'  '})

    def test_registered_commands_source_and_gpu_reservation(self):
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['minimax-h3-i2v'],'/minimax-h3-i2v')
        self.assertTrue({'generate','status','history-observe','prioritize','cancel','history-delete','history-reset','model-status'} <= set(MANAGEMENT_SERVICE_COMMANDS['minimax-h3-i2v']))
        manager=make_hermes_video_source_manager('minimax-h3-i2v')
        self.assertEqual(manager.select_generation_service(),'minimax-h3-i2v')
        self.assertEqual(manager.select_generation_runner(),'generators/minimax_h3/worker.py')
        self.assertIn('minimax-h3-i2v',GPU_EXCLUSIVE_SERVICES)
        self.assertEqual(GPU_MEMORY_REQUIREMENTS['minimax-h3-i2v'],81920)
        self.assertTrue(is_dedicated_gpu_source_verifiable('minimax-h3-i2v'))
        validate_hermes_video_service('minimax-h3-i2v')

    def test_runtime_reports_missing_files_without_crashing(self):
        from generators.minimax_h3 import contracts
        with patch.object(contracts,'FILES',[(contracts.ROOT/'does-not-exist',1,'')]):
            result=contracts.inspect_runtime()
        self.assertFalse(result['ready']);self.assertIn('does-not-exist',result['missing'])

if __name__=='__main__':unittest.main()
