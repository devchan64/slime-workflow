"""음악·효과음 위임의 서비스 분리, 결과 경로, 중지 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import audio_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesAudioOperationsTests(unittest.TestCase):
    def test_services_validate_and_reuse_independent_receipts(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_requests_value={'music-heartmula':{'prompt':'piano','lyrics':'[Verse]\nHello','duration_seconds':10,'seed':7},'sfx-dasheng-audiogen':{'prompt':'water splash','seed':42}}
        with TemporaryDirectory() as current_root_name, patch.object(audio_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier}) as current_gateway_mock:
            for current_index_value,current_service_name in enumerate(current_requests_value):
                current_request_id='audio_request_'+str(current_index_value)
                self.assertFalse(audio_operations.submit_hermes_audio_request(current_request_id,current_service_name,current_requests_value[current_service_name])['duplicate'])
                self.assertTrue(audio_operations.submit_hermes_audio_request(current_request_id,current_service_name,current_requests_value[current_service_name])['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,2)
            with self.assertRaises(ValueError):
                audio_operations.read_hermes_audio_status('audio_request_0','sfx-dasheng-audiogen')
            with self.assertRaises(ValueError):
                audio_operations.validate_hermes_audio_request('music-heartmula',{'action':'prepare'})
            with self.assertRaises(ValueError):
                audio_operations.validate_hermes_audio_service('music-magenta')

    def test_audio_resume_receipts_prevent_duplicate_and_preserve_unknown(self):
        from pathlib import Path
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_fingerprint_value='a'*64
        with TemporaryDirectory() as current_root_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_root_name)),patch.object(audio_resume_operations,'call_hermes_audio_service') as current_gateway_mock:
            current_gateway_mock.return_value={'id':current_job_identifier,'service':'music-heartmula','status':'failed','expected_resume_fingerprint':current_fingerprint_value}
            self.assertEqual(audio_resume_operations.preview_hermes_audio_resume('music-heartmula',current_job_identifier)['status'],'failed')
            current_gateway_mock.return_value={'id':current_job_identifier,'status':'queued'}
            current_first_value=audio_resume_operations.submit_hermes_audio_resume_once('resume_request_123','music-heartmula',current_job_identifier,current_fingerprint_value)
            self.assertEqual(current_first_value['state'],'accepted')
            self.assertTrue(audio_resume_operations.submit_hermes_audio_resume_once('resume_request_123','music-heartmula',current_job_identifier,current_fingerprint_value)['duplicate'])
            with self.assertRaises(ValueError):audio_resume_operations.submit_hermes_audio_resume_once('resume_request_123','music-heartmula',current_job_identifier,'b'*64)
            current_gateway_mock.side_effect=OSError('response lost')
            with self.assertRaises(OSError):audio_resume_operations.submit_hermes_audio_resume_once('resume_request_lost','music-heartmula',current_job_identifier,'b'*64)
            self.assertEqual(audio_resume_operations.read_hermes_audio_resume_receipt('resume_request_lost')['state'],'unknown')
            self.assertTrue(audio_resume_operations.submit_hermes_audio_resume_once('resume_request_lost','music-heartmula',current_job_identifier,'b'*64)['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,3)

    def test_audio_resume_concurrent_same_request_dispatches_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        import threading
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_fingerprint_value='a'*64
        current_start_barrier=threading.Barrier(2)
        def submit_concurrent_request():
            current_start_barrier.wait(timeout=5)
            return audio_resume_operations.submit_hermes_audio_resume_once('resume_concurrent_123','music-heartmula',current_job_identifier,current_fingerprint_value)
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier,'status':'queued'}) as current_service_mock:
            with ThreadPoolExecutor(max_workers=2) as current_executor_value:
                current_result_values=list(current_executor_value.map(lambda current_unused_value:submit_concurrent_request(),range(2)))
            self.assertEqual(sum(not item['duplicate'] for item in current_result_values),1)
            self.assertTrue(all(item['state']=='accepted' for item in current_result_values))
            current_service_mock.assert_called_once()

    def test_audio_resume_unverified_response_is_not_resent(self):
        from pathlib import Path
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service',return_value={'id':'other','status':'queued'}) as current_service_mock:
            with self.assertRaises(ValueError):audio_resume_operations.submit_hermes_audio_resume_once('resume_invalid_123','music-heartmula',current_job_identifier,'a'*64)
            current_receipt_value=audio_resume_operations.read_hermes_audio_resume_receipt('resume_invalid_123')
            self.assertEqual(current_receipt_value['state'],'unknown')
            self.assertTrue(audio_resume_operations.submit_hermes_audio_resume_once('resume_invalid_123','music-heartmula',current_job_identifier,'a'*64)['duplicate'])
            current_service_mock.assert_called_once()

    def test_audio_resume_separate_processes_and_crash_recovery(self):
        import json
        import subprocess
        import sys
        from tools.review.domains.hermes_agent.audio_resume_operations import validate_audio_resume_target
        from tools.review.domains.hermes_agent.resume_receipt_store import read_resume_receipt_record
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_child_source="""import json, pathlib, sys, time
from tools.review.domains.hermes_agent.audio_resume_operations import validate_audio_resume_target
from tools.review.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
root=pathlib.Path(sys.argv[1])
def submit(service,job,fingerprint):
 with (root/'calls').open('a') as stream: stream.write('called\\n')
 time.sleep(.15)
 return {'id':job,'status':'queued'}
