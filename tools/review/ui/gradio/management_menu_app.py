"""기존 관리 화면을 연결하는 Gradio 메뉴 클라이언트."""
import argparse
import html
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.parse import quote

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gpu_status import read_gpu_status

CATEGORY_LABEL_VALUES={'all':'전체','writer-agent':'작가 AI 에이전트','image-generation':'이미지 생성','animation':'등록 애니메이션','animation-tool':'애니메이션 도구','town-map-review':'마을맵 검수','field-map-review':'필드맵 검수','game-ui':'게임 UI · 디자인 시스템'}
MANAGEMENT_FRAME_PATH_PREFIX='/management/frame/'
MANAGEMENT_FRAME_IDENTIFIER_VALUES={'anny-attribute-renderer':'anny-attributes'}
LEGACY_PAGE_IDENTIFIER_VALUES={'map-review':'map-review-iseulon','animation-2':'animation-1','animation-3':'animation-1'}
DEFAULT_PAGE_RECORDS=(
    {'id':'animation-separation','label':'캐릭터 레퍼런스 복장 분리 생성','path':'/animation-separation/','category':'animation-tool','uiMode':'gradio','description':'Qwen 2.1 · 원본 1프레임 선택 · 신체 베이스·복장 별도 이미지'},
    {'id':'qwen-21-generator','label':'Qwen 2.1 이미지 생성기','path':'/image-generation-21/','category':'image-generation','uiMode':'gradio','description':'입력 프롬프트 그대로 · 추가 문구 없음 · 참조 선택'},
    {'id':'seamless-tile-generator','label':'Qwen2.1 심리스 패턴 생성기','path':'/seamless-tile-generator/','category':'image-generation','uiMode':'gradio','description':'5단계 가로·세로 연결 · 검수 · 일시정지·재개'},
    {'id':'floor-tile-generator','label':'맵 타일 생성기','path':'/floor-tile-generator/','category':'image-generation','uiMode':'gradio','description':'512×512 · 4스텝 · 단일 이미지 생성'},
    {'id':'writer-agent','label':'작가 AI 에이전트','path':'/writer-agent/','category':'writer-agent','uiMode':'gradio','description':'Gradio · 문서 학습 · 아이디어 작성 · 실행 기록'},
    {'id':'expression-generator','label':'표정 생성기','path':'/expression-generator/','category':'image-generation','uiMode':'gradio','description':'Qwen 2511 · AU 표정 39종 · 참조 1~3장'},
)

def format_gpu_status(gpu_status_record):
    if gpu_status_record.get('status')=='busy':
        process_status_values=[]
        for current_process_record in gpu_status_record.get('processes',[]):
            identifier_text_value=current_process_record.get('id') or f"PID {current_process_record.get('pid','?')}"
            memory_text_value=f" · {current_process_record['memory_mib']} MiB" if current_process_record.get('memory_mib') is not None else ''
            process_status_values.append(f"{current_process_record.get('command','외부 GPU 작업')} · {identifier_text_value}{memory_text_value}")
        return 'GPU 사용 중 · '+' / '.join(process_status_values)
    if gpu_status_record.get('status')=='idle':return 'GPU · 실행 중인 연산 작업 없음'
    return 'GPU · 상태 확인 불가'


def render_gpu_status_card(gpu_status_record):
    memory_total_mib=gpu_status_record.get('memory_total_mib')
    memory_used_mib=gpu_status_record.get('memory_used_mib')
    memory_free_mib=gpu_status_record.get('memory_free_mib')
    memory_summary_text=''
    if all(isinstance(current_value,int) and current_value >= 0 for current_value in (memory_total_mib,memory_used_mib,memory_free_mib)):
        memory_summary_text=f'<span class="management-gpu-memory"><span>사용 <strong>{memory_used_mib:,} MiB</strong></span><span>여유 <strong>{memory_free_mib:,} MiB</strong></span><span>총 {memory_total_mib:,} MiB</span></span>'
    if gpu_status_record.get('status') == 'busy':
        status_kind_name = 'busy'
        status_title_text = 'GPU 사용 중'
        process_card_values=[]
        for process_record in gpu_status_record.get('processes',[]):
            process_name_text=html.escape(str(process_record.get('command','이름 없는 작업')))
            process_identifier_text=str(process_record.get('id',''))
            process_summary_text=html.escape(process_identifier_text[-8:]) if process_identifier_text else 'ID 없음'
            process_title_text=html.escape(f'{process_record.get("command","이름 없는 작업")} · {process_identifier_text}')
            memory_amount_text=html.escape(str(process_record.get('memory_mib','?')))
            process_card_values.append(f'<span class="management-gpu-process" title="{process_title_text}"><span class="management-gpu-process-name">{process_name_text}</span><span class="management-gpu-process-id">#{process_summary_text}</span><strong>{memory_amount_text} MiB</strong></span>')
        status_detail_text=f'<span class="management-gpu-process-list">{"".join(process_card_values)}</span>{memory_summary_text}'
    elif gpu_status_record.get('status') == 'idle':
        status_kind_name = 'idle'
        status_title_text = 'GPU 대기'
        status_detail_text = f'<span class="management-gpu-status-message">실행 중인 연산 작업 없음</span>{memory_summary_text}'
    else:
        status_kind_name = 'unavailable'
        status_title_text = 'GPU 상태 확인 필요'
        status_detail_text = '<span class="management-gpu-status-message">상태 조회 연결을 확인하세요.</span>'
    return f'<div class="management-gpu-status-card is-{status_kind_name}" role="status" aria-live="polite"><span class="management-gpu-status-indicator" aria-hidden="true"></span><strong>{html.escape(status_title_text)}</strong><span class="management-gpu-status-detail">{status_detail_text}</span></div>'

