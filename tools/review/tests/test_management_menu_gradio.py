"""Gradio 관리 메뉴의 목록 필터와 내부 화면 연결을 검증한다."""
import unittest

from tools.review.ui.gradio.management_menu_app import create_page_preview_html, create_tool_choice_values, filter_manager_page_records, format_gpu_status


class GradioManagementMenuTests(unittest.TestCase):
    def setUp(self):
        self.page_record_values=[
            {'id':'momask-generator','label':'MoMask 모션 생성기','path':'/momask-generator/','category':'animation-tool','uiMode':'gradio','description':'고정 포즈 스크립트'},
            {'id':'character-animation','label':'캐릭터 애니메이션 생성기','path':'/character-animation/','category':'animation-tool','description':'방향 선택'},
        ]

    def test_filter_supports_gradio_state_and_search(self):
        self.assertEqual([record['id'] for record in filter_manager_page_records(self.page_record_values,'모션','animation-tool','gradio')],['momask-generator'])
        self.assertEqual([record['id'] for record in filter_manager_page_records(self.page_record_values,'','animation-tool','html')],['character-animation'])

    def test_preview_uses_review_server_path(self):
        preview_html_text=create_page_preview_html('momask-generator',self.page_record_values,8770)
        self.assertIn('http://127.0.0.1:8770/momask-generator/',preview_html_text)
        self.assertIn('MoMask 모션 생성기',preview_html_text)
        self.assertIn('allow="clipboard-write http://127.0.0.1:8770 http://127.0.0.1:8871"',preview_html_text)

    def test_tool_choices_include_category_for_long_lists(self):
        self.assertEqual(
            create_tool_choice_values(self.page_record_values),
            [('애니메이션 도구 · MoMask 모션 생성기','momask-generator'),('애니메이션 도구 · 캐릭터 애니메이션 생성기','character-animation')],
        )

    def test_gpu_status_is_human_readable(self):
        self.assertEqual(format_gpu_status({'status':'idle','processes':[]}),'GPU · 실행 중인 연산 작업 없음')
        self.assertIn('MoMask 모션 생성 · sample · 512 MiB',format_gpu_status({'status':'busy','processes':[{'command':'MoMask 모션 생성','id':'sample','memory_mib':512}]}))