print(json.dumps(submit_resume_receipt_once(root/'receipts','resume_process_123','music-heartmula','2026-11-18_00-00-00-12345678','a'*64,validate_audio_resume_target,submit)))
"""
            current_children=[subprocess.Popen([sys.executable,'-c',current_child_source,current_directory_name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for current_index_value in range(3)]
            current_result_values=[]
            for current_child_value in current_children:
                current_stdout_text,current_stderr_text=current_child_value.communicate(timeout=15)
                self.assertEqual(current_child_value.returncode,0,current_stderr_text)
                current_result_values.append(json.loads(current_stdout_text))
            self.assertEqual(sum(not item['duplicate'] for item in current_result_values),1)
            self.assertEqual((current_root_path/'calls').read_text().count('called'),1)
            current_crash_source="""import os,sys
from tools.review.domains.hermes_agent.audio_resume_operations import validate_audio_resume_target
from tools.review.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
submit_resume_receipt_once(sys.argv[1],'resume_crashed_123','music-heartmula','2026-11-18_00-00-00-12345678','b'*64,validate_audio_resume_target,lambda service,job,fingerprint:os._exit(37))
"""
            current_crash_value=subprocess.run([sys.executable,'-c',current_crash_source,str(current_root_path/'receipts')],timeout=15)
            self.assertEqual(current_crash_value.returncode,37)
            current_receipt_value=read_resume_receipt_record(current_root_path/'receipts','resume_crashed_123',validate_audio_resume_target)
            self.assertEqual(current_receipt_value['state'],'unknown')
            self.assertEqual(current_receipt_value['job_id'],current_job_identifier)

    def test_audio_resume_different_ids_race_across_processes(self):
        import json
        import subprocess
        import sys
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_child_source="""import json, pathlib, sys, time
from tools.review.domains.hermes_agent.audio_resume_operations import validate_audio_resume_target
from tools.review.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
root=pathlib.Path(sys.argv[1])
def submit(service,job,fingerprint):
 with (root/'calls').open('a') as stream: stream.write('called\\n')
 time.sleep(.15)
 return {'id':job,'status':'queued'}
try:
 result=submit_resume_receipt_once(root/'receipts',sys.argv[2],'music-heartmula','2026-11-18_00-00-00-12345678','a'*64,validate_audio_resume_target,submit)
 print(json.dumps({'state':result['state']}))
except ValueError as error:
 print(json.dumps({'error':str(error)}))
