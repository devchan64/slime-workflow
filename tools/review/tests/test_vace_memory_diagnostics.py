"""CUDA 실행 없이 진단의 예외 보존·저장소 중복 제거 계약을 검사한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack
import torch

from generators.wan_vace.memory_diagnostics import record_cuda_memory_failure


class VaceMemoryDiagnosticsTest(unittest.TestCase):
    def test_oom_preserves_exception_and_deduplicates_storage(self):
        current_failure_error = torch.OutOfMemoryError('검증용 OOM')
        current_tensor_records = [
            {'device': 'cuda:0', 'storage_address': 123, 'storage_bytes': 1024},
            {'device': 'cuda:0', 'storage_address': 123, 'storage_bytes': 1024},
            {'device': 'cuda:0', 'storage_address': 456, 'storage_bytes': 2048},
        ]
        with tempfile.TemporaryDirectory() as current_directory_name, ExitStack() as current_patch_stack:
            current_history_mock = current_patch_stack.enter_context(patch('torch.cuda.memory._record_memory_history'))
            current_snapshot_mock = current_patch_stack.enter_context(patch('torch.cuda.memory._dump_snapshot'))
            current_patch_stack.enter_context(patch('generators.wan_vace.memory_diagnostics.collect_traceback_tensors', return_value=current_tensor_records))
            for current_function_name in ('memory_allocated', 'memory_reserved', 'max_memory_allocated'):
                current_patch_stack.enter_context(patch(f'torch.cuda.{current_function_name}', return_value=4096))
            with self.assertRaises(torch.OutOfMemoryError) as current_exception_context:
                with record_cuda_memory_failure(Path(current_directory_name)):
                    raise current_failure_error
            self.assertIs(current_exception_context.exception, current_failure_error)
            current_saved_record = json.loads((Path(current_directory_name) / 'cuda-oom-tensors.json').read_text())
            self.assertEqual(current_saved_record['traceback_unique_storage_bytes'], 3072)
            self.assertEqual(current_saved_record['allocated_bytes'], 4096)
            current_snapshot_mock.assert_called_once()
            self.assertEqual(current_history_mock.call_args.kwargs, {'enabled': None})

    def test_success_leaves_no_failure_artifact(self):
        with tempfile.TemporaryDirectory() as current_directory_name, patch('torch.cuda.memory._record_memory_history') as current_history_mock:
            with record_cuda_memory_failure(Path(current_directory_name)):
                pass
            self.assertEqual(list(Path(current_directory_name).iterdir()), [])
            self.assertEqual(current_history_mock.call_args.kwargs, {'enabled': None})
