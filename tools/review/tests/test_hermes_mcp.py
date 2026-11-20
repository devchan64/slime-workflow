import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class FakeHermesMcpServer:
    def __init__(self, *server_argument_values, **server_keyword_values):
        self.test_instructions=server_keyword_values.get("instructions", "")
    def tool(self, **tool_keyword_values):
        def register_fake_tool(current_tool_callback):
            current_tool_callback.test_annotations=tool_keyword_values.get('annotations',{})
            return current_tool_callback
        return register_fake_tool


fake_mcp_module = types.ModuleType('mcp')
fake_mcp_server = types.ModuleType('mcp.server')
fake_mcp_internal = types.ModuleType('mcp.server.mcpserver')
fake_mcp_exceptions = types.ModuleType('mcp.server.mcpserver.exceptions')
fake_mcp_types = types.ModuleType('mcp.types')
fake_mcp_server.MCPServer = FakeHermesMcpServer
fake_mcp_exceptions.ToolError = ValueError
fake_mcp_types.ToolAnnotations = lambda **annotation_keyword_values: annotation_keyword_values
hermes_module_path = Path(__file__).resolve().parents[1] / 'domains/hermes_agent/mcp_server.py'
hermes_module_spec = importlib.util.spec_from_file_location('hermes_mcp_test_module', hermes_module_path)
hermes_module_value = importlib.util.module_from_spec(hermes_module_spec)
with patch.dict(sys.modules, {'mcp':fake_mcp_module, 'mcp.server':fake_mcp_server, 'mcp.server.mcpserver':fake_mcp_internal, 'mcp.server.mcpserver.exceptions':fake_mcp_exceptions, 'mcp.types':fake_mcp_types}):
    hermes_module_spec.loader.exec_module(hermes_module_value)


