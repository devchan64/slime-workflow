import unittest

from tools.review.serve import write_proxy_response_body


class ClosedBrowserOutput:
    def write(self, response_body_bytes):
        raise BrokenPipeError('browser closed the connection')


class GradioProxyResponseTest(unittest.TestCase):
    def test_ignores_closed_browser_connection(self):
        self.assertFalse(write_proxy_response_body(ClosedBrowserOutput(), b'payload'))


if __name__ == '__main__':
    unittest.main()
