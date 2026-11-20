"""과거 앵커 검수 이력의 제한 관측 계약."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.review.domains.hermes_agent.anchor_history_observer import read_hermes_anchor_history


class HermesAnchorHistoryObserverTests(unittest.TestCase):
    def test_pagination_hides_private_paths_and_rejects_changed_history(self):
        from tools.review.domains.character_animation import anchor_history
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

    def test_invalid_or_oversized_records_are_not_empty_history(self):
        from tools.review.domains.character_animation import anchor_history
        from tools.review.domains.hermes_agent import anchor_history_observer
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
        from tools.review.ui.gradio import hermes_agent_app
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
        from tools.review.domains.character_animation import anchor_history
        from tools.review.domains.hermes_agent import management_bridge
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
