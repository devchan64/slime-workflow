import unittest

from tools.review.common.gradio_history import format_history_choice_label


class GradioHistoryTest(unittest.TestCase):
    def test_history_choice_includes_status_time_identifier_and_request_summary(self):
        history_choice_label = format_history_choice_label({'id':'tile-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'tile_type':'wall','width':512,'height':512,'steps':30,'seed':10107}})

        self.assertEqual(history_choice_label,'completed · 2026-09-27T09:15:00+09:00 · tile-123 · tile_type=wall · width=512 · height=512 · steps=30 · seed=10107')

    def test_history_choice_handles_legacy_minimal_record(self):
        self.assertEqual(format_history_choice_label({'id':'legacy-1','status':'failed','request':{}}),'failed · 시각 없음 · legacy-1 · 설정 요약 없음')
