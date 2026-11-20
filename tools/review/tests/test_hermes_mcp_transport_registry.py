"""Hermes MCP의 실제 stdio 도구 목록을 GPU 없이 검증한다."""
import os
from pathlib import Path
import subprocess
import unittest


class HermesMcpTransportRegistryTests(unittest.TestCase):
    def setUp(self):
        import socket
        from unittest.mock import patch
        current_closed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        current_closed_socket.bind(('127.0.0.1', 0))
        self.addCleanup(current_closed_socket.close)
        current_gateway_url = 'http://127.0.0.1:' + str(current_closed_socket.getsockname()[1])
        current_gateway_patch = patch.dict(os.environ, {'SLIME_MANAGEMENT_GATEWAY_URL': current_gateway_url})
        current_gateway_patch.start()
        self.addCleanup(current_gateway_patch.stop)

    def test_default_gateway_is_reserved_and_not_listening(self):
        import socket
        from urllib.parse import urlsplit
        current_gateway_value = urlsplit(os.environ['SLIME_MANAGEMENT_GATEWAY_URL'])
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as current_probe_socket:
            current_probe_socket.settimeout(1)
            self.assertNotEqual(current_probe_socket.connect_ex((current_gateway_value.hostname, current_gateway_value.port)), 0)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as current_other_socket:
            with self.assertRaises(OSError):
                current_other_socket.bind((current_gateway_value.hostname, current_gateway_value.port))

    def test_fresh_stdio_session_exposes_registered_operations(self):
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():
            self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def inspect_fresh_mcp_registry():
    current_server_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_server_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_client_session:
            await current_client_session.initialize()
            current_tool_response=await current_client_session.list_tools()
            current_tool_names={current_tool_value.name for current_tool_value in current_tool_response.tools}
            current_required_names={'read_hermes_map_database_receipt','preview_hermes_cleanup','read_hermes_video_resume_proposal','preview_hermes_video_resume','submit_hermes_video_resume','read_hermes_video_resume_receipt','read_hermes_writer_job_material','read_hermes_sprite_pending_status','read_hermes_model_download_status','read_hermes_writer_index_status','search_hermes_translation_evidence','read_hermes_writer_search_paths','read_hermes_writer_job_search_paths','preview_hermes_translation_resume','submit_hermes_translation_resume','read_hermes_translation_resume_receipt','preview_hermes_audio_resume','submit_hermes_audio_resume','read_hermes_audio_resume_receipt','read_hermes_capture_proposal','read_hermes_capture_status'}
            current_missing_names=current_required_names-current_tool_names
            if current_missing_names:raise RuntimeError('MCP 도구 누락: '+', '.join(sorted(current_missing_names)))
asyncio.run(inspect_fresh_mcp_registry())
"""
        current_environment_values=dict(os.environ)
        current_environment_values['PYTHONPATH']=str(current_repository_root)
        current_test_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
        self.assertEqual(current_test_process.returncode,0,current_test_process.stderr[-4000:])


    def test_bounded_queue_failure_crosses_stdio_without_gpu_status(current_test_case):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_queue_failure():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_reader,current_writer):
        async with ClientSession(current_reader,current_writer) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_gpu_queue_status',{})
            if not current_result.is_error or '대기열을 확인할 수 없습니다' not in str(current_result.content):raise RuntimeError(str(current_result))
asyncio.run(inspect_queue_failure())
"""
        with tempfile.TemporaryDirectory() as current_root_name:
            current_manager_value=HermesServiceManager(Path(current_root_name)/'jobs',Path(current_root_name)/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                with patch('tools.review.domains.hermes_agent.management_observer.read_hermes_management_snapshot',return_value={'queue':{'status':'unavailable','jobs':[]}}) as current_snapshot_mock,patch('tools.review.common.gpu_status.read_gpu_status',side_effect=AssertionError('GPU 조회 금지')) as current_gpu_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_snapshot_mock.assert_called_once()
                    current_gpu_mock.assert_not_called()
                current_invalid_gpu_script=current_client_script.replace('대기열을 확인할 수 없습니다','GPU 상태와 프로세스 목록이 일치하지 않습니다')
                with patch('tools.review.domains.hermes_agent.management_observer.read_hermes_management_snapshot',return_value={'queue':{'status':'available','jobs':[]}}),patch('tools.review.common.gpu_status.read_gpu_status',return_value={'status':'idle','processes':[{'pid':1}]}):
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_invalid_gpu_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                current_management_script=r'''
import asyncio,os,sys,json
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_management_status():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_reader,current_writer):
        async with ClientSession(current_reader,current_writer) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_management_status',{})
            if current_result.is_error:raise RuntimeError('관리 상태 조회 오류')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['gpu']['status']!='unavailable' or current_value['memory_capacity']['status']!='unavailable' or current_value['queue']['jobs'][0]['id']!='mock-job':raise RuntimeError('관측 결과 불일치')
asyncio.run(inspect_management_status())
'''
                from tools.review.domains.hermes_agent import management_observer
                with patch('tools.review.common.gpu_status.read_gpu_status',return_value={'status':'idle','processes':[{'pid':1}]}),patch('tools.review.common.gpu_job_queue.list_waiting_gpu_jobs',return_value={'jobs':[{'id':'mock-job','service':'image'}]}),patch.object(management_observer,'inspect_hermes_model_status',return_value={}),patch.object(management_observer,'read_hermes_generator_snapshot',return_value={}),patch.object(management_observer,'read_hermes_gpu_reservation_snapshot',return_value={}),patch.object(management_observer,'read_hermes_recent_job_snapshot',return_value={}):
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_management_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_map_receipt_crosses_stdio_and_gateway_without_writes(current_test_case):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_map_receipt_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_reader,current_writer):
        async with ClientSession(current_reader,current_writer) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_map_database_receipt',{'database_request_identifier':'db id & x','request_sha256_value':'a'*64})
            if current_result.is_error:raise RuntimeError(str(current_result))
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value.get('state')!='not_found' or current_value.get('request_sha256')!='a'*64 or '보장하지 않습니다' not in current_value.get('note',''):raise RuntimeError(str(current_value))
asyncio.run(inspect_map_receipt_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                with patch('tools.review.domains.map_assets.database_client.execute_content_api_request',return_value={'state':'not_found'}) as current_content_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_content_mock.assert_called_once()
                    current_test_case.assertEqual(current_content_mock.call_args.args[0],'GET')
                    current_test_case.assertIn('requestId=db+id+%26+x',current_content_mock.call_args.args[1])
                    current_content_mock.side_effect=ValueError('콘텐츠 API 오류 (404): 지원하지 않는 경로')
                    current_error_script=current_client_script.replace("if current_result.is_error:raise RuntimeError(str(current_result))","if not current_result.is_error:raise RuntimeError('404가 접수 결과로 표시됨')\n            return")
                    current_error_process=subprocess.run([str(current_runtime_python),'-c',current_error_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_error_process.returncode,0,current_error_process.stderr[-4000:])
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_capture_proposal_registration_crosses_stdio_and_gateway(current_test_case):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def verify_capture_proposal():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_reader,current_writer):
        async with ClientSession(current_reader,current_writer) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_capture_proposal',{'hermes_job_identifier':'2026-11-20_00-00-00-12345678'})
            if current_result.is_error:raise RuntimeError(str(current_result))
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value.get('map_registration')!={'status':'registered','map':'stonewarm'}:raise RuntimeError(str(current_value))
            if current_value.get('proposal',{}).get('settings',{}).get('map')!='stonewarm':raise RuntimeError(str(current_value))
asyncio.run(verify_capture_proposal())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_job_record={'status':{'status':'completed'},'final_response':'HERMES_CAPTURE_PROPOSAL\n{"service":"map-review","settings":{"map":"stonewarm"}}\nEND_HERMES_CAPTURE_PROPOSAL','final_response_truncated':False}
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                from tools.review.common.map_asset_sources import load_review_map_menu
                with patch.object(current_manager_value,'resolve_hermes_job_path',return_value=current_root_path),patch.object(current_manager_value,'read_hermes_job_record',return_value=current_job_record),patch('tools.review.common.map_asset_sources.load_review_map_menu',return_value=[{'id':'stonewarm'}]) as current_menu_mock,patch('tools.review.domains.map_review.capture.capture_map_review',side_effect=AssertionError('캡처 금지')) as current_capture_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_menu_mock.side_effect=load_review_map_menu
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_capture_mock.assert_not_called()
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_model_prepare_block_crosses_stdio_and_temporary_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.common.model_prepare_process import hold_hermes_model_usage_guard
        from tools.review.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root = Path(__file__).resolve().parents[3]
        current_runtime_python = current_repository_root / '.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():
            self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script = r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_model_prepare_block():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_reader,current_writer):
        async with ClientSession(current_reader,current_writer) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('prepare_hermes_managed_model',{'request_identifier_value':'request_model_block','model_service_name':'hermes-model'})
            if current_result.is_error:raise RuntimeError(str(current_result))
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value != {'request_id':'request_model_block','service':'hermes-model','state':'blocked','reason':'model_in_use'}:raise RuntimeError(str(current_value))
asyncio.run(inspect_model_prepare_block())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_store_value = HermesModelPreparationStore(current_root_path / 'receipts')
            current_hermes_manager = HermesServiceManager(current_root_path/'jobs', current_root_path/'sessions')
            current_gateway_value = ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request})
            current_server_value = ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace = lambda *current_values: None
            current_thread_value = threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_url = 'http://127.0.0.1:' + str(current_server_value.server_port)
            current_environment_values = dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root))
            try:
                with patch('tools.review.domains.hermes_agent.service.WORKFLOW_ROOT_DIRECTORY',current_root_path), patch('tools.review.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore',return_value=current_store_value), patch('tools.review.common.hermes_model_download.inspect_hermes_model_files',return_value=False), hold_hermes_model_usage_guard(current_root_path):
                    current_process_value = subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    self.assertEqual(current_store_value.read_model_preparation_receipt('request_model_block','hermes-model')['state'],'not_found')
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)


    def test_kimodo_resume_crosses_stdio_gateway_with_mocked_worker(self):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import kimodo_resume_operations
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.image.image_generation import WORKFLOW_ROOT_PATH
        from tools.review.domains.kimodo.generation import KimodoGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_kimodo_resume_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            async def call_checked_tool(current_tool_name,current_arguments):
                current_result=await current_session.call_tool(current_tool_name,current_arguments)
                if current_result.is_error:raise RuntimeError(current_tool_name+' failed: '+str(current_result.content))
                return current_result.structured_content or json.loads(current_result.content[0].text)
            current_job='2026-11-20_00-00-00-12345678'
            current_preview=await call_checked_tool('preview_hermes_kimodo_resume',{'job_identifier_value':current_job})
            current_args={'request_identifier_value':'request_123','job_identifier_value':current_job,'expected_resume_fingerprint':current_preview['expected_resume_fingerprint']}
            current_receipt=await call_checked_tool('submit_hermes_kimodo_resume',current_args)
            if current_receipt.get('state')!='accepted' or current_receipt.get('job_id')!=current_job:raise RuntimeError('재개 접수 불일치')
            current_again=await call_checked_tool('submit_hermes_kimodo_resume',current_args)
            if not current_again.get('duplicate'):raise RuntimeError('중복 재접수')
            current_read=await call_checked_tool('read_hermes_kimodo_resume_receipt',{'request_identifier_value':'request_123'})
            if current_read.get('state')!='accepted' or current_read.get('expected_resume_fingerprint')!=current_args['expected_resume_fingerprint']:raise RuntimeError('재개 접수 기록 불일치')
