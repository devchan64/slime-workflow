"""GPU 상태 카드에 필요한 실제 메모리 요약을 검증한다."""
import subprocess
import unittest
from unittest.mock import patch

from tools.review.common import gpu_status


class GpuStatusTests(unittest.TestCase):
    def test_gpu_status_includes_total_used_and_free_memory(self):
        compute_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='100, 512\n200, 768\n', stderr=''
        )
        memory_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='12288, 1280, 11008\n', stderr=''
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
