"""GPU 상태 카드에 필요한 실제 메모리 요약을 검증한다."""
import subprocess
import json
import unittest
from unittest.mock import patch

from tools.review.common import gpu_status
from tools.review.common import gpu_job_queue, gpu_memory_history


class GpuStatusTests(unittest.TestCase):
    def test_gpu_status_includes_total_used_and_free_memory(self):
        compute_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps([{'gpu': 0, 'process_list': [{'process_info': {'pid': 100, 'memory_usage': {'vram_mem': {'value': 12 * 1048576, 'unit': 'B'}, 'gtt_mem': {'value': 500 * 1048576, 'unit': 'B'}}}}, {'process_info': {'pid': 200, 'memory_usage': {'vram_mem': {'value': 768 * 1048576, 'unit': 'B'}, 'gtt_mem': {'value': 0, 'unit': 'B'}}}}]}]), stderr=''
        )
        memory_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({'gpu_data': [{'mem_usage': {'total_gtt': {'value': 12288}, 'used_gtt': {'value': 1000}, 'used_vram': {'value': 280}, 'free_gtt': {'value': 11288}, 'total_vram': {'value': 4096}, 'free_vram': {'value': 3816}}}]}), stderr=''
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
        self.assertEqual(status_record['memory_used_mib'], 1000)
        self.assertEqual(status_record['memory_free_mib'], 11288)
        self.assertEqual([status_record[f'gtt_{current_name}_mib'] for current_name in ('total','used','free')], [12288,1000,11288])
        self.assertEqual([status_record[f'vram_{current_name}_mib'] for current_name in ('total','used','free')], [4096,280,3816])
        self.assertEqual(status_record['processes'][0]['gtt_memory_mib'], 500)
        self.assertEqual(status_record['processes'][0]['vram_memory_mib'], 12)
        self.assertEqual([process_record['memory_mib'] for process_record in status_record['processes']], [512, 768])

    def test_kimodo_child_stage_is_not_momask_generation(self):
        with patch.object(gpu_status.Path,'read_bytes',return_value=b'python\0generators/momask/templates/run_stage.py\0generators/kimodo/anny_stage.py\0'),patch.object(gpu_status.Path,'read_text',return_value='PPid:\t1\n'):
            current_process_record=gpu_status.identify_gpu_command(123)
        self.assertEqual(current_process_record['command'],'Kimodo 모션·SOMA 렌더')

    def test_queue_uses_gtt_free_without_subtracting_vram(self):
        current_metrics = {'gpu_data':[{'mem_usage':{'total_gtt':{'value':12288},'free_gtt':{'value':11288},'used_vram':{'value':280}}}]}
        with patch.object(gpu_job_queue.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,json.dumps(current_metrics))):
            self.assertEqual(gpu_job_queue.read_gpu_memory(), (12288,11288))

    def test_queue_uses_vram_when_vram_is_larger_pool(self):
        current_metrics = {'gpu_data':[{'mem_usage':{'total_gtt':{'value':15542},'free_gtt':{'value':15450},'total_vram':{'value':98304},'free_vram':{'value':96000}}}]}
        with patch.object(gpu_job_queue.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,json.dumps(current_metrics))):
            self.assertEqual(gpu_job_queue.read_gpu_memory(), (98304,96000))
            self.assertEqual(gpu_job_queue.read_gpu_memory_domain(), 'vram')

    def test_worker_measurement_selects_requested_pool(self):
        current_processes = [{'process_list':[{'process_info':{'pid':123,'memory_usage':{'gtt_mem':{'value':500*1048576,'unit':'B'},'vram_mem':{'value':12*1048576,'unit':'B'}}}}]}]
        with patch.object(gpu_memory_history.Path, 'glob', return_value=[]), patch.object(gpu_memory_history.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,json.dumps(current_processes))):
            self.assertEqual(gpu_memory_history.read_worker_memory(123,current_memory_domain='gtt'),500)
            self.assertEqual(gpu_memory_history.read_worker_memory(123,current_memory_domain='vram'),12)
            self.assertEqual(gpu_memory_history.read_worker_memory(123),512)
