"""Anny 속성 렌더러를 Gradio 작업 영역에 연결한다."""
import argparse
import threading
import time

import gradio as gr


def build_anny_attribute_interface(review_server_port):
    with gr.Blocks(title='Anny 속성 렌더러') as interface_blocks_value:
        gr.Markdown('## Anny 속성 렌더러\n기존의 속성 입력, 미리보기, 렌더 이력은 유지하며 작업 영역에서 제공합니다.')
        gr.HTML(f'<iframe title="Anny 속성 렌더러" class="anny-attribute-frame" src="http://127.0.0.1:{review_server_port}/anny-attributes/embedded/"></iframe>')
    return interface_blocks_value


if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/anny-attributes/')
    argument_values = argument_parser_value.parse_args()
    threading.Thread(target=lambda: time.sleep(1), daemon=True).start()
    build_anny_attribute_interface(argument_values.review_port).queue().launch(
        server_name='127.0.0.1', server_port=argument_values.port, root_path=argument_values.root_path,
        css='.anny-attribute-frame{width:100%;height:calc(100vh - 190px);min-height:700px;border:0}', allowed_paths=[])
