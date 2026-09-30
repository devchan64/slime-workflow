"""공용 Qwen 참조 UI를 사용하는 표정 생성기 진입점."""
import argparse
from qwen_2511_app import build_qwen_2511_interface, LOG_PANEL_STYLES, MANAGEMENT_SHARED_STYLES
import gradio as gr

if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/expression-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_qwen_2511_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}', expression_mode_enabled=True).queue().launch(server_name='127.0.0.1', server_port=parsed_argument_values.port, root_path=parsed_argument_values.root_path, theme=gr.themes.Soft(), css=LOG_PANEL_STYLES+MANAGEMENT_SHARED_STYLES, allowed_paths=[])
