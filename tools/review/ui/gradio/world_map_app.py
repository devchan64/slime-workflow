"""표준 Gradio 조작과 SVG 월드맵을 직접 합성하는 읽기 전용 검수 화면."""
import argparse
import html
import sys
from pathlib import Path
from urllib.parse import quote
import gradio as gr

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path: sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.domains.world_map.catalog import load_world_review_catalog

WORLD_REVIEW_CELL_WIDTH = 190
WORLD_REVIEW_CELL_HEIGHT = 210
WORLD_REVIEW_IMAGE_SIZE = 128
WORLD_REVIEW_NODE_WIDTH = 160
WORLD_REVIEW_NODE_HEIGHT = 184


def render_world_review_graph(current_world_catalog,current_selected_identifier):
    current_world_nodes = current_world_catalog['maps']
    current_minimum_column = min(current_world_node['column'] for current_world_node in current_world_nodes)
    current_minimum_row = min(current_world_node['row'] for current_world_node in current_world_nodes)
    current_canvas_width = (max(current_world_node['column'] for current_world_node in current_world_nodes)-current_minimum_column+1)*WORLD_REVIEW_CELL_WIDTH
    current_canvas_height = (max(current_world_node['row'] for current_world_node in current_world_nodes)-current_minimum_row+1)*WORLD_REVIEW_CELL_HEIGHT
    current_node_positions = {current_world_node['id']:((current_world_node['column']-current_minimum_column+.5)*WORLD_REVIEW_CELL_WIDTH,(current_world_node['row']-current_minimum_row+.5)*WORLD_REVIEW_CELL_HEIGHT) for current_world_node in current_world_nodes}
    current_svg_fragments = [f'<div id="world-review-scroll" style="overflow:auto;max-height:65vh" tabindex="0" aria-label="월드맵 스크롤"><svg id="world-review-graph" role="img" aria-label="전체 맵과 이동 연결" width="{current_canvas_width}" height="{current_canvas_height}" viewBox="0 0 {current_canvas_width} {current_canvas_height}">']
    for current_world_node in current_world_nodes:
        current_source_x,current_source_y = current_node_positions[current_world_node['id']]
        for current_world_link in current_world_node['connections']:
            if current_world_node['id'] < current_world_link['target']:
                current_target_x,current_target_y = current_node_positions[current_world_link['target']]
                current_svg_fragments.append(f'<line x1="{current_source_x}" y1="{current_source_y}" x2="{current_target_x}" y2="{current_target_y}" stroke="currentColor" stroke-width="2"/>')
    for current_world_node in current_world_nodes:
        current_node_x,current_node_y = current_node_positions[current_world_node['id']]
        current_map_label = html.escape(current_world_node['name'])
        current_map_kind = '도시' if current_world_node['safeTown'] else '필드'
        current_selected_suffix = ' · 선택' if current_world_node['id']==current_selected_identifier else ''
        current_image_url = html.escape(current_world_node['thumbnail']['url'],quote=True)
        current_map_link = '?tool=world-map&category=map-review&map='+quote(current_world_node['id'])
        current_svg_fragments.append(f'<a href="{html.escape(current_map_link,quote=True)}" aria-label="{current_map_label} 선택"><title>{current_map_label} · {current_map_kind}{current_selected_suffix}</title><image href="{current_image_url}" x="{current_node_x-WORLD_REVIEW_IMAGE_SIZE/2}" y="{current_node_y-WORLD_REVIEW_NODE_HEIGHT/2}" width="{WORLD_REVIEW_IMAGE_SIZE}" height="{WORLD_REVIEW_IMAGE_SIZE}"/><text x="{current_node_x}" y="{current_node_y+56}" text-anchor="middle" fill="currentColor">{current_map_label}</text><text x="{current_node_x}" y="{current_node_y+78}" text-anchor="middle" fill="currentColor">{current_map_kind}{current_selected_suffix}</text></a>')
    current_svg_fragments.append('</svg></div>')
    return ''.join(current_svg_fragments)


