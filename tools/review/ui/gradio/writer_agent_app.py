"""작가 AI 에이전트 기존 관리 화면을 Gradio 작업 영역에 연결한다."""
import argparse
import threading
import time

import gradio as gr


def build_writer_agent_interface(review_server_port):
    with gr.Blocks(title='작가 AI 에이전트') as interface_blocks_value:
        gr.Markdown('## 작가 AI 에이전트\n문서 학습, 작성 제안, 검토 적용 및 실행 기록은 기존 작업 서비스와 저장소를 사용합니다.')
        gr.HTML(f'<iframe title="작가 AI 에이전트" class="writer-agent-frame" src="http://127.0.0.1:{review_server_port}/writer-agent/embedded/"></iframe>')
    return interface_blocks_value


if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/writer-agent/')
    argument_values = argument_parser_value.parse_args()
    threading.Thread(target=lambda: time.sleep(1), daemon=True).start()
    build_writer_agent_interface(argument_values.review_port).queue().launch(
        server_name='127.0.0.1', server_port=argument_values.port, root_path=argument_values.root_path,
        css='.writer-agent-frame{width:100%;height:calc(100vh - 190px);min-height:700px;border:0}', allowed_paths=[])