asyncio.run(inspect_kimodo_resume_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_kimodo_manager=KimodoGenerationManager()
            current_kimodo_manager.job_storage_root=current_root_path/'jobs'
            current_job_identifier='2026-11-20_00-00-00-12345678'
            current_job_path=current_kimodo_manager.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text('{"action":"generate"}')
            (current_job_path/'status.json').write_text('{"status":"failed"}')
            current_command_values=[str(current_kimodo_manager.select_generation_python()),str(WORKFLOW_ROOT_PATH/current_kimodo_manager.select_generation_runner()),'--job-dir',str(current_job_path)]
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':current_kimodo_manager.select_generation_service(),'command':current_command_values}))
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'kimodo':current_kimodo_manager.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server_value.server_port)
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root))
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}),patch.object(kimodo_resume_operations,'KIMODO_RESUME_RECEIPT_ROOT',current_root_path/'receipts'),patch.object(current_kimodo_manager,'validate_generation_resume'),patch('tools.review.domains.kimodo.generation.inspect_kimodo_preparation_for_resume',return_value='idle'),patch('tools.review.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_launch_mock.assert_called_once()
                    self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'queued')
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_direct_writer_search_crosses_stdio_and_gateway(current_test_case):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import writer_operations
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_writer_search_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_writer_job_search_paths',{'job_identifier_value':'20261120-120000-abcdef12'})
            if current_result.is_error:raise RuntimeError('작가 검색 MCP 호출 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value!={'paths':['world/town.md'],'truncated':False}:raise RuntimeError('작가 검색 경로 전달 오류')
            current_review=await current_session.call_tool('read_hermes_writer_job_review',{'job_identifier_value':'20261120-120000-abcdef12'})
            if current_review.is_error:raise RuntimeError('작가 작업 검토 MCP 호출 실패')
            current_review_value=current_review.structured_content or json.loads(current_review.content[0].text)
            if current_review_value['job_id']!='20261120-120000-abcdef12' or current_review_value['job']['changes'][0]['diff']!='-old\\n+new':raise RuntimeError('작가 작업 제안 전달 오류')
            current_invalid=await current_session.call_tool('read_hermes_writer_job_search_paths',{'job_identifier_value':'../secret'})
            if not current_invalid.is_error:raise RuntimeError('잘못된 작업 ID가 허용됨')
asyncio.run(inspect_writer_search_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                with patch.object(writer_operations,'call_hermes_writer_service',side_effect=lambda current_command,current_payload: {'paths':['world/town.md'],'truncated':False} if current_command=='writer-search-paths' else {'id':current_payload['id'],'status':{'stage':'review'},'proposal':{'changes':[{'path':'world/town.md','diff':'-old\n+new'}],'warnings':[]}}) as current_writer_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_test_case.assertEqual(current_writer_mock.call_count,2)
                    current_test_case.assertEqual({current_call.args[0] for current_call in current_writer_mock.call_args_list},{'writer-search-paths','writer-detail'})
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_receipt_and_queue_cross_stdio_and_gateway(current_test_case):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common import gpu_job_queue
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import delegation_store, management_observer
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_receipt_queue_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_receipt=await current_session.call_tool('read_hermes_delegation_status',{'request_identifier_value':'test_receipt'})
            current_queue=await current_session.call_tool('read_hermes_management_status',{})
            if current_receipt.is_error or current_queue.is_error:raise RuntimeError('접수 또는 대기열 MCP 조회 실패')
            current_receipt_value=current_receipt.structured_content or json.loads(current_receipt.content[0].text)
            current_queue_value=current_queue.structured_content or json.loads(current_queue.content[0].text)
            if current_receipt_value.get('request_id')!='test_receipt' or current_receipt_value.get('service')!='kimodo' or current_receipt_value.get('state')!='accepted':raise RuntimeError('접수 식별자 오류')
            current_jobs=current_queue_value['queue']['jobs']
            if len(current_jobs)!=1 or current_jobs[0].get('id')!=current_receipt_value.get('job_id') or current_jobs[0].get('source_service')!='kimodo':raise RuntimeError('접수와 대기 작업 식별자 불일치')
            if os.environ['TEST_TEMP_ROOT'] in str(current_queue_value):raise RuntimeError('임시 경로가 노출됨')
asyncio.run(inspect_receipt_queue_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_target_job='2026-11-18_12-00-00-12345678'
            current_job_path=current_root_path/'.tmp/test/kimodo'/current_target_job
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            (current_job_path/'gpu-command.json').write_text('{"service":"image"}')
            current_ticket_path=current_root_path/'ticket.json'
            current_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_path)}))
            current_receipt_store=delegation_store.HermesDelegationStore(current_root_path/'receipts')
            current_receipt_store.execute_delegation_once('test_receipt',{},lambda current_request_value:{'id':current_target_job})
            current_manager=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_manager.handle_hermes_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_thread.start()
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server.server_port),PYTHONPATH=str(current_repository_root),TEST_TEMP_ROOT=str(current_root_path))
            try:
                with patch.object(delegation_store,'HermesDelegationStore',return_value=current_receipt_store),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(gpu_job_queue,'read_priority_tickets',return_value=[current_ticket_path]),patch.object(management_observer,'read_hermes_management_snapshot',side_effect=lambda:{'queue':{'status':'available',**gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)}}):
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_thread.join(timeout=5)

    def test_animation_history_crosses_stdio_gateway_and_screen(current_test_case):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway, execute_management_command
        from tools.review.domains.character_animation import character_animation_jobs
        from tools.review.domains.character_animation.character_animation import CharacterAnimationManager
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        from tools.review.ui.gradio import hermes_agent_app
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_animation_history_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('list_hermes_generator_source_history',{'generator_service_name':'character-animation'})
            if current_result.is_error:raise RuntimeError('애니메이션 이력 MCP 호출 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['records']!=[{'id':'2026-11-18_12-00-00-aaaaaaaa','recorded_status':'completed','status_source':'job'}]:raise RuntimeError('애니메이션 이력 전달 오류')
asyncio.run(inspect_animation_history_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_animation_root=current_root_path/'animation'
            current_history_root=current_animation_root/'history'
            current_history_root.mkdir(parents=True)
            current_job_identifier='2026-11-18_12-00-00-aaaaaaaa'
            current_job_path=current_animation_root/current_job_identifier[:19]/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_history_root/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier}))
            current_hermes_manager=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_animation_manager=CharacterAnimationManager()
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'character-animation':current_animation_manager.handle})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_thread.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_origin,PYTHONPATH=str(current_repository_root))
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(character_animation_jobs,'GENERATION_ROOT_DIRECTORY',current_animation_root),patch.object(character_animation_jobs,'GENERATION_HISTORY_DIRECTORY',current_history_root),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=lambda current_service,current_command,current_payload:execute_management_command(current_service,current_command,current_payload,current_gateway_origin)):
                    current_rows=hermes_agent_app.read_hermes_generator_source_rows('character-animation')[0]
                    current_test_case.assertEqual(current_rows,[[current_job_identifier,'completed','작업 상태 파일']])
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
                    current_test_case.assertEqual(sorted(current_history_root.iterdir()),[current_history_root/(current_job_identifier+'.json')])
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_thread.join(timeout=5)

    def test_model_download_observation_crosses_stdio_and_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.common import model_download_records
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_download_mcp_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_model_download_status',{})
            if current_result.is_error:raise RuntimeError('MCP 다운로드 조회 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['unavailable_count']!=1 or current_value['records'][0]['model']!='org/model':raise RuntimeError('MCP 관측 결과 오류')
asyncio.run(inspect_download_mcp_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            import json
            current_root_path=Path(current_directory_name)
            current_records_root=current_root_path/'records'
            current_records_root.mkdir()
            (current_records_root/'valid.json').write_text(json.dumps({'model':'org/model','status':'completed','bytes':42,'total_bytes':42}))
            (current_records_root/'invalid.json').write_text('{')
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            current_original_observer=model_download_records.observe_model_download_records
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_environment_values['SLIME_MANAGEMENT_GATEWAY_URL']}), patch.object(model_download_records,'observe_model_download_records',side_effect=lambda **current_arguments:current_original_observer(current_records_root,**current_arguments)):
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    self.assertEqual(len(list(current_records_root.glob('*.json'))),2)
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_audio_resume_blocked_then_accepted_across_stdio_and_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from generators.music.contracts import build_music_request
        from tools.review.common.generation_records import write_record_atomically
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import audio_resume_operations
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.music.generation import MusicGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_audio_resume_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            async def call_mcp_operation(current_name,current_args):
                current_reply=await current_session.call_tool(current_name,current_args)
                if current_reply.is_error:raise RuntimeError('MCP 재개 통신 오류')
                return current_reply.structured_content or json.loads(current_reply.content[0].text)
            current_job='2026-11-18_00-00-00-12345678'
            current_request='resume_stdio_123'
            current_preview=await call_mcp_operation('preview_hermes_audio_resume',{'service_name':'music-heartmula','job_identifier_value':current_job})
            if current_preview['resume_availability']!='download_running':raise RuntimeError('다운로드 상태 전달 오류')
            current_payload={'request_identifier_value':current_request,'service_name':'music-heartmula','job_identifier_value':current_job,'expected_resume_fingerprint':current_preview['expected_resume_fingerprint']}
            current_block=await call_mcp_operation('submit_hermes_audio_resume',current_payload)
            if (current_block['state'],current_block['reason'])!=('blocked','download_running'):raise RuntimeError('재개 차단 전달 오류')
            current_receipt=await call_mcp_operation('read_hermes_audio_resume_receipt',{'request_identifier_value':current_request})
            if current_receipt['state']!='not_found':raise RuntimeError('차단 접수 기록 오류')
            current_accept=await call_mcp_operation('submit_hermes_audio_resume',current_payload)
            if current_accept['state']!='accepted':raise RuntimeError('재개 접수 오류')
            current_duplicate=await call_mcp_operation('submit_hermes_audio_resume',current_payload)
            if current_duplicate['state']!='accepted' or current_duplicate['duplicate'] is not True:raise RuntimeError('재개 중복 방지 오류')
