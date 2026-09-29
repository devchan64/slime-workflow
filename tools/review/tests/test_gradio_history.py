import inspect
import unittest

from tools.review.common.gradio_history import build_generation_history_view, collect_image_history_thumbnails, format_history_choice_label, format_history_selection_summary, render_history_detail_cards


class GradioHistoryTest(unittest.TestCase):
    def test_history_view_uses_selected_card_as_the_only_result_lookup_entry(self):
        history_view_parameter_names=inspect.signature(build_generation_history_view).parameters

        self.assertNotIn('direct_result_identifier_component',history_view_parameter_names)
        self.assertNotIn('direct_result_button_component',history_view_parameter_names)

    def test_history_choice_includes_status_time_identifier_and_request_summary(self):
        history_choice_label = format_history_choice_label({'id':'tile-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'tile_type':'wall','width':512,'height':512,'steps':30,'seed':10107}})

        self.assertEqual(history_choice_label,'완료 · 2026-09-27 09:15:00\n타일 wall · 너비 512 · 높이 512 · 스텝 30 · 시드 10107\nID · tile-123')

    def test_history_choice_handles_legacy_minimal_record(self):
        self.assertEqual(format_history_choice_label({'id':'legacy-1','status':'failed','request':{}}),'실패 · 시각 없음\n설정 요약 없음\nID · legacy-1')

    def test_history_selection_summary_makes_status_and_identifier_scannable(self):
        summary_text=format_history_selection_summary({'id':'animation-123','created_at':'2026-09-27T09:15:00.123456+09:00','status':{'status':'completed'},'request':{'motion':'standing-v8','action':'generate','start_frame':1,'end_frame':12}})
        self.assertIn('**완료**',summary_text)
        self.assertIn('ID: `animation-123`',summary_text)
        self.assertIn('모션 standing-v8',summary_text)
        self.assertNotIn('동작 generate',summary_text)
        self.assertNotIn('.123456',summary_text)

    def test_collects_only_image_history_thumbnails(self):
        thumbnail_item_values,thumbnail_identifier_values=collect_image_history_thumbnails([
            {'id':'completed-image','status':{'status':'completed'},'image':'/image-generation/jobs/completed-image/result.png'},
            {'id':'running-image','status':{'status':'running'},'image':None},
        ],'http://127.0.0.1:8770')
        self.assertEqual(thumbnail_item_values,[('http://127.0.0.1:8770/image-generation/jobs/completed-image/result.png','completed · completed-image')])
        self.assertEqual(thumbnail_identifier_values,['completed-image'])

    def test_history_card_uses_tag_and_image_type_as_heading(self):
        rendered_history_html=render_history_detail_cards([{'id':'image-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'action':'generate','tag':'돌온재 자갈 지면','prompt':'gravel ground','width':512,'steps':4}}])
        self.assertIn('돌온재 자갈 지면 · 이미지 생성',rendered_history_html)
        self.assertNotIn('<strong>생성 작업</strong>',rendered_history_html)

    def test_result_view_displays_original_and_crop_with_labels(self):
        from tools.review.common.gradio_history import render_generation_images
        rendered_result_html=render_generation_images({'image':'/jobs/sample/result.png','cropped_image':'/jobs/sample/border-crop.png'},'http://127.0.0.1:8770')
        self.assertIn('생성 원본',rendered_result_html)
        self.assertIn('보더 크롭 결과',rendered_result_html)
        self.assertEqual(rendered_result_html.count('<img '),2)
        self.assertIn('http://127.0.0.1:8770/jobs/sample/border-crop.png',rendered_result_html)

    def test_legacy_result_view_does_not_show_missing_crop(self):
        from tools.review.common.gradio_history import render_generation_images
        rendered_result_html=render_generation_images({'image':'/jobs/sample/result.png'},'http://127.0.0.1:8770')
        self.assertEqual(rendered_result_html.count('<img '),1)
        self.assertNotIn('보더 크롭 결과',rendered_result_html)
