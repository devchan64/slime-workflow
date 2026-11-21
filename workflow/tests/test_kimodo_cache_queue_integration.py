"""실제 CPU 프로세스로 캐시 검사와 생성기의 대기열 배타성을 검증한다."""
import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import time
import unittest


def execute_isolated_queue_job(current_queue_path,current_job_path):
    from workflow.common import gpu_job_queue as current_queue_module
    current_queue_module.GPU_QUEUE_DIRECTORY=Path(current_queue_path)
    current_queue_module.GPU_POLL_INTERVAL=0.05
    current_queue_module.read_gpu_memory=lambda:(100000,100000)
    current_queue_module.read_gpu_memory_domain=lambda:'vram'
    current_queue_module.read_host_available_memory=lambda:100000
    current_queue_module.read_worker_memory=lambda *current_args,**current_kwargs:0
    current_queue_module.identify_execution_command=lambda *current_args,**current_kwargs:'isolated-cpu-test'
    current_queue_module.estimate_required_memory=lambda *current_args,**current_kwargs:{'required_memory_mib':1,'samples':0}
    current_queue_module.save_memory_observation=lambda *current_args,**current_kwargs:{}
    class IsolatedTelemetryRecorder:
        def __init__(self,*current_args):pass
        def capture_generation_memory(self):pass
        def save_generation_metrics(self):pass
        def start_generation_telemetry(self):pass
        def finish_generation_telemetry(self,*current_args):pass
    current_queue_module.QueueGenerationTelemetry=IsolatedTelemetryRecorder
    current_queue_module.execute_queued_generation(current_job_path)


class KimodoCacheQueueIntegrationTests(unittest.TestCase):
    def test_live_cache_check_blocks_generation_until_release(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_queue_path=current_root_path/'queue'
            current_cache_job=current_root_path/'cache'
            current_image_job=current_root_path/'image'
            current_worker_script=current_root_path/'worker.py'
            current_worker_script.write_text("import pathlib,sys,time\np=pathlib.Path(sys.argv[1]);(p/'started').touch()\nwhile not (p/'release').exists():time.sleep(0.02)\n")
            for current_job_path,current_service_name in ((current_cache_job,'kimodo-cache-check'),(current_image_job,'image')):
                current_job_path.mkdir()
                (current_job_path/'status.json').write_text(json.dumps({'status':'queued'}))
                (current_job_path/'gpu-command.json').write_text(json.dumps({'service':current_service_name,'command':[sys.executable,str(current_worker_script),str(current_job_path)]}))
            current_context=multiprocessing.get_context('fork')
            current_cache_process=current_context.Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_cache_job)))
            current_image_process=current_context.Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_image_job)))
            def wait_for_test_condition(current_condition_value,current_failure_message):
                current_deadline_value=time.monotonic()+8
                while not current_condition_value():
                    if time.monotonic()>current_deadline_value:self.fail(current_failure_message)
                    time.sleep(0.05)
            try:
                current_cache_process.start()
                wait_for_test_condition(lambda:(current_cache_job/'started').exists(),'캐시 작업 시작 실패')
                current_image_process.start()
                wait_for_test_condition(lambda:(current_image_job/'status.json').exists() and json.loads((current_image_job/'status.json').read_text()).get('queue_position')==1,'생성 작업이 대기열에 등록되지 않음')
                self.assertFalse((current_image_job/'started').exists())
                (current_cache_job/'release').touch()
                current_cache_process.join(timeout=8)
                self.assertEqual(current_cache_process.exitcode,0)
                wait_for_test_condition(lambda:(current_image_job/'started').exists(),'캐시 작업 종료 뒤 생성 작업 시작 실패')
                (current_image_job/'cancel.request').touch()
                current_image_process.join(timeout=8)
                self.assertEqual(current_image_process.exitcode,0)
                self.assertEqual(json.loads((current_image_job/'status.json').read_text())['status'],'cancelled')
                self.assertEqual(list((current_queue_path/'active').glob('*.json')),[])
                self.assertEqual(list(current_queue_path.glob('*.json')),[])
            finally:
                for current_job_path in (current_cache_job,current_image_job):
                    (current_job_path/'release').touch()
                    (current_job_path/'cancel.request').touch()
                for current_process_value in (current_cache_process,current_image_process):
                    if current_process_value.pid is not None:
                        current_process_value.join(timeout=4)
                        if current_process_value.is_alive():
                            current_process_value.terminate()
                            current_process_value.join(timeout=4)
