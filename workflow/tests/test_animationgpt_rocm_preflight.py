import unittest
from types import SimpleNamespace
from unittest.mock import patch
from workflow.domains.animationgpt.rocm_inference import require_rocm

class AnimationGptRocmPreflightTest(unittest.TestCase):
    def test_rejects_cpu_and_missing_queue_ticket(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'ROCm PyTorch'):
                require_rocm(SimpleNamespace(version=SimpleNamespace(hip=None)))
            with self.assertRaisesRegex(RuntimeError, '대기열'):
                require_rocm(SimpleNamespace(version=SimpleNamespace(hip='7'), cuda=SimpleNamespace(is_available=lambda: True)))
    def test_rejects_unavailable_gpu(self):
        with patch.dict('os.environ', {'SLIME_GPU_QUEUE_TICKET':'ticket'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GPU'):
                require_rocm(SimpleNamespace(version=SimpleNamespace(hip='7'), cuda=SimpleNamespace(is_available=lambda: False)))
