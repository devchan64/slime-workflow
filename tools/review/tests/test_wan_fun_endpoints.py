"""양끝 조건 저장·복원과 공식 시간 마스크의 경계 검증."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.wan_fun.contracts import validate_fun_request
from tools.review.domains.wan_fun.generation import FunControlGenerationManager


class FunEndpointContractTests(unittest.TestCase):
    def test_endpoint_roundtrip_and_invalid_combinations(self):
        from tools.review.ui.gradio.wan_fun_app import build_fun_payload, restore_fun_inputs
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory = Path(current_directory_name)/'sample'
            current_job_directory.mkdir()
            current_image_path = current_job_directory/'reference-1.png'
            Image.new('RGB', (832, 480), 'white').save(current_image_path)
            current_payload_record = build_fun_payload(str(current_image_path), None, None, 'pose', 'A person rests.', '', 21, 42, 20, 5, 6, .3, 'reference-only', False, False, str(current_image_path), None, True)
            current_reused_record = build_fun_payload(str(current_image_path), None, None, 'pose', 'A person rests.', '', 21, 42, 20, 5, 6, .3, 'reference-only', False, False, str(current_image_path), str(current_image_path), True)
            self.assertNotIn('end_image', current_reused_record)
            self.assertTrue(current_reused_record['end_image_same_as_start'])
            current_valid_record = validate_fun_request(current_payload_record)
            current_saved_record = FunControlGenerationManager.save_generation_attachments(None, current_job_directory, current_valid_record)
            self.assertNotIn('start_image', current_saved_record)
            self.assertEqual((current_job_directory/'start-image.png').read_bytes(), current_image_path.read_bytes())
            current_saved_record['references'] = ['reference-1.png']
            with patch('tools.review.ui.gradio.wan_fun_app.FUN_JOB_STORAGE', Path(current_directory_name)):
                current_restored_values = restore_fun_inputs({'id':'sample', 'request':current_saved_record})
            self.assertEqual(current_restored_values[15:18], (str(current_job_directory/'start-image.png'), None, True))
            for current_invalid_fields in ({'start_image': ''}, {'end_image': current_payload_record['start_image']}, {'end_image_same_as_start': 'true'}):
                with self.assertRaises(ValueError):
                    validate_fun_request({**current_payload_record, **current_invalid_fields})

    def test_temporal_mask_and_control_preservation(self):
        import torch
        from types import SimpleNamespace
        from generators.wan_fun.endpoints import build_fun_endpoint_tensors, apply_fun_endpoint_conditions
        current_start_tensor = torch.ones((1, 8, 8, 3))
        current_end_tensor = torch.zeros_like(current_start_tensor)
        for current_frame_count in (5, 21, 129):
            current_video_tensor, current_mask_tensor = build_fun_endpoint_tensors(current_frame_count, current_start_tensor, current_end_tensor)
            self.assertTrue(torch.equal(current_video_tensor[:1], current_start_tensor))
            self.assertTrue(torch.equal(current_video_tensor[-1:], current_end_tensor))
            self.assertTrue((current_video_tensor[1:-1] == .5).all())
            # 첫 프레임을 네 번 확장하고 마지막 프레임만 관측하는 공식 마스크.
            current_expected_mask = torch.ones(current_frame_count+3)
            current_expected_mask[:4] = 0
            current_expected_mask[-1] = 0
            self.assertTrue(torch.equal(current_mask_tensor.transpose(1, 2).flatten(), current_expected_mask))
        current_latent_tensor = torch.randn(1, 32, 6, 1, 1)
        current_reference_data = [torch.ones(1)]
        current_metadata_record = {'concat_latent_image':current_latent_tensor, 'reference_latents':current_reference_data, 'concat_mask_index':16}
        current_conditions_group = [[torch.ones(1), current_metadata_record]]
        current_vae_model = SimpleNamespace(latent_channels=16, encode=lambda current_video_tensor: torch.full((1,16,6,1,1), 7.))
        current_output_values = apply_fun_endpoint_conditions((current_conditions_group, current_conditions_group, {'samples': 'unchanged'}), current_vae_model, 21, current_start_tensor, current_end_tensor)
        for current_condition_group in current_output_values[:2]:
            current_result_record = current_condition_group[0][1]
            self.assertTrue(torch.equal(current_result_record['concat_latent_image'][:,:16], current_latent_tensor[:,:16]))
            self.assertTrue((current_result_record['concat_latent_image'][:,16:] == 7).all())
            self.assertIs(current_result_record['reference_latents'], current_reference_data)
            self.assertEqual(current_result_record['concat_mask_index'],16)
        self.assertEqual(current_output_values[2], {'samples':'unchanged'})