asyncio.run(inspect_audio_resume_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_music_manager=MusicGenerationManager('music-heartmula')
            current_music_manager.job_storage_root=current_root_path/'music-jobs'
            current_music_manager.history_storage_root=current_root_path/'history'
            current_job_root=current_music_manager.job_storage_root/'2026-11-18_00-00-00-12345678'
            current_job_root.mkdir(parents=True)
            write_record_atomically(current_job_root/'request.json',build_music_request('music-heartmula',{'prompt':'piano','lyrics':'','seed':1}))
            write_record_atomically(current_job_root/'status.json',{'status':'failed'})
            write_record_atomically(current_job_root/'gpu-command.json',{'service':'music-heartmula','command':current_music_manager.build_music_worker_command(current_job_root)})
            current_hermes_manager=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'music-heartmula':current_music_manager.handle_music_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_address='http://127.0.0.1:'+str(current_server_value.server_port)
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_address,PYTHONPATH=str(current_repository_root))
            current_inspection_calls=[]
            def inspect_fake_download(*current_arguments):
                current_inspection_calls.append(True)
                return 'running' if len(current_inspection_calls)<=2 else 'idle'
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_address}),patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',current_root_path/'receipts'),patch('tools.review.common.model_prepare_process.inspect_registered_preparation',side_effect=inspect_fake_download),patch('tools.review.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_launch_mock.assert_called_once()
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_sprite_save_blocked_without_receipt_across_stdio(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import sprite_operations, sprite_pending_observer
        from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_sprite_save_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            async def call_mcp_operation(current_name,current_arguments):
                current_response=await current_session.call_tool(current_name,current_arguments)
                if current_response.is_error:raise RuntimeError('MCP 스프라이트 통신 실패')
                return current_response.structured_content or json.loads(current_response.content[0].text)
            current_draft={'path':'assets/characters/default/animations/example/sheet.png','snapshot':'a'*64,'columns':1,'anchors':[{'frame_id':'idle.0','x':1,'y':1}]}
            current_payload={'request_identifier_value':'sprite_stdio_123','draft_record_value':current_draft,'preview_token_value':os.environ['TEST_SPRITE_DRAFT_TOKEN'],'review_digest_value':'b'*64}
            current_result=await call_mcp_operation('save_hermes_sprite_anchor',current_payload)
            if (current_result['state'],current_result['reason'],current_result['saved'])!=('blocked','pending',False):raise RuntimeError('차단 상태 전달 오류')
            current_receipt=await call_mcp_operation('read_hermes_sprite_anchor_receipt',{'request_identifier_value':'sprite_stdio_123'})
            if current_receipt['state']!='not_found':raise RuntimeError('차단된 저장의 접수 기록 오류')
asyncio.run(inspect_sprite_save_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_draft_value={'path':'assets/characters/default/animations/example/sheet.png','snapshot':'a'*64,'columns':1,'anchors':[{'frame_id':'idle.0','x':1,'y':1}]}
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root),TEST_SPRITE_DRAFT_TOKEN=sprite_operations.validate_hermes_sprite_anchor_draft(current_draft_value))
            try:
                with patch.object(sprite_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(sprite_pending_observer,'inspect_hermes_sprite_pending_status',return_value={'state':'pending','files':[]}),patch.object(sprite_operations,'call_hermes_sprite_editor') as current_editor_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_editor_mock.assert_not_called()
                    self.assertFalse((current_root_path/'receipts'/'sprite_stdio_123.json').exists())
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_sprite_pending_status_crosses_stdio_and_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import sprite_pending_observer
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_sprite_pending_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_sprite_pending_status',{})
            if current_result.is_error:raise RuntimeError('MCP 스프라이트 상태 조회 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['state']!='pending' or current_value['files'][0]['backup']!='valid':raise RuntimeError('MCP 중단 상태 전달 오류')
asyncio.run(inspect_sprite_pending_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                with patch.object(sprite_pending_observer,'inspect_hermes_sprite_pending_status',return_value={'state':'pending','files':[{'path':'assets/example.png','current':'after','backup':'valid'}],'note':'조회 시점'}):
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_translation_evidence_crosses_stdio_and_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import translation_operations
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_translation_mcp_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('search_hermes_translation_evidence',{'source_text_value':'나무'})
            if current_result.is_error:raise RuntimeError('MCP 근거 조회 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['candidates'][0]['text']!='테스트 문서 근거':raise RuntimeError('MCP 근거 전달 오류')
asyncio.run(inspect_translation_mcp_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_candidate_record={'path':'world/tree.md','heading':'나무','text':'테스트 문서 근거','matched_terms':['나무']}
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                with patch.object(translation_operations,'call_hermes_translation_service',return_value={'candidates':[current_candidate_record]}) as current_search_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_search_mock.assert_called_once_with('translation-rag',{'text':'나무'})
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_map_pending_status_crosses_stdio_and_screen_without_database(current_test_case):
        import hashlib
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common import management_gateway
        from tools.review.domains.map_assets import map_editor
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        from tools.review.ui.gradio import hermes_agent_app
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_map_pending_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_content_database_status',{})
            if current_result.is_error:raise RuntimeError('콘텐츠 상태 MCP 호출 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['status']!='unavailable' or current_value['map_save']['state']!='pending' or current_value['map_save']['backup_valid']!=1 or current_value['map_save']['changed_since_backup']!=1:raise RuntimeError('맵 중단 상태 전달 오류')
            if current_value['map_save']['file_details']!=[{'path':'assets/maps/field_tiles/example.yaml','current':'changed','backup':'valid'}]:raise RuntimeError('맵 파일별 상태 전달 오류')
asyncio.run(inspect_map_pending_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root=Path(current_directory_name)
            current_asset_root=current_root/'slime-assets'
            current_map_path=current_asset_root/'assets/maps/field_tiles/example.yaml'
            current_map_path.parent.mkdir(parents=True)
            current_map_path.write_text('changed')
            current_storage_root=current_root/'editor'
            current_storage_root.mkdir()
            (current_storage_root/'save.lock').touch()
            current_backup_name='a'*64+'-backup'
            current_backup_path=current_storage_root/current_backup_name
            current_backup_path.mkdir()
            (current_backup_path/'0').write_text('original')
            (current_backup_path/'paths.json').write_text(json.dumps([str(current_map_path)]))
            (current_storage_root/'map-save-pending.json').write_text(json.dumps({'version':1,'map':'example','backup':current_backup_name,'before_sha256':[hashlib.sha256(b'original').hexdigest()]}))
            current_manager=HermesServiceManager(current_root/'jobs',current_root/'sessions')
            current_gateway=management_gateway.ManagementCommandGateway({'hermes-agent':current_manager.handle_hermes_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_thread.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_origin,PYTHONPATH=str(current_repository_root))
            current_execute_original=management_gateway.execute_management_command
            def respond_database_offline(current_service,current_command,current_payload,current_address=None,**current_keyword_arguments):
                if current_service=='map-assets' and current_command=='database-status':raise OSError('offline')
                return current_execute_original(current_service,current_command,current_payload,current_address,**current_keyword_arguments)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin,'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(map_editor,'MAP_EDITOR_STORAGE_ROOT',current_storage_root),patch.object(management_gateway,'execute_management_command',side_effect=respond_database_offline),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=lambda current_service,current_command,current_payload:current_execute_original(current_service,current_command,current_payload,current_gateway_origin)):
                    current_summary=hermes_agent_app.read_hermes_content_database_summary()
                    current_test_case.assertIn('콘텐츠 DB 상태 확인 불가',current_summary)
                    current_test_case.assertIn('중단 기록 확인 필요',current_summary)
                    current_test_case.assertIn('백업 유효 1',current_summary)
                    current_test_case.assertIn('변경된 파일 1',current_summary)
                    current_test_case.assertIn('assets/maps/field_tiles/example.yaml',current_summary)
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
                    current_test_case.assertTrue((current_storage_root/'map-save-pending.json').exists())
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_thread.join(timeout=5)

    def test_field_alignment_crosses_stdio_gateway_and_review(current_test_case):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway, execute_management_command
        from tools.review.domains.hermes_agent import field_map_operations
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        from tools.review.ui.gradio import hermes_agent_app
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_field_alignment_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_draft={'map':'example','revision':'rev-1','cells':[],'objects':[]}
            current_result=await current_session.call_tool('preview_hermes_field_map',{'draft_record_value':current_draft})
            if current_result.is_error:raise RuntimeError('야외 맵 MCP 검토 실패')
            current_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_value['source_alignment']['status']!='mismatch' or current_value['save_available'] is not False or current_value.get('save_block_reason')!='database':raise RuntimeError('야외 맵 비교 또는 저장 차단 전달 오류')
            current_draft['revision']='legacy-rev'
            current_legacy_result=await current_session.call_tool('preview_hermes_field_map',{'draft_record_value':current_draft})
            if current_legacy_result.is_error:raise RuntimeError('구형 야외 맵 MCP 검토 실패')
            current_legacy_value=current_legacy_result.structured_content or json.loads(current_legacy_result.content[0].text)
            if current_legacy_value['save_available'] is not False or 'save_block_reason' in current_legacy_value or 'source_alignment' in current_legacy_value:raise RuntimeError('구형 응답에서 차단 사유를 추정했습니다')
asyncio.run(inspect_field_alignment_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root=Path(current_directory_name)
            current_manager=HermesServiceManager(current_root/'jobs',current_root/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_manager.handle_hermes_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_thread.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_origin,PYTHONPATH=str(current_repository_root))
            current_draft={'map':'example','revision':'rev-1','cells':[],'objects':[]}
            current_token=field_map_operations.validate_field_map_draft(current_draft)
            def respond_field_editor(current_command,current_payload):
                if current_command=='map-edit-preview':
                    current_preview_value={'token':field_map_operations.validate_field_map_draft(current_payload),'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':False}
                    if current_payload['revision']!='legacy-rev':current_preview_value['save_block_reason']='database'
                    return current_preview_value
                if current_command=='map-edit-load':return {'map':'example','revision':'rev-1','tiles':{},'terrain':{},'textures':[],'codes':{}}
                raise AssertionError('예상하지 못한 맵 명령')
            try:
                with patch.object(field_map_operations,'call_field_map_editor',side_effect=respond_field_editor),patch('tools.review.domains.map_assets.source_consistency.inspect_field_source_alignment',return_value={'status':'mismatch','note':'모의 비교'}),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=lambda current_service,current_command,current_payload:execute_management_command(current_service,current_command,current_payload,current_gateway_origin)),patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}):
                    current_review,current_summary,_=hermes_agent_app.review_hermes_field_map_draft(json.dumps(current_draft),'field_review_123')
                    current_test_case.assertFalse(current_review['save_available'])
                    current_test_case.assertIn('등록 원본 비교: 불일치',current_summary)
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_thread.join(timeout=5)

    def test_city_alignment_crosses_real_stdio_and_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import city_map_operations
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script="import asyncio\nimport json\nimport os\nimport sys\nfrom mcp import ClientSession, StdioServerParameters\nfrom mcp.client.stdio import stdio_client\n\n\nasync def inspect_city_mcp_transport():\n    current_server_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))\n    async with stdio_client(current_server_parameters) as (current_read_stream,current_write_stream):\n        async with ClientSession(current_read_stream,current_write_stream) as current_client_session:\n            await current_client_session.initialize()\n            current_draft_record={'map':'example','generation':5,'revision':2,'document':{'data':{'cityId':'example','version':2}}}\n            current_result_record=await current_client_session.call_tool('preview_hermes_city_map',{'draft_record_value':current_draft_record})\n            if current_result_record.is_error:raise RuntimeError('MCP 도시 검토 호출 실패')\n            current_result_value=current_result_record.structured_content\n            if current_result_value is None:current_result_value=json.loads(current_result_record.content[0].text)\n            if current_result_value['source_alignment']['status']!='mismatch' or current_result_value['save_available'] is not False:raise RuntimeError('MCP 비교 상태 전달 오류')\n            print('city_mcp_mismatch_and_save_block=ok',flush=True)\n\n\nasyncio.run(inspect_city_mcp_transport())\n"
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_database_record={'map':'example','generation':5,'revision':2,'document':{'data':{'cityId':'example','version':1}}}
            def respond_to_city_editor(current_command_name,current_payload_record):
                if current_command_name=='city-edit-load':return current_database_record
                if current_command_name=='city-edit-preview':return {'token':city_map_operations.validate_hermes_city_draft(current_payload_record),'cityId':'example','changed':True,'columns':5,'rows':5,'buildings':1,'objects':0}
                raise AssertionError('예상하지 못한 도시 명령')
            current_environment_values=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root))
            try:
                with patch.object(city_map_operations,'call_field_map_editor',side_effect=respond_to_city_editor),patch('tools.review.domains.map_assets.source_consistency.inspect_city_source_alignment',return_value={'status':'mismatch','note':'모의 비교'}):
                    current_client_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment_values,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_client_process.returncode,0,current_client_process.stderr[-4000:])
                    self.assertIn('city_mcp_mismatch_and_save_block=ok',current_client_process.stdout)
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)


    def test_writer_material_crosses_stdio_and_gateway(current_test_case):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent import writer_operations
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,hashlib,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_writer_material_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_input_stream,current_output_stream):
        async with ClientSession(current_input_stream,current_output_stream) as current_session:
            await current_session.initialize()
            current_request={'job_identifier_value':'20261115-114927-8d274ccd','section_name':'search','limit_value':1000}
            current_fragments=[]
            while True:
                current_result=await current_session.call_tool('read_hermes_writer_job_material',current_request)
                if current_result.is_error:raise RuntimeError('작가 자료 조회 오류')
                current_page=current_result.structured_content or json.loads(current_result.content[0].text)
                current_fragments.append(current_page['content'])
                if current_page['next_offset'] is None:break
                current_request.update(offset_value=current_page['next_offset'],snapshot_value=current_page['snapshot'])
            current_complete_text=''.join(current_fragments)
            if hashlib.sha256(current_complete_text.encode()).hexdigest()!=current_page['snapshot']:raise RuntimeError('작가 자료 해시 불일치')
            if json.loads(current_complete_text)['results'][0]['text']!='안녕'*3000:raise RuntimeError('작가 자료 누락')
            current_request.update(offset_value=1,snapshot_value='0'*64)
            if not (await current_session.call_tool('read_hermes_writer_job_material',current_request)).is_error:raise RuntimeError('지문 충돌 미거부')
            current_review=await current_session.call_tool('read_hermes_writer_job_review',{'job_identifier_value':current_request['job_identifier_value']})
            if current_review.is_error:raise RuntimeError('작가 진단 조회 오류')
            current_review_value=current_review.structured_content or json.loads(current_review.content[0].text)
            if current_review_value['job']['diagnostic']['error']!='오류 /private/test':raise RuntimeError('작가 오류 누락')
            if current_review_value['job']['diagnostic']['log_tail']!='시험 로그':raise RuntimeError('작가 로그 누락')
            print('writer_material_transport=ok')
asyncio.run(inspect_writer_material_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_manager.handle_hermes_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server.server_port),PYTHONPATH=str(current_repository_root))
            current_detail={'id':'20261115-114927-8d274ccd','status':{'stage':'failed','error':'오류 /private/test'},'log':'시험 로그','search':{'results':[{'text':'안녕'*3000}]}}
            try:
                def respond_legacy_writer_service(current_command_name,current_payload_record):
                    if current_command_name=='writer-material-page':raise ValueError('관리 API 오류 (404): 지원하지 않는 경로')
                    return current_detail
                with patch.object(writer_operations,'call_hermes_writer_service',side_effect=respond_legacy_writer_service):
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
                current_test_case.assertIn('writer_material_transport=ok',current_process.stdout)
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)

    def test_writer_material_page_crosses_stdio_and_live_page_api(current_test_case):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from generators.writer_agent import management
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_writer_pages():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_input,current_output):
        async with ClientSession(current_input,current_output) as current_session:
            await current_session.initialize()
            current_request={'job_identifier_value':'20261115-114927-8d274ccd','section_name':'search','limit_value':97}
            current_fragments=[]
            while True:
                current_response=await current_session.call_tool('read_hermes_writer_job_material',current_request)
                if current_response.is_error:raise RuntimeError(str(current_response.content))
                current_page=current_response.structured_content or json.loads(current_response.content[0].text)
                current_fragments.append(current_page['content'])
                if current_page['next_offset'] is None:break
                current_request.update(offset_value=current_page['next_offset'],snapshot_value=current_page['snapshot'])
            if json.loads(''.join(current_fragments))!={'results':[{'text':'자료😀'*100}]}:raise RuntimeError('페이지 자료 불일치')
            Path(os.environ['WRITER_TEST_MATERIAL_PATH']).write_text('results: []\n')
            current_request.update(offset_value=1,snapshot_value=current_page['snapshot'])
            if not (await current_session.call_tool('read_hermes_writer_job_material',current_request)).is_error:raise RuntimeError('변경된 자료를 허용했습니다')
