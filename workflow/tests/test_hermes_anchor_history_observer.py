"""과거 앵커 검수 이력의 제한 관측 계약."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.anchor_history_observer import read_hermes_anchor_history


class HermesAnchorHistoryObserverTests(unittest.TestCase):
    def test_pagination_hides_private_paths_and_rejects_changed_history(self):
        from workflow.domains.character_animation import anchor_history
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)/'history'
            current_identifiers=['2026-11-20_10-00-00-12345678','2026-11-20_10-00-01-12345678','2026-11-20_10-00-02-12345678']
            for current_identifier_value in current_identifiers:
                current_job_path=current_root_path/current_identifier_value[:19]/current_identifier_value
                current_job_path.mkdir(parents=True)
                (current_job_path/'result.json').write_text(json.dumps({'id':current_identifier_value,'created_at':'2026-11-20T10:00:00+09:00','status':'completed','source':{'animationId':'walk','animationVersion':'v1','sheets':[{'image':'/private/image.png'}]},'frames':4}))
            current_hidden_path=current_root_path/current_identifiers[0][:19]/current_identifiers[0]/'history-hidden.json'
            current_hidden_path.write_text('{}')
            with patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',current_root_path):
                current_first_page=read_hermes_anchor_history({'animation_id':'walk','animation_version':'v1','limit':1})
                self.assertEqual(current_first_page['total'],2)
                self.assertEqual(current_first_page['records'][0]['id'],current_identifiers[2])
                self.assertNotIn('/private/',str(current_first_page))
                current_next_page=read_hermes_anchor_history({'animation_id':'walk','animation_version':'v1','limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
                self.assertEqual(current_next_page['records'][0]['id'],current_identifiers[1])
                current_hidden_path.unlink()
                with self.assertRaisesRegex(ValueError,'변경'):
                    read_hermes_anchor_history({'animation_id':'walk','animation_version':'v1','limit':1,'offset':1,'snapshot':current_first_page['snapshot']})

    def test_original_save_and_hide_are_visible_without_modifying_records(self):
        from workflow.domains.character_animation import anchor_history
        current_document_record = {
            'schemaVersion': 1, 'artifactType': 'character-animation-anchor-review',
            'description': 'temporary test', 'coordinateMode': 'anchor',
            'source': {'animationId': 'walk', 'animationVersion': 'v1', 'sheets': [{'image': '/private/sheet.png', 'sha256': 'a' * 64}]},
            'frames': [{'frameId': 'down.0', 'direction': 'down_left', 'image': '/private/sheet.png',
                        'rect': {'x': 0, 'y': 0, 'width': 8, 'height': 8},
                        'points': [{'x': 3, 'y': 6}], 'anchor': {'x': 3, 'y': 6}}],
        }
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path = Path(current_temporary_directory) / 'history'
            with patch.object(anchor_history, 'ANCHOR_HISTORY_ROOT', current_root_path):
                current_saved_record = anchor_history.execute_anchor_history_command('anchor-save', {'document': current_document_record})
                current_original_page = anchor_history.execute_anchor_history_command('anchor-history', {'animation_id': 'walk', 'animation_version': 'v1'})
                current_record_path = current_root_path / current_saved_record['id'][:19] / current_saved_record['id'] / 'result.json'
                current_before_bytes = current_record_path.read_bytes()
                current_observed_page = read_hermes_anchor_history({'animation_id': 'walk', 'animation_version': 'v1'})
                self.assertEqual([current_item['id'] for current_item in current_observed_page['records']], [current_item['id'] for current_item in current_original_page['items']])
                self.assertNotIn('/private/', str(current_observed_page))
                self.assertEqual(current_before_bytes, current_record_path.read_bytes())
                anchor_history.execute_anchor_history_command('anchor-history-reset', {'animation_id': 'walk', 'animation_version': 'v1'})
                self.assertEqual(read_hermes_anchor_history({'animation_id': 'walk', 'animation_version': 'v1'})['records'], [])
                with self.assertRaisesRegex(ValueError, '변경'):
                    read_hermes_anchor_history({'animation_id': 'walk', 'animation_version': 'v1', 'snapshot': current_observed_page['snapshot']})
                self.assertEqual(current_before_bytes, current_record_path.read_bytes())

    def test_invalid_or_oversized_records_are_not_empty_history(self):
        from workflow.domains.character_animation import anchor_history
        from workflow.domains.hermes_agent import anchor_history_observer
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)/'history'
            current_identifier_value='2026-11-20_10-00-00-12345678'
            current_job_path=current_root_path/current_identifier_value[:19]/current_identifier_value
            current_job_path.mkdir(parents=True)
            (current_job_path/'result.json').write_text('{}')
            with patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',current_root_path):
                with self.assertRaises(ValueError):read_hermes_anchor_history({'animation_id':'walk','animation_version':'v1'})
                with patch.object(anchor_history_observer,'ANCHOR_OBSERVER_MAXIMUM_ENTRIES',1):
                    with self.assertRaisesRegex(ValueError,'한도'):read_hermes_anchor_history({'animation_id':'walk','animation_version':'v1'})
                with self.assertRaises(ValueError):read_hermes_anchor_history({'animation_id':'../bad','animation_version':'v1'})

class HermesAnchorHistoryUiTests(unittest.TestCase):
    def test_page_request_and_late_response_guard(self):
        import gradio as gr
        from gui.ui.gradio import hermes_agent_app
        current_first_response={'records':[{'id':'2026-11-20_10-00-00-12345678','created_at':'2026-11-20T10:00:00+09:00','frames':4}],'total':2,'offset':0,'next_offset':1,'snapshot':'a'*64}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_first_response) as current_gateway_mock:
            current_result_record=hermes_agent_app.collect_hermes_legacy_anchor_page('walk','v1',None,'token-a',False)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-anchor-history-observe',{'animation_id':'walk','animation_version':'v1','limit':20})
        current_rendered_values=hermes_agent_app.render_hermes_legacy_anchor_page('walk','v1','token-a',current_result_record)
        self.assertEqual(current_rendered_values[0][0][0],'2026-11-20_10-00-00-12345678')
        self.assertTrue(current_rendered_values[3]['interactive'])
        for current_changed_values in (('run','v1','token-a'),('walk','v2','token-a'),('walk','v1','token-b')):
            self.assertEqual(hermes_agent_app.render_hermes_legacy_anchor_page(*current_changed_values,current_result_record),(gr.skip(),)*4)
        with patch.object(hermes_agent_app,'execute_remote_management_command') as current_gateway_mock:
            current_result_values=hermes_agent_app.read_next_hermes_legacy_anchor_page('run','v1',current_rendered_values[2])
            self.assertIn('검색 조건이 바뀌었습니다',current_result_values[1])
            current_gateway_mock.assert_not_called()

class HermesAnchorHistoryBridgeTests(unittest.TestCase):
    def test_bridge_returns_bounded_anchor_history_and_rejects_invalid_requests(self):
        import socket
        import threading
        from workflow.domains.character_animation import anchor_history
        from workflow.domains.hermes_agent import management_bridge
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)/'history'
            current_identifier_value='2026-11-20_10-00-00-12345678'
            current_job_path=current_root_path/current_identifier_value[:19]/current_identifier_value
            current_job_path.mkdir(parents=True)
            (current_job_path/'result.json').write_text(json.dumps({'id':current_identifier_value,'created_at':'2026-11-20T10:00:00+09:00','status':'completed','source':{'animationId':'walk','animationVersion':'v1','sheets':[{'image':'/private/image.png'}]},'frames':4}))
            current_cases=[(b'legacy-anchor-history {"animation_id":"walk","animation_version":"v1"}\n',True),(b'legacy-anchor-history {"animation_id":"walk","animation_id":"other","animation_version":"v1"}\n',False),(b'legacy-anchor-history {"animation_id":"walk","animation_version":"v1","extra":true}\n',False)]
            with patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',current_root_path):
                for current_request_bytes,current_expected_success in current_cases:
                    with self.subTest(request=current_request_bytes):
                        current_client_socket,current_server_socket=socket.socketpair()
                        current_client_socket.settimeout(3)
                        current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                        current_thread_value.start()
                        try:
                            current_client_socket.sendall(current_request_bytes)
                            with current_client_socket.makefile('rb') as current_response_stream:current_result_value=json.loads(current_response_stream.readline())
                        finally:
                            current_client_socket.close()
                            current_thread_value.join(timeout=3)
                        self.assertFalse(current_thread_value.is_alive())
                        if current_expected_success:self.assertEqual(current_result_value['records'][0]['id'],current_identifier_value)
                        else:self.assertIn('error',current_result_value)
                        self.assertNotIn('/private/',str(current_result_value))
            self.assertTrue((current_job_path/'result.json').is_file())

    def test_sandbox_client_round_trip_and_error_redaction(self):
        import socket
        import threading
        from types import SimpleNamespace
        from workflow.domains.character_animation import anchor_history
        from workflow.domains.hermes_agent import management_bridge, management_status_client
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path = Path(current_temporary_directory) / 'history'
            current_identifier_value = '2026-11-20_10-00-00-12345678'
            current_job_path = current_root_path / current_identifier_value[:19] / current_identifier_value
            current_job_path.mkdir(parents=True)
            (current_job_path / 'result.json').write_text(json.dumps({'id': current_identifier_value, 'created_at': '2026-11-20T10:00:00+09:00', 'status': 'completed', 'source': {'animationId': 'walk', 'animationVersion': 'v1', 'sheets': [{'image': '/private/image.png'}]}, 'frames': 4}))
            current_real_socket_factory = socket.socket
            current_socket_path = str(Path(current_temporary_directory) / 'observer.sock')
            with current_real_socket_factory(socket.AF_UNIX, socket.SOCK_STREAM) as current_listener_socket:
                current_listener_socket.bind(current_socket_path)
                current_listener_socket.listen(2)
                def serve_temporary_observer():
                    for current_connection_number in range(2):
                        current_connection_socket, _ = current_listener_socket.accept()
                        management_bridge.handle_hermes_observer_connection(current_connection_socket)
                class TemporaryClientSocket:
                    def __init__(self, *current_socket_arguments):
                        self.current_socket = current_real_socket_factory(*current_socket_arguments)
                    def __enter__(self):
                        return self
                    def __exit__(self, *current_exit_arguments):
                        self.current_socket.close()
                    def settimeout(self, current_timeout_value):
                        self.current_socket.settimeout(current_timeout_value)
                    def connect(self, current_original_path):
                        if current_original_path != '/control/management-status.sock':
                            raise AssertionError('unexpected observer socket')
                        self.current_socket.connect(current_socket_path)
                    def sendall(self, current_request_bytes):
                        self.current_socket.sendall(current_request_bytes)
                    def recv(self, current_response_limit):
                        return self.current_socket.recv(current_response_limit)
                current_server_thread = threading.Thread(target=serve_temporary_observer, daemon=True)
                current_server_thread.start()
                with patch.object(anchor_history, 'ANCHOR_HISTORY_ROOT', current_root_path), patch.object(management_status_client, 'socket', SimpleNamespace(socket=TemporaryClientSocket, AF_UNIX=socket.AF_UNIX, SOCK_STREAM=socket.SOCK_STREAM)):
                    current_page_result = management_status_client.read_sandbox_management_status('legacy-anchor-history', json.dumps({'animation_id': 'walk', 'animation_version': 'v1'}))
                    self.assertEqual(current_page_result['records'][0]['id'], current_identifier_value)
                    self.assertNotIn('/private/', str(current_page_result))
                    with self.assertRaisesRegex(ValueError, '과거 앵커 이력 조회 실패'):
                        management_status_client.read_sandbox_management_status('legacy-anchor-history', '{"animation_id":"walk","animation_id":"other","animation_version":"v1"}')
                current_server_thread.join(timeout=3)
                self.assertFalse(current_server_thread.is_alive())
