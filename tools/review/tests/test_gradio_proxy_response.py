import unittest
from email.message import Message

from tools.review.serve import write_proxy_response_body, build_gradio_proxy_headers


class ClosedBrowserOutput:
    def write(self, response_body_bytes):
        raise BrokenPipeError('browser closed the connection')


class GradioProxyResponseTest(unittest.TestCase):
    def test_public_origin_survives_internal_gradio_proxy(self):
        from fastapi import Request
        from gradio.route_utils import get_root_url
        incoming_headers = Message()
        incoming_headers['Host'] = '127.0.0.1:8770'
        incoming_headers['X-Forwarded-Host'] = 'untrusted.example'
        incoming_headers['Cookie'] = 'session=test'
        headers = build_gradio_proxy_headers(incoming_headers)
        request = Request({'type': 'http', 'scheme': 'http', 'path': '/config',
                           'query_string': b'', 'server': ('127.0.0.1', 8875),
                           'headers': [(name.lower().encode(), value.encode()) for name, value in headers.items()]})
        self.assertEqual(headers['Host'], '127.0.0.1:8770')
        self.assertEqual(headers['Cookie'], 'session=test')
        self.assertEqual(get_root_url(request, '/config', '/management/frame/tile-map-generator/'),
                         'http://127.0.0.1:8770/management/frame/tile-map-generator')

    def test_ignores_closed_browser_connection(self):
        self.assertFalse(write_proxy_response_body(ClosedBrowserOutput(), b'payload'))


if __name__ == '__main__':
    unittest.main()