asyncio.run(inspect_writer_pages())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_identifier='20261115-114927-8d274ccd'
            current_job_path=current_root_path/'writer'/'jobs'/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.yaml').write_text('id: '+current_job_identifier+'\nstage: completed\n')
            current_material_path=current_job_path/'search.yaml'
            current_material_path.write_text(json.dumps({'results':[{'text':'자료😀'*100}]},ensure_ascii=False))
            current_writer_manager=management.WriterAgentManager(current_root_path/'workspace.yaml')
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'writer-agent':current_writer_manager.handle_writer_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server.server_port),WRITER_TEST_MATERIAL_PATH=str(current_material_path),PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='')
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_environment['SLIME_MANAGEMENT_GATEWAY_URL']}),patch.object(management,'load_workspace_config',return_value={'state_root':str(current_root_path/'writer')}),patch.object(current_writer_manager,'read_writer_detail',side_effect=AssertionError('전체 상세 조회 금지')) as current_detail_mock,patch.object(current_writer_manager,'read_writer_material_page',wraps=current_writer_manager.read_writer_material_page) as current_page_mock:
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
                    current_detail_mock.assert_not_called()
                    current_test_case.assertGreater(current_page_mock.call_count,2)
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)

    def test_audio_source_status_crosses_real_stdio_and_gateway(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent import audio_operations
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def verify_audio_source_status():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_input,current_output):
        async with ClientSession(current_input,current_output) as current_session:
            await current_session.initialize()
            if 'read_hermes_audio_source_status' not in {item.name for item in (await current_session.list_tools()).tools}:raise RuntimeError('원본 오디오 MCP 도구 누락')
            current_request={'audio_service_name':'music-heartmula','job_identifier_value':'2026-11-18_00-00-00-12345678'}
            current_response=await current_session.call_tool('read_hermes_audio_source_status',current_request)
            if current_response.is_error:raise RuntimeError(str(current_response.content))
            current_value=current_response.structured_content or json.loads(current_response.content[0].text)
            if current_value['job_id']!=current_request['job_identifier_value'] or current_value['job']['status']!='completed' or not current_value['job']['audio'].endswith('/music.wav'):raise RuntimeError('원본 상태 불일치')
            current_request['job_identifier_value']='../invalid'
            if not (await current_session.call_tool('read_hermes_audio_source_status',current_request)).is_error:raise RuntimeError('잘못된 작업 ID 허용')