def load_manager_page_records(source_file_path):
    source_record_values=json.loads(source_file_path.read_text())
    page_record_values=source_record_values.get('pages',[])
    if not isinstance(page_record_values,list):raise ValueError('관리 메뉴 페이지 목록 형식 오류')
    page_identifier_values=set()
    validated_page_records=[]
    for current_page_record in [*page_record_values,*DEFAULT_PAGE_RECORDS]:
        if current_page_record.get('id') in ('three-reference-generator','image-generator'):continue
        if not isinstance(current_page_record,dict) or not all(isinstance(current_page_record.get(current_field_name),str) for current_field_name in ('id','label','path','category','description')):raise ValueError('관리 메뉴 페이지 항목 형식 오류')
        if any(current_page_record.get(current_field_name) is not None and not isinstance(current_page_record[current_field_name],str) for current_field_name in ('frameIdentifier','frameQuery')):raise ValueError('관리 메뉴 프레임 항목 형식 오류')
        if current_page_record['id']=='tile-map-generator':continue
        if current_page_record['id'].startswith('map-review-'):
            from tools.review.common.map_asset_sources import MAP_CITY_REVIEW_IDENTIFIERS
            current_map_identifier=current_page_record['id'].removeprefix('map-review-')
            current_review_category='town-map-review' if current_map_identifier in MAP_CITY_REVIEW_IDENTIFIERS else 'field-map-review'
            current_map_name=current_page_record['label'].split(' · ')[0]
            current_page_record={**current_page_record,'category':current_review_category,'label':current_map_name+' · '+CATEGORY_LABEL_VALUES[current_review_category]}
        if current_page_record['id']=='floor-tile-generator':
            current_page_record={**current_page_record,'label':'맵 타일 생성기','category':'image-generation','description':'512×512 · 4스텝 · 단일 이미지 생성'}
        if current_page_record['id'] in page_identifier_values:continue
        if not current_page_record['path'].startswith('/'):current_page_record={**current_page_record,'path':'/'+current_page_record['path']}
        page_identifier_values.add(current_page_record['id'])
        validated_page_records.append(current_page_record)
    return validated_page_records

def filter_manager_page_records(page_record_values, search_text_value, category_name_value):
    search_token_values=search_text_value.casefold().split()
    return [current_page_record for current_page_record in page_record_values if (category_name_value=='all' or current_page_record['category']==category_name_value) and all(current_search_token in f"{current_page_record['label']} {current_page_record['description']} {current_page_record['id']}".casefold() for current_search_token in search_token_values)]

def create_tool_choice_values(page_record_values):
    """분류를 함께 표시해 긴 도구 목록에서도 찾기 쉽게 만든다."""
    return [
        (f"{CATEGORY_LABEL_VALUES.get(current_page_record['category'],current_page_record['category'])} · {current_page_record['label'].split(' · ')[0] if current_page_record['id'].startswith('map-review-') else current_page_record['label']}",current_page_record['id'])
        for current_page_record in page_record_values
    ]