"""
            current_children=[subprocess.Popen([sys.executable,'-c',current_child_source,current_directory_name,f'resume_race_{current_index_value:03d}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for current_index_value in range(3)]
            current_result_values=[]
            for current_child_value in current_children:
                current_stdout_text,current_stderr_text=current_child_value.communicate(timeout=15)
                self.assertEqual(current_child_value.returncode,0,current_stderr_text)
                current_result_values.append(json.loads(current_stdout_text))
            self.assertEqual(sum(current_item_value.get('state')=='accepted' for current_item_value in current_result_values),1)
            self.assertEqual(sum('기존 접수' in current_item_value.get('error','') for current_item_value in current_result_values),2)
            self.assertEqual((current_root_path/'calls').read_text().count('called'),1)

    def test_audio_resume_rejects_same_target_under_different_request_id(self):
        from pathlib import Path
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service',side_effect=OSError('response lost')) as current_service_mock:
            with self.assertRaises(OSError):audio_resume_operations.submit_hermes_audio_resume_once('resume_original_123','music-heartmula',current_job_identifier,'a'*64)
            with self.assertRaisesRegex(ValueError,'기존 접수'):
                audio_resume_operations.submit_hermes_audio_resume_once('resume_different_123','music-heartmula',current_job_identifier,'a'*64)
            self.assertEqual(audio_resume_operations.read_hermes_audio_resume_receipt('resume_original_123')['state'],'unknown')
            current_service_mock.assert_called_once()

    def test_audio_paths_are_same_service_job_and_attempt(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_good_path='/music-heartmula/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/music.wav'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('audio_request_123','music-heartmula',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(audio_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier,'status':'completed','audio':current_good_path,'log':'private'}) as current_gateway_mock:
                current_result_value=audio_operations.read_hermes_audio_status('audio_request_123','music-heartmula')
                self.assertEqual(current_result_value['job']['audio'],current_good_path)
                self.assertEqual(current_result_value['job']['result_status'],'available')
                self.assertNotIn('private',str(current_result_value))
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'completed','audio':'https://evil.invalid/audio.wav'}
                current_invalid_result=audio_operations.read_hermes_audio_status('audio_request_123','music-heartmula')['job']
                self.assertIsNone(current_invalid_result['audio'])
                self.assertEqual(current_invalid_result['result_status'],'unavailable')
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'running'}
                self.assertEqual(audio_operations.read_hermes_audio_status('audio_request_123','music-heartmula')['job']['result_status'],'not_ready')
                with self.assertRaises(ValueError):
                    audio_operations.cancel_hermes_audio_request('audio_request_123','music-heartmula','2026-11-18_00-00-00-ffffffff')

    def test_lost_audio_response_is_not_resent(self):
        with TemporaryDirectory() as current_root_name, patch.object(audio_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(audio_operations,'call_hermes_audio_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                audio_operations.submit_hermes_audio_request('audio_unknown_123','sfx-dasheng-audiogen',{'prompt':'water','seed':42})
            self.assertEqual(audio_operations.read_hermes_audio_status('audio_unknown_123','sfx-dasheng-audiogen')['receipt']['state'],'unknown')
            self.assertTrue(audio_operations.submit_hermes_audio_request('audio_unknown_123','sfx-dasheng-audiogen',{'prompt':'water','seed':42})['duplicate'])
            current_gateway_mock.assert_called_once()

    def test_source_history_rejects_incomplete_or_mismatched_pages(self):
        from tools.review.domains.hermes_agent.audio_operations import sanitize_hermes_source_history
        current_request_value={'offset':1,'limit':1,'snapshot':'a'*64}
        current_record_value={'id':'legacy-id','recorded_status':'completed','status_source':'index'}
        current_result_value={'records':[current_record_value],'total':3,'offset':1,'next_offset':2,'snapshot':'a'*64,'unavailable_count':0}
        self.assertEqual(sanitize_hermes_source_history('music-heartmula',current_request_value,current_result_value)['records'],[current_record_value])
        for current_bad_result in ({**current_result_value,'records':[]},{**current_result_value,'next_offset':None},{**current_result_value,'snapshot':'b'*64},{**current_result_value,'next_offset':True}):
            with self.subTest(result=current_bad_result),self.assertRaises(ValueError):
                sanitize_hermes_source_history('music-heartmula',current_request_value,current_bad_result)

    def test_retired_audio_history_does_not_enable_delegation(self):
        current_response_value={'records':[],'total':0,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        with patch.object(audio_operations,'execute_management_command',return_value=current_response_value) as current_gateway_mock:
            self.assertEqual(audio_operations.read_hermes_audio_source_history('music-magenta',{})['records'],[])
            self.assertEqual(current_gateway_mock.call_args.args[:3],('music-magenta','history-observe',{}))
        with self.assertRaises(ValueError):
            audio_operations.submit_hermes_audio_request('request_123','music-magenta',{})
