"""세션 heartbeat 전송 및 종료 계약 검사."""
import asyncio
import unittest

from tools.review.common.management_asgi import bridge_gradio_heartbeat


class ManagementHeartbeatBridgeTests(unittest.IsolatedAsyncioTestCase):
    def create_scope(self, origin='http://localhost:8770'):
        return {
            'type': 'websocket', 'scheme': 'ws',
            'path': '/management/frame/example/gradio_api/heartbeat-ws/session123',
            'headers': [(b'host', b'localhost:8770'), (b'origin', origin.encode())],
            'query_string': b'', 'server': ('localhost', 8770), 'client': ('127.0.0.1', 1234),
        }

    async def test_stream_and_disconnect_are_forwarded(self):
        current_messages = asyncio.Queue()
        await current_messages.put({'type': 'websocket.connect'})
        current_sent_messages = []
        current_http_scopes = []
        current_stream_started = asyncio.Event()

        async def current_send_message(current_message):
            current_sent_messages.append(current_message)
            if current_message['type'] == 'websocket.send':
                current_stream_started.set()

        async def current_gradio_app(current_scope, current_receive, current_send):
            current_http_scopes.append(current_scope)
            self.assertEqual((await current_receive())['type'], 'http.request')
            await current_send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await current_send({'type': 'http.response.body', 'body': b'data: ALIVE\n\n', 'more_body': True})
            self.assertEqual((await current_receive())['type'], 'http.disconnect')

        current_task = asyncio.create_task(bridge_gradio_heartbeat(current_gradio_app, self.create_scope(), current_messages.get, current_send_message))
        await asyncio.wait_for(current_stream_started.wait(), 2)
        await current_messages.put({'type': 'websocket.disconnect', 'code': 1000})
        await asyncio.wait_for(current_task, 2)
        self.assertEqual(current_http_scopes[0]['path'], '/management/frame/example/gradio_api/heartbeat/session123')
        self.assertEqual(current_sent_messages, [{'type': 'websocket.accept'}, {'type': 'websocket.send', 'bytes': b'data: ALIVE\n\n'}])

    async def test_disconnected_client_during_heartbeat_send_is_normal(self):
        from uvicorn.protocols.utils import ClientDisconnected
        from starlette.requests import ClientDisconnect
        for current_error_type in (ClientDisconnected,ClientDisconnect):
            with self.subTest(error=current_error_type.__name__):
                current_messages=asyncio.Queue()
                await current_messages.put({'type':'websocket.connect'})
                async def current_send_message(current_message):
                    if current_message['type']=='websocket.send':raise current_error_type()
                async def current_gradio_app(current_scope,current_receive,current_send):
                    await current_receive()
                    await current_send({'type':'http.response.start','status':200,'headers':[]})
                    await current_send({'type':'http.response.body','body':b'alive','more_body':True})
                await asyncio.wait_for(bridge_gradio_heartbeat(current_gradio_app,self.create_scope(),current_messages.get,current_send_message),2)

    async def test_unexpected_application_error_is_not_suppressed(self):
        current_messages=asyncio.Queue()
        await current_messages.put({'type':'websocket.connect'})
        async def current_send_message(current_message):pass
        async def current_gradio_app(current_scope,current_receive,current_send):raise RuntimeError('unexpected')
        with self.assertRaisesRegex(RuntimeError,'unexpected'):
            await bridge_gradio_heartbeat(current_gradio_app,self.create_scope(),current_messages.get,current_send_message)

    async def test_untrusted_origin_is_rejected(self):
        current_sent_messages = []
        async def current_send_message(current_message):
            current_sent_messages.append(current_message)
        async def current_forbidden_app(*current_arguments):
            self.fail('외부 origin의 요청을 Gradio에 전달하면 안 됩니다.')
        await bridge_gradio_heartbeat(current_forbidden_app, self.create_scope('http://untrusted.test'), None, current_send_message)
        self.assertEqual(current_sent_messages, [{'type': 'websocket.close', 'code': 1008}])