def create_page_preview_html(selected_page_identifier, page_record_values, review_server_port):
    selected_page_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==selected_page_identifier),None)
    if selected_page_record is None:return '<div class="menu-empty-state">표시할 관리 화면을 선택하세요.</div>'
    selected_page_path=selected_page_record['path']
    if selected_page_record.get('uiMode')=='gradio':
        frame_application_identifier=selected_page_record.get('frameIdentifier') or MANAGEMENT_FRAME_IDENTIFIER_VALUES.get(selected_page_record['id'],selected_page_record['id'])
        frame_query_value=selected_page_record.get('frameQuery')
        selected_page_path=f'{MANAGEMENT_FRAME_PATH_PREFIX}{frame_application_identifier}/'+(f'?{frame_query_value}' if frame_query_value else '')
    elif selected_page_record.get('uiMode')=='gradio-static':
        selected_page_path=f'{MANAGEMENT_FRAME_PATH_PREFIX}static-review/?review={quote(selected_page_record["id"],safe="")}'
    selected_page_path=html.escape(selected_page_path,quote=True)
    return f'<iframe title="{html.escape(selected_page_record["label"],quote=True)}" class="management-page-frame" allow="clipboard-write http://127.0.0.1:{review_server_port} http://127.0.0.1:{review_server_port+101}; clipboard-read http://127.0.0.1:{review_server_port} http://127.0.0.1:{review_server_port+101}" src="http://127.0.0.1:{review_server_port}{selected_page_path}"></iframe>'


def create_menu_navigation_script(page_record_values, history_method_name):
    """선택 도구와 탐색 필터를 하나의 공개 URL 상태로 동기화한다."""
    serialized_page_records=json.dumps(page_record_values,ensure_ascii=False).replace('<','\\u003c')
    return f"""(searchTextValue,categoryNameValue,selectedPageIdentifier)=>{{const pageRecords={serialized_page_records};const searchTokenValues=String(searchTextValue||'').toLocaleLowerCase().trim().split(/\\s+/).filter(Boolean);const filteredPageRecords=pageRecords.filter((pageRecord)=>{{const pageTextValue=`${{pageRecord.label}} ${{pageRecord.description}} ${{pageRecord.id}}`.toLocaleLowerCase();return(categoryNameValue==='all'||pageRecord.category===categoryNameValue)&&searchTokenValues.every((searchTokenValue)=>pageTextValue.includes(searchTokenValue));}});const selectedPageRecord=filteredPageRecords.find((pageRecord)=>pageRecord.id===selectedPageIdentifier)||filteredPageRecords[0];const nextUrlValue=new URL(window.top.location.href);if(selectedPageRecord){{nextUrlValue.pathname='/';nextUrlValue.searchParams.set('tool',selectedPageRecord.id);}}for(const [parameterName,parameterValue,defaultValue] of [['search',searchTextValue,''],['category',categoryNameValue,'all']]){{if(parameterValue&&parameterValue!==defaultValue)nextUrlValue.searchParams.set(parameterName,parameterValue);else nextUrlValue.searchParams.delete(parameterName);}}nextUrlValue.searchParams.delete('view');window.top.history.{history_method_name}({{managementTool:selectedPageRecord?.id||null,managementFilters:{{search:searchTextValue||'',category:categoryNameValue||'all'}}}},'',nextUrlValue.pathname+nextUrlValue.search+nextUrlValue.hash);}}"""


def create_initial_selection_script(page_record_values):
    serialized_page_records=json.dumps(page_record_values,ensure_ascii=False).replace('<','\\u003c')
    category_name_values=json.dumps(list(CATEGORY_LABEL_VALUES)).replace('<','\\u003c')
    return f"""()=>{{
        const pageRecords={serialized_page_records};
        const currentUrlValue=new URL(window.location.href);
        const requestedPageIdentifier=currentUrlValue.searchParams.get('tool');
        const resolvedPageIdentifier={json.dumps(LEGACY_PAGE_IDENTIFIER_VALUES)}[requestedPageIdentifier]||requestedPageIdentifier;
        const selectedPageRecord=pageRecords.find(record=>record.id===resolvedPageIdentifier)||pageRecords.find(record=>record.path===currentUrlValue.pathname)||pageRecords[0];
        if(!selectedPageRecord)return;
        // 초기 선택은 목록 인덱스가 아닌 도구 ID로 확정한다. 충돌 필터는 해제한다.
        const categoryValue=currentUrlValue.searchParams.get('category');
        if(currentUrlValue.pathname!=='/'||(categoryValue&&categoryValue!=='all'&&categoryValue!==selectedPageRecord.category)){{
            currentUrlValue.pathname='/';
            currentUrlValue.searchParams.set('tool',selectedPageRecord.id);
            currentUrlValue.searchParams.delete('category');
            currentUrlValue.searchParams.delete('search');
            window.location.replace(currentUrlValue.href);return;
        }}
        let attempts=0;
        const selectByIdentifier=()=>{{
            const selectedInput=[...document.querySelectorAll('#management-tool-list input')].find(input=>input.value===selectedPageRecord.id);
            if(selectedInput){{selectedInput.click();return;}}
            if(++attempts<40)window.setTimeout(selectByIdentifier,100);
        }};
        selectByIdentifier();
    }}"""


