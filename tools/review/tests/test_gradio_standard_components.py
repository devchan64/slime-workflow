"""공용 Gradio 컴포넌트의 기본 입력과 스타일 비주입 계약."""
import ast
from pathlib import Path
import unittest
import gradio as gr
from tools.review.common.gradio_history import build_generation_history_view, build_history_table_rows
from tools.review.common.gradio_history_cards import CardGallery
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_seed import build_generation_seed

# 브라우저 캔버스·프레임 표시용 CSS만 허용하는 기존 사용자 정의 컴포넌트.
CANVAS_STYLE_APPLICATIONS = frozenset(('sprite_editor_app.py',))


class GradioStandardComponentTests(unittest.TestCase):
    def test_native_upload_clipboard_and_seed_do_not_generate(self):
        with gr.Blocks() as current_interface_blocks:
            _,current_reference_controls=build_reference_image_inputs(reference_slot_count=2)
            current_seed_control=build_generation_seed(123)
        self.assertTrue(all(current_reference_control.sources==['upload','clipboard'] for current_reference_control in current_reference_controls))
        current_script_controls = [current_block_value for current_block_value in current_interface_blocks.blocks.values() if isinstance(current_block_value,gr.HTML)]
        self.assertEqual(len(current_script_controls), 1)
        self.assertEqual(current_script_controls[0].html_template, '<span hidden></span>')
        self.assertIn('preserveReferenceDropFiles', current_script_controls[0].js_on_load)
        current_seed_callback=next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn.__name__=='generate_random_seed_value')
        self.assertEqual(current_seed_callback.outputs,[current_seed_control])
        self.assertEqual(current_seed_control.value,123)

    def test_seed_limit_matches_random_selection(self):
        from unittest.mock import patch
        from generators.kimodo.contracts import KIMODO_MAXIMUM_SEED_VALUE
        with gr.Blocks() as current_interface_blocks:
            current_seed_control = build_generation_seed(42, maximum_seed_value=KIMODO_MAXIMUM_SEED_VALUE)
        self.assertEqual(current_seed_control.maximum, KIMODO_MAXIMUM_SEED_VALUE)
        current_seed_callback = next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn.__name__ == 'generate_bounded_seed_value')
        with patch('tools.review.common.gradio_seed.secrets.randbelow', return_value=KIMODO_MAXIMUM_SEED_VALUE) as current_random_function:
            self.assertEqual(current_seed_callback.fn(), KIMODO_MAXIMUM_SEED_VALUE)
            current_random_function.assert_called_once_with(KIMODO_MAXIMUM_SEED_VALUE + 1)

    def test_wan_video_pages_use_generator_seed_limits(self):
        from generators.wan_animate2.contracts import ANIMATE_MAXIMUM_SEED_VALUE
        from generators.wan_vace.contracts import VACE_MAXIMUM_SEED_VALUE
        from generators.wan_animate2.page.interface import build_animate_interface
        from generators.wan_vace.page.interface import build_vace_interface
        for current_builder,current_maximum in ((build_animate_interface,ANIMATE_MAXIMUM_SEED_VALUE),(build_vace_interface,VACE_MAXIMUM_SEED_VALUE)):
            with self.subTest(builder=current_builder.__name__):
                current_interface=current_builder('http://localhost:8770',lambda *_:{})
                current_seed_controls=[current_block for current_block in current_interface.blocks.values() if isinstance(current_block,gr.Number) and current_block.label=='Seed']
                self.assertEqual(len(current_seed_controls),1)
                self.assertEqual(current_seed_controls[0].maximum,current_maximum)
                with self.assertRaises(gr.Error):current_seed_controls[0].preprocess(current_maximum+1)

    def test_history_summary_prioritizes_seed_and_shows_direction(self):
        from tools.review.common.gradio_history import format_history_request_summary
        current_summary_text = format_history_request_summary({'prompt':'A person walks.','seed':202,'directions':['front_right_30']})
        self.assertTrue(current_summary_text.startswith('시드 202'))
        self.assertIn('방향 front_right_30',current_summary_text)

    def test_wan_history_cards_identify_selected_model(self):
        current_history_records = [
            {'id': 'wan-small', 'status': 'completed', 'request': {'model_profile': 'wan21-1.3b', 'tag': 'wan22-fun-control', 'seed': 137}},
            {'id': 'wan-large', 'status': 'failed', 'request': {'model_profile': 'wan22-14b', 'seed': 137}},
            {'id': 'wan-legacy', 'status': 'completed', 'request': {'tag': 'wan22-fun-control'}},
            {'id': 'other', 'status': 'completed', 'request': {'tag': 'other'}},
        ]
        current_history_rows = build_history_table_rows(current_history_records)
        self.assertTrue(current_history_rows[0][2].startswith('모델 Wan 2.1 1.3B'))
        self.assertTrue(current_history_rows[1][2].startswith('모델 Wan 2.2 A14B'))
        self.assertTrue(current_history_rows[2][2].startswith('모델 Wan 2.2 A14B'))
        self.assertNotIn('모델 Wan', current_history_rows[3][2])

    def test_history_selection_uses_card_gallery_and_shared_state(self):
        with gr.Blocks() as current_interface_blocks:
            _,current_history_outputs=build_generation_history_view(lambda *_:{'records':[]},'http://localhost','검수용')
        self.assertIsInstance(current_history_outputs[0],gr.Dropdown)
        self.assertFalse(current_history_outputs[0].visible)
        current_history_gallery = current_history_outputs[3]
        self.assertIsInstance(current_history_gallery, CardGallery)
        self.assertFalse(current_history_gallery.allow_preview)
        self.assertEqual(current_history_gallery.columns, CardGallery.DEFAULT_COLUMNS)
        current_selection_callback = next(current_function for current_function in current_interface_blocks.fns.values() if current_function.name == 'select_history_table_record')
        self.assertIn(current_history_outputs[0], current_selection_callback.outputs)
        self.assertIsInstance(current_history_outputs[6],gr.Column)
        self.assertTrue(any(isinstance(current_block_value,gr.Gallery) for current_block_value in current_interface_blocks.blocks.values()))
        self.assertFalse(any(current_function_value.js and 'selectionInputElement' in current_function_value.js for current_function_value in current_interface_blocks.fns.values()))

    def test_progress_and_failed_reason_survive_native_table(self):
        current_table_rows=build_history_table_rows([{'id':'job-a','status':'running','request':{'tag':'비교'},'progress':{'stage':'inference','percent':50,'step':20,'total':40,'current_source_frame':4,'detail':'현재 프레임'}}])
        self.assertEqual(current_table_rows[0][0],'생성 중')
        self.assertIn('20/40',current_table_rows[0][3])
        self.assertIn('Fra:4',current_table_rows[0][3])
        self.assertEqual(current_table_rows[0][-1],'job-a')

    def test_queue_status_is_not_repeated_in_progress_column(self):
        current_table_rows=build_history_table_rows([{'id':'queued-job','status':{'status':'queued'},'progress':{'stage':'queued','queue_position':3,'detail':'메모리 대기'}}, {'id':'done-job','status':'completed','progress':{'stage':'completed'}}])
        self.assertEqual(current_table_rows[0][0], 'GPU 대기 중')
        self.assertEqual(current_table_rows[0][3], '대기 순서 3 · 메모리 대기')
        self.assertEqual(current_table_rows[1][3], '')

    def test_consumers_do_not_inject_theme_or_css(self):
        current_application_root=Path(__file__).parents[1]/'ui/gradio'
        for current_application_path in sorted(current_application_root.glob('*_app.py')):
            with self.subTest(application=current_application_path.name):
                current_source_tree=ast.parse(current_application_path.read_text())
                for current_call_node in ast.walk(current_source_tree):
                    if isinstance(current_call_node,ast.Call) and isinstance(current_call_node.func,ast.Attribute) and current_call_node.func.attr in ('launch','Blocks'):
                        current_keyword_names = {current_keyword_node.arg for current_keyword_node in current_call_node.keywords}
                        self.assertNotIn('theme', current_keyword_names)
                        if current_application_path.name not in CANVAS_STYLE_APPLICATIONS:
                            self.assertNotIn('css', current_keyword_names)
