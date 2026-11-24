import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from workflow.generators.minimax_h3_ref2va.contiguous_attention import install_contiguous_attention


class Tensor:
    def __init__(self, length=32025, contiguous=False):
        self.shape = (1, length, 56, 128)
        self.device = types.SimpleNamespace(type='cuda')
        self.dtype = 'bf16'
        self.contiguous_value = contiguous
    def numel(self): return 100
    def element_size(self): return 2
    def permute(self, *dims): return self
    def contiguous(self): self.contiguous_value = True; return self
    def is_contiguous(self): return self.contiguous_value


class AttentionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.original = Mock(side_effect=AssertionError('비연속 기본 경로가 호출됨'))
        self.h3 = types.SimpleNamespace(dispatch_attention_fn=self.original)
        self.registry = types.SimpleNamespace(get_active_backend=lambda: ('native', None))
        fake_transformers = types.ModuleType('diffusers.models.transformers')
        fake_transformers.transformer_minimax_h3 = self.h3
        fake_dispatch = types.ModuleType('diffusers.models.attention_dispatch')
        fake_dispatch._AttentionBackendRegistry = self.registry
        fake_dispatch.AttentionBackendName = types.SimpleNamespace(NATIVE='native')
        self.modules = patch.dict(sys.modules, {'diffusers':types.ModuleType('diffusers'),
            'diffusers.models':types.ModuleType('diffusers.models'),
            'diffusers.models.transformers':fake_transformers,
            'diffusers.models.attention_dispatch':fake_dispatch})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.result = Tensor()
        self.sdpa = Mock(return_value=self.result)
        self.torch = types.SimpleNamespace(bfloat16='bf16',
            cuda=types.SimpleNamespace(mem_get_info=lambda device:(10*1024**3, 16*1024**3)),
            nn=types.SimpleNamespace(functional=types.SimpleNamespace(scaled_dot_product_attention=self.sdpa)))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = install_contiguous_attention(Path(self.temp.name), self.torch)

    def test_supported_calls_use_contiguous_qkv_without_baseline(self):
        for length in (2751, 32025):
            tensors = [Tensor(length) for _ in range(3)]
            self.h3.dispatch_attention_fn(*tensors)
            self.assertTrue(all(t.is_contiguous() for t in self.sdpa.call_args.args[:3]))
        self.assertEqual(self.sdpa.call_count, 2)
        self.original.assert_not_called()
        self.assertEqual([json.loads(line)['event'] for line in self.path.read_text().splitlines()],
                         ['contiguous_attention', 'contiguous_attention'])

    def test_unsupported_conditions_and_low_memory_stop_without_baseline(self):
        tensors = [Tensor() for _ in range(3)]
        with self.assertRaisesRegex(RuntimeError, '지원하지 않는'):
            self.h3.dispatch_attention_fn(*tensors, attn_mask=object())
        self.torch.cuda.mem_get_info = lambda device:(1000, 10000)
        with self.assertRaisesRegex(RuntimeError, '메모리 부족'):
            self.h3.dispatch_attention_fn(*tensors)
        self.original.assert_not_called()
        self.sdpa.assert_not_called()
        self.assertEqual([json.loads(line)['event'] for line in self.path.read_text().splitlines()],
                         ['stopped', 'stopped'])


if __name__ == '__main__':
    unittest.main()