def build_management_menu_interface(page_record_values, review_server_port):
    initial_page_identifier=page_record_values[0]['id'] if page_record_values else ''
    initial_selection_script=create_initial_selection_script(page_record_values)
    with gr.Blocks(title='SLIME 관리도구') as interface_blocks_value:
        with gr.Row(elem_id='management-header'):
            gr.Markdown('## SLIME 관리도구',scale=3)
            gpu_status_value=gr.HTML(render_gpu_status_card({}),elem_id='management-gpu-status',scale=2)
        with gr.Row(elem_id='management-shell'):
            with gr.Column(scale=1,min_width=240,elem_id='management-sidebar'):
                gr.Markdown('### 도구 탐색')
                search_text_value=gr.Textbox(label='도구 검색',placeholder='이름, ID, 기능',info='검색 결과에서 도구를 선택하면 해당 주소로 이동합니다.',elem_id='management-tool-search')
                category_select_value=gr.Dropdown(choices=[(current_label_value,current_name_value) for current_name_value,current_label_value in sorted(CATEGORY_LABEL_VALUES.items(),key=lambda category_entry_value:(category_entry_value[0]!='all',category_entry_value[1]))],value='all',label='분류',elem_id='management-category-filter')
                tool_count_value=gr.Markdown(f'**{len(page_record_values)}개** 도구',elem_id='management-tool-count')
                page_select_value=gr.Radio(choices=create_tool_choice_values(page_record_values),value=initial_page_identifier,label='도구 목록',elem_id='management-tool-list')
                with gr.Row(elem_classes=['management-pagination']):
                    previous_page_button_value=gr.Button('← 이전',scale=0,min_width=0)
                    navigation_position_value=gr.Markdown(f'1 / {len(page_record_values)}',elem_classes=['management-pagination-position'])
                    next_page_button_value=gr.Button('다음 →',scale=0,min_width=0)
            with gr.Column(scale=3,min_width=520,elem_id='management-workspace'):
                selected_page_status_value=gr.Markdown(f"**{html.escape(page_record_values[0]['label'])}** · {html.escape(page_record_values[0]['description'])}" if page_record_values else '표시할 관리 화면이 없습니다.')
                page_preview_value=gr.HTML(create_page_preview_html(initial_page_identifier,page_record_values,review_server_port))
        def update_menu_choices(search_text_value,category_name_value,selected_page_identifier):
            filtered_page_records=filter_manager_page_records(page_record_values,search_text_value or '',category_name_value)
            filtered_identifier_values=[current_page_record['id'] for current_page_record in filtered_page_records]
            retained_identifier_value=selected_page_identifier if selected_page_identifier in filtered_identifier_values else (filtered_identifier_values[0] if filtered_identifier_values else None)
            selected_position_value=(filtered_identifier_values.index(retained_identifier_value)+1) if retained_identifier_value else 0
            selected_status_text,selected_preview_html=select_menu_page(retained_identifier_value)
            return gr.update(choices=create_tool_choice_values(filtered_page_records),value=retained_identifier_value),f'**{len(filtered_page_records)}개** 도구 · 전체 {len(page_record_values)}개',selected_status_text,selected_preview_html,f'{selected_position_value} / {len(filtered_identifier_values)}'
        def select_menu_page(selected_page_identifier):
            selected_page_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==selected_page_identifier),None)
            if selected_page_record is None:return '표시할 관리 화면을 선택하세요.','<div class="menu-empty-state">검색 조건을 바꾸거나 메뉴를 선택하세요.</div>'
            return f"**{html.escape(selected_page_record['label'])}** · {html.escape(selected_page_record['description'])}",create_page_preview_html(selected_page_identifier,page_record_values,review_server_port)
        def move_menu_page(selected_page_identifier,search_text_value,category_name_value,selection_step_value):
            filtered_page_records=filter_manager_page_records(page_record_values,search_text_value or '',category_name_value)
            filtered_identifier_values=[current_page_record['id'] for current_page_record in filtered_page_records]
            current_index_value=filtered_identifier_values.index(selected_page_identifier) if selected_page_identifier in filtered_identifier_values else 0
            next_index_value=max(0,min(len(filtered_identifier_values)-1,current_index_value+selection_step_value)) if filtered_identifier_values else 0
            next_identifier_value=filtered_identifier_values[next_index_value] if filtered_identifier_values else None
            next_status_text,next_preview_html=select_menu_page(next_identifier_value)
            return next_identifier_value,next_status_text,next_preview_html,f'{next_index_value+1 if next_identifier_value else 0} / {len(filtered_identifier_values)}'
        for current_filter_component in (search_text_value,category_select_value):current_filter_component.change(update_menu_choices,[search_text_value,category_select_value,page_select_value],[page_select_value,tool_count_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
        page_select_value.change(select_menu_page,page_select_value,[selected_page_status_value,page_preview_value],queue=False)
        filter_navigation_script=create_menu_navigation_script(page_record_values,'replaceState')
        page_navigation_script=create_menu_navigation_script(page_record_values,'pushState')
        for current_filter_component in (search_text_value,category_select_value):
            current_filter_component.input(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=filter_navigation_script,queue=False)
        page_select_value.input(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=page_navigation_script,queue=False)
        search_text_value.submit(lambda search_text_value,category_name_value: update_menu_choices(search_text_value,category_name_value,None),[search_text_value,category_select_value],[page_select_value,tool_count_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
        page_select_value.change(lambda selected_page_identifier,search_text_value,category_name_value: move_menu_page(selected_page_identifier,search_text_value,category_name_value,0)[3],[page_select_value,search_text_value,category_select_value],navigation_position_value,queue=False)
        previous_page_button_value.click(fn=None,js="()=>{const toolInputValues=[...document.querySelectorAll('#management-tool-list input')];const selectedIndexValue=toolInputValues.findIndex((currentInputValue)=>currentInputValue.checked);toolInputValues[Math.max(0,selectedIndexValue-1)]?.click();}",queue=False)
        next_page_button_value.click(fn=None,js="()=>{const toolInputValues=[...document.querySelectorAll('#management-tool-list input')];const selectedIndexValue=toolInputValues.findIndex((currentInputValue)=>currentInputValue.checked);toolInputValues[Math.min(toolInputValues.length-1,selectedIndexValue+1)]?.click();}",queue=False)
        interface_blocks_value.load(lambda:render_gpu_status_card(read_gpu_status()),outputs=gpu_status_value,queue=False)
        if hasattr(gr,'Timer'):gr.Timer(3).tick(lambda:render_gpu_status_card(read_gpu_status()),outputs=gpu_status_value,show_progress='hidden')
    return interface_blocks_value,initial_selection_script

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()

if __name__=='__main__':
    argument_parser_value=argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--source-file',type=Path,required=True)
    argument_parser_value.add_argument('--root-path',default='/management/')
    parsed_argument_values=argument_parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==parsed_argument_values.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    application_css_text=(Path(__file__).parents[1]/'shared/management.css').read_text()
    application_css_text+='''.gradio-container{max-width:1560px!important;padding:16px!important}#management-shell{align-items:stretch;min-height:calc(100vh - 132px)}#management-sidebar{position:sticky;top:12px;height:calc(100vh - 30px);overflow:hidden;display:flex;flex-direction:column;padding:12px;background:#192230;border:1px solid #314055;border-radius:12px}#management-sidebar>div{min-height:0}#management-tool-count{margin-top:4px;margin-bottom:2px;color:#b9cae2}#management-tool-list{flex:1;min-height:180px;overflow-y:auto;padding:6px 2px;border-top:1px solid #314055;border-bottom:1px solid #314055}#management-tool-list .wrap{display:flex;flex-direction:column;gap:4px}#management-tool-list label{padding:7px 8px;border-radius:7px;line-height:1.35}#management-tool-list label:hover{background:#26374d}#management-tool-list label:has(input:checked){background:#315482}.management-page-frame{width:100%;height:calc(100vh - 220px);min-height:560px;border:1px solid #314055;border-radius:12px;background:#10151f}.menu-empty-state{min-height:320px;display:grid;place-items:center;border:1px dashed #40516a;border-radius:12px;color:#a7b5c8}@media(max-width:800px){#management-shell{min-height:0}#management-sidebar{position:static;height:auto;max-height:none;overflow:visible}#management-tool-list{max-height:300px;flex:none}.management-page-frame{height:70vh;min-height:460px}}'''
    application_css_text+=(Path(__file__).parent/'management-layout.css').read_text()
    interface_blocks_value,initial_selection_script=build_management_menu_interface(load_manager_page_records(parsed_argument_values.source_file),parsed_argument_values.review_port)
    interface_blocks_value.queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,theme=gr.themes.Soft(),css=application_css_text+MANAGEMENT_DENSITY_STYLES,js=initial_selection_script,allowed_paths=[])