asyncio.run(verify_audio_source_status())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_audio_path='/music-heartmula/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/music.wav'
            try:
                with patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier,'status':'completed','audio':current_audio_path}) as current_service_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_service_mock.assert_called_once_with('music-heartmula','status',{'id':current_job_identifier})
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_video_source_status_crosses_real_stdio_without_recovery(self):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent import video_operations
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_video_source():
 current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
 async with stdio_client(current_parameters) as (current_input,current_output):
  async with ClientSession(current_input,current_output) as current_session:
   await current_session.initialize()
   if 'read_hermes_video_source_status' not in {item.name for item in (await current_session.list_tools()).tools}:raise RuntimeError('영상 도구 누락')
   current_request={'video_service_name':'wan22-vace','job_identifier_value':'2026-11-18_00-00-00-12345678'}
   current_result=await current_session.call_tool('read_hermes_video_source_status',current_request)
   if current_result.is_error:raise RuntimeError(str(current_result.content))
   current_value=current_result.structured_content or json.loads(current_result.content[0].text)
   if current_value['job']['status']!='running' or current_value['job']['result_status']!='not_ready':raise RuntimeError('영상 상태 오류')
   current_request['job_identifier_value']='../invalid'
   if not (await current_session.call_tool('read_hermes_video_source_status',current_request)).is_error:raise RuntimeError('잘못된 ID 허용')
