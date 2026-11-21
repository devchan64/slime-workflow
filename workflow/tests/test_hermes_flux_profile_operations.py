"""FLUX 프로필별 위임 경계와 결과 복구 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from workflow.domains.hermes_agent import flux_profile_operations
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS


class HermesFluxProfileOperationsTests(unittest.TestCase):
    def test_flux_source_observation_reads_only_selected_profile_storage(self):
        import json
        from types import SimpleNamespace
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            current_result_path=current_job_path/'result.png'
            current_result_path.write_bytes(b'not-an-image')
            with patch('workflow.domains.image.flux_image_generation.FluxImageGenerationManager',return_value=SimpleNamespace(job_storage_root=current_root_path)),patch.object(flux_profile_operations,'call_hermes_flux_profile') as current_gateway_mock:
                current_result_value=flux_profile_operations.read_hermes_flux_source_job('flux-building',current_job_identifier)
                self.assertEqual(current_result_value['image'],'/flux-building-generator/jobs/'+current_job_identifier+'/result.png')
                self.assertEqual(current_result_value['result_status'],'available')
                current_result_path.unlink()
                current_result_path.symlink_to(current_job_path/'status.json')
                self.assertEqual(flux_profile_operations.read_hermes_flux_source_job('flux-building',current_job_identifier)['result_status'],'unavailable')
                self.assertEqual(json.loads((current_job_path/'status.json').read_text()),{'status':'completed'})
                current_gateway_mock.assert_not_called()
                with self.assertRaises(ValueError):flux_profile_operations.read_hermes_flux_source_job('flux-building','../invalid')

    def test_all_flux_source_links_reach_actual_manager_file_handlers(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import urlopen
        from workflow.common.management_gateway import ManagementCommandGateway,execute_management_command
        from workflow.common.management_transport import proxy_management_request
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        from workflow.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        from workflow.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_managers_map={current_name:FluxImageGenerationManager(current_name) for current_name in FLUX_IMAGE_PROFILE_RECORDS}
            current_managers_map['flux-expression']=FluxExpressionGenerationManager()
            for current_service_name,current_manager_value in current_managers_map.items():
                current_manager_value.job_storage_root=current_root_path/current_service_name
                current_job_root=current_manager_value.job_storage_root/current_job_identifier
                current_job_root.mkdir(parents=True)
                (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
                (current_job_root/'result.png').write_bytes(('fixture-'+current_service_name).encode())
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request})
            def dispatch_test_runtime(current_http_handler):
                for current_manager_value in current_managers_map.values():
                    if current_http_handler.path.startswith(current_manager_value.route_prefix_value+'/jobs/'):
                        return current_manager_value.handle_image_request(current_http_handler)
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
                with patch('workflow.domains.image.flux_image_generation.FluxImageGenerationManager',side_effect=lambda current_name:current_managers_map[current_name]),patch('workflow.domains.image.flux_expression_generation.FluxExpressionGenerationManager',return_value=current_managers_map['flux-expression']):
                    for current_service_name in current_managers_map:
                        with self.subTest(service=current_service_name):
                            current_response_value=execute_management_command('hermes-agent','hermes-flux-source-status',{'service':current_service_name,'job_id':current_job_identifier},current_gateway_url)
                            current_job_record=flux_profile_operations.validate_hermes_flux_source_response(current_service_name,current_job_identifier,current_response_value)
                            self.assertEqual(current_job_record['result_status'],'available')
                            with urlopen(current_proxy_url+current_job_record['image'],timeout=5) as current_http_response:
                                self.assertEqual(current_http_response.read(),('fixture-'+current_service_name).encode())
                            self.assertEqual(json.loads((current_managers_map[current_service_name].job_storage_root/current_job_identifier/'status.json').read_text()),{'status':'completed'})
            finally:
                current_proxy_server.shutdown();current_proxy_server.server_close();current_proxy_thread.join(timeout=5)
                current_gateway_server.shutdown();current_gateway_server.server_close();current_gateway_thread.join(timeout=5)

    def test_all_archived_image_source_links_reach_actual_manager_file_handlers(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import urlopen
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES,execute_management_command
        from workflow.common.management_runtime import ManagementServiceRuntime,bind_stored_management_service,build_building_compatibility_handler
        from workflow.common.management_transport import proxy_management_request
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent import image_source_operations
        from workflow.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_managers_map={current_name:image_source_operations.make_image_source_manager(current_name) for current_name in image_source_operations.IMAGE_SOURCE_MANAGER_RECORDS}
            for current_service_name,current_manager_value in current_managers_map.items():
                current_manager_value.job_storage_root=current_root_path/current_service_name
                current_job_root=current_manager_value.job_storage_root/current_job_identifier
                current_job_root.mkdir(parents=True)
                (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
                (current_job_root/'result.png').write_bytes(('fixture-'+current_service_name).encode())
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_bindings_map={current_name:bind_stored_management_service(lambda current_request:False,current_root_path) for current_name in MANAGEMENT_SERVICE_ROUTES}
            for current_service_name,current_manager_value in current_managers_map.items():
                current_bindings_map[current_service_name]=bind_stored_management_service(current_manager_value.handle_image_request,current_manager_value.job_storage_root)
            current_billboard_manager=current_managers_map['billboard-generator']
            current_bindings_map['building-generator']=bind_stored_management_service(build_building_compatibility_handler(current_billboard_manager),current_billboard_manager.job_storage_root)
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
                with patch.object(image_source_operations,'make_image_source_manager',side_effect=lambda current_name:current_managers_map[current_name]):
                    for current_service_name in image_source_operations.IMAGE_SOURCE_SERVICES:
                        with self.subTest(service=current_service_name):
                            current_response_value=execute_management_command('hermes-agent','hermes-image-source-status',{'service':current_service_name,'job_id':current_job_identifier},current_gateway_url)
                            current_job_record=image_source_operations.validate_hermes_image_source_response(current_service_name,current_job_identifier,current_response_value)
                            self.assertEqual(current_job_record['result_status'],'available')
                            with urlopen(current_proxy_url+current_job_record['image'],timeout=5) as current_http_response:
                                self.assertEqual(current_http_response.read(),('fixture-'+image_source_operations.SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)).encode())
                            self.assertEqual(json.loads((current_managers_map[image_source_operations.SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)].job_storage_root/current_job_identifier/'status.json').read_text()),{'status':'completed'})
                    with urlopen(current_proxy_url+'/building-generator/jobs/'+current_job_identifier+'/result.png',timeout=5) as current_compat_response:
                        self.assertEqual(current_compat_response.read(),b'fixture-billboard-generator')
            finally:
                current_proxy_server.shutdown();current_proxy_server.server_close();current_proxy_thread.join(timeout=5)
                current_gateway_server.shutdown();current_gateway_server.server_close();current_gateway_thread.join(timeout=5)

    def test_archived_image_source_rejects_unsafe_records_and_changed_status(self):
        import json
        from types import SimpleNamespace
        from workflow.domains.hermes_agent import image_source_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_root=current_root_path/current_job_identifier
            current_job_root.mkdir()
            current_status_path=current_job_root/'status.json'
            current_status_path.write_text(json.dumps({'status':'completed'}))
            current_result_path=current_job_root/'result.png'
            current_result_path.write_bytes(b'fixture')
            with patch.object(image_source_operations,'make_image_source_manager',return_value=SimpleNamespace(job_storage_root=current_root_path)):
                current_job_record=image_source_operations.read_hermes_image_source_job('building-generator',current_job_identifier)
                self.assertEqual(current_job_record['source_service'],'billboard-generator')
                current_response_value={'service':'building-generator','job_id':current_job_identifier,'job':current_job_record}
                self.assertEqual(image_source_operations.validate_hermes_image_source_response('building-generator',current_job_identifier,current_response_value),current_job_record)
                with self.assertRaises(ValueError):image_source_operations.validate_hermes_image_source_response('building-generator',current_job_identifier,{**current_response_value,'job':{**current_job_record,'source_service':'building-generator'}})
                with self.assertRaises(ValueError):image_source_operations.validate_hermes_image_source_response('building-generator',current_job_identifier,{**current_response_value,'job':{**current_job_record,'image':'/private/secret'}})
                current_result_path.unlink()
                current_result_path.symlink_to(current_status_path)
                self.assertEqual(image_source_operations.read_hermes_image_source_job('building-generator',current_job_identifier)['result_status'],'unavailable')
                with patch.object(image_source_operations,'read_bounded_delegation_record',side_effect=[{'status':'running'},{'status':'completed'}]):
                    with self.assertRaises(ValueError):image_source_operations.read_hermes_image_source_job('building-generator',current_job_identifier)
                current_status_path.unlink()
                current_status_path.symlink_to(current_result_path)
                with self.assertRaises((ValueError,OSError)):image_source_operations.read_hermes_image_source_job('building-generator',current_job_identifier)
                with self.assertRaises(ValueError):image_source_operations.read_hermes_image_source_job('building-generator','../invalid')
                with self.assertRaises(ValueError):image_source_operations.read_hermes_image_source_job('unknown',current_job_identifier)

    def test_flux_source_response_rejects_wrong_identity_paths_and_status(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_path_value='/flux-building-generator/jobs/'+current_job_identifier+'/result.png'
        current_response_value={'service':'flux-building','job_id':current_job_identifier,'job':{'status':'completed','image':current_path_value,'result_status':'available'}}
        self.assertEqual(flux_profile_operations.validate_hermes_flux_source_response('flux-building',current_job_identifier,current_response_value)['image'],current_path_value)
        for current_bad_response in ({**current_response_value,'service':'flux-character'}, {**current_response_value,'job_id':'other'}, {**current_response_value,'job':{'status':'completed','image':'/private/secret','result_status':'available'}}, {**current_response_value,'job':{'status':'running','image':current_path_value,'result_status':'available'}}, {**current_response_value,'job':{'status':'completed','image':None,'result_status':'available'}}):
            with self.subTest(response=current_bad_response),self.assertRaises(ValueError):flux_profile_operations.validate_hermes_flux_source_response('flux-building',current_job_identifier,current_bad_response)

    def test_every_profile_delegates_to_own_service_and_isolates_receipts(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name, patch.object(flux_profile_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch('workflow.domains.image.flux_image_generation.FluxImageGenerationManager.validate_generation_request') as current_validate_mock, patch.object(flux_profile_operations,'call_hermes_flux_profile',return_value={'id':current_job_identifier}) as current_gateway_mock:
            for current_index_value,current_profile_name in enumerate(FLUX_IMAGE_PROFILE_RECORDS):
                current_request_identifier='profile_request_'+str(current_index_value)
                current_request_value={'profile':current_profile_name}
                self.assertFalse(flux_profile_operations.submit_hermes_flux_profile(current_request_identifier,current_profile_name,current_request_value)['duplicate'])
                self.assertTrue(flux_profile_operations.submit_hermes_flux_profile(current_request_identifier,current_profile_name,current_request_value)['duplicate'])
                self.assertEqual(flux_profile_operations.list_hermes_flux_profile_receipts(current_profile_name)['records'][0]['request_id'],current_request_identifier)
            self.assertEqual(current_validate_mock.call_count,len(FLUX_IMAGE_PROFILE_RECORDS))
            self.assertEqual(current_gateway_mock.call_count,len(FLUX_IMAGE_PROFILE_RECORDS))
            with self.assertRaises(ValueError):
                flux_profile_operations.read_hermes_flux_profile_status('profile_request_0','flux-building')
            with self.assertRaises(ValueError):
                flux_profile_operations.list_hermes_flux_profile_receipts('arbitrary-service')

    def test_reference_ui_confirms_actual_service_receipt_once(self):
        from gui.ui.gradio import hermes_agent_app
        current_job='2026-11-18_00-00-00-12345678'
        current_source={'proposal':{'service':'flux-building'},'request_id':'profile_request_123'}
        current_review={'source':current_source,'review':{'request_id':'profile_request_123','service':'flux-building','request':{'prompt':'house'}}}
        def current_gateway(current_service,current_command,current_payload):
            self.assertEqual(current_service,'hermes-agent')
            if current_command=='hermes-delegate-flux-profile':return flux_profile_operations.submit_hermes_flux_profile(current_payload['request_id'],current_payload['service'],current_payload['request'])
            if current_command=='hermes-flux-profile-status':return flux_profile_operations.read_hermes_flux_profile_status(current_payload['request_id'],current_payload['service'])
            raise AssertionError(current_command)
        def current_profile_service(current_service,current_command,current_payload):
            return {'id':current_job} if current_command=='generate' else {'id':current_job,'status':'queued'}
        with TemporaryDirectory() as current_root, patch.object(flux_profile_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root))), patch('workflow.domains.image.flux_image_generation.FluxImageGenerationManager.validate_generation_request'), patch.object(flux_profile_operations,'call_hermes_flux_profile',side_effect=current_profile_service) as current_profile_mock, patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway), patch.object(hermes_agent_app,'review_conversation_flux_reference',return_value=(current_review,'','')):
            for current_iteration in range(2):
                _,current_status=hermes_agent_app.submit_conversation_flux_reference(current_review,current_source,'session','job',None,None)
                self.assertIn('접수 기록 확인',current_status)
                self.assertIn('queued',current_status)
            self.assertEqual(sum(current_call.args[1]=='generate' for current_call in current_profile_mock.call_args_list),1)

    def test_expression_uses_its_own_manager_and_service(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name, patch.object(flux_profile_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch('workflow.domains.image.flux_expression_generation.FluxExpressionGenerationManager.validate_generation_request') as current_validate_mock, patch.object(flux_profile_operations,'call_hermes_flux_profile',return_value={'id':current_job_identifier}) as current_gateway_mock:
            current_request_value={'prompt':'joy'}
            self.assertFalse(flux_profile_operations.submit_hermes_flux_profile('expression_request_123','flux-expression',current_request_value)['duplicate'])
            self.assertTrue(flux_profile_operations.submit_hermes_flux_profile('expression_request_123','flux-expression',current_request_value)['duplicate'])
            current_validate_mock.assert_called_once_with(current_request_value)
            current_gateway_mock.assert_called_once_with('flux-expression','generate',current_request_value)
            self.assertEqual(flux_profile_operations.list_hermes_flux_profile_receipts('flux-expression')['records'][0]['job_id'],current_job_identifier)
            with self.assertRaises(ValueError):
                flux_profile_operations.read_hermes_flux_profile_status('expression_request_123','flux-image')

    def test_completed_image_link_requires_exact_service_job_and_path(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_expected_path='/flux-building-generator/jobs/'+current_job_identifier+'/result.png'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('profile_request_123','flux-building',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(flux_profile_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(flux_profile_operations,'call_hermes_flux_profile') as current_gateway_mock:
                current_gateway_mock.return_value={'status':'completed','image':current_expected_path}
                current_result_value=flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']
                self.assertEqual(current_result_value['image'],current_expected_path)
                self.assertEqual(current_result_value['result_status'],'available')
                current_gateway_mock.return_value={'id':'2026-11-18_00-00-00-ffffffff','status':'completed','image':current_expected_path}
                with self.assertRaises(ValueError):
                    flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'completed','image':current_expected_path}
                self.assertEqual(flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']['image'],current_expected_path)
                with self.assertRaises(ValueError):
                    flux_profile_operations.inspect_hermes_flux_result('flux-image',current_job_identifier,{'id':'2026-11-18_00-00-00-ffffffff','status':'running'})
                for current_bad_path in ('https://example.com/result.png',current_expected_path+'?x=1',current_expected_path.replace('flux-building','flux-prop'),current_expected_path.replace(current_job_identifier,'2026-11-18_00-00-00-ffffffff')):
                    current_gateway_mock.return_value={'status':'completed','image':current_bad_path}
                    current_result_value=flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']
                    self.assertIsNone(current_result_value['image'])
                    self.assertEqual(current_result_value['result_status'],'unavailable')
                current_gateway_mock.return_value={'status':'running','image':current_expected_path}
                self.assertIsNone(flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']['image'])

    def test_cancellation_requires_explicit_service_acknowledgement(self):
        from workflow.domains.hermes_agent import audio_operations,video_operations,translation_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_cases=[(flux_profile_operations,'call_hermes_flux_profile','flux-building','cancel_hermes_flux_profile'),(audio_operations,'call_hermes_audio_service','music-heartmula','cancel_hermes_audio_request'),(video_operations,'call_hermes_video_service','wan22-vace','cancel_hermes_video_request'),(translation_operations,'call_hermes_translation_service','prompt-translation','cancel_hermes_translation_request')]
        for current_module_value,current_gateway_name,current_service_name,current_function_name in current_cases:
            with self.subTest(service=current_service_name),TemporaryDirectory() as current_root_name:
                current_store_value=HermesDelegationStore(Path(current_root_name))
                current_store_value.execute_service_delegation_once('cancel_request_123',current_service_name,{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
                current_arguments=('cancel_request_123',current_job_identifier) if current_service_name=='prompt-translation' else ('cancel_request_123',current_service_name,current_job_identifier)
                with patch.object(current_module_value,'HermesDelegationStore',return_value=current_store_value),patch.object(current_module_value,current_gateway_name) as current_gateway_mock:
                    for current_response_value in ({},{'cancel_requested':False},{'cancel_requested':'true'}):
                        current_gateway_mock.return_value=current_response_value
                        with self.assertRaises(ValueError):getattr(current_module_value,current_function_name)(*current_arguments)
                    current_gateway_mock.return_value={'status':'running','cancel_requested':True,'id':'2026-11-18_00-00-00-ffffffff'}
                    with self.assertRaises(ValueError):getattr(current_module_value,current_function_name)(*current_arguments)
                    for current_response_value in ({'status':'running','cancel_requested':True},{'status':'running','cancel_requested':True,'id':current_job_identifier}):
                        current_gateway_mock.return_value=current_response_value
                        self.assertTrue(getattr(current_module_value,current_function_name)(*current_arguments)['cancel_requested'])

    def test_cancel_rejects_other_service_and_job_before_dispatch(self):
        from workflow.domains.hermes_agent import audio_operations,video_operations,translation_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_cases=((flux_profile_operations,'call_hermes_flux_profile','flux-building','flux-prop','cancel_hermes_flux_profile'),(audio_operations,'call_hermes_audio_service','music-heartmula','sfx-dasheng-audiogen','cancel_hermes_audio_request'),(video_operations,'call_hermes_video_service','wan22-vace','dwpose','cancel_hermes_video_request'),(translation_operations,'call_hermes_translation_service','prompt-translation',None,'cancel_hermes_translation_request'))
        for current_module_value,current_gateway_name,current_service_name,current_other_service,current_function_name in current_cases:
            with self.subTest(service=current_service_name),TemporaryDirectory() as current_root_name:
                current_store_value=HermesDelegationStore(Path(current_root_name))
                current_store_value.execute_service_delegation_once('cancel_request_123',current_service_name,{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
                with patch.object(current_module_value,'HermesDelegationStore',return_value=current_store_value),patch.object(current_module_value,current_gateway_name) as current_gateway_mock:
                    current_function_value=getattr(current_module_value,current_function_name)
                    current_bad_job_arguments=('cancel_request_123','2026-11-18_00-00-00-ffffffff') if current_other_service is None else ('cancel_request_123',current_service_name,'2026-11-18_00-00-00-ffffffff')
                    with self.assertRaises(ValueError):current_function_value(*current_bad_job_arguments)
                    if current_other_service is not None:
                        with self.assertRaises(ValueError):current_function_value('cancel_request_123',current_other_service,current_job_identifier)
                    current_gateway_mock.assert_not_called()

    def test_unknown_response_and_cancel_require_matching_service_and_job(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('profile_request_123','flux-building',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(flux_profile_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(flux_profile_operations,'call_hermes_flux_profile',return_value={'status':'running','cancel_requested':True}) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    flux_profile_operations.cancel_hermes_flux_profile('profile_request_123','flux-building','2026-11-18_00-00-00-ffffffff')
                with self.assertRaises(ValueError):
                    flux_profile_operations.cancel_hermes_flux_profile('profile_request_123','flux-prop',current_job_identifier)
                current_gateway_mock.assert_not_called()
                self.assertTrue(flux_profile_operations.cancel_hermes_flux_profile('profile_request_123','flux-building',current_job_identifier)['cancel_requested'])
