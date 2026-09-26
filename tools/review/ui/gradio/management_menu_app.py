"""기존 관리 화면을 연결하는 Gradio 메뉴 클라이언트."""
import argparse
import html
import json
import os
from pathlib import Path
import threading
import time

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
CATEGORY_LABEL_VALUES={'all':'전체','writer-agent':'작가 AI 에이전트','image-generation':'이미지 생성','animation':'등록 애니메이션','animation-tool':'애니메이션 도구','tile-review':'타일맵 검수','game-ui':'게임 UI · 디자인 시스템'}
DEFAULT_PAGE_RECORDS=(
    {'id':'tile-map-generator','label':'타일 에셋 생성기','path':'/tile-map-generator/','category':'tile-review','description':'지붕 · 벽 · 맵 타일 에셋 생성'},
    {'id':'writer-agent','label':'작가 AI 에이전트','path':'/writer-agent/','category':'writer-agent','description':'문서 학습 · 아이디어 작성 · 실행 기록'},
    {'id':'three-reference-generator','label':'Qwen 2511 3참조 생성','path':'/image-generation-2511/','category':'image-generation','description':'참조 이미지 3장 · 프롬프트 · 결과 비교'},
    {'id':'image-generator','label':'Qwen 2512 이미지 생성','path':'/image-generation/','category':'image-generation','description':'프롬프트로 이미지 생성 · 실행 상태 · 결과 다운로드'},
)

def load_manager_page_records(source_file_path):
    source_record_values=json.loads(source_file_path.read_text())
    page_record_values=source_record_values.get('pages',[])
    if not isinstance(page_record_values,list):raise ValueError('관리 메뉴 페이지 목록 형식 오류')
    page_identifier_values=set()
    validated_page_records=[]
    for current_page_record in [*page_record_values,*DEFAULT_PAGE_RECORDS]:
        if not isinstance(current_page_record,dict) or not all(isinstance(current_page_record.get(current_field_name),str) for current_field_name in ('id','label','path','category','description')):raise ValueError('관리 메뉴 페이지 항목 형식 오류')
        if current_page_record['id'] in page_identifier_values:continue
        if not current_page_record['path'].startswith('/'):current_page_record={**current_page_record,'path':'/'+current_page_record['path']}
        page_identifier_values.add(current_page_record['id'])
        validated_page_records.append(current_page_record)
    return validated_page_records

def filter_manager_page_records(page_record_values, search_text_value, category_name_value, ui_mode_name_value):
    search_token_values=search_text_value.casefold().split()
    return [current_page_record for current_page_record in page_record_values if (category_name_value=='all' or current_page_record['category']==category_name_value) and (ui_mode_name_value=='all' or (ui_mode_name_value=='gradio')==((current_page_record.get('uiMode')=='gradio'))) and all(current_search_token in f"{current_page_record['label']} {current_page_record['description']} {current_page_record['id']}".casefold() for current_search_token in search_token_values)]

def create_page_preview_html(selected_page_identifier, page_record_values, review_server_port):
    selected_page_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==selected_page_identifier),None)
    if selected_page_record is None:return '<div class="menu-empty-state">표시할 관리 화면을 선택하세요.</div>'
    selected_page_path=html.escape(selected_page_record['path'],quote=True)
    return f'<iframe title="{html.escape(selected_page_record["label"],quote=True)}" class="management-page-frame" src="http://127.0.0.1:{review_server_port}{selected_page_path}"></iframe>'

