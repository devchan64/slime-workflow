"""Gradio 관리 메뉴의 목록 필터와 내부 화면 연결을 검증한다."""
import unittest
import ast
import inspect

from tools.review.ui.gradio.management_menu_app import build_management_menu_interface

from tools.review.ui.gradio.management_menu_app import create_initial_selection_script, create_menu_navigation_script, create_page_preview_html, create_tool_choice_values, filter_manager_page_records, format_gpu_status, render_gpu_status_card


class GradioManagementMenuTests(unittest.TestCase):
    def test_animation_menu_preserves_full_catalog(self):
        import json
        import tempfile
        from pathlib import Path
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        current_page_records=[{'id':f'animation-{current_sprite_number}','label':f'스프라이트 {current_sprite_number}','path':f'/animation-{current_sprite_number}/anchors.html','category':'animation','description':'등록 원본'} for current_sprite_number in (1,17)]
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_source_path=Path(current_temporary_directory)/'pages.json'
            current_source_path.write_text(json.dumps({'pages':current_page_records}))
            current_menu_records=[current_page_record for current_page_record in load_manager_page_records(current_source_path) if current_page_record["category"]=="animation"]
            self.assertEqual(len(current_menu_records),1)
            self.assertEqual(current_menu_records[0]['reviewAliases'],['animation-1','animation-17'])
            self.assertEqual(len([current_page_record for current_page_record in load_manager_page_records(current_source_path,current_animation_catalog=True) if current_page_record["category"]=="animation"]),2)

    def test_menu_source_validation_explains_root_and_fields(self):
        import json
        import tempfile
        from pathlib import Path
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        current_valid_page = {'id':'audit-page','label':'검증','path':'/audit/','category':'animation-tool','description':'검증 페이지'}
        current_invalid_sources = [(None, '원본은 객체'), ([], '원본은 객체'), ('pages', '원본은 객체'), (12, '원본은 객체'), ({'pages':{}}, '목록 형식')]
        current_invalid_sources += [({'pages':[{**current_valid_page,current_field_name:None}]}, current_field_name) for current_field_name in current_valid_page]
        current_invalid_sources += [({'pages':[{current_field_name:current_field_value for current_field_name,current_field_value in current_valid_page.items() if current_field_name!='path'}]}, 'path')]
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_source_path = Path(current_temporary_directory)/'pages.json'
            for current_source_record,current_error_message in current_invalid_sources:
                with self.subTest(source=current_source_record):
                    current_source_path.write_text(json.dumps(current_source_record))
                    with self.assertRaisesRegex(ValueError,current_error_message):
                        load_manager_page_records(current_source_path)
            current_source_path.write_text(json.dumps({'pages':[current_valid_page]}))
            self.assertIn('audit-page',[current_page_record['id'] for current_page_record in load_manager_page_records(current_source_path)])

    def test_invalid_page_record_reports_explicit_type_error(self):
        import json
        import tempfile
        from pathlib import Path
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_source_path = Path(current_temporary_directory)/'pages.json'
            for current_invalid_record in (None, 12, 'page', []):
                with self.subTest(record=current_invalid_record):
                    current_source_path.write_text(json.dumps({'pages':[current_invalid_record]}))
                    with self.assertRaisesRegex(ValueError, '페이지 항목은 객체'):
                        load_manager_page_records(current_source_path)

    def test_pose_generator_release_metadata(self):
        import json
        import tempfile
        from pathlib import Path
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_source_path = Path(current_temporary_directory) / 'pages.json'
            current_source_path.write_text(json.dumps({'pages': [{'id': 'pose-transfer-generator', 'label': '포즈 변환 생성기 · Alpha Ver.', 'path': '/pose-transfer/', 'category': 'animation-tool', 'description': 'Alpha Ver.'}]}))
            self.assertNotIn('pose-transfer-generator', [current_page_record['id'] for current_page_record in load_manager_page_records(current_source_path)])

    def setUp(self):
        self.page_record_values=[
            {'id':'momask-generator','label':'MoMask 모션 생성기','path':'/momask-generator/','category':'animation-tool','uiMode':'gradio','description':'고정 포즈 스크립트'},
            {'id':'character-animation','label':'캐릭터 애니메이션 생성기','path':'/character-animation/','category':'animation-tool','description':'방향 선택'},
        ]

    def test_filter_supports_category_and_search(self):
        self.assertEqual([record['id'] for record in filter_manager_page_records(self.page_record_values,'모션','animation-tool')],['momask-generator'])
        self.assertEqual([record['id'] for record in filter_manager_page_records(self.page_record_values,'캐릭터','all')],['character-animation'])

    def test_preview_uses_native_tool_link_without_iframe(self):
        current_page_records=[{'id':'kimodo-generator','label':'Kimodo','path':'/kimodo-generator/','category':'animation-tool','description':'모션','uiMode':'gradio'}]
        current_preview_markup=create_page_preview_html('kimodo-generator',current_page_records,8770)
        self.assertIn('/management/frame/kimodo-generator/',current_preview_markup)
        self.assertIn('Kimodo',current_preview_markup)
        self.assertNotIn('iframe',current_preview_markup)

    def test_map_route_preserves_shared_application_and_query(self):
        from tools.review.ui.gradio.management_menu_app import resolve_management_page_path
        current_page_record={'id':'map-review-meadow','uiMode':'gradio','frameIdentifier':'map-review','frameQuery':'map=meadow&townPage=1'}
        self.assertEqual(resolve_management_page_path(current_page_record),'/management/frame/map-review/?map=meadow&townPage=1')

    def test_static_review_uses_gradio_component_path(self):
        static_review_records=[{'id':'walk-review','label':'걷기 검수','path':'walk/anchors.html','category':'animation','uiMode':'gradio-static','description':'앵커'}]

        preview_html_text=create_page_preview_html('walk-review',static_review_records,8770)

        self.assertIn('/management/frame/static-review/?review=walk-review',preview_html_text)
        self.assertNotIn('<iframe',preview_html_text)

    def test_standalone_document_link_is_root_relative(self):
        current_page_records=[{'id':'walk-review','label':'걷기 비교','path':'walking/preview.html','category':'animation','uiMode':'html','description':'비교'}]
        current_preview_markup=create_page_preview_html('walk-review',current_page_records,8770)
        self.assertIn('href="/walking/preview.html"',current_preview_markup)
        self.assertNotIn('<iframe',current_preview_markup)


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
    def test_inline_blocks_keep_shared_sidebar_and_remove_frame_sizing(self):
        import gradio as gr
        from tools.review.ui.gradio.management_menu_app import create_sidebar_responsive_script
        with gr.Blocks() as current_child_interface:
            current_child_input=gr.Textbox(label='도구 입력')
            current_child_button=gr.Button('도구 실행')
            current_child_button.click(lambda current_input_value:current_input_value,current_child_input,current_child_input)
        current_interface_blocks,_=build_management_menu_interface([],8770,current_child_interface)
        self.assertIn(current_child_input._id,current_interface_blocks.blocks)
        self.assertTrue(any(current_event_record['backend_fn'] for current_event_record in current_interface_blocks.get_config_file()['dependencies']))
        self.assertNotIn('contentDocument',create_sidebar_responsive_script(True))
        self.assertNotIn('ResizeObserver',create_sidebar_responsive_script(True))

    def test_native_navigation_preserves_filters_and_does_not_reload_current_tool(self):
        import subprocess
        current_page_records=[{'id':'anchor-a','label':'앵커 A','path':'/a/anchors.html','category':'animation','description':'검수','uiMode':'gradio-static'}, {'id':'anchor-b','label':'앵커 B','path':'/b/anchors.html','category':'animation','description':'검수','uiMode':'gradio-static'}, {'id':'image','label':'이미지','path':'/image','category':'image-generation','description':'생성','uiMode':'gradio'}]
        current_navigation_source=create_menu_navigation_script(current_page_records,'pushState',True)
        current_filter_source=create_menu_navigation_script(current_page_records,'replaceState',True)
        current_script_source="""
const assert=require('node:assert/strict');const currentNavigationCalls=[];
const currentLocationValue={href:'http://review.test/management/frame/static-review/?review=anchor-a&action=walk',pathname:'/management/frame/static-review/',assign:currentUrlText=>currentNavigationCalls.push(['assign',currentUrlText])};
global.window={location:currentLocationValue,history:{state:null,pushState:(currentStateValue,currentTitleText,currentUrlText)=>currentNavigationCalls.push(['push',currentUrlText]),replaceState:(currentStateValue,currentTitleText,currentUrlText)=>currentNavigationCalls.push(['replace',currentUrlText])}};window.top=window;
const currentNavigateTool="""+current_navigation_source+""";
currentNavigateTool('앵커','animation','anchor-a');assert.equal(currentNavigationCalls.at(-1)[0],'push');assert.match(currentNavigationCalls.at(-1)[1],/action=walk/);
currentNavigateTool('앵커','animation','anchor-b');assert.equal(currentNavigationCalls.at(-1)[0],'assign');
const currentTargetLocation=new URL(currentNavigationCalls.at(-1)[1]);assert.equal(currentTargetLocation.searchParams.get('review'),'anchor-b');assert.equal(currentTargetLocation.searchParams.get('category'),'animation');assert.equal(currentTargetLocation.searchParams.get('search'),'앵커');assert.equal(currentTargetLocation.searchParams.has('action'),false);
currentNavigateTool('','all','image');assert.equal(new URL(currentNavigationCalls.at(-1)[1]).pathname,'/');
currentNavigateTool('결과 없음','all','anchor-a');assert.equal(currentNavigationCalls.at(-1)[0],'replace');assert.match(currentNavigationCalls.at(-1)[1],/review=anchor-a/);
const currentFilterCallback="""+current_filter_source+""";
currentFilterCallback('이미지','all','anchor-a');assert.equal(currentNavigationCalls.at(-1)[0],'replace');assert.match(currentNavigationCalls.at(-1)[1],/review=anchor-a/);assert.match(currentNavigationCalls.at(-1)[1],/action=walk/);
"""
        current_command_result=subprocess.run(['node','-e',current_script_source],text=True,capture_output=True)
        self.assertEqual(current_command_result.returncode,0,current_command_result.stderr)

    def test_unknown_initial_url_does_not_redirect_or_select_first_tool(self):
        import subprocess
        current_page_records=[{'id':'first','label':'첫 도구','path':'/first','category':'animation-tool','description':'첫 도구'}]
        current_selection_source=create_initial_selection_script(current_page_records)
        current_script_source="""
const assert=require('node:assert/strict');
let currentNavigationCount=0;
global.window={location:{href:'http://review.test/management/frame/static-review/?review=removed'},history:{state:null,replaceState:()=>currentNavigationCount++}};
window.location.replace=()=>currentNavigationCount++;
const currentSelectInitial="""+current_selection_source+""";
assert.equal(currentSelectInitial()[2],'removed');
assert.equal(currentNavigationCount,0);
window.location.href='http://review.test/?tool=first';
assert.equal(currentSelectInitial()[2],'first');
window.location.href='http://review.test/';
assert.equal(currentSelectInitial()[2],'first');
"""
        current_command_result=subprocess.run(['node','-e',current_script_source],text=True,capture_output=True)
        self.assertEqual(current_command_result.returncode,0,current_command_result.stderr)
        current_interface_blocks,_=build_management_menu_interface(current_page_records,8770)
        current_load_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='initialize_menu_selection')
        current_load_function=next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn is current_load_callback)
        self.assertFalse(current_load_function.preprocess)
        current_update_values=current_load_callback('','all','removed')
        self.assertIsNone(current_update_values[2]['value'])
        self.assertIn('등록되지 않은',current_update_values[4])
        self.assertEqual(current_update_values[5],'')

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

class ManagementResponsiveSidebarTests(unittest.TestCase):
    def test_navigation_uses_fixed_width_native_sidebar(self):
        import gradio as gr
        current_interface_blocks,_=build_management_menu_interface([],8770)
        current_sidebar_values=[value for value in current_interface_blocks.blocks.values() if isinstance(value,gr.Sidebar)]
        self.assertEqual(len(current_sidebar_values),1)
        self.assertEqual(current_sidebar_values[0].width,320)
        self.assertEqual(current_sidebar_values[0].elem_id,'management-sidebar')
        self.assertTrue(current_sidebar_values[0].open)
        self.assertFalse(current_interface_blocks.css)
        self.assertTrue(current_interface_blocks.fill_width)
