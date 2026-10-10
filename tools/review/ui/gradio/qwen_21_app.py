"""선택형 화풍·투명 배경 옵션을 제공하는 Qwen Image 2.1 UI."""
import argparse
import gradio as gr
from qwen_2511_app import build_qwen_2511_interface

if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/qwen-21-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_qwen_2511_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}', qwen21_mode_enabled=True).queue().launch(
        server_name='127.0.0.1', server_port=parsed_argument_values.port, root_path=parsed_argument_values.root_path,
           allowed_paths=[])