def build_management_menu_interface(page_record_values, review_server_port):
    initial_page_identifier=page_record_values[0]['id'] if page_record_values else ''
    with gr.Blocks(title='SLIME 관리도구') as interface_blocks_value:
        gr.Markdown('## SLIME 관리도구\n생성기와 검수 도구를 검색해 열고, 전환된 Gradio 화면만 따로 확인할 수 있습니다.')
        with gr.Row():
            search_text_value=gr.Textbox(label='검색',placeholder='이름, ID, 검수 종류')
            category_select_value=gr.Dropdown(choices=[(current_label_value,current_name_value) for current_name_value,current_label_value in CATEGORY_LABEL_VALUES.items()],value='all',label='분류')
            ui_mode_select_value=gr.Dropdown(choices=[('전체','all'),('Gradio 전환 완료','gradio'),('기존 화면','html')],value='all',label='화면 방식')
        page_select_value=gr.Radio(choices=[(current_page_record['label'],current_page_record['id']) for current_page_record in page_record_values],value=initial_page_identifier,label='관리 메뉴')
        with gr.Row():
            previous_page_button_value=gr.Button('← 이전')
            navigation_position_value=gr.Markdown(f'1 / {len(page_record_values)}')
            next_page_button_value=gr.Button('다음 →')
        selected_page_status_value=gr.Markdown(f"**{html.escape(page_record_values[0]['label'])}** · {html.escape(page_record_values[0]['description'])}" if page_record_values else '표시할 관리 화면이 없습니다.')
        page_preview_value=gr.HTML(create_page_preview_html(initial_page_identifier,page_record_values,review_server_port))
        def update_menu_choices(search_text_value,category_name_value,ui_mode_name_value,selected_page_identifier):
            filtered_page_records=filter_manager_page_records(page_record_values,search_text_value or '',category_name_value,ui_mode_name_value)
            filtered_identifier_values=[current_page_record['id'] for current_page_record in filtered_page_records]
            retained_identifier_value=selected_page_identifier if selected_page_identifier in filtered_identifier_values else (filtered_identifier_values[0] if filtered_identifier_values else None)
            selected_position_value=(filtered_identifier_values.index(retained_identifier_value)+1) if retained_identifier_value else 0
            return gr.update(choices=[(current_page_record['label'],current_page_record['id']) for current_page_record in filtered_page_records],value=retained_identifier_value),f'**{len(filtered_page_records)}개** 항목 · 전체 {len(page_record_values)}개',create_page_preview_html(retained_identifier_value,page_record_values,review_server_port),f'{selected_position_value} / {len(filtered_page_records)}'
        def select_menu_page(selected_page_identifier):
            selected_page_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==selected_page_identifier),None)
            if selected_page_record is None:return '표시할 관리 화면을 선택하세요.','<div class="menu-empty-state">검색 조건을 바꾸거나 메뉴를 선택하세요.</div>'
            return f"**{html.escape(selected_page_record['label'])}** · {html.escape(selected_page_record['description'])}",create_page_preview_html(selected_page_identifier,page_record_values,review_server_port)
        def move_menu_page(selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value,selection_step_value):
            filtered_page_records=filter_manager_page_records(page_record_values,search_text_value or '',category_name_value,ui_mode_name_value)
            filtered_identifier_values=[current_page_record['id'] for current_page_record in filtered_page_records]
            current_index_value=filtered_identifier_values.index(selected_page_identifier) if selected_page_identifier in filtered_identifier_values else 0
            next_index_value=max(0,min(len(filtered_identifier_values)-1,current_index_value+selection_step_value)) if filtered_identifier_values else 0
            next_identifier_value=filtered_identifier_values[next_index_value] if filtered_identifier_values else None
            next_status_text,next_preview_html=select_menu_page(next_identifier_value)
            return next_identifier_value,next_status_text,next_preview_html,f'{next_index_value+1 if next_identifier_value else 0} / {len(filtered_identifier_values)}'
        for current_filter_component in (search_text_value,category_select_value,ui_mode_select_value):current_filter_component.change(update_menu_choices,[search_text_value,category_select_value,ui_mode_select_value,page_select_value],[page_select_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
        page_select_value.change(select_menu_page,page_select_value,[selected_page_status_value,page_preview_value],queue=False)
        page_select_value.change(lambda selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value: move_menu_page(selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value,0)[3],[page_select_value,search_text_value,category_select_value,ui_mode_select_value],navigation_position_value,queue=False)
        previous_page_button_value.click(lambda selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value: move_menu_page(selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value,-1),[page_select_value,search_text_value,category_select_value,ui_mode_select_value],[page_select_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
        next_page_button_value.click(lambda selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value: move_menu_page(selected_page_identifier,search_text_value,category_name_value,ui_mode_name_value,1),[page_select_value,search_text_value,category_select_value,ui_mode_select_value],[page_select_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
    return interface_blocks_value

if __name__=='__main__':
    argument_parser_value=argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--source-file',type=Path,required=True)
    parsed_argument_values=argument_parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==parsed_argument_values.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    application_css_text='''.gradio-container{max-width:1560px!important;padding:16px!important}.management-page-frame{width:100%;height:calc(100vh - 290px);min-height:560px;border:1px solid #314055;border-radius:12px;background:#10151f}.menu-empty-state{min-height:320px;display:grid;place-items:center;border:1px dashed #40516a;border-radius:12px;color:#a7b5c8}@media(max-width:800px){.management-page-frame{height:70vh;min-height:460px}}'''
    build_management_menu_interface(load_manager_page_records(parsed_argument_values.source_file),parsed_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,theme=gr.themes.Soft(),css=application_css_text,allowed_paths=[])
