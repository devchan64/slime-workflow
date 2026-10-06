"""Gradio 관리 메뉴의 목록 필터와 내부 화면 연결을 검증한다."""
import unittest
import ast
import inspect

from tools.review.ui.gradio.management_menu_app import build_management_menu_interface

from tools.review.ui.gradio.management_menu_app import create_initial_selection_script, create_menu_navigation_script, create_page_preview_html, create_tool_choice_values, filter_manager_page_records, format_gpu_status, render_gpu_status_card


class GradioManagementMenuTests(unittest.TestCase):
    def setUp(self):
        self.page_record_values=[
            {'id':'momask-generator','label':'MoMask 모션 생성기','path':'/momask-generator/','category':'animation-tool','uiMode':'gradio','description':'고정 포즈 스크립트'},
            {'id':'character-animation','label':'캐릭터 애니메이션 생성기','path':'/character-animation/','category':'animation-tool','description':'방향 선택'},
        ]

    def test_filter_supports_category_and_search(self):
        self.assertEqual([record['id'] for record in filter_manager_page_records(self.page_record_values,'모션','animation-tool')],['momask-generator'])
        self.assertEqual([record['id'] for record in filter_manager_page_records(self.page_record_values,'캐릭터','all')],['character-animation'])

    def test_preview_uses_review_server_path(self):
        preview_html_text=create_page_preview_html('momask-generator',self.page_record_values,8770)
        self.assertIn('http://127.0.0.1:8770/management/frame/momask-generator/',preview_html_text)
        self.assertIn('MoMask 모션 생성기',preview_html_text)
        self.assertIn('allow="clipboard-write http://127.0.0.1:8770 http://127.0.0.1:8871; clipboard-read http://127.0.0.1:8770 http://127.0.0.1:8871"',preview_html_text)

    def test_static_review_uses_gradio_component_path(self):
        static_review_records=[{'id':'walk-review','label':'걷기 검수','path':'walk/anchors.html','category':'animation','uiMode':'gradio-static','description':'앵커'}]

        preview_html_text=create_page_preview_html('walk-review',static_review_records,8770)

        self.assertIn('/management/frame/static-review/?review=walk-review',preview_html_text)

    def test_uses_gradio_frame_identifier_when_page_id_is_a_public_alias(self):
        anny_page_records=[{'id':'anny-attribute-renderer','label':'Anny 속성 렌더러','path':'/anny-attributes/','category':'animation-tool','uiMode':'gradio','description':'속성 렌더'}]

        preview_html_text=create_page_preview_html('anny-attribute-renderer',anny_page_records,8770)

        self.assertIn('/management/frame/anny-attributes/',preview_html_text)
        self.assertNotIn('/management/frame/anny-attribute-renderer/',preview_html_text)

    def test_direct_static_review_tool_identifier_selects_the_page(self):
        initial_selection_script=create_initial_selection_script(self.page_record_values)

        self.assertIn('record.path===currentUrlValue.pathname',initial_selection_script)
        self.assertIn("searchParams.get('tool')",initial_selection_script)
        self.assertIn('return [',initial_selection_script)
        self.assertNotIn('querySelector',initial_selection_script)
        self.assertNotIn('selectedPageIndex',initial_selection_script)

    def test_navigation_script_persists_filter_values_with_selected_tool_path(self):
        navigation_script=create_menu_navigation_script(self.page_record_values,'pushState')

        self.assertIn("['search',searchTextValue,'']",navigation_script)
        self.assertIn("['category',categoryNameValue,'all']",navigation_script)
        self.assertIn("nextUrlValue.searchParams.delete('view')",navigation_script)
        self.assertIn('window.top.history.pushState',navigation_script)
        self.assertIn('filteredPageRecords[0]',navigation_script)

    def test_tool_choices_include_category_for_long_lists(self):
        self.assertEqual(
            create_tool_choice_values(self.page_record_values),
            [('애니메이션 도구 · MoMask 모션 생성기','momask-generator'),('애니메이션 도구 · 캐릭터 애니메이션 생성기','character-animation')],
        )

    def test_gpu_status_is_human_readable(self):
        self.assertEqual(format_gpu_status({'status':'idle','processes':[]}),'GPU · 실행 중인 연산 작업 없음')
        self.assertIn('MoMask 모션 생성 · sample · 512 MiB',format_gpu_status({'status':'busy','processes':[{'command':'MoMask 모션 생성','id':'sample','memory_mib':512}]}))

    def test_gpu_status_card_exposes_idle_and_busy_states(self):
        idle_status_card = render_gpu_status_card({'status':'idle','processes':[]})
        busy_status_card = render_gpu_status_card({'status':'busy','processes':[{'command':'MoMask 모션 생성','id':'sample','memory_mib':512}], 'memory_total_mib': 12288, 'memory_used_mib': 1024, 'memory_free_mib': 11264})

        self.assertNotIn('<', idle_status_card)
        self.assertIn('실행 중인 연산 작업 없음', idle_status_card)
        self.assertIn('GPU 사용 중', busy_status_card)
        self.assertIn('MoMask 모션 생성', busy_status_card)
        self.assertIn('sample', busy_status_card)
        self.assertIn('사용 1,024 MiB', busy_status_card)
        self.assertIn('여유 11,264 MiB', busy_status_card)
        self.assertIn('총 12,288 MiB', busy_status_card)


class ManagementMenuRefreshTests(unittest.TestCase):
    def test_menu_updates_do_not_bind_server_change_events(self):
        interface_syntax_tree = ast.parse(inspect.getsource(build_management_menu_interface))
        change_event_calls = [current_syntax_node for current_syntax_node in ast.walk(interface_syntax_tree)
                              if isinstance(current_syntax_node, ast.Call)
                              and isinstance(current_syntax_node.func, ast.Attribute)
                              and current_syntax_node.func.attr == 'change']
        self.assertEqual(change_event_calls, [])

    def test_initial_selection_does_not_click_selected_tool(self):
        selection_script_text = create_initial_selection_script([])
        self.assertNotIn('.click()', selection_script_text)

class ManagementNativeNavigationTests(unittest.TestCase):
    def test_initial_query_keeps_selected_page_and_clears_conflicting_filter(self):
        import gradio as gr
        current_page_records=[{'id':'first','label':'첫 도구','path':'/first','category':'animation-tool','description':'첫 도구'}, {'id':'second','label':'둘째 도구','path':'/second','category':'image-generation','description':'둘째 도구'}]
        current_interface_blocks,_=build_management_menu_interface(current_page_records,8770)
        current_load_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='initialize_menu_selection')
        current_update_values=current_load_callback('불일치','animation-tool','second')
        self.assertEqual(current_update_values[:2],['','all'])
        self.assertEqual(current_update_values[2]['value'],'second')
        self.assertIn('/second',current_update_values[5])
        self.assertFalse(any(isinstance(current_component_value,gr.Radio) for current_component_value in current_interface_blocks.blocks.values()))