asyncio.run(inspect_video_source())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_video_root=current_root_path/'video'
            current_job_path=current_video_root/'2026-11-18_00-00-00-12345678'
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text(json.dumps({'status':'running'}))
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
            try:
                with patch.object(video_operations,'make_hermes_video_manager',return_value=SimpleNamespace(job_storage_root=current_video_root)),patch('tools.review.common.video_job_recovery.recover_interrupted_video_job') as current_recovery_mock:
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_recovery_mock.assert_not_called()
                    self.assertEqual(json.loads((current_job_path/'status.json').read_text()),{'status':'running'})
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_flux_resume_preview_and_submit_cross_stdio_and_gateway(current_test_case):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent import flux_resume_operations
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_flux_preview_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('preview_hermes_flux_resume',{'service_name':'flux-character','job_identifier_value':'2026-11-20_00-00-00-abcdef12'})
            if current_result.is_error:raise RuntimeError(str(current_result.content))
            current_preview_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_preview_value['service']!='flux-character' or current_preview_value['status']!='failed' or len(current_preview_value['expected_resume_fingerprint'])!=64:raise RuntimeError('FLUX 검토 응답 오류')
            current_request_value={'request_identifier_value':'flux_transport_test_123','service_name':'flux-character','job_identifier_value':'2026-11-20_00-00-00-abcdef12','expected_resume_fingerprint':current_preview_value['expected_resume_fingerprint']}
            current_submit_value=await current_session.call_tool('submit_hermes_flux_resume',current_request_value)
            if current_submit_value.is_error:raise RuntimeError('FLUX 접수 실패: '+str(current_submit_value.content))
            current_submit_record=current_submit_value.structured_content or json.loads(current_submit_value.content[0].text)
            if current_submit_record.get('state')!='accepted' or current_submit_record.get('duplicate') is not False:raise RuntimeError('FLUX 접수 확인 오류')
            current_duplicate_value=await current_session.call_tool('submit_hermes_flux_resume',current_request_value)
            current_duplicate_record=current_duplicate_value.structured_content or json.loads(current_duplicate_value.content[0].text)
            if current_duplicate_value.is_error or current_duplicate_record.get('duplicate') is not True:raise RuntimeError('FLUX 중복 방지 오류')
            current_receipt_value=await current_session.call_tool('read_hermes_flux_resume_receipt',{'request_identifier_value':'flux_transport_test_123'})
            current_receipt_record=current_receipt_value.structured_content or json.loads(current_receipt_value.content[0].text)
            if current_receipt_value.is_error or current_receipt_record.get('state')!='accepted':raise RuntimeError('FLUX 접수 조회 오류')
            print('flux_preview_transport=ok')
