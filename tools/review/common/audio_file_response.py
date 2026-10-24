"""브라우저 오디오 탐색을 위한 단일 바이트 구간 응답."""
import re

AUDIO_TRANSFER_CHUNK_BYTES = 256 * 1024


def send_audio_file_response(current_http_handler,current_audio_path):
    with current_audio_path.open('rb') as current_audio_stream:
        current_audio_stream.seek(0,2)
        current_total_bytes = current_audio_stream.tell()
        current_start_byte = 0
        current_end_byte = current_total_bytes - 1
        current_status_code = 200
        current_range_header = current_http_handler.headers.get('Range')
        if current_range_header:
            current_range_match = re.fullmatch(r'bytes=(\d*)-(\d*)',current_range_header.strip())
            current_range_valid = bool(current_range_match and any(current_range_match.groups()))
            if current_range_valid:
                current_start_text,current_end_text = current_range_match.groups()
                if current_start_text:
                    current_start_byte = int(current_start_text)
                    current_end_byte = min(int(current_end_text),current_end_byte) if current_end_text else current_end_byte
                else:
                    current_suffix_bytes = int(current_end_text)
                    current_start_byte = max(0,current_total_bytes-current_suffix_bytes)
                    current_range_valid = current_suffix_bytes > 0
                current_range_valid = current_range_valid and 0 <= current_start_byte <= current_end_byte < current_total_bytes
            if not current_range_valid:
                current_http_handler.send_response(416)
                current_http_handler.send_header('Content-Range',f'bytes */{current_total_bytes}')
                current_http_handler.send_header('Accept-Ranges','bytes')
                current_http_handler.send_header('Content-Length','0')
                current_http_handler.end_headers()
                return
            current_status_code = 206
        current_response_size = max(0,current_end_byte-current_start_byte+1)
        current_http_handler.send_response(current_status_code)
        current_http_handler.send_header('Content-Type','audio/wav')
        current_http_handler.send_header('Accept-Ranges','bytes')
        current_http_handler.send_header('Content-Length',str(current_response_size))
        current_http_handler.send_header('Cache-Control','no-store')
        if current_status_code == 206:
            current_http_handler.send_header('Content-Range',f'bytes {current_start_byte}-{current_end_byte}/{current_total_bytes}')
        current_http_handler.end_headers()
        current_audio_stream.seek(current_start_byte)
        while current_response_size:
            current_audio_chunk = current_audio_stream.read(min(current_response_size,AUDIO_TRANSFER_CHUNK_BYTES))
            if not current_audio_chunk:
                raise OSError('오디오 전송 중 파일 길이가 변경되었습니다.')
            try:
                current_http_handler.wfile.write(current_audio_chunk)
            except (BrokenPipeError,ConnectionResetError):
                return
            current_response_size -= len(current_audio_chunk)
