"""오디오 구간 탐색 응답과 잘못된 범위를 격리 검증한다."""
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from tools.review.common.audio_file_response import send_audio_file_response


class AudioFileResponseTests(unittest.TestCase):
    def test_audio_range_responses(self):
        with TemporaryDirectory() as current_temp_directory:
            current_audio_path = Path(current_temp_directory)/'sample.wav'
            current_audio_path.write_bytes(bytes(range(100)))
            for current_range_value,current_status_code,current_expected_bytes,current_content_range in (
                (None,200,bytes(range(100)),None),
                ('bytes=20-29',206,bytes(range(20,30)),'bytes 20-29/100'),
                ('bytes=90-',206,bytes(range(90,100)),'bytes 90-99/100'),
                ('bytes=-5',206,bytes(range(95,100)),'bytes 95-99/100'),
                ('bytes=95-200',206,bytes(range(95,100)),'bytes 95-99/100'),
                ('bytes=100-',416,b'','bytes */100'),
                ('bytes=40-20',416,b'','bytes */100'),
                ('bytes=0-1,4-5',416,b'','bytes */100'),
                ('bytes=-0',416,b'','bytes */100'),
            ):
                with self.subTest(range=current_range_value):
                    current_response_headers = {}
                    current_http_handler = SimpleNamespace(headers={'Range':current_range_value} if current_range_value else {},send_response=Mock(),send_header=lambda current_header_name,current_header_value:current_response_headers.update({current_header_name:current_header_value}),end_headers=Mock(),wfile=io.BytesIO())
                    send_audio_file_response(current_http_handler,current_audio_path)
                    current_http_handler.send_response.assert_called_once_with(current_status_code)
                    self.assertEqual(current_http_handler.wfile.getvalue(),current_expected_bytes)
                    self.assertEqual(current_response_headers['Content-Length'],str(len(current_expected_bytes)))
                    self.assertEqual(current_response_headers.get('Content-Range'),current_content_range)
