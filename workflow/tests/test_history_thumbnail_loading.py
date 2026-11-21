"""이력 썸네일 지연이 페이지 전체를 직렬로 막지 않는지 검증한다."""
import time
import unittest
from unittest.mock import patch

from workflow.common.gradio_history_cards import render_generation_history_cards


class HistoryThumbnailLoadingTest(unittest.TestCase):
    def test_slow_thumbnails_are_parallel_and_failure_is_visible(self):
        current_records = [{'id':str(current_index), 'image':f'/image-{current_index}.png', 'status':'completed'} for current_index in range(4)]
        current_rows = [['완료','시각','설정','',str(current_index)] for current_index in range(4)]
        def fail_slow_thumbnail(current_items, current_server, timeout_seconds):
            self.assertEqual(timeout_seconds, 1)
            time.sleep(0.2)
            raise TimeoutError('지연')
        with patch('workflow.common.gradio_history_cards.load_gallery_image_values', side_effect=fail_slow_thumbnail):
            current_started_time = time.monotonic()
            current_cards = render_generation_history_cards(current_records, current_rows, server_base_address='http://127.0.0.1:8770')
            current_elapsed_time = time.monotonic() - current_started_time
        self.assertLess(current_elapsed_time, 0.65)
        self.assertEqual(len(current_cards), 4)
        self.assertTrue(all('썸네일 조회 실패' in current_caption for _,current_caption in current_cards))
