"""ANNY 속성 렌더러를 Gradio 내부 사용자 정의 구성 요소로 제공한다."""
import argparse
import json
import re
import threading
import time
from pathlib import Path

import gradio as gr


WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
ANNY_ATTRIBUTE_PAGE_PATH=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/anny/anny-attributes.html'
ANNY_ATTRIBUTE_STYLE_PATH=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/anny/anny-attributes.css'


def read_anny_attribute_markup():
    attribute_page_text=ANNY_ATTRIBUTE_PAGE_PATH.read_text()
    main_markup_match=re.search(r'(<main>.*?</main>\s*<dialog.*?</dialog>)',attribute_page_text,re.DOTALL)
    if main_markup_match is None:raise ValueError('ANNY 속성 편집기 본문을 찾을 수 없습니다.')
    return '<div id="anny-attribute-root">'+main_markup_match.group(1)+'</div>'


def read_anny_attribute_script():
    attribute_page_text=ANNY_ATTRIBUTE_PAGE_PATH.read_text()
    inline_script_match=re.search(r'<script>\s*(const attributeLogViewer=.*?)</script>',attribute_page_text,re.DOTALL)
    if inline_script_match is None:raise ValueError('ANNY 속성 편집기 스크립트를 찾을 수 없습니다.')
    return inline_script_match.group(1)


def create_anny_attribute_loader(review_server_port):
    inline_script_text=json.dumps(read_anny_attribute_script()).replace('<','\\u003c')
    review_server_base=f'http://127.0.0.1:{review_server_port}'
    return f"""async()=>{{if(document.querySelector('script[data-anny-attribute-component]'))return;const componentScriptText={inline_script_text};const loadComponentScript=currentPathValue=>new Promise((resolve,reject)=>{{const nextScriptElement=document.createElement('script');nextScriptElement.src='{review_server_base}'+currentPathValue;nextScriptElement.dataset.annyAttributeComponent='true';nextScriptElement.onload=resolve;nextScriptElement.onerror=()=>reject(new Error('ANNY 구성 요소를 불러오지 못했습니다: '+currentPathValue));document.body.append(nextScriptElement);}});await loadComponentScript('/anny-attributes/log-viewer.js');await loadComponentScript('/anny-attributes/mesh-viewer.js');const inlineScriptElement=document.createElement('script');inlineScriptElement.dataset.annyAttributeComponent='true';inlineScriptElement.textContent=componentScriptText;document.body.append(inlineScriptElement);await loadComponentScript('/anny-attributes/history-ui.js');await loadComponentScript('/management/workflow-ui.js');}}"""


def build_anny_attribute_interface(review_server_port):
    with gr.Blocks(title='Anny 속성 렌더러') as interface_blocks_value:
        gr.Markdown('## Anny 속성 렌더러\nGradio 작업 영역에서 체형 설정, 3D 프리뷰, 렌더 결과와 생성 이력을 관리합니다.')
        gr.HTML(read_anny_attribute_markup())
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
        css=ANNY_ATTRIBUTE_STYLE_PATH.read_text(), js=create_anny_attribute_loader(argument_values.review_port), allowed_paths=[])