asyncio.run(inspect_flux_preview_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_flux_manager=FluxImageGenerationManager('flux-character')
            current_flux_manager.job_storage_root=current_root_path/'flux-jobs'
            current_job_path=current_flux_manager.job_storage_root/'2026-11-20_00-00-00-abcdef12'
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps({'profile':'flux-character','references':['reference-1.png']}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'reference-1.png').write_bytes(b'temporary reference')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'flux-character':current_flux_manager.handle_image_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root))
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}),patch.object(flux_resume_operations,'FLUX_RESUME_RECEIPT_ROOT',current_root_path/'flux-receipts'),patch('tools.review.common.model_prepare_process.resolve_model_preparation_root',return_value=current_root_path/'model-prep'),patch.object(current_flux_manager,'inspect_flux_resume_availability',return_value='available'),patch.object(current_flux_manager,'validate_generation_runtime'),patch.object(current_flux_manager,'validate_generation_resume'),patch.object(current_flux_manager,'resume_generation_job') as current_resume_mock,patch('tools.review.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
                    current_test_case.assertIn('flux_preview_transport=ok',current_process.stdout)
                    current_resume_mock.assert_not_called()
                    current_launch_mock.assert_called_once()
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)


    def test_video_resume_preview_and_submit_cross_stdio_and_gateway(current_test_case):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent import video_resume_operations
        from tools.review.domains.dwpose.generation import DwposeGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():current_test_case.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_video_preview_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_bad_result=await current_session.call_tool('preview_hermes_video_resume',{'service_name':'dwpose','job_identifier_value':'2026-11-20_00-00-00-abcdef12'})
            if not current_bad_result.is_error:raise RuntimeError('변조된 영상 명령을 검토에서 거부하지 않았습니다.')
            from pathlib import Path
            Path(os.environ['TEST_VIDEO_COMMAND_PATH']).write_text(os.environ['TEST_VIDEO_VALID_COMMAND'])
            current_result=await current_session.call_tool('preview_hermes_video_resume',{'service_name':'dwpose','job_identifier_value':'2026-11-20_00-00-00-abcdef12'})
            if current_result.is_error:raise RuntimeError(str(current_result.content))
            current_preview_value=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_preview_value['service']!='dwpose' or current_preview_value['status']!='failed' or len(current_preview_value['expected_resume_fingerprint'])!=64:raise RuntimeError('영상 검토 응답 오류')
            current_request_value={'request_identifier_value':'video_transport_test_123','service_name':'dwpose','job_identifier_value':'2026-11-20_00-00-00-abcdef12','expected_resume_fingerprint':current_preview_value['expected_resume_fingerprint']}
            current_submit_value=await current_session.call_tool('submit_hermes_video_resume',current_request_value)
            if current_submit_value.is_error:raise RuntimeError('영상 접수 실패: '+str(current_submit_value.content))
            current_submit_record=current_submit_value.structured_content or json.loads(current_submit_value.content[0].text)
            if current_submit_record.get('state')!='accepted' or current_submit_record.get('duplicate') is not False:raise RuntimeError('영상 접수 확인 오류')
            current_duplicate_value=await current_session.call_tool('submit_hermes_video_resume',current_request_value)
            current_duplicate_record=current_duplicate_value.structured_content or json.loads(current_duplicate_value.content[0].text)
            if current_duplicate_value.is_error or current_duplicate_record.get('duplicate') is not True:raise RuntimeError('영상 중복 방지 오류')
            current_receipt_value=await current_session.call_tool('read_hermes_video_resume_receipt',{'request_identifier_value':'video_transport_test_123'})
            current_receipt_record=current_receipt_value.structured_content or json.loads(current_receipt_value.content[0].text)
            if current_receipt_value.is_error or current_receipt_record.get('state')!='accepted':raise RuntimeError('영상 접수 조회 오류')
            print('video_preview_transport=ok')
asyncio.run(inspect_video_preview_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_flux_manager=DwposeGenerationManager()
            current_flux_manager.job_storage_root=current_root_path/'flux-jobs'
            current_job_path=current_flux_manager.job_storage_root/'2026-11-20_00-00-00-abcdef12'
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps({'references':['reference-1.png']}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'reference-1.png').write_bytes(b'temporary reference')
            current_command_path=current_job_path/'gpu-command.json'
            current_command_path.write_text(json.dumps({'service':'image','command':['tampered']}))
            from tools.review.domains.image.image_generation import WORKFLOW_ROOT_PATH
            current_expected_command={'service':current_flux_manager.select_generation_service(), 'command':[str(current_flux_manager.select_generation_python()),str(WORKFLOW_ROOT_PATH/current_flux_manager.select_generation_runner()),'--job-dir',str(current_job_path)]}
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'dwpose':current_flux_manager.handle_image_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root),TEST_VIDEO_COMMAND_PATH=str(current_command_path),TEST_VIDEO_VALID_COMMAND=json.dumps(current_expected_command))
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}),patch.object(video_resume_operations,'VIDEO_RESUME_RECEIPT_ROOT',current_root_path/'flux-receipts'),patch('tools.review.common.model_prepare_process.resolve_model_preparation_root',return_value=current_root_path/'model-prep'),patch.object(current_flux_manager,'inspect_video_resume_availability',return_value='available'),patch.object(current_flux_manager,'validate_generation_runtime'),patch.object(current_flux_manager,'validate_generation_resume'),patch.object(current_flux_manager,'resume_generation_job') as current_resume_mock,patch('tools.review.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    current_test_case.assertEqual(current_process.returncode,0,current_process.stderr[-4000:])
                    current_test_case.assertIn('video_preview_transport=ok',current_process.stdout)
                    current_resume_mock.assert_not_called()
                    current_launch_mock.assert_called_once()
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)


    def test_fun_resume_preview_and_submission_cross_stdio(self):
        import hashlib
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.wan_fun.generation import FunControlGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root = Path(__file__).resolve().parents[3]
        current_runtime_python = current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file(): self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script = r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_fun_preview_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_reader,current_writer):
        async with ClientSession(current_reader,current_writer) as current_session:
            await current_session.initialize()
            current_job_id='2026-11-20_20-00-00-1234abcd'
            current_result=await current_session.call_tool('preview_hermes_video_resume',{'service_name':'wan22-fun-control','job_identifier_value':current_job_id})
            if current_result.is_error: raise RuntimeError(str(current_result.content))
            current_record=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_record.get('service')!='wan22-fun-control' or current_record.get('job_id')!=current_job_id or current_record.get('resume_availability')!='available': raise RuntimeError(str(current_record))
            current_submit=await current_session.call_tool('submit_hermes_video_resume',{'request_identifier_value':'request_fun_123','service_name':'wan22-fun-control','job_identifier_value':current_job_id,'expected_resume_fingerprint':current_record['expected_resume_fingerprint']})
            if current_submit.is_error: raise RuntimeError(str(current_submit.content))
            current_receipt=current_submit.structured_content or json.loads(current_submit.content[0].text)
            if current_receipt.get('state')!='accepted': raise RuntimeError(str(current_receipt))
