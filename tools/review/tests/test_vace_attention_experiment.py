"""진단용 시간 토큰 제한을 명시적 마스크와 대조한다."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class VaceAttentionExperimentTest(unittest.TestCase):
    def test_prefix_mask_and_cross_attention(self):
        import torch
        from generators.wan_vace import attention_experiment as current_experiment_module
        def calculate_reference_attention(current_query_tensor, current_key_tensor, v, **current_options_record):
            return torch.nn.functional.scaled_dot_product_attention(current_query_tensor.transpose(1,2), current_key_tensor.transpose(1,2), v.transpose(1,2)).transpose(1,2)
        current_query_tensor = torch.randn(1,6,2,4)
        current_key_tensor = torch.randn_like(current_query_tensor)
        current_value_tensor = torch.randn_like(current_query_tensor)
        current_attention_module = SimpleNamespace(attention=calculate_reference_attention)
        with patch.object(current_experiment_module, 'EXPERIMENT_PREFIX_TOKEN_COUNT', 3), patch.object(current_experiment_module, 'EXPERIMENT_TOTAL_TOKEN_COUNT', 6):
            current_experiment_module.install_prefix_attention_isolation(current_attention_module)
            current_actual_output = current_attention_module.attention(current_query_tensor,current_key_tensor,v=current_value_tensor)
            current_expected_mask = torch.ones(6,6,dtype=torch.bool)
            current_expected_mask[:3,3:] = False
            current_expected_output = torch.nn.functional.scaled_dot_product_attention(current_query_tensor.transpose(1,2),current_key_tensor.transpose(1,2),current_value_tensor.transpose(1,2),attn_mask=current_expected_mask).transpose(1,2)
            torch.testing.assert_close(current_actual_output,current_expected_output)
            torch.testing.assert_close(current_attention_module.attention(current_query_tensor,current_key_tensor[:,:2],v=current_value_tensor[:,:2]),calculate_reference_attention(current_query_tensor,current_key_tensor[:,:2],v=current_value_tensor[:,:2]))
            with self.assertRaises(ValueError):
                current_attention_module.attention(current_query_tensor,current_key_tensor,v=current_value_tensor,causal=True)

    def test_branch_selection_and_restoration(self):
        import torch
        from generators.wan_vace import attention_experiment as current_experiment_module
        current_call_lengths = []
        def calculate_reference_attention(current_query_tensor, current_key_tensor, v, **current_options_record):
            current_call_lengths.append(current_query_tensor.shape[1])
            return current_query_tensor
        current_attention_module = SimpleNamespace(attention=calculate_reference_attention)
        class BranchAttentionProbe(torch.nn.Module):
            def forward(self, current_input_tensor):
                return current_attention_module.attention(current_input_tensor, current_input_tensor, v=current_input_tensor)
        current_base_attention = BranchAttentionProbe()
        current_vace_attention = BranchAttentionProbe()
        current_model_record = SimpleNamespace(blocks=[SimpleNamespace(self_attn=current_base_attention)], vace_blocks=[SimpleNamespace(self_attn=current_vace_attention)])
        current_empty_model = SimpleNamespace(blocks=[], vace_blocks=[])
        current_pipeline_record = SimpleNamespace(transformer=current_model_record, transformer_2=current_empty_model)
        with patch.object(current_experiment_module, 'EXPERIMENT_PREFIX_TOKEN_COUNT', 3), patch.object(current_experiment_module, 'EXPERIMENT_TOTAL_TOKEN_COUNT', 6):
            current_experiment_module.install_prefix_attention_isolation(current_attention_module, current_pipeline_record, 'base')
            current_base_attention(torch.zeros(1,6,2,4))
            self.assertEqual(current_call_lengths, [3,3])
            current_call_lengths.clear()
            current_vace_attention(torch.zeros(1,6,2,4))
            self.assertEqual(current_call_lengths, [6])
            self.assertIs(current_attention_module.attention, calculate_reference_attention)
