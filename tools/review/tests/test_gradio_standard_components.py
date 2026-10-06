"""공용 Gradio 컴포넌트의 기본 입력과 스타일 비주입 계약."""
import ast
from pathlib import Path
import unittest
import gradio as gr
from tools.review.common.gradio_history import build_generation_history_view, build_history_table_rows
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_seed import build_generation_seed

STANDARD_APPLICATION_NAMES=('momask','qwen_2511','qwen_2512','qwen_21','qwen_circular','expression','pose_transfer','outfit_transfer','seamless_tile','floor_tile','character_animation','animation_separation')


class GradioStandardComponentTests(unittest.TestCase):
    def test_native_upload_clipboard_and_seed_do_not_generate(self):
        with gr.Blocks() as current_interface_blocks:
            _,current_reference_controls=build_reference_image_inputs(reference_slot_count=2)
            current_seed_control=build_generation_seed(123)
        self.assertTrue(all(current_reference_control.sources==['upload','clipboard'] for current_reference_control in current_reference_controls))
        self.assertFalse(any(isinstance(current_block_value,gr.HTML) for current_block_value in current_interface_blocks.blocks.values()))
        current_seed_callback=next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn.__name__=='generate_random_seed_value')
        self.assertEqual(current_seed_callback.outputs,[current_seed_control])
        self.assertEqual(current_seed_control.value,123)

    def test_history_selection_uses_visible_native_dropdown(self):
        with gr.Blocks() as current_interface_blocks:
            _,current_history_outputs=build_generation_history_view(lambda *_:{'records':[]},'http://localhost','검수용')
        self.assertIsInstance(current_history_outputs[0],gr.Dropdown)
        self.assertTrue(current_history_outputs[0].visible)
        self.assertIsInstance(current_history_outputs[3],gr.Dataframe)
        self.assertIsInstance(current_history_outputs[6],gr.Gallery)
        self.assertFalse(any(current_function_value.js and 'selectionInputElement' in current_function_value.js for current_function_value in current_interface_blocks.fns.values()))

    def test_progress_and_failed_reason_survive_native_table(self):
        current_table_rows=build_history_table_rows([{'id':'job-a','status':'running','request':{'tag':'비교'},'progress':{'stage':'inference','percent':50,'step':20,'total':40,'current_source_frame':4,'detail':'현재 프레임'}}])
        self.assertEqual(current_table_rows[0][0],'생성 중')
        self.assertIn('20/40',current_table_rows[0][3])
        self.assertIn('Fra:4',current_table_rows[0][3])
        self.assertEqual(current_table_rows[0][-1],'job-a')

    def test_consumers_do_not_inject_theme_or_css(self):
        current_application_root=Path(__file__).parents[1]/'ui/gradio'
        for current_application_name in STANDARD_APPLICATION_NAMES:
            with self.subTest(application=current_application_name):
                current_source_tree=ast.parse((current_application_root/(current_application_name+'_app.py')).read_text())
                for current_call_node in ast.walk(current_source_tree):
                    if isinstance(current_call_node,ast.Call) and isinstance(current_call_node.func,ast.Attribute) and current_call_node.func.attr in ('launch','Blocks'):
                        self.assertFalse({'css','theme'} & {current_keyword_node.arg for current_keyword_node in current_call_node.keywords})
