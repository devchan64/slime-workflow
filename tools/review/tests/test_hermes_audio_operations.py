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

    def test_audio_resume_preview_passes_verified_availability_and_marks_old_server_unknown(self):
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_preview_record={'id':current_job_identifier,'service':'music-heartmula','status':'failed','expected_resume_fingerprint':'a'*64}
        with patch.object(audio_resume_operations,'call_hermes_audio_service',return_value=current_preview_record):
            self.assertEqual(audio_resume_operations.preview_hermes_audio_resume('music-heartmula',current_job_identifier)['resume_availability'],'unknown')
            current_preview_record['resume_availability']='download_running'
            self.assertEqual(audio_resume_operations.preview_hermes_audio_resume('music-heartmula',current_job_identifier)['resume_availability'],'download_running')
            current_preview_record['resume_availability']='invalid'
            with self.assertRaises(ValueError):audio_resume_operations.preview_hermes_audio_resume('music-heartmula',current_job_identifier)

    def test_audio_resume_preflight_rejects_conflicts_without_receipt_or_dispatch(self):
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_fingerprint_value='a'*64
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service') as current_service_mock:
            for current_availability_value in ('download_running','other_preparation','unknown'):
                current_service_mock.return_value={'id':current_job_identifier,'service':'music-heartmula','status':'failed','expected_resume_fingerprint':current_fingerprint_value,'resume_availability':current_availability_value}
                with self.subTest(current_availability_value=current_availability_value):
                    current_result_value=audio_resume_operations.submit_hermes_audio_resume_once('resume_preflight_123','music-heartmula',current_job_identifier,current_fingerprint_value)
                    self.assertEqual(current_result_value['state'],'blocked')
                    self.assertEqual(current_result_value['reason'],'unavailable' if current_availability_value=='unknown' else current_availability_value)
                self.assertEqual(audio_resume_operations.read_hermes_audio_resume_receipt('resume_preflight_123')['state'],'not_found')
            self.assertTrue(all(current_call.args[1]=='resume-preview' for current_call in current_service_mock.call_args_list))

    def test_audio_resume_preflight_blocks_changed_record_without_receipt(self):
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_preview_record={'id':current_job_identifier,'service':'music-heartmula','status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'available'}
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service',return_value=current_preview_record) as current_gateway_mock:
            current_result_value=audio_resume_operations.submit_hermes_audio_resume_once('resume_changed_123','music-heartmula',current_job_identifier,'a'*64)
            self.assertEqual((current_result_value['state'],current_result_value['reason']),('blocked','fingerprint_changed'))
            self.assertEqual(audio_resume_operations.read_hermes_audio_resume_receipt('resume_changed_123')['state'],'not_found')
            self.assertEqual(current_gateway_mock.call_count,1)
            self.assertEqual(current_gateway_mock.call_args.args[1],'resume-preview')

    def test_audio_resume_receipts_prevent_duplicate_and_preserve_unknown(self):
        self.enterContext(patch('tools.review.domains.hermes_agent.audio_resume_operations.validate_current_audio_resume_preflight',return_value=None))
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
        self.enterContext(patch('tools.review.domains.hermes_agent.audio_resume_operations.validate_current_audio_resume_preflight',return_value=None))
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
        self.enterContext(patch('tools.review.domains.hermes_agent.audio_resume_operations.validate_current_audio_resume_preflight',return_value=None))
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
        self.enterContext(patch('tools.review.domains.hermes_agent.audio_resume_operations.validate_current_audio_resume_preflight',return_value=None))
        from pathlib import Path
        from tools.review.domains.hermes_agent import audio_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service',side_effect=OSError('response lost')) as current_service_mock:
            with self.assertRaises(OSError):audio_resume_operations.submit_hermes_audio_resume_once('resume_original_123','music-heartmula',current_job_identifier,'a'*64)
            with self.assertRaisesRegex(ValueError,'기존 접수'):
                audio_resume_operations.submit_hermes_audio_resume_once('resume_different_123','music-heartmula',current_job_identifier,'a'*64)
            self.assertEqual(audio_resume_operations.read_hermes_audio_resume_receipt('resume_original_123')['state'],'unknown')
            current_service_mock.assert_called_once()

    def test_source_audio_status_through_hermes_command(self):
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_payload_value={'service':'music-heartmula','job_id':current_job_identifier}
        with patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier,'status':'queued'}) as current_service_mock:
            current_result_value=HermesServiceManager().execute_hermes_command('hermes-audio-source-status',current_payload_value)
            self.assertEqual((current_result_value['service'],current_result_value['job_id'],current_result_value['job']['status']),('music-heartmula',current_job_identifier,'queued'))
            with self.assertRaises(ValueError):HermesServiceManager().execute_hermes_command('hermes-audio-source-status',{**current_payload_value,'extra':True})
            current_service_mock.assert_called_once()

    def test_source_audio_status_reads_actual_service_records_over_gateway(self):
        import json
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from tools.review.common.management_gateway import ManagementCommandGateway,execute_management_command
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.music.generation import MusicGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_handlers_value={}
            for current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
                current_manager_value=MusicGenerationManager(current_service_name)
                current_manager_value.job_storage_root=current_root_path/current_service_name/'jobs'
                current_manager_value.history_storage_root=current_root_path/current_service_name/'history'
                current_job_path=current_manager_value.job_storage_root/current_job_identifier
                current_job_path.mkdir(parents=True)
                (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
                (current_job_path/'result.json').write_text(json.dumps({'format':'wav','attempt':'a'*32}))
                current_handlers_value[current_service_name]=current_manager_value.handle_music_request
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_handlers_value['hermes-agent']=current_hermes_manager.handle_hermes_request
            current_gateway_value=ManagementCommandGateway(current_handlers_value)
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}):
                    for current_service_name,current_file_name in (('music-heartmula','music.wav'),('sfx-dasheng-audiogen','sound.wav')):
                        current_result_value=execute_management_command('hermes-agent','hermes-audio-source-status',{'service':current_service_name,'job_id':current_job_identifier},current_gateway_url)
                        self.assertEqual(current_result_value['job']['status'],'completed')
                        self.assertEqual(current_result_value['job']['result_status'],'available')
                        self.assertEqual(current_result_value['job']['audio'],'/'+current_service_name+'/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/'+current_file_name)
                        self.assertNotIn(str(current_root_path),str(current_result_value))
                        self.assertFalse((current_root_path/current_service_name/'history').exists())
                        current_job_path=current_root_path/current_service_name/'jobs'/current_job_identifier
                        self.assertEqual(json.loads((current_job_path/'status.json').read_text()),{'status':'completed'})
                        self.assertEqual(json.loads((current_job_path/'result.json').read_text()),{'format':'wav','attempt':'a'*32})
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_server_thread.join(timeout=5)

    def test_media_result_links_cross_runtime_proxy_to_actual_service_files(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import Request,urlopen
        from tools.review.common.management_gateway import ManagementCommandGateway,execute_management_command
        from tools.review.common.management_transport import proxy_management_request
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent import video_operations
        from tools.review.domains.music.generation import MusicGenerationManager
        from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_audio_manager=MusicGenerationManager('music-heartmula')
            current_audio_manager.job_storage_root=current_root_path/'music'
            current_video_manager=VaceVideoGenerationManager()
            current_video_manager.job_storage_root=current_root_path/'video'
            for current_storage_root,current_file_names in ((current_audio_manager.job_storage_root,('music.wav',)),(current_video_manager.job_storage_root,('preview.mp4','output-000.png','frames.zip'))):
                current_job_root=current_storage_root/current_job_identifier
                current_attempt_root=current_job_root/'attempts'/('a'*32)
                current_attempt_root.mkdir(parents=True)
                (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
                (current_job_root/'result.json').write_text(json.dumps({'format':'wav','attempt':'a'*32}))
                for current_file_name in current_file_names:(current_attempt_root/current_file_name).write_bytes(b'fixture-'+current_file_name.encode())
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'music-heartmula':current_audio_manager.handle_music_request})
            def dispatch_test_runtime(current_http_handler):
                if current_http_handler.path.startswith('/music-heartmula/jobs/'):return current_audio_manager.handle_music_request(current_http_handler)
                if current_http_handler.path.startswith('/wan22-vace/jobs/'):return current_video_manager.handle_image_request(current_http_handler)
                return current_gateway_value.handle(current_http_handler)
            current_gateway_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(dispatch_test_runtime))
            current_gateway_server.emit_gateway_trace=lambda *current_values:None
            current_gateway_thread=threading.Thread(target=current_gateway_server.serve_forever,daemon=True)
            current_gateway_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_gateway_server.server_port)
            class TestProxyHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if not proxy_management_request(self,current_gateway_url):self.send_error(404)
                def log_message(self,*current_values):pass
            current_proxy_server=ThreadingHTTPServer(('127.0.0.1',0),TestProxyHandler)
            current_proxy_thread=threading.Thread(target=current_proxy_server.serve_forever,daemon=True)
            current_proxy_thread.start()
            current_proxy_url='http://127.0.0.1:'+str(current_proxy_server.server_port)
            try:
                with patch.dict('os.environ',{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}),patch.object(video_operations,'make_hermes_video_manager',return_value=current_video_manager):
                    for current_service_name,current_field_name,current_expected_name in (('music-heartmula','audio','music.wav'),('wan22-vace','video','preview.mp4'),('wan22-vace','image','output-000.png'),('wan22-vace','download','frames.zip')):
                        current_result_value=execute_management_command('hermes-agent','hermes-'+('audio' if current_service_name=='music-heartmula' else 'video')+'-source-status',{'service':current_service_name,'job_id':current_job_identifier},current_gateway_url)
                        current_link_value=current_result_value['job'][current_field_name]
                        with urlopen(current_proxy_url+current_link_value,timeout=5) as current_response_value:
                            self.assertEqual(current_response_value.read(),b'fixture-'+current_expected_name.encode())
                    current_audio_link='/music-heartmula/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/music.wav'
                    with urlopen(Request(current_proxy_url+current_audio_link,headers={'Range':'bytes=0-3'}),timeout=5) as current_range_response:
                        self.assertEqual((current_range_response.status,current_range_response.read()),(206,b'fixt'))
            finally:
                current_proxy_server.shutdown();current_proxy_server.server_close();current_proxy_thread.join(timeout=5)
                current_gateway_server.shutdown();current_gateway_server.server_close();current_gateway_thread.join(timeout=5)

    def test_audio_file_observation_crosses_actual_runtime_and_proxy(self):
        import json
        import os
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import Request,urlopen
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES,execute_management_command
        from tools.review.common.management_runtime import ManagementServiceRuntime,bind_stored_management_service
        from tools.review.common.management_transport import proxy_management_request
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.music.generation import MusicGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_managers_map={current_service_name:MusicGenerationManager(current_service_name) for current_service_name in ('music-heartmula','sfx-dasheng-audiogen')}
            for current_service_name,current_manager_value in current_managers_map.items():
                current_manager_value.job_storage_root=current_root_path/current_service_name
                current_job_root=current_manager_value.job_storage_root/current_job_identifier
                current_attempt_root=current_job_root/'attempts'/('a'*32)
                current_attempt_root.mkdir(parents=True)
                (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
                (current_job_root/'result.json').write_text(json.dumps({'format':'wav','attempt':'a'*32}))
                (current_attempt_root/current_manager_value.audio_output_filename).write_bytes(b'fixture-audio')
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_bindings_map={current_name:bind_stored_management_service(lambda current_request:False,current_root_path) for current_name in MANAGEMENT_SERVICE_ROUTES}
            for current_service_name,current_manager_value in current_managers_map.items():current_bindings_map[current_service_name]=bind_stored_management_service(current_manager_value.handle_music_request,current_manager_value.job_storage_root)
            current_bindings_map['hermes-agent']=bind_stored_management_service(current_hermes_manager.handle_hermes_request,current_root_path/'hermes')
            current_runtime_value=ManagementServiceRuntime(current_bindings_map,lambda current_request:False,lambda:None)
            current_gateway_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_runtime_value.dispatch_runtime_request))
            current_gateway_server.emit_gateway_trace=lambda *current_values:None
            current_gateway_thread=threading.Thread(target=current_gateway_server.serve_forever,daemon=True)
            current_gateway_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_gateway_server.server_port)
            class TestProxyHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if not proxy_management_request(self,current_gateway_url):self.send_error(404)
                def log_message(self,*current_values):pass
            current_proxy_server=ThreadingHTTPServer(('127.0.0.1',0),TestProxyHandler)
            current_proxy_thread=threading.Thread(target=current_proxy_server.serve_forever,daemon=True)
            current_proxy_thread.start()
            current_proxy_url='http://127.0.0.1:'+str(current_proxy_server.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}),patch('tools.review.domains.music.generation.MusicGenerationManager',side_effect=lambda current_name:current_managers_map[current_name]):
                    for current_service_name,current_manager_value in current_managers_map.items():
                        with self.subTest(service=current_service_name):
                            current_payload_record={'service':current_service_name,'job_id':current_job_identifier}
                            current_response_value=execute_management_command('hermes-agent','hermes-audio-source-status',current_payload_record,current_gateway_url)
                            current_job_record=audio_operations.validate_hermes_audio_source_response(current_service_name,current_job_identifier,current_response_value)
                            self.assertEqual(current_job_record['file_observation'],'present')
                            with urlopen(Request(current_proxy_url+current_job_record['audio'],headers={'Range':'bytes=0-3'}),timeout=5) as current_http_response:self.assertEqual((current_http_response.status,current_http_response.read()),(206,b'fixt'))
                            current_original_call=audio_operations.call_hermes_audio_service
                            current_status_path=current_manager_value.job_storage_root/current_job_identifier/'status.json'
                            def change_status_after_response(current_name,current_command,current_payload):
                                current_response=current_original_call(current_name,current_command,current_payload)
                                current_status_path.write_text(json.dumps({'status':'running'}))
                                return current_response
                            with patch.object(audio_operations,'call_hermes_audio_service',side_effect=change_status_after_response):
                                current_stale_value=execute_management_command('hermes-agent','hermes-audio-source-status',current_payload_record,current_gateway_url)
                            self.assertEqual(current_stale_value['job']['file_observation'],'unavailable')
                            self.assertEqual(current_stale_value['job']['audio'],current_job_record['audio'])
                            current_status_path.write_text(json.dumps({'status':'completed'}))
                            (current_manager_value.job_storage_root/current_job_identifier/'attempts'/('a'*32)/current_manager_value.audio_output_filename).unlink()
                            current_missing_value=execute_management_command('hermes-agent','hermes-audio-source-status',current_payload_record,current_gateway_url)
                            self.assertEqual(current_missing_value['job']['file_observation'],'unavailable')
                            self.assertEqual(current_missing_value['job']['audio'],current_job_record['audio'])
            finally:
                current_proxy_server.shutdown();current_proxy_server.server_close();current_proxy_thread.join(timeout=5)
                current_gateway_server.shutdown();current_gateway_server.server_close();current_gateway_thread.join(timeout=5)

    def test_audio_file_observation_checks_records_and_file_without_mutation(self):
        import json
        from types import SimpleNamespace
        current_job_identifier='2026-11-18_00-00-00-12345678'
        for current_service_name,current_file_name in (('music-heartmula','music.wav'),('sfx-dasheng-audiogen','sound.wav')):
            with self.subTest(service=current_service_name),TemporaryDirectory() as current_directory_name:
                current_root_path=Path(current_directory_name)
                current_job_path=current_root_path/current_job_identifier
                current_attempt_path=current_job_path/'attempts'/('a'*32)
                current_attempt_path.mkdir(parents=True)
                current_status_record={'status':'completed'}
                current_result_record={'format':'wav','attempt':'a'*32}
                (current_job_path/'status.json').write_text(json.dumps(current_status_record))
                (current_job_path/'result.json').write_text(json.dumps(current_result_record))
                current_audio_file=current_attempt_path/current_file_name
                current_audio_file.write_bytes(b'fixture')
                current_audio_path='/'+current_service_name+'/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/'+current_file_name
                with patch('tools.review.domains.music.generation.MusicGenerationManager',return_value=SimpleNamespace(job_storage_root=current_root_path)):
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'present')
                    current_audio_file.unlink()
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unavailable')
                    current_audio_file.symlink_to(current_job_path/'status.json')
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unavailable')
                    with patch('tools.review.domains.hermes_agent.delegation_store.read_bounded_delegation_record',side_effect=[current_status_record,current_result_record,current_status_record,{'format':'wav','attempt':'b'*32}]):
                        self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unavailable')
                    (current_job_path/'status.json').write_text(json.dumps({'status':'running'}))
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unavailable')
                    (current_job_path/'status.json').write_text(json.dumps(current_status_record))
                    (current_job_path/'result.json').write_text(json.dumps({'format':'wav','attempt':'b'*32}))
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unavailable')
                    (current_job_path/'result.json').write_text('{broken')
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unavailable')
                    (current_job_path/'result.json').unlink()
                    self.assertEqual(audio_operations.observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path),'unknown')
                    self.assertEqual(json.loads((current_job_path/'status.json').read_text()),current_status_record)

    def test_source_audio_status_checks_service_job_and_result(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_result_path='/music-heartmula/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/music.wav'
        current_source_record={'id':current_job_identifier,'status':'completed','audio':current_result_path}
        with patch.object(audio_operations,'call_hermes_audio_service',return_value=current_source_record) as current_service_mock:
            current_result_value=audio_operations.read_hermes_audio_source_job('music-heartmula',current_job_identifier)
            self.assertEqual(current_result_value['audio'],current_result_path)
            current_service_mock.assert_called_once_with('music-heartmula','status',{'id':current_job_identifier})
            with self.assertRaises(ValueError):audio_operations.read_hermes_audio_source_job('music-heartmula','../invalid')
            with self.assertRaises(ValueError):audio_operations.read_hermes_audio_source_job('music-magenta',current_job_identifier)
            current_source_record['id']='other-job'
            with self.assertRaises(ValueError):audio_operations.read_hermes_audio_source_job('music-heartmula',current_job_identifier)
            self.assertEqual(current_service_mock.call_count,2)

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

    def test_concurrent_source_history_rejects_same_owner_without_blocking_others(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        current_entered_event=threading.Event()
        current_release_event=threading.Event()
        current_empty_result={'records':[],'total':0,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        def current_source_response(current_service_name,current_command_name,current_request_value,current_gateway_address):
            if current_service_name=='building-generator':
                current_entered_event.set()
                if not current_release_event.wait(5):raise RuntimeError('시험 동기화 실패')
            return current_empty_result
        with patch.object(audio_operations,'execute_management_command',side_effect=current_source_response) as current_gateway_mock:
            with ThreadPoolExecutor(max_workers=2) as current_executor_value:
                current_pending_future=current_executor_value.submit(audio_operations.read_hermes_generator_source_history,'building-generator',{})
                try:
                    self.assertTrue(current_entered_event.wait(3))
                    with self.assertRaisesRegex(ValueError,'조회 중'):audio_operations.read_hermes_generator_source_history('billboard-generator',{})
                    self.assertEqual(audio_operations.read_hermes_audio_source_history('music-heartmula',{})['total'],0)
                finally:
                    current_release_event.set()
                self.assertEqual(current_pending_future.result(timeout=5)['source_service'],'billboard-generator')
            self.assertEqual(current_gateway_mock.call_count,2)
            self.assertEqual(audio_operations.read_hermes_generator_source_history('billboard-generator',{})['total'],0)

    def test_invalid_history_request_does_not_call_source_service(self):
        current_invalid_requests=[{'offset':1},{'offset':True},{'limit':31},{'snapshot':'bad'},{'query':'bad query'},{'extra':1}]
        for current_reader_value,current_service_name in ((audio_operations.read_hermes_audio_source_history,'music-heartmula'),(audio_operations.read_hermes_generator_source_history,'wan22-fun-control')):
            for current_request_value in current_invalid_requests:
                with self.subTest(service=current_service_name,request=current_request_value),patch.object(audio_operations,'execute_management_command') as current_gateway_mock:
                    with self.assertRaises(ValueError):current_reader_value(current_service_name,current_request_value)
                    current_gateway_mock.assert_not_called()

    def test_source_history_rejects_out_of_range_and_missing_snapshot(self):
        from tools.review.domains.hermes_agent.audio_operations import sanitize_hermes_source_history
        current_empty_record={'records':[],'total':2,'offset':3,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        with self.assertRaises(ValueError):
            sanitize_hermes_source_history('music-heartmula',{'offset':3,'limit':1,'snapshot':'a'*64},current_empty_record)
        current_last_record={'records':[],'total':2,'offset':2,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        with self.assertRaises(ValueError):
            sanitize_hermes_source_history('music-heartmula',{'offset':2,'limit':1},current_last_record)
        self.assertEqual(sanitize_hermes_source_history('music-heartmula',{'offset':2,'limit':1,'snapshot':'a'*64},current_last_record)['records'],[])

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
