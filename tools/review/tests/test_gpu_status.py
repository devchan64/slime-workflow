"""GPU 상태 카드에 필요한 실제 메모리 요약을 검증한다."""
import subprocess
import json
import unittest
from unittest.mock import patch

from tools.review.common import gpu_status


class GpuStatusTests(unittest.TestCase):
    def test_gpu_status_includes_total_used_and_free_memory(self):
        compute_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps([{'gpu': 0, 'process_list': [{'process_info': {'pid': 100, 'memory_usage': {'vram_mem': {'value': 12 * 1048576, 'unit': 'B'}, 'gtt_mem': {'value': 500 * 1048576, 'unit': 'B'}}}}, {'process_info': {'pid': 200, 'memory_usage': {'vram_mem': {'value': 768 * 1048576, 'unit': 'B'}, 'gtt_mem': {'value': 0, 'unit': 'B'}}}}]}]), stderr=''
        )
        memory_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({'gpu_data': [{'mem_usage': {'total_gtt': {'value': 12288}, 'used_gtt': {'value': 1000}, 'used_vram': {'value': 280}, 'free_gtt': {'value': 11288}}}]}), stderr=''
        )
        with patch.object(gpu_status.subprocess, 'run', side_effect=[compute_result, memory_result]), patch.object(
            gpu_status, 'identify_gpu_command', side_effect=[
                {'command': '타일맵 생성', 'id': 'tile-job'},
                {'command': '캐릭터 애니메이션', 'id': 'animation-job'},
            ]
        ):
            gpu_status._status_cache = (0, {})
            status_record = gpu_status.read_gpu_status()

        self.assertEqual(status_record['status'], 'busy')
        self.assertEqual(status_record['memory_total_mib'], 12288)
        self.assertEqual(status_record['memory_used_mib'], 1280)
        self.assertEqual(status_record['memory_free_mib'], 11008)
        self.assertEqual([process_record['memory_mib'] for process_record in status_record['processes']], [512, 768])

    def test_kimodo_child_stage_is_not_momask_generation(self):
        with patch.object(gpu_status.Path,'read_bytes',return_value=b'python\0generators/momask/templates/run_stage.py\0generators/kimodo/anny_stage.py\0'),patch.object(gpu_status.Path,'read_text',return_value='PPid:\t1\n'):
            current_process_record=gpu_status.identify_gpu_command(123)
        self.assertEqual(current_process_record['command'],'Kimodo 모션·ANNY 렌더')