asyncio.run(inspect_fun_preview_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_fun_manager = FunControlGenerationManager()
            current_fun_manager.job_storage_root = current_root_path/'fun-jobs'
            current_job_path = current_fun_manager.job_storage_root/'2026-11-20_20-00-00-1234abcd'
            current_job_path.mkdir(parents=True)
            current_video_bytes = b'pose-input'
            (current_job_path/'request.json').write_text(json.dumps({'action':'generate','frames':5,'references':['reference-1.png'],'pose_video_file':'pose-input.mp4','pose_video_sha256':hashlib.sha256(current_video_bytes).hexdigest()}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'reference-1.png').write_bytes(b'reference')
            (current_job_path/'pose-input.mp4').write_bytes(current_video_bytes)
            current_hermes_manager = HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway = ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'wan22-fun-control':current_fun_manager.handle_image_request})
            current_server = ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace = lambda *current_values: None
            current_server_thread = threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url = 'http://127.0.0.1:'+str(current_server.server_port)
            current_environment = dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root))
            try:
                from tools.review.domains.hermes_agent import video_resume_operations
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}), patch.object(video_resume_operations,'VIDEO_RESUME_RECEIPT_ROOT',current_root_path/'receipts'), patch.object(current_fun_manager,'validate_generation_runtime'), patch('tools.review.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_process_value = subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                    current_launch_mock.assert_called_once()
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)


    def test_cleanup_preview_crosses_stdio_and_gateway_without_paths(self):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.dwpose.generation import DwposeGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_cleanup_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('preview_hermes_cleanup',{'generator_service_name':'dwpose'})
            if current_result.is_error:raise RuntimeError(str(current_result.content))
            current_record=current_result.structured_content or json.loads(current_result.content[0].text)
            if current_record.get('job_count')!=2 or current_record.get('blocked_count')!=1 or current_record.get('status_counts')!={'failed':1,'running':1}:raise RuntimeError(str(current_record))
            if 'secret' in json.dumps(current_record) or 'path' in json.dumps(current_record):raise RuntimeError('경로 노출')
            print('cleanup_transport=ok')
asyncio.run(inspect_cleanup_transport())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_instance=DwposeGenerationManager()
            current_manager_instance.job_storage_root=current_root_path/'private-secret'
            for current_index_value,current_status_value in enumerate(('failed','running')):
                current_job_path=current_manager_instance.job_storage_root/('2026-11-20_00-00-00-'+str(current_index_value).zfill(8))
                current_job_path.mkdir(parents=True)
                (current_job_path/'status.json').write_text(json.dumps({'status':current_status_value}))
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'dwpose':current_manager_instance.handle_image_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root))
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}):
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                self.assertEqual(current_process.returncode,0,current_process.stderr[-3000:])
                self.assertIn('cleanup_transport=ok',current_process.stdout)
                self.assertEqual(len(list(current_manager_instance.job_storage_root.iterdir())),2)
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)


    def test_legacy_wan_fun_source_history_crosses_stdio_and_gateway(self):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.wan_fun.generation import FunControlGenerationManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_wan_fun_history():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('list_hermes_generator_source_history',{'generator_service_name':'wan22-fun-control'})
            if current_result.is_error:raise RuntimeError(str(current_result.content))
            current_record=current_result.structured_content or json.loads(current_result.content[0].text)
            current_expected={'id':'2026-11-20_20-02-00-prepare','recorded_status':'queued','status_source':'job'}
            if current_record.get('service')!='wan22-fun-control' or current_record.get('records')!=[current_expected]:raise RuntimeError(str(current_record))
            if 'private-secret' in json.dumps(current_record):raise RuntimeError('경로 노출')
            print('legacy_fun_history_transport=ok')
asyncio.run(inspect_wan_fun_history())
"""
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_instance=FunControlGenerationManager()
            current_manager_instance.job_storage_root=current_root_path/'private-secret'
            current_job_path=current_manager_instance.job_storage_root/'2026-11-20_20-02-00-prepare'
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text('{"action":"prepare"}')
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'wan22-fun-control':current_manager_instance.handle_image_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}),patch.object(current_manager_instance,'history_storage_path',return_value=None):
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                self.assertEqual(current_process.returncode,0,current_process.stderr[-3000:])
                self.assertIn('legacy_fun_history_transport=ok',current_process.stdout)
                self.assertEqual((current_job_path/'status.json').read_text(),'{"status":"queued"}')
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)


    def test_legacy_fun_prepare_reservation_crosses_mcp_without_mutation(self):
        import json
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from tools.review.common import gpu_job_queue, gpu_status
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.domains.hermes_agent import management_observer
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[3]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_reservation_transport():
    current_parameters=StdioServerParameters(command=sys.executable,args=['tools/review/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
    async with stdio_client(current_parameters) as (current_read_stream,current_write_stream):
        async with ClientSession(current_read_stream,current_write_stream) as current_session:
            await current_session.initialize()
            current_result=await current_session.call_tool('read_hermes_management_status',{})
            if current_result.is_error:raise RuntimeError(str(current_result.content))
            current_record=current_result.structured_content or json.loads(current_result.content[0].text)
            current_reservations=current_record['reservations']['records']
            if len(current_reservations)!=1 or current_reservations[0].get('job_id')!='2026-11-20_20-02-00-prepare' or current_reservations[0].get('source_service')!='wan22-fun-control' or current_reservations[0].get('state')!='cleanup_unverified':raise RuntimeError(str(current_reservations))
            if 'private-secret' in json.dumps(current_record):raise RuntimeError('경로 노출')
            print('legacy_fun_reservation_transport=ok')
asyncio.run(inspect_reservation_transport())
"""
        with tempfile.TemporaryDirectory(prefix='private-secret-') as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/'.tmp'/'test'/'wan22-fun-control'/'2026-11-20_20-02-00-prepare'
            current_job_path.mkdir(parents=True)
            current_queue_root=current_root_path/'queue'
            (current_queue_root/'active').mkdir(parents=True)
            current_reservation_path=current_queue_root/'active'/'entry.json'
            current_reservation_path.write_text(json.dumps({'service':'wan-fun-prepare','path':str(current_job_path),'required_memory_mib':6144,'cleanup_unverified':True}))
            current_before_bytes=current_reservation_path.read_bytes()
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_server_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
            try:
                with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root),patch.object(gpu_job_queue,'list_waiting_gpu_jobs',return_value={'jobs':[]}),patch.object(gpu_status,'read_gpu_status',return_value={'status':'unavailable'}),patch.object(management_observer,'inspect_hermes_model_status',return_value={}),patch.object(management_observer,'read_hermes_generator_snapshot',return_value={}),patch.object(management_observer,'read_hermes_recent_job_snapshot',return_value={}):
                    current_process=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                self.assertEqual(current_process.returncode,0,current_process.stderr[-3000:])
                self.assertIn('legacy_fun_reservation_transport=ok',current_process.stdout)
                self.assertEqual(current_reservation_path.read_bytes(),current_before_bytes)
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_server_thread.join(timeout=5)


if __name__=='__main__':
    unittest.main()
