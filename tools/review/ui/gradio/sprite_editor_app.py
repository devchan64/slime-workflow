"""기존 브라우저 프레임 편집기를 Gradio 작업 영역에 연결한다."""
import argparse
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))

def build_sprite_editor_interface(review_server_port):
    with gr.Blocks(title='스프라이트 정규화 편집기') as interface_blocks_value:
        gr.Markdown('## 스프라이트 정규화 편집기\n재생·프레임 이동·좌표 편집은 브라우저에서 처리하며 원본 편집 기능과 저장 계약을 유지합니다.')
        gr.HTML(f'<iframe title="스프라이트 정규화 편집기" class="sprite-editor-frame" src="http://127.0.0.1:{review_server_port}/character-animation/sprite-editor"></iframe>')
    return interface_blocks_value

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/sprite-editor/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start()
    build_sprite_editor_interface(arguments_value.review_port).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css='.sprite-editor-frame{width:100%;height:calc(100vh - 190px);min-height:700px;border:0}',allowed_paths=[])
