"""Gradio 안에서 브라우저 기반 v2 편집기를 제공한다."""
import argparse
import re
import sys
from pathlib import Path
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.ui_assets import resolve_review_ui_asset, read_review_shared_styles


def build_sprite_v2_interface():
    current_markup_text=resolve_review_ui_asset('sprite-editor-v2.html').read_text()
    with gr.Blocks(title='스프라이트 정규화 편집기 v2') as current_interface_blocks:
        gr.HTML(re.sub(r'<style>.*?</style>','',current_markup_text,flags=re.S))
    return current_interface_blocks


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/sprite-editor-v2/')
    current_argument_values=current_argument_parser.parse_args()
    current_markup_text=resolve_review_ui_asset('sprite-editor-v2.html').read_text()
    current_style_text=re.search(r'<style>(.*?)</style>',current_markup_text,re.S).group(1)
    current_style_text+=(Path(__file__).parents[1]/'shared/management-density.css').read_text()
    current_loader_script=f"""()=>{{if(document.querySelector('script[data-sprite-v2]'))return;window.spriteV2ServerBase='http://127.0.0.1:{current_argument_values.review_port}';const currentScriptElement=document.createElement('script');currentScriptElement.dataset.spriteV2='true';currentScriptElement.src=window.spriteV2ServerBase+'/character-animation/sprite-editor-v2.js';document.body.append(currentScriptElement);}}"""
    build_sprite_v2_interface().queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,css=read_review_shared_styles()+current_style_text,js=current_loader_script,allowed_paths=[])
