"""실행별 정적 검수 페이지를 Gradio 작업 영역에서 연다."""
import argparse
import threading
import time

import gradio as gr


def build_static_review_interface():
    with gr.Blocks(title='정적 검수 화면') as interface_blocks_value:
        gr.Markdown('## 검수 화면\n등록된 검수 스냅샷을 현재 관리도구 탐색과 함께 표시합니다.')
        gr.HTML('''<iframe title="정적 검수 화면" id="static-review-frame" class="static-review-frame"></iframe>
<script>(function(){const selectedPathValue=new URLSearchParams(window.location.search).get('path')||'';const selectedPathSegments=selectedPathValue.split('?')[0].split('/');if(!selectedPathValue.startsWith('/')||selectedPathValue.startsWith('//')||selectedPathSegments.includes('..')){document.querySelector('#static-review-frame').replaceWith(Object.assign(document.createElement('p'),{textContent:'허용되지 않은 검수 화면 경로입니다.'}));return;}document.querySelector('#static-review-frame').src=selectedPathValue;})();</script>''')
    return interface_blocks_value


if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/static-review/')
    argument_values = argument_parser_value.parse_args()
    threading.Thread(target=lambda: time.sleep(1), daemon=True).start()
    build_static_review_interface().queue().launch(
        server_name='127.0.0.1', server_port=argument_values.port, root_path=argument_values.root_path,
        css='.static-review-frame{width:100%;height:calc(100vh - 190px);min-height:700px;border:0}', allowed_paths=[])
