import unittest

from tools.review.common.management_asgi import wrap_predict_diagnostic_receiver


class HermesPredictDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunked_request_preserves_messages_and_records_only_event(self):
        current_messages = [
            {'type': 'http.request', 'body': b'{"data":["private"],', 'more_body': True},
            {'type': 'http.request', 'body': b'"fn_index":42}', 'more_body': False},
        ]
        current_originals = list(current_messages)
        current_events = []
        async def receive_original_message():
            return current_messages.pop(0)
        current_receiver = wrap_predict_diagnostic_receiver(receive_original_message, current_events.append)
        self.assertEqual(await current_receiver(), current_originals[0])
        self.assertEqual(current_events, [])
        self.assertEqual(await current_receiver(), current_originals[1])
        self.assertEqual(current_events, [42])

    async def test_invalid_and_oversized_bodies_are_not_logged(self):
        for current_body_value in (b'{bad', b'{"fn_index":true}', b'{"data":"' + b'x' * 65536 + b'","fn_index":5}'):
            with self.subTest(size=len(current_body_value)):
                current_events = []
                current_message_value = {'type':'http.request','body':current_body_value,'more_body':False}
                async def receive_original_message():
                    return current_message_value
                current_receiver = wrap_predict_diagnostic_receiver(receive_original_message, current_events.append)
                self.assertEqual(await current_receiver(), current_message_value)
                self.assertEqual(current_events, [])


class HermesPredictRouteTests(unittest.TestCase):
    def test_diagnostic_is_opt_in_and_does_not_log_input(self):
        import os
        import tempfile
        from http.server import SimpleHTTPRequestHandler
        from pathlib import Path
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        import gradio as gr
        from tools.review.common.management_asgi import build_management_application
        def build_mock_hermes_interface(*current_arguments):
            with gr.Blocks() as current_blocks_value:
                current_input_value=gr.Textbox()
                current_output_value=gr.Textbox()
                gr.Button().click(lambda current_text_value: current_text_value, current_input_value, current_output_value, api_name='echo')
            return current_blocks_value, {'allowed_paths': []}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            with patch('tools.review.common.management_asgi.build_management_blocks',side_effect=build_mock_hermes_interface), patch('tools.review.common.management_asgi.logging.warning') as current_log_mock:
                current_application=build_management_application(SimpleHTTPRequestHandler,current_root_path,current_root_path/'source.json',8770,[])
                with TestClient(current_application) as current_client:
                    current_prefix='/management/frame/hermes-agent'
                    self.assertEqual(current_client.get(current_prefix+'/config').status_code,200)
                    for current_enabled_value in ('0','1'):
                        with patch.dict(os.environ,{'SLIME_HERMES_PREDICT_DIAGNOSTIC':current_enabled_value}):
                            current_response=current_client.post(current_prefix+'/gradio_api/run/predict',json={'data':['private input'],'fn_index':0})
                        self.assertEqual(current_response.status_code,200)
                        self.assertEqual(current_response.json()['data'],['private input'])
                    current_log_mock.assert_called_once_with('Hermes predict event=%d',0)
