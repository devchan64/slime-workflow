"""기존 마을 맵 검수 캔버스를 Gradio 작업 영역에 연결한다."""
import argparse
import os
import threading
import time
import gradio as gr

def build_map_review_interface(review_server_port):
    with gr.Blocks(title='마을 맵 검수') as interface_blocks_value:
        gr.Markdown('## 마을 맵 검수\n기존 캔버스 검수 도구의 회전·선택·마커 기능을 그대로 사용합니다.')
        gr.HTML(f'<iframe title="마을 맵 검수" class="map-review-frame" src="http://127.0.0.1:{review_server_port}/isloon-map-review/map-review.html"></iframe>')
    return interface_blocks_value

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/map-review/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start();build_map_review_interface(arguments_value.review_port).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css='.map-review-frame{width:100%;height:calc(100vh - 190px);min-height:700px;border:0}',allowed_paths=[])
