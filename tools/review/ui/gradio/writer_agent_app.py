"""작가 AI 에이전트 기존 관리 화면을 Gradio 작업 영역에 연결한다."""
import argparse
import re
import threading
import time
from pathlib import Path

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]

def read_writer_agent_markup():
    manager_source_text=(WORKFLOW_ROOT_DIRECTORY/'generators/writer_agent/manager.html').read_text()
    manager_markup_match=re.search(r'<main>(.*)</main>',manager_source_text,re.DOTALL)
    if manager_markup_match is None:raise ValueError('작가 에이전트 본문을 찾을 수 없습니다.')
    return '<main id="writer-agent-root">'+manager_markup_match.group(1)+'</main>'

def create_writer_agent_loader(review_server_port):
    return f"""()=>{{window.writerAgentServerBase='http://127.0.0.1:{review_server_port}';const currentScriptElement=document.querySelector('script[data-writer-agent-component]');if(currentScriptElement)return;const nextScriptElement=document.createElement('script');nextScriptElement.src=window.writerAgentServerBase+'/writer-agent/manager.js';nextScriptElement.dataset.writerAgentComponent='true';document.body.append(nextScriptElement);}}"""

def build_writer_agent_interface(review_server_port):
    with gr.Blocks(title='작가 AI 에이전트') as interface_blocks_value:
        gr.Markdown('## 작가 AI 에이전트\nGradio 작업 영역에서 문서 학습, 작성 제안, 검토 적용과 실행 기록을 관리합니다.')
        gr.HTML(read_writer_agent_markup())
    return interface_blocks_value


from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()

if __name__=='__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/writer-agent/')
    argument_values = argument_parser_value.parse_args()
    threading.Thread(target=lambda: time.sleep(1), daemon=True).start()
    build_writer_agent_interface(argument_values.review_port).queue().launch(
        server_name='127.0.0.1', server_port=argument_values.port, root_path=argument_values.root_path,
        css='#writer-agent-root{max-width:1100px}#writer-agent-root section{margin:20px 0}#writer-agent-root .actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}#writer-agent-root pre{max-height:480px;overflow:auto}#writer-agent-root .path{overflow-wrap:anywhere}'+MANAGEMENT_DENSITY_STYLES, js=create_writer_agent_loader(argument_values.review_port), allowed_paths=[])
