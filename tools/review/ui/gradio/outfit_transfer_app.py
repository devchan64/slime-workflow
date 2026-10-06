"""바디·아웃핏 두 이미지로 복장 착용하는 공용 UI 진입점."""
import argparse
import gradio as gr
from qwen_2511_app import build_qwen_2511_interface

if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/outfit-transfer-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_qwen_2511_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}', qwen21_mode_enabled=True, outfit_transfer_enabled=True).queue().launch(
        server_name='127.0.0.1', server_port=parsed_argument_values.port, root_path=parsed_argument_values.root_path,
           allowed_paths=[])
