"""GPU 상태 카드에 필요한 실제 메모리 요약을 검증한다."""
import subprocess
import json
import unittest
from unittest.mock import patch

from workflow.common import gpu_status
from workflow.common import gpu_job_queue, gpu_memory_history


class GpuStatusTests(unittest.TestCase):
    def test_hermes_and_vace_worker_are_identified_from_process_command(self):
        for command, label in ((b'python\0workflow/domains/hermes_agent/worker.py\0.tmp/test/hermes-agent/jobs/2026-11-22_10-32-00-62c162ba\0', '헤르메스 작업'),
                               (b'python\0generators/wan_vace/worker.py\0.tmp/test/wan22-vace/2026-11-22_14-18-27-ff28fdbc\0', 'Wan2.2 VACE')):
            with self.subTest(label=label), patch.object(gpu_status.Path,'read_bytes',return_value=command), patch.object(gpu_status.Path,'read_text',return_value='PPid:\t1\n'):
                record=gpu_status.identify_gpu_command(123)
                self.assertEqual(record['command'],label)
                self.assertIsNotNone(record['id'])

    def test_unrecognized_process_is_not_claimed_external(self):
        with patch.object(gpu_status.Path,'read_bytes',return_value=b'unknown\0'), patch.object(gpu_status.Path,'read_text',return_value='PPid:\t1\n'):
            record=gpu_status.identify_gpu_command(123)
        self.assertEqual(record['command'],'식별되지 않은 GPU 프로세스')
        self.assertIsNone(record['id'])

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

    def test_repeated_gpu_status_within_cache_does_not_repeat_smi(self):
        current_memory_values={f'{current_measure}_{current_domain}':{'value':1000 if current_measure=='total' else 500} for current_domain in ('gtt','vram') for current_measure in ('total','used','free')}
        current_process_result=subprocess.CompletedProcess([],0,json.dumps([]))
        current_memory_result=subprocess.CompletedProcess([],0,json.dumps({'gpu_data':[{'mem_usage':current_memory_values}]}))
        with patch.object(gpu_status,'_status_cache',(0,{})), patch.object(gpu_status.time,'monotonic',side_effect=[10,10,11]), patch.object(gpu_status.subprocess,'run',side_effect=[current_process_result,current_memory_result]) as current_command_mock:
            current_first_result=gpu_status.read_gpu_status()
            current_second_result=gpu_status.read_gpu_status()
        self.assertEqual(current_first_result,current_second_result)
        self.assertEqual(current_first_result['status'],'idle')
        self.assertEqual(current_command_mock.call_count,2)
        self.assertEqual(current_command_mock.call_args_list[0].args[0],['amd-smi','process','--json'])
        self.assertEqual(current_command_mock.call_args_list[1].args[0],['amd-smi','metric','-m','-u','--json'])

    def test_hermes_capacity_uses_queue_device_instead_of_gpu_sum(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_memory_capacity
        def build_device_memory(current_total_value,current_free_value):
            return {'mem_usage':{'total_gtt':{'value':1000},'used_gtt':{'value':100},'free_gtt':{'value':900},'total_vram':{'value':current_total_value},'used_vram':{'value':current_total_value-current_free_value},'free_vram':{'value':current_free_value}}}
        current_process_result=subprocess.CompletedProcess(args=[],returncode=0,stdout='[]',stderr='')
        current_metric_result=subprocess.CompletedProcess(args=[],returncode=0,stdout=json.dumps({'gpu_data':[build_device_memory(48000,4000),build_device_memory(48000,44000)]}),stderr='')
        with patch.object(gpu_status.subprocess,'run',side_effect=[current_process_result,current_metric_result]),patch('workflow.common.gpu_job_queue.read_host_available_memory',return_value=100000),patch('workflow.common.gpu_memory_history.estimate_required_memory',return_value={'required_memory_mib':32000}):
            gpu_status._status_cache=(0,{})
            current_status_value=gpu_status.read_gpu_status()
            current_capacity_value=read_hermes_memory_capacity(current_status_value)
        self.assertEqual(current_status_value['gpu_count'],2)
        self.assertEqual(current_status_value['vram_free_mib'],48000)
        self.assertEqual(current_capacity_value['gpu_free_mib'],4000)
        self.assertFalse(current_capacity_value['capacity_sufficient'])
        self.assertEqual(read_hermes_memory_capacity({'status':'idle','gtt_total_mib':1000,'gtt_free_mib':900,'vram_total_mib':96000,'vram_free_mib':48000}),{'status':'unavailable'})

    def test_kimodo_child_stage_is_not_momask_generation(self):
        with patch.object(gpu_status.Path,'read_bytes',return_value=b'python\0generators/momask/templates/run_stage.py\0generators/kimodo/anny_stage.py\0'),patch.object(gpu_status.Path,'read_text',return_value='PPid:\t1\n'):
            current_process_record=gpu_status.identify_gpu_command(123)
        self.assertEqual(current_process_record['command'],'Kimodo 모션·SOMA 렌더')

    def test_parent_detection_skips_non_gpu_intermediate_process(self):
        current_process_list = [{'process_info':{'pid':current_pid,'memory_usage':{'vram_mem':{'value':1048576,'unit':'B'},'gtt_mem':{'value':0,'unit':'B'}}}} for current_pid in (100,200)]
        current_metrics = {'gpu_data':[{'mem_usage':{f'{current_measure}_{current_domain}':{'value':1000 if current_measure=='total' else 0} for current_domain in ('gtt','vram') for current_measure in ('total','used','free')}}]}
        current_results = [subprocess.CompletedProcess([],0,json.dumps([{'process_list':current_process_list}])),subprocess.CompletedProcess([],0,json.dumps(current_metrics))]
        current_identity_records = [{'command':'Kimodo','id':'same','ancestor_pids':[50]},{'command':'Kimodo','id':'same','ancestor_pids':[150,100,50]}]
        with patch.object(gpu_status.subprocess,'run',side_effect=current_results),patch.object(gpu_status,'identify_gpu_command',side_effect=current_identity_records):
            gpu_status._status_cache = (0,{})
            current_status_record = gpu_status.read_gpu_status()
        self.assertIsNone(current_status_record['processes'][0]['gpu_parent_pid'])
        self.assertEqual(current_status_record['processes'][1]['gpu_parent_pid'],100)

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
