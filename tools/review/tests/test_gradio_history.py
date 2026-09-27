import unittest

from tools.review.common.gradio_history import collect_image_history_thumbnails, format_history_choice_label, format_history_selection_summary


class GradioHistoryTest(unittest.TestCase):
    def test_history_choice_includes_status_time_identifier_and_request_summary(self):
        history_choice_label = format_history_choice_label({'id':'tile-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'tile_type':'wall','width':512,'height':512,'steps':30,'seed':10107}})

        self.assertEqual(history_choice_label,'completed · 2026-09-27 09:15:00\n타일 wall · 너비 512 · 높이 512 · 스텝 30 · 시드 10107\nID · tile-123')

    def test_history_choice_handles_legacy_minimal_record(self):
        self.assertEqual(format_history_choice_label({'id':'legacy-1','status':'failed','request':{}}),'failed · 시각 없음\n설정 요약 없음\nID · legacy-1')

    def test_history_selection_summary_makes_status_and_identifier_scannable(self):
        summary_text=format_history_selection_summary({'id':'animation-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'motion':'standing-v8','start_frame':1,'end_frame':12}})
        self.assertIn('**completed**',summary_text)
        self.assertIn('`animation-123`',summary_text)
        self.assertIn('모션 standing-v8',summary_text)

    def test_collects_only_image_history_thumbnails(self):
        thumbnail_item_values,thumbnail_identifier_values=collect_image_history_thumbnails([
            {'id':'completed-image','status':{'status':'completed'},'image':'/image-generation/jobs/completed-image/result.png'},
            {'id':'running-image','status':{'status':'running'},'image':None},
        ],'http://127.0.0.1:8770')
        self.assertEqual(thumbnail_item_values,[('http://127.0.0.1:8770/image-generation/jobs/completed-image/result.png','completed · completed-image')])
        self.assertEqual(thumbnail_identifier_values,['completed-image'])