def load_world_review_selection(current_selected_identifier,request:gr.Request):
    try:
        current_world_catalog = load_world_review_catalog()
        current_world_lookup = {current_world_node['id']:current_world_node for current_world_node in current_world_catalog['maps']}
        current_selected_identifier = current_selected_identifier or request.query_params.get('map') or next(iter(current_world_lookup))
        if current_selected_identifier not in current_world_lookup: raise ValueError('등록되지 않은 맵 선택입니다.')
        current_selected_node = current_world_lookup[current_selected_identifier]
        current_thumbnail_record = current_selected_node['thumbnail']
        current_edge_count = sum(len(current_world_node['connections']) for current_world_node in current_world_catalog['maps'])//2
        current_image_markup = f'<img src="{html.escape(current_thumbnail_record["url"],quote=True)}" alt="{html.escape(current_selected_node["name"],quote=True)}" width="256" height="256" style="max-width:100%;height:auto"/>'
        current_detail_text = f"{current_selected_node['name']} · {'도시' if current_selected_node['safeTown'] else '필드'}\n\n썸네일: `{current_thumbnail_record['managementId']}` · `{current_thumbnail_record['version']}`\n\nSHA-256: `{current_thumbnail_record['sha256']}`\n\n원본: `{current_thumbnail_record['path']}`"
        current_connection_rows = [[current_world_lookup[current_world_link['target']]['name'],current_world_link['direction'],current_world_link['id'],current_world_link['targetWaypointId']] for current_world_link in current_selected_node['connections']]
        return (gr.update(choices=[(current_world_node['name'],current_world_node['id']) for current_world_node in current_world_catalog['maps']],value=current_selected_identifier,interactive=True),f'검증 통과 · 맵 {len(current_world_lookup)}개 · 연결 {current_edge_count}개 · 썸네일 누락 0 · 해시·방향·상대 웨이포인트·고립 검사 통과',render_world_review_graph(current_world_catalog,current_selected_identifier),current_image_markup,current_detail_text,current_connection_rows,gr.update(interactive=True),gr.update(interactive=True),gr.update(interactive=True))
    except (ValueError,OSError,KeyError,TypeError) as current_load_error:
        return (gr.update(interactive=False),f'불러오기 실패: {current_load_error}. 에셋 원본·등록부를 수정한 뒤 다시 불러오세요.','','','',[],gr.update(interactive=False),gr.update(interactive=False),gr.update(interactive=False))


def build_world_review_interface(review_server_port):
    with gr.Blocks(title='월드맵 검수') as current_interface_blocks:
        gr.Markdown('## 월드맵 검수\n등록된 맵 원본의 연결과 1:1 특징 썸네일을 확인합니다. 썸네일은 실제 맵 배치도가 아닙니다.')
        with gr.Row():
            current_map_selector = gr.Dropdown(label='맵 선택',choices=[],interactive=False)
            current_reload_button = gr.Button('원본 다시 불러오기')
        current_status_message = gr.Markdown('원본을 불러오는 중입니다. 준비가 끝나면 선택·확대·축소를 사용할 수 있습니다.')
        with gr.Row():
            current_zoom_out_button = gr.Button('축소',interactive=False)
            current_zoom_in_button = gr.Button('확대',interactive=False)
            current_fit_map_button = gr.Button('전체 보기',interactive=False)
        current_graph_preview = gr.HTML()
        with gr.Row():
            current_image_preview = gr.HTML()
            current_detail_preview = gr.Markdown()
        current_connection_table = gr.Dataframe(headers=['연결 맵','방향','출발 웨이포인트','도착 웨이포인트'],datatype=['str']*4,interactive=False,label='선택 맵의 이동 연결')
        current_output_components = [current_map_selector,current_status_message,current_graph_preview,current_image_preview,current_detail_preview,current_connection_table,current_zoom_out_button,current_zoom_in_button,current_fit_map_button]
        current_interface_blocks.load(load_world_review_selection,inputs=current_map_selector,outputs=current_output_components)
        current_reload_button.click(load_world_review_selection,inputs=current_map_selector,outputs=current_output_components)
        current_map_selector.input(load_world_review_selection,inputs=current_map_selector,outputs=current_output_components)
        for current_zoom_button,current_zoom_factor in ((current_zoom_out_button,.8),(current_zoom_in_button,1.25),(current_fit_map_button,0)):
            current_zoom_button.click(fn=None,queue=False,js=f"""()=>{{const currentWorldGraph=document.getElementById('world-review-graph'),currentWorldScroll=document.getElementById('world-review-scroll');if(!currentWorldGraph||!currentWorldScroll)return;const currentGraphBounds=currentWorldGraph.viewBox.baseVal;const currentZoomValue={current_zoom_factor}===0?Math.min(1,currentWorldScroll.clientWidth/currentGraphBounds.width,currentWorldScroll.clientHeight/currentGraphBounds.height):Math.max(.1,Math.min(2,Number(currentWorldGraph.getAttribute('width'))/currentGraphBounds.width*{current_zoom_factor}));currentWorldGraph.setAttribute('width',currentGraphBounds.width*currentZoomValue);currentWorldGraph.setAttribute('height',currentGraphBounds.height*currentZoomValue);}}""")
    return current_interface_blocks


if __name__=='__main__':
    from tools.review.ui.gradio.management_menu_app import compose_management_interface
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/world-map/')
    current_argument_values = current_argument_parser.parse_args()
    compose_management_interface(build_world_review_interface(current_argument_values.review_port),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
