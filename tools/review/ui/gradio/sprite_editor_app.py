"""기존 브라우저 프레임 편집기를 Gradio 작업 영역에 연결한다."""
import argparse
import re
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.ui_assets import resolve_review_ui_asset, read_review_shared_styles

def read_sprite_editor_styles():
    editor_source_text=resolve_review_ui_asset('sprite-editor.html').read_text()
    editor_style_match=re.search(r'<style>(.*?)</style>',editor_source_text,re.DOTALL)
    if editor_style_match is None:raise ValueError('스프라이트 편집기 스타일을 찾을 수 없습니다.')
    return read_review_shared_styles()+editor_style_match.group(1)+MANAGEMENT_DENSITY_STYLES

def read_sprite_editor_markup():
    editor_source_text=resolve_review_ui_asset('sprite-editor.html').read_text()
    editor_markup_match=re.search(r'<main>(.*)</main>',editor_source_text,re.DOTALL)
    if editor_markup_match is None:raise ValueError('스프라이트 편집기 본문을 찾을 수 없습니다.')
    return '<main id="sprite-editor-root">'+editor_markup_match.group(1)+'</main>'

def create_sprite_editor_loader(review_server_port):
    return f"""()=>{{window.spriteEditorServerBase='http://127.0.0.1:{review_server_port}';const currentScriptElement=document.querySelector('script[data-sprite-editor-component]');if(currentScriptElement)return;const nextScriptElement=document.createElement('script');nextScriptElement.src=window.spriteEditorServerBase+'/character-animation/sprite-editor.js';nextScriptElement.dataset.spriteEditorComponent='true';document.body.append(nextScriptElement);}}"""

def build_sprite_editor_interface(review_server_port):
    with gr.Blocks(title='스프라이트 정규화 편집기') as interface_blocks_value:
        gr.HTML(read_sprite_editor_markup())
    return interface_blocks_value

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/sprite-editor/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start()
    build_sprite_editor_interface(arguments_value.review_port).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css=read_sprite_editor_styles(),js=create_sprite_editor_loader(arguments_value.review_port),allowed_paths=[])