class HermesMcpTests(unittest.TestCase):
    def test_city_source_mcp_rejects_mismatched_identity_and_hash(self):
        current_document_value={'managementId':'config.city-layouts.stonewarm','data':{'cityId':'stonewarm'}}
        current_response_value={'map':'stonewarm','document':current_document_value,'source_sha256':'a'*64}
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value=current_response_value) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_city_source('stonewarm'),current_response_value)
            current_gateway_mock.assert_called_once_with('hermes-city-source',{'map':'stonewarm'})
        for current_bad_response in ({**current_response_value,'source_sha256':'invalid'}, {**current_response_value,'map':'other'}, {**current_response_value,'document':{'managementId':'config.city-layouts.other','data':{'cityId':'stonewarm'}}}, {**current_response_value,'document':{'managementId':'config.city-layouts.stonewarm','data':{'cityId':'other'}}}):
            with self.subTest(current_bad_response=current_bad_response), patch.object(hermes_module_value,'run_hermes_mcp_command',return_value=current_bad_response):
                with self.assertRaises(ValueError):hermes_module_value.read_hermes_city_source('stonewarm')

    def test_server_instructions_distinguish_isolation_and_live_delegation(self):
        current_instructions_text=hermes_module_value.hermes_mcp_server.test_instructions
        self.assertIn('관리도구 사본',current_instructions_text)
        self.assertIn('실제 생성기·데이터',current_instructions_text)
        self.assertIn('요청 식별자',current_instructions_text)

    def test_writer_reservation_recovery_forwards_acknowledgement(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.recover_hermes_writer_reservation('recovery_123','20261118-120000-12345678','a'*64,True)
            current_gateway_mock.assert_called_once_with('hermes-writer-reservation-recover',{'request_id':'recovery_123','job_id':'20261118-120000-12345678','review_sha256':'a'*64,'outside_processes_checked':True})
            self.assertTrue(hermes_module_value.recover_hermes_writer_reservation.test_annotations['destructive_hint'])

    def test_generator_reservation_recovery_forwards_confirmation_and_receipt(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.recover_hermes_generator_reservation('recovery_123','kimodo','job-123','a'*64,True)
            current_gateway_mock.assert_called_once_with('hermes-generator-reservation-recover',{'request_id':'recovery_123','service':'kimodo','job_id':'job-123','review_sha256':'a'*64,'outside_processes_checked':True})
            self.assertTrue(hermes_module_value.recover_hermes_generator_reservation.test_annotations['destructive_hint'])
            current_gateway_mock.reset_mock()
            hermes_module_value.read_hermes_generator_reservation_receipt('recovery_123')
            current_gateway_mock.assert_called_once_with('hermes-generator-reservation-receipt',{'request_id':'recovery_123'})

    def test_writer_cancel_forwards_both_identifiers(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={'job_id':'20261118-120000-12345678','cancel_requested':True}) as current_gateway_mock:
            hermes_module_value.cancel_hermes_writer('request_123','20261118-120000-12345678')
            current_gateway_mock.assert_called_once_with('hermes-writer-cancel',{'request_id':'request_123','job_id':'20261118-120000-12345678'})
            self.assertTrue(hermes_module_value.cancel_hermes_writer.test_annotations['destructive_hint'])
            self.assertFalse(hermes_module_value.cancel_hermes_writer.test_annotations['idempotent_hint'])

    def test_expression_catalog_is_read_only_and_forwards_snapshot(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.list_hermes_expression_presets('기쁨',3,3,'a'*64)
            current_gateway_mock.assert_called_once_with('hermes-expression-catalog',{'query':'기쁨','offset':3,'limit':3,'snapshot':'a'*64})
            self.assertTrue(hermes_module_value.list_hermes_expression_presets.test_annotations['read_only_hint'])

    def test_building_anchor_review_save_and_receipt_are_forwarded(self):
        current_draft_value={'texture':'town-test-v1'}
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.preview_hermes_building_anchor(current_draft_value)
            current_gateway_mock.assert_called_with('hermes-building-preview',{'draft':current_draft_value})
            hermes_module_value.save_hermes_building_anchor('request_123',current_draft_value,'a'*64)
            current_gateway_mock.assert_called_with('hermes-building-save',{'request_id':'request_123','draft':current_draft_value,'review_sha256':'a'*64})
            hermes_module_value.read_hermes_building_anchor_receipt('request_123')
            current_gateway_mock.assert_called_with('hermes-building-receipt',{'request_id':'request_123'})
            self.assertTrue(hermes_module_value.save_hermes_building_anchor.test_annotations['destructive_hint'])

    def test_city_and_building_proposal_reads_forward_exact_job(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_city_proposal('city-job')
            current_gateway_mock.assert_called_with('hermes-city-proposal',{'id':'city-job'})
            hermes_module_value.read_hermes_building_proposal('building-job')
            current_gateway_mock.assert_called_with('hermes-building-proposal',{'id':'building-job'})

    def test_building_catalog_forwards_snapshot(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_building_catalog('길드',1,1,'a'*64)
            current_gateway_mock.assert_called_once_with('hermes-building-catalog',{'query':'길드','offset':1,'limit':1,'snapshot':'a'*64})

    def test_kimodo_keyframe_batch_validation_forwards_inputs(self):
        current_placements_value=[{'id':'a'*32,'frame':1}]
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.validate_hermes_kimodo_keyframes(current_placements_value,30)
            current_gateway_mock.assert_called_once_with('hermes-kimodo-keyframe-validate',{'keyframes':current_placements_value,'frames':30})

    def test_kimodo_keyframe_search_forwards_pagination(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.list_hermes_kimodo_keyframes('walk',20,10)
            current_gateway_mock.assert_called_once_with('hermes-kimodo-keyframes',{'query':'walk','offset':20,'limit':10})

    def test_effect_registration_commands_forward_confirmed_inputs(self):
        current_draft_value={'id':'fog-v1'}
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={'state':'completed'}) as current_command_mock:
            hermes_module_value.preview_hermes_effect_registration(current_draft_value)
            current_command_mock.assert_called_with('hermes-effect-register-preview',{'draft':current_draft_value})
            hermes_module_value.register_hermes_effect('request_123',current_draft_value,'b'*64)
            current_command_mock.assert_called_with('hermes-effect-register',{'request_id':'request_123','draft':current_draft_value,'review_sha256':'b'*64})
            hermes_module_value.read_hermes_effect_registration_receipt('request_123')
            current_command_mock.assert_called_with('hermes-effect-register-receipt',{'request_id':'request_123'})

    def test_waypoint_replacement_commands_forward_confirmed_inputs(self):
        current_draft_value={'id':'waypoint-v1','revision':'a'*64,'effect':{}}
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={'state':'completed'}) as current_command_mock:
            hermes_module_value.preview_hermes_waypoint_replacement(current_draft_value)
            current_command_mock.assert_called_with('hermes-waypoint-preview',{'draft':current_draft_value})
            hermes_module_value.replace_hermes_waypoint('request_123',current_draft_value,'b'*64)
            current_command_mock.assert_called_with('hermes-waypoint-replace',{'request_id':'request_123','draft':current_draft_value,'review_sha256':'b'*64})
            hermes_module_value.read_hermes_waypoint_receipt('request_123')
            current_command_mock.assert_called_with('hermes-waypoint-receipt',{'request_id':'request_123'})
        self.assertTrue(hermes_module_value.replace_hermes_waypoint.test_annotations['destructive_hint'])

    def test_local_locking_queries_are_not_advertised_as_read_only(self):
        current_tool_names=('read_hermes_coding_task','list_hermes_coding_tasks','read_hermes_task_diff','read_hermes_session','read_hermes_session_view','list_hermes_sessions','read_hermes_video_proposal','read_hermes_audio_proposal','read_hermes_translation_proposal','read_hermes_sprite_proposal','read_hermes_effect_proposal','read_hermes_billboard_proposal','read_hermes_field_map_proposal','list_hermes_delegation_receipts','read_hermes_delegation_status','read_hermes_kimodo_proposal','read_hermes_flux_proposal','list_hermes_flux_delegations','read_hermes_management_status')
        for current_tool_name in current_tool_names:
            with self.subTest(tool=current_tool_name):
                self.assertFalse(getattr(hermes_module_value,current_tool_name).test_annotations['read_only_hint'])
        self.assertTrue(hermes_module_value.list_hermes_management_capabilities.test_annotations['read_only_hint'])

    def test_coding_cancel_requires_matching_response_identity(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with patch.object(hermes_module_value,'call_hermes_management_gateway') as current_gateway_mock:
            for current_bad_response in ({'id':'other','cancel_requested':True,'status':'running'},{'cancel_requested':True,'status':'running'},{'id':current_job_identifier,'cancel_requested':False,'status':'running'}):
                current_gateway_mock.return_value=current_bad_response
                with self.subTest(current_bad_response=current_bad_response),self.assertRaises(ValueError):hermes_module_value.cancel_hermes_coding_task(current_job_identifier)
            current_gateway_mock.return_value={'id':current_job_identifier,'cancel_requested':True,'status':'queued'}
            self.assertEqual(hermes_module_value.cancel_hermes_coding_task(current_job_identifier),current_gateway_mock.return_value)

    def test_cancel_error_never_retries_and_guides_status_check(self):
        current_cases=(
            ('cancel_hermes_video',('request_123','dwpose','job-1')),
            ('cancel_hermes_audio',('request_123','music-heartmula','job-1')),
            ('cancel_hermes_flux_profile',('request_123','flux-image','job-1')),
            ('cancel_hermes_translation',('request_123','job-1')),
            ('cancel_hermes_writer',('request_123','job-1')),
            ('cancel_hermes_kimodo_delegation',('request_123','job-1')),
            ('cancel_hermes_flux_delegation',('request_123','job-1')),
        )
        for current_tool_name,current_tool_arguments in current_cases:
            with self.subTest(tool=current_tool_name),patch.object(hermes_module_value,'run_hermes_mcp_command',side_effect=OSError('response lost')) as current_gateway_mock:
                with self.assertRaisesRegex(Exception,'실제 상태를 확인하고 자동으로 다시 요청하지 마세요'):
                    getattr(hermes_module_value,current_tool_name)(*current_tool_arguments)
                current_gateway_mock.assert_called_once()

    def test_cancel_response_requires_job_and_acknowledgement(self):
        current_request_value={'request_id':'request_123','job_id':'job-1'}
        with patch.object(hermes_module_value,'run_hermes_mcp_command') as current_gateway_mock:
            for current_bad_response in ({},{'job_id':'other','cancel_requested':True},{'job_id':'job-1','cancel_requested':False},None):
                with self.subTest(response=current_bad_response):
                    current_gateway_mock.return_value=current_bad_response
                    with self.assertRaisesRegex(Exception,'실제 상태를 확인'):
                        hermes_module_value.execute_hermes_cancellation_command('hermes-video-cancel',current_request_value)
            current_gateway_mock.return_value={'job_id':'job-1','cancel_requested':True,'status':'running'}
            self.assertEqual(hermes_module_value.execute_hermes_cancellation_command('hermes-video-cancel',current_request_value),current_gateway_mock.return_value)

    def test_cancellation_tools_do_not_promise_repeatable_success(self):
        for current_tool_name in ('cancel_hermes_video','cancel_hermes_audio','cancel_hermes_flux_profile','cancel_hermes_translation','cancel_hermes_flux_delegation','cancel_hermes_kimodo_delegation'):
            with self.subTest(tool=current_tool_name):
                self.assertFalse(getattr(hermes_module_value,current_tool_name).test_annotations['idempotent_hint'])
                self.assertTrue(getattr(hermes_module_value,current_tool_name).test_annotations['destructive_hint'])

    def test_submit_forwards_same_request_identifier_to_gateway(self):
        hermes_response_file = io.BytesIO(b'{"id":"job-id","status":"queued"}')
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:8771'}), patch.object(hermes_module_value.urllib.request, 'build_opener') as hermes_opener_mock:
            hermes_opener_mock.return_value.open.return_value = hermes_response_file
            hermes_result_record = hermes_module_value.submit_hermes_coding_task('same-request-1234', '작업')
            hermes_request_object = hermes_opener_mock.return_value.open.call_args.args[0]
        self.assertEqual(hermes_result_record['id'], 'job-id')
        self.assertEqual(json.loads(hermes_request_object.data), {'service':'hermes-agent', 'command':'hermes-submit', 'payload':{'request_id':'same-request-1234', 'prompt':'작업'}})
        self.assertEqual(hermes_request_object.full_url, 'http://127.0.0.1:8771/management/command')

    def test_gpu_queue_status_uses_read_only_loopback_endpoint(self):
        hermes_response_file = io.BytesIO(b'{"jobs":[],"gpu_status":{"status":"unavailable","processes":[]}}')
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:8771'}), patch.object(hermes_module_value.urllib.request, 'build_opener') as hermes_opener_mock:
            hermes_opener_mock.return_value.open.return_value = hermes_response_file
            hermes_status_record = hermes_module_value.read_hermes_gpu_queue_status()
            hermes_request_object = hermes_opener_mock.return_value.open.call_args.args[0]
        self.assertEqual(hermes_request_object.get_method(), 'GET')
        self.assertEqual(hermes_request_object.full_url, 'http://127.0.0.1:8771/management/gpu-queue')
        self.assertEqual(hermes_status_record['gpu_status']['status'], 'unavailable')
        self.assertIn('queried_at', hermes_status_record)

    def test_gpu_queue_status_rejects_non_loopback_and_invalid_response(self):
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://example.com:8771'}), self.assertRaises(ValueError):
            hermes_module_value.read_hermes_gpu_queue_status()
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:8771'}), patch.object(hermes_module_value.urllib.request, 'build_opener') as hermes_opener_mock:
            hermes_opener_mock.return_value.open.return_value = io.BytesIO(b'{"jobs":{}}')
            with self.assertRaisesRegex(ValueError, '형식'):
                hermes_module_value.read_hermes_gpu_queue_status()

    def test_writer_search_paths_mcp_forwards_only_request_id(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'paths':['world/town.md'],'truncated':False}) as current_gateway_mock:
            current_response_value=hermes_module_value.read_hermes_writer_search_paths('request_123')
            self.assertEqual(current_response_value,{'paths':['world/town.md'],'truncated':False})
            current_gateway_mock.assert_called_once_with('hermes-writer-search-paths',{'request_id':'request_123'})
            for current_bad_response in ({'paths':['../secret'],'truncated':False},{'paths':['/secret'],'truncated':False},{'paths':['a'],'truncated':False,'text':'private'}):
                current_gateway_mock.return_value=current_bad_response
                with self.subTest(current_bad_response=current_bad_response),self.assertRaises(ValueError):hermes_module_value.read_hermes_writer_search_paths('request_123')
            current_gateway_mock.side_effect=ValueError('/private/secret')
            with self.assertRaises(ValueError) as current_error:hermes_module_value.read_hermes_writer_search_paths('request_123')
            self.assertNotIn('/private/secret',str(current_error.exception))

    def test_direct_writer_job_search_mcp(current_test_case):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'paths':['world/town.md'],'truncated':False}) as current_gateway_mock:
            current_test_case.assertEqual(hermes_module_value.read_hermes_writer_job_search_paths('20261120-120000-abcdef12'), {'paths':['world/town.md'],'truncated':False})
            current_gateway_mock.assert_called_once_with('hermes-writer-job-search-paths',{'job_id':'20261120-120000-abcdef12'})
            current_gateway_mock.return_value={'paths':['../secret'],'truncated':False}
            with current_test_case.assertRaises(ValueError):
                hermes_module_value.read_hermes_writer_job_search_paths('20261120-120000-abcdef12')

    def test_capability_catalog_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'records':[],'unlisted_commands':['hermes-new-command']}) as current_gateway_mock:
            current_catalog_value=hermes_module_value.list_hermes_management_capabilities()
        self.assertEqual(current_catalog_value['unlisted_commands'],['hermes-new-command'])
        current_gateway_mock.assert_called_once_with('hermes-capabilities', {})

    def test_mcp_gateway_commands_match_catalog_interfaces(self):
        """공개 MCP 도구와 기능 목록 사이의 누락·잘못된 지원 표시를 검출한다."""
        import ast
        from tools.review.domains.hermes_agent.capabilities import HERMES_CAPABILITY_RECORDS
        current_module_tree=ast.parse(hermes_module_path.read_text(encoding='utf-8'))
        current_command_names=set()
        for current_function_node in current_module_tree.body:
            if not isinstance(current_function_node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                continue
            if not any(isinstance(current_decorator,ast.Call) and isinstance(current_decorator.func,ast.Attribute) and current_decorator.func.attr=='tool' and isinstance(current_decorator.func.value,ast.Name) and current_decorator.func.value.id=='hermes_mcp_server' for current_decorator in current_function_node.decorator_list):
                continue
            for current_node_value in ast.walk(current_function_node):
                if not isinstance(current_node_value,ast.Call) or not isinstance(current_node_value.func,ast.Name):
                    continue
                if current_node_value.func.id not in ('run_hermes_mcp_command','call_hermes_management_gateway','execute_hermes_cancellation_command'):
                    continue
                if not current_node_value.args or not isinstance(current_node_value.args[0],ast.Constant):
                    continue
                current_command_name=current_node_value.args[0].value
                if isinstance(current_command_name,str):current_command_names.add(current_command_name)
        current_catalog_names={current_record['command'] for current_record in HERMES_CAPABILITY_RECORDS if 'mcp' in current_record['interfaces']}
        self.assertSetEqual(current_command_names,current_catalog_names)

    def test_service_registration_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'services':[]}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.list_management_service_registration()['services'], [])
        current_gateway_mock.assert_called_once_with('hermes-service-registration', {})

    def test_service_search_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'services':[],'next_offset':None}) as current_gateway_mock:
            self.assertIsNone(hermes_module_value.search_hermes_management_services('음악',5,5)['next_offset'])
        current_gateway_mock.assert_called_once_with('hermes-service-registration', {'query':'음악','offset':5,'limit':5})

    def test_generator_source_history_uses_shared_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'records':[]}) as current_gateway_mock:
            hermes_module_value.list_hermes_generator_source_history('wan22-vace',10,10,'a'*64)
        current_gateway_mock.assert_called_once_with('hermes-generator-source-history',{'service':'wan22-vace','offset':10,'limit':10,'snapshot':'a'*64})

    def test_audio_source_history_uses_shared_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'records':[]}) as current_gateway_mock:
            hermes_module_value.list_hermes_audio_source_history('music-heartmula',10,10,'a'*64)
        current_gateway_mock.assert_called_once_with('hermes-audio-source-history',{'service':'music-heartmula','offset':10,'limit':10,'snapshot':'a'*64})

    def test_kimodo_build_status_uses_shared_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'status':'checking'}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_kimodo_build_status()['status'],'checking')
        current_gateway_mock.assert_called_once_with('hermes-kimodo-build-status',{})

    def test_flux_proposal_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'proposal':{}}) as current_gateway_mock:
            hermes_module_value.read_hermes_flux_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-flux-proposal', {'id':'job-1'})

    def test_flux_delegation_uses_matching_gateway_commands(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={}) as current_gateway_mock:
            hermes_module_value.delegate_hermes_flux_generation('request_123', {'prompt':'x'})
            current_gateway_mock.assert_called_with('hermes-delegate-flux-image', {'request_id':'request_123', 'request':{'prompt':'x'}})
            hermes_module_value.read_hermes_flux_delegation('request_123')
            current_gateway_mock.assert_called_with('hermes-flux-delegation-status', {'request_id':'request_123'})
            current_gateway_mock.return_value={'job_id':'job-1','cancel_requested':True}
            hermes_module_value.cancel_hermes_flux_delegation('request_123', 'job-1')
            current_gateway_mock.assert_called_with('hermes-flux-delegation-cancel', {'request_id':'request_123', 'job_id':'job-1'})

    def test_source_history_mcp_forwards_id_search(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={}) as current_gateway_mock:
            hermes_module_value.list_hermes_generator_source_history('kimodo',query_text='job-1')
            current_gateway_mock.assert_called_once_with('hermes-generator-source-history',{'service':'kimodo','offset':0,'limit':10,'query':'job-1'})

    def test_generator_reservation_inspection_uses_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.inspect_hermes_generator_reservation('kimodo','2026-11-18_12-00-00-12345678')
            current_gateway_mock.assert_called_once_with('hermes-generator-reservation-inspect',{'service':'kimodo','job_id':'2026-11-18_12-00-00-12345678'})

    def test_model_preparation_mcp_preserves_request_and_service(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={}) as current_gateway_mock:
            hermes_module_value.list_hermes_model_preparation_receipts()
            current_gateway_mock.assert_called_with('hermes-model-prepare-history', {})
            current_gateway_mock.return_value = {'request_id':'request_123','service':'flux-image','state':'accepted'}
            hermes_module_value.prepare_hermes_managed_model('request_123', 'flux-image')
            current_gateway_mock.assert_called_with('hermes-model-prepare', {'request_id':'request_123', 'service':'flux-image'})
            hermes_module_value.read_hermes_model_preparation_receipt('request_123', 'flux-image')
            current_gateway_mock.assert_called_with('hermes-model-prepare-status', {'request_id':'request_123', 'service':'flux-image'})

    def test_model_preparation_mcp_validates_response_identity_and_block_reason(self):
        current_valid_record = {'request_id':'request_123', 'service':'hermes-model', 'state':'blocked', 'reason':'model_in_use'}
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value=current_valid_record) as current_gateway_mock:
            self.assertEqual(hermes_module_value.prepare_hermes_managed_model('request_123', 'hermes-model'), current_valid_record)
            current_gateway_mock.return_value = {**current_valid_record, 'reason':'preparation_unknown'}
            self.assertEqual(hermes_module_value.prepare_hermes_managed_model('request_123', 'hermes-model')['reason'], 'preparation_unknown')
            for current_invalid_record in ({**current_valid_record, 'request_id':'wrong'}, {**current_valid_record, 'service':'flux-image'}, {**current_valid_record, 'reason':'unknown'}, {'request_id':'request_123','service':'hermes-model','state':'other'}, None):
                current_gateway_mock.return_value = current_invalid_record
                with self.assertRaisesRegex(hermes_module_value.ToolError, '자동 재접수하지'):
                    hermes_module_value.prepare_hermes_managed_model('request_123', 'hermes-model')

    def test_video_proposal_mcp_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_video_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-video-proposal',{'id':'job-1'})

    def test_video_mcp_uses_matching_service(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.delegate_hermes_video('video_request_123','dwpose',{'action':'generate'})
            current_gateway_mock.assert_called_with('hermes-delegate-video',{'request_id':'video_request_123','service':'dwpose','request':{'action':'generate'}})
            hermes_module_value.read_hermes_video_status('video_request_123','dwpose')
            current_gateway_mock.assert_called_with('hermes-video-status',{'request_id':'video_request_123','service':'dwpose'})
            hermes_module_value.list_hermes_video_receipts('dwpose')
            current_gateway_mock.assert_called_with('hermes-video-history',{'service':'dwpose'})
            current_gateway_mock.return_value={'job_id':'job-1','cancel_requested':True}
            hermes_module_value.cancel_hermes_video('video_request_123','dwpose','job-1')
            current_gateway_mock.assert_called_with('hermes-video-cancel',{'request_id':'video_request_123','service':'dwpose','job_id':'job-1'})

    def test_capture_mcp_reads_preserve_service_and_request_identifiers(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'status':'unknown'}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_capture_proposal('source_job'), {'status':'unknown'})
            current_gateway_mock.assert_called_with('hermes-capture-proposal', {'id':'source_job'})
            self.assertEqual(hermes_module_value.read_hermes_capture_status('request_123', 'map-review'), {'status':'unknown'})
            current_gateway_mock.assert_called_with('hermes-capture-status', {'request_id':'request_123', 'service':'map-review'})
            self.assertEqual(current_gateway_mock.call_count, 2)
        for current_tool_function in (hermes_module_value.read_hermes_capture_proposal, hermes_module_value.read_hermes_capture_status):
            self.assertFalse(current_tool_function.test_annotations['read_only_hint'])
            self.assertTrue(current_tool_function.test_annotations['idempotent_hint'])
            self.assertIn('캡처 실행은 지원하지 않는다', current_tool_function.__doc__)

    def test_resume_mcp_tools_use_fixed_commands_and_exact_payloads(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_fingerprint_value='a'*64
        current_cases_value=(
            (hermes_module_value.preview_hermes_audio_resume,('music-heartmula',current_job_identifier),'hermes-audio-resume-preview',{'service':'music-heartmula','job_id':current_job_identifier}),
            (hermes_module_value.submit_hermes_audio_resume,('request_123','music-heartmula',current_job_identifier,current_fingerprint_value),'hermes-audio-resume-submit',{'request_id':'request_123','service':'music-heartmula','job_id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value}),
            (hermes_module_value.read_hermes_audio_resume_receipt,('request_123',),'hermes-audio-resume-receipt',{'request_id':'request_123'}),
            (hermes_module_value.preview_hermes_translation_resume,(current_job_identifier,),'hermes-translation-resume-preview',{'job_id':current_job_identifier}),
            (hermes_module_value.submit_hermes_translation_resume,('request_123',current_job_identifier,current_fingerprint_value),'hermes-translation-resume-submit',{'request_id':'request_123','job_id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value}),
            (hermes_module_value.read_hermes_translation_resume_receipt,('request_123',),'hermes-translation-resume-receipt',{'request_id':'request_123'}),
        )
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'state':'unknown'}) as current_gateway_mock:
            for current_function_value,current_arguments_value,current_command_name,current_payload_value in current_cases_value:
                with self.subTest(current_command_name=current_command_name):
                    self.assertEqual(current_function_value(*current_arguments_value),{'state':'unknown'})
                    current_gateway_mock.assert_called_with(current_command_name,current_payload_value)
            self.assertEqual(current_gateway_mock.call_count,len(current_cases_value))

    def test_priority_submit_and_receipt_mcp_use_fixed_commands(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.submit_hermes_queue_priority('request_123','kimodo','job-1','a'*64)
            current_gateway_mock.assert_called_with('hermes-priority-submit',{'request_id':'request_123','service':'kimodo','id':'job-1','ticket_revision':'a'*64})
            hermes_module_value.read_hermes_queue_priority_receipt('request_123')
            current_gateway_mock.assert_called_with('hermes-priority-receipt',{'request_id':'request_123'})

    def test_priority_preview_mcp_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.preview_hermes_queue_priority('kimodo','job-1')
        current_gateway_mock.assert_called_once_with('hermes-priority-preview',{'service':'kimodo','id':'job-1'})

    def test_writer_proposal_mcp_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_writer_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-writer-proposal',{'id':'job-1'})

    def test_audio_proposal_mcp_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_audio_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-audio-proposal',{'id':'job-1'})

    def test_audio_mcp_uses_matching_service(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.delegate_hermes_audio('audio_request_123','sfx-dasheng-audiogen',{'prompt':'splash'})
            current_gateway_mock.assert_called_with('hermes-delegate-audio',{'request_id':'audio_request_123','service':'sfx-dasheng-audiogen','request':{'prompt':'splash'}})
            hermes_module_value.read_hermes_audio_status('audio_request_123','sfx-dasheng-audiogen')
            current_gateway_mock.assert_called_with('hermes-audio-status',{'request_id':'audio_request_123','service':'sfx-dasheng-audiogen'})
            hermes_module_value.list_hermes_audio_receipts('sfx-dasheng-audiogen')
            current_gateway_mock.assert_called_with('hermes-audio-history',{'service':'sfx-dasheng-audiogen'})
            current_gateway_mock.return_value={'job_id':'job-1','cancel_requested':True}
            hermes_module_value.cancel_hermes_audio('audio_request_123','sfx-dasheng-audiogen','job-1')
            current_gateway_mock.assert_called_with('hermes-audio-cancel',{'request_id':'audio_request_123','service':'sfx-dasheng-audiogen','job_id':'job-1'})

    def test_flux_profile_mcp_uses_matching_service(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.delegate_hermes_flux_profile('profile_request_123','flux-building',{'prompt':'house'})
            current_gateway_mock.assert_called_with('hermes-delegate-flux-profile',{'request_id':'profile_request_123','service':'flux-building','request':{'prompt':'house'}})
            hermes_module_value.read_hermes_flux_profile_status('profile_request_123','flux-building')
            current_gateway_mock.assert_called_with('hermes-flux-profile-status',{'request_id':'profile_request_123','service':'flux-building'})
            hermes_module_value.list_hermes_flux_profile_receipts('flux-building')
            current_gateway_mock.assert_called_with('hermes-flux-profile-history',{'service':'flux-building'})
            current_gateway_mock.return_value={'job_id':'job-1','cancel_requested':True}
            hermes_module_value.cancel_hermes_flux_profile('profile_request_123','flux-building','job-1')
            current_gateway_mock.assert_called_with('hermes-flux-profile-cancel',{'request_id':'profile_request_123','service':'flux-building','job_id':'job-1'})

    def test_writer_apply_mcp_uses_matching_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.apply_hermes_writer_proposal('apply_request_123','writer_request_123','job-1','a'*64)
            current_gateway_mock.assert_called_with('hermes-writer-apply',{'request_id':'apply_request_123','writer_request_id':'writer_request_123','job_id':'job-1','proposal_hash':'a'*64})
            hermes_module_value.read_hermes_writer_apply_receipt('apply_request_123')
            current_gateway_mock.assert_called_with('hermes-writer-apply-status',{'request_id':'apply_request_123'})
            hermes_module_value.list_hermes_writer_apply_receipts()
            current_gateway_mock.assert_called_with('hermes-writer-apply-history',{})

    def test_writer_mcp_uses_matching_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.delegate_hermes_writer('writer_request_123',{'mode':'write','prompt':'제안'})
            current_gateway_mock.assert_called_with('hermes-delegate-writer',{'request_id':'writer_request_123','request':{'mode':'write','prompt':'제안'}})
            hermes_module_value.read_hermes_writer_status('writer_request_123')
            current_gateway_mock.assert_called_with('hermes-writer-status',{'request_id':'writer_request_123'})
            hermes_module_value.list_hermes_writer_receipts()
            current_gateway_mock.assert_called_with('hermes-writer-history',{})

    def test_translation_proposal_mcp_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_translation_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-translation-proposal',{'id':'job-1'})

    def test_translation_mcp_uses_matching_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.delegate_hermes_translation('translation_123',{'text':'나무','target_language':'en'})
            current_gateway_mock.assert_called_with('hermes-delegate-translation',{'request_id':'translation_123','request':{'text':'나무','target_language':'en'}})
            hermes_module_value.read_hermes_translation_status('translation_123')
            current_gateway_mock.assert_called_with('hermes-translation-status',{'request_id':'translation_123'})
            hermes_module_value.list_hermes_translation_receipts()
            current_gateway_mock.assert_called_with('hermes-translation-history',{})
            current_gateway_mock.return_value={'job_id':'job-1','cancel_requested':True}
            hermes_module_value.cancel_hermes_translation('translation_123','job-1')
            current_gateway_mock.assert_called_with('hermes-translation-cancel',{'request_id':'translation_123','job_id':'job-1'})

    def test_field_proposal_mcp_forwards_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_field_map_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-field-proposal',{'id':'job-1'})

    def test_writer_material_mcp_preserves_paging_identity(self):
        with patch.object(hermes_module_value,'run_hermes_mcp_command',return_value={'content':'{}'}) as current_command_mock:
            hermes_module_value.read_hermes_writer_job_material('20261115-114927-8d274ccd','search',10,50,'a'*64)
        current_command_mock.assert_called_once_with('hermes-writer-job-material',{'job_id':'20261115-114927-8d274ccd','section':'search','offset':10,'limit':50,'snapshot':'a'*64})

    def test_field_region_mcp_preserves_revision_and_bounds(self):
        self.assertTrue(hermes_module_value.read_hermes_field_region.test_annotations['read_only_hint'])
        self.assertIn('편집 리비전이 아니다',hermes_module_value.read_hermes_field_region.__doc__)
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_field_region('sample',2,3,4,5,6,7,'revision')
        current_gateway_mock.assert_called_once_with('hermes-field-region',{'map':'sample','column':2,'row':3,'width':4,'height':5,'offset':6,'limit':7,'revision':'revision'})

    def test_city_map_mcp_forwards_fixed_operations(self):
        current_draft_value = {'map':'stonewarm','generation':5,'revision':2,'document':{}}
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.load_hermes_city_map('stonewarm')
            current_gateway_mock.assert_called_with('hermes-city-load',{'map':'stonewarm'})
            hermes_module_value.preview_hermes_city_map(current_draft_value)
            current_gateway_mock.assert_called_with('hermes-city-preview',{'draft':current_draft_value})
            hermes_module_value.save_hermes_city_map('city_request_123',current_draft_value,'a'*64)
            current_gateway_mock.assert_called_with('hermes-city-save',{'request_id':'city_request_123','draft':current_draft_value,'token':'a'*64})
            hermes_module_value.read_hermes_city_map_receipt('city_request_123')
            current_gateway_mock.assert_called_with('hermes-city-receipt',{'request_id':'city_request_123'})
            hermes_module_value.list_hermes_city_map_receipts()
            current_gateway_mock.assert_called_with('hermes-city-history',{})

    def test_field_map_mcp_forwards_fixed_operations(self):
        current_draft_value = {'map':'moss-clearing','revision':'r','cells':[],'objects':[]}
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={}) as current_gateway_mock:
            hermes_module_value.list_hermes_field_map_receipts()
            current_gateway_mock.assert_called_with('hermes-field-history',{})
            hermes_module_value.read_hermes_field_map_receipt('field_request_123')
            current_gateway_mock.assert_called_with('hermes-field-receipt',{'request_id':'field_request_123'})
            hermes_module_value.load_hermes_field_map('moss-clearing')
            current_gateway_mock.assert_called_with('hermes-field-load',{'map':'moss-clearing'})
            hermes_module_value.preview_hermes_field_map(current_draft_value)
            current_gateway_mock.assert_called_with('hermes-field-preview',{'draft':current_draft_value})
            hermes_module_value.save_hermes_field_map('field_request_123',current_draft_value,'a'*64)
            current_gateway_mock.assert_called_with('hermes-field-save',{'request_id':'field_request_123','draft':current_draft_value,'token':'a'*64})

    def test_content_database_status_uses_fixed_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'status':'unavailable'}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_content_database_status()['status'], 'unavailable')
        current_gateway_mock.assert_called_once_with('hermes-content-database-status', {})

    def test_model_readiness_uses_shared_gateway(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'status':'available'}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_model_readiness('flux-image')['status'],'available')
        current_gateway_mock.assert_called_once_with('hermes-model-readiness',{'service':'flux-image'})

    def test_model_inventory_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'status':'available', 'models':[]}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_model_inventory()['status'], 'available')
        current_gateway_mock.assert_called_once_with('hermes-model-inventory', {})

    def test_delegation_history_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'records':[]}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.list_hermes_delegation_receipts()['records'], [])
        current_gateway_mock.assert_called_once_with('hermes-delegation-history', {})

    def test_delegated_job_status_uses_receipt_command(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'receipt':{'state':'unknown'}}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_kimodo_job_status('request_123456')['receipt']['state'], 'unknown')
        current_gateway_mock.assert_called_once_with('hermes-delegation-job-status', {'request_id':'request_123456'})

    def test_cancel_forwards_confirmed_request_and_job(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'job_id':'job-1','cancel_requested':True}) as current_gateway_mock:
            hermes_module_value.cancel_hermes_kimodo_delegation('request_123456', 'job-1')
        current_gateway_mock.assert_called_once_with('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'job-1'})

    def test_delegation_receipt_is_read_without_submission(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'state':'unknown'}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_delegation_status('request_123456')['state'], 'unknown')
        current_gateway_mock.assert_called_once_with('hermes-delegation-status', {'request_id':'request_123456'})

    def test_kimodo_proposal_is_read_through_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'proposal':{}}) as current_gateway_mock:
            hermes_module_value.read_hermes_kimodo_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-kimodo-proposal', {'id':'job-1'})

    def test_kimodo_delegation_uses_shared_gateway_without_waiting(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}) as current_gateway_mock:
            current_result_value = hermes_module_value.delegate_hermes_kimodo_generation('request_123456', {'action':'generate'})
        self.assertEqual(current_result_value['state'], 'accepted')
        current_gateway_mock.assert_called_once_with('hermes-delegate-kimodo', {'request_id':'request_123456', 'request':{'action':'generate'}})

    def test_paged_coding_history_uses_existing_gateway_contract(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'records':[]}) as current_gateway:
            hermes_module_value.list_hermes_coding_tasks_page()
            current_gateway.assert_called_with('hermes-history',{'offset':0,'limit':30})
            hermes_module_value.list_hermes_coding_tasks_page(30,30,'a'*64)
            current_gateway.assert_called_with('hermes-history',{'offset':30,'limit':30,'snapshot':'a'*64})
            hermes_module_value.list_hermes_coding_tasks_page(0,30,None,'오래된 작업','failed')
            current_gateway.assert_called_with('hermes-history',{'offset':0,'limit':30,'query':'오래된 작업','status':'failed'})

    def test_paged_sessions_use_shared_gateway_contract(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={'sessions':[]}) as current_gateway:
            hermes_module_value.list_hermes_sessions_page(30,30,'a'*64,'abc')
            current_gateway.assert_called_with('hermes-session-list',{'offset':30,'limit':30,'snapshot':'a'*64,'query':'abc'})
            hermes_module_value.list_hermes_sessions_page(0,30,None,'나무 빌보드')
            current_gateway.assert_called_with('hermes-session-list',{'offset':0,'limit':30,'query':'나무 빌보드'})

    def test_management_status_uses_shared_gateway_command(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'model': {'status':'unavailable'}}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_management_status()['model']['status'], 'unavailable')
            current_gateway_mock.assert_called_once_with('hermes-management-status', {})

    def test_session_tools_use_shared_gateway_commands(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'id':'a' * 32}) as hermes_gateway_mock:
            hermes_module_value.create_hermes_session('a' * 32)
            hermes_gateway_mock.assert_called_with('hermes-session-create', {'session_id':'a' * 32})
            hermes_module_value.read_hermes_session('a' * 32)
            hermes_gateway_mock.assert_called_with('hermes-session-read', {'session_id':'a' * 32})
            hermes_module_value.submit_hermes_session_message('a' * 32, 'request-1234', '질문')
            hermes_gateway_mock.assert_called_with('hermes-session-submit', {'session_id':'a' * 32, 'request_id':'request-1234', 'prompt':'질문'})
            hermes_module_value.read_hermes_session_view('a' * 32)
            hermes_gateway_mock.assert_called_with('hermes-session-view', {'session_id':'a' * 32})
            hermes_module_value.list_hermes_sessions()
            hermes_gateway_mock.assert_called_with('hermes-session-list', {})

    def test_non_loopback_gateway_is_rejected(self):
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://example.com:8771'}), self.assertRaises(ValueError):
            hermes_module_value.list_hermes_coding_tasks()

    def test_gateway_redirect_is_rejected(self):
        with self.assertRaises(ValueError):
            hermes_module_value.RejectHermesGatewayRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com/')

    def test_submit_forwards_selected_verification_modules(self):
        hermes_module_values = ['tools.review.tests.test_hermes_service']
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'id':'job-id'}) as hermes_gateway_mock:
            hermes_module_value.submit_hermes_coding_task('request-1234', '테스트', hermes_module_values)
            hermes_gateway_mock.assert_called_once_with('hermes-submit', {'request_id':'request-1234', 'prompt':'테스트', 'verification_modules':hermes_module_values})


if __name__ == '__main__':
    unittest.main()
