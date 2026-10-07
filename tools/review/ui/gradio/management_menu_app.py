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
    {'id':'character-review','label':'캐릭터 표현 검수','path':'/management/frame/character-review/','category':'animation-tool','uiMode':'gradio','description':'3×3 검수 맵 · 바닥 선택 · 형태선·분리선·접지 그림자 비교'},
    {'id':'animation-separation','label':'캐릭터 레퍼런스 복장 분리 생성','path':'/animation-separation/','category':'image-generation','uiMode':'gradio','description':'Qwen 2.1 · 참조 이미지 1장 · 신체 베이스·복장 별도 이미지'},
    {'id':'qwen-21-circular-generator','label':'Qwen 2.1 순환 VAE 생성기','path':'/image-generation-21-circular/','category':'image-generation','uiMode':'gradio','description':'XY 순환 디코더 · 3×3 반복 검수'},
    {'id':'pose-transfer-generator','label':'포즈 변환 생성기 · Alpha Ver.','path':'/pose-transfer/','category':'animation-tool','uiMode':'gradio','description':'Alpha Ver. · Qwen 2.1 · 아이덴티티 1장 + 포즈 1장'},
    {'id':'outfit-transfer-generator','label':'복장 착용 생성기','path':'/outfit-transfer/','category':'image-generation','uiMode':'gradio','description':'Qwen 2.1 · 바디 1장 + 아웃핏 1장 · 신체 비율 유지'},
    {'id':'qwen-21-generator','label':'Qwen 2.1 이미지 생성기','path':'/image-generation-21/','category':'image-generation','uiMode':'gradio','description':'입력 프롬프트 그대로 · 추가 문구 없음 · 참조 선택'},
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
    """기본 Markdown으로 GPU 상태와 메모리를 표시한다."""
    current_status_text=format_gpu_status(gpu_status_record)
    current_memory_values=[gpu_status_record.get(current_field_name) for current_field_name in ('memory_used_mib','memory_free_mib','memory_total_mib')]
    if all(isinstance(current_memory_value,int) and current_memory_value>=0 for current_memory_value in current_memory_values):
        current_status_text+='\n\n'+ ' · '.join(f'{current_memory_label} {current_memory_value:,} MiB' for current_memory_label,current_memory_value in zip(('사용','여유','총'),current_memory_values))
    return current_status_text

def load_manager_page_records(source_file_path):
    source_record_values=json.loads(source_file_path.read_text())
    page_record_values=source_record_values.get('pages',[])
    if not isinstance(page_record_values,list):raise ValueError('관리 메뉴 페이지 목록 형식 오류')
    page_identifier_values=set()
    validated_page_records=[]
    for current_page_record in [*page_record_values,*DEFAULT_PAGE_RECORDS]:
        if current_page_record.get('id') in ('three-reference-generator','image-generator','floor-tile-generator','seamless-tile-generator'):continue
        if not isinstance(current_page_record,dict) or not all(isinstance(current_page_record.get(current_field_name),str) for current_field_name in ('id','label','path','category','description')):raise ValueError('관리 메뉴 페이지 항목 형식 오류')
        if any(current_page_record.get(current_field_name) is not None and not isinstance(current_page_record[current_field_name],str) for current_field_name in ('frameIdentifier','frameQuery')):raise ValueError('관리 메뉴 프레임 항목 형식 오류')
        if current_page_record['id']=='tile-map-generator':continue
        if current_page_record['id'].startswith('map-review-'):
            from tools.review.common.map_asset_sources import MAP_CITY_REVIEW_IDENTIFIERS
            current_map_identifier=current_page_record['id'].removeprefix('map-review-')
            current_review_category='town-map-review' if current_map_identifier in MAP_CITY_REVIEW_IDENTIFIERS else 'field-map-review'
            current_map_name=current_page_record['label'].split(' · ')[0]
            current_page_record={**current_page_record,'category':current_review_category,'label':current_map_name+' · '+CATEGORY_LABEL_VALUES[current_review_category]}
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
    return f'<iframe title="{html.escape(selected_page_record["label"],quote=True)}" class="management-page-frame" width="100%" height="1000" frameborder="0" allow="clipboard-write http://127.0.0.1:{review_server_port} http://127.0.0.1:{review_server_port+101}; clipboard-read http://127.0.0.1:{review_server_port} http://127.0.0.1:{review_server_port+101}" src="http://127.0.0.1:{review_server_port}{selected_page_path}"></iframe>'


def create_menu_navigation_script(page_record_values, history_method_name):
    """선택 도구와 탐색 필터를 하나의 공개 URL 상태로 동기화한다."""
    serialized_page_records=json.dumps(page_record_values,ensure_ascii=False).replace('<','\\u003c')
    return f"""(searchTextValue,categoryNameValue,selectedPageIdentifier)=>{{const pageRecords={serialized_page_records};const searchTokenValues=String(searchTextValue||'').toLocaleLowerCase().trim().split(/\\s+/).filter(Boolean);const filteredPageRecords=pageRecords.filter((pageRecord)=>{{const pageTextValue=`${{pageRecord.label}} ${{pageRecord.description}} ${{pageRecord.id}}`.toLocaleLowerCase();return(categoryNameValue==='all'||pageRecord.category===categoryNameValue)&&searchTokenValues.every((searchTokenValue)=>pageTextValue.includes(searchTokenValue));}});const selectedPageRecord=filteredPageRecords.find((pageRecord)=>pageRecord.id===selectedPageIdentifier)||filteredPageRecords[0];const nextUrlValue=new URL(window.top.location.href);if(selectedPageRecord){{nextUrlValue.pathname='/';nextUrlValue.searchParams.set('tool',selectedPageRecord.id);}}for(const [parameterName,parameterValue,defaultValue] of [['search',searchTextValue,''],['category',categoryNameValue,'all']]){{if(parameterValue&&parameterValue!==defaultValue)nextUrlValue.searchParams.set(parameterName,parameterValue);else nextUrlValue.searchParams.delete(parameterName);}}nextUrlValue.searchParams.delete('view');window.top.history.{history_method_name}({{managementTool:selectedPageRecord?.id||null,managementFilters:{{search:searchTextValue||'',category:categoryNameValue||'all'}}}},'',nextUrlValue.pathname+nextUrlValue.search+nextUrlValue.hash);}}"""


def create_initial_selection_script(page_record_values):
    """Gradio load 입력으로 URL 상태를 전달하고 DOM 클릭을 사용하지 않는다."""
    serialized_page_records=json.dumps(page_record_values,ensure_ascii=False).replace('<','\\u003c')
    return f"""()=>{{
        const pageRecords={serialized_page_records};
        const currentUrlValue=new URL(window.location.href);
        const requestedPageIdentifier=currentUrlValue.searchParams.get('tool');
        const resolvedPageIdentifier={json.dumps(LEGACY_PAGE_IDENTIFIER_VALUES)}[requestedPageIdentifier]||requestedPageIdentifier;
        const selectedPageRecord=pageRecords.find(record=>record.id===resolvedPageIdentifier)||pageRecords.find(record=>record.path===currentUrlValue.pathname)||pageRecords[0];
        return [currentUrlValue.searchParams.get('search')||'',currentUrlValue.searchParams.get('category')||'all',selectedPageRecord?.id||null];
    }}"""


MANAGEMENT_NAVIGATION_WIDTH = 320
MANAGEMENT_MOBILE_BREAKPOINT = 768
MANAGEMENT_FRAME_MIN_HEIGHT = 240
MANAGEMENT_FRAME_BOTTOM_GAP = 16


def create_sidebar_responsive_script():
    """Gradio 기본 슬라이딩 동작에 화면 폭 전환과 접근성 이름만 연결한다."""
    return """()=>{
        const currentMediaQuery=window.matchMedia('(max-width: BREAKPOINTpx)');
        const currentMinimumHeight=MINHEIGHT,currentBottomGap=BOTTOMGAP;
        let currentObservedFrame=null,currentContentObserver=null,currentContentMutations=null,currentResizePending=false;
        const resizeWorkspaceFrame=()=>{
            if(currentResizePending)return;
            currentResizePending=true;
            requestAnimationFrame(()=>{
                currentResizePending=false;
                const currentFrameElement=document.querySelector('.management-page-frame');
                if(!currentFrameElement)return;
                if(currentObservedFrame!==currentFrameElement){
                    currentContentObserver?.disconnect();currentContentMutations?.disconnect();
                    currentObservedFrame=currentFrameElement;
                    currentFrameElement.addEventListener('load',()=>{currentObservedFrame=null;resizeWorkspaceFrame();},{once:true});
                    const currentFrameDocument=currentFrameElement.contentDocument;
                    if(!currentFrameDocument?.body)return;
                    const currentContentRoot=currentFrameDocument.querySelector('.gradio-container')||currentFrameDocument.body;
                    const currentSizingStyle=currentFrameDocument.createElement('style');
                    currentSizingStyle.textContent='html,body,.gradio-container,.gradio-container>.main,.gradio-container>.main>.wrap,.gradio-container main.contain{min-height:0!important;height:auto!important;flex-grow:0!important}.gallery-container .grid-wrap[style*="max-content"]{overflow-y:visible!important}';
                    currentFrameDocument.head.append(currentSizingStyle);
                    currentContentObserver=new ResizeObserver(resizeWorkspaceFrame);
                    currentContentObserver.observe(currentContentRoot);
                    currentContentMutations=new MutationObserver(resizeWorkspaceFrame);
                    currentContentMutations.observe(currentFrameDocument.body,{childList:true,subtree:true,attributes:true});
                }
                const currentFrameDocument=currentFrameElement.contentDocument;
                const currentContentRoot=currentFrameDocument?.querySelector('.gradio-container')||currentFrameDocument?.body;
                if(!currentContentRoot)return;
                const currentContentHeight=currentContentRoot.getBoundingClientRect().height;
                const currentHeightValue=Math.ceil(Math.max(currentMinimumHeight,currentContentHeight+currentBottomGap))+'px';
                if(currentFrameElement.style.height!==currentHeightValue)currentFrameElement.style.height=currentHeightValue;
            });
        };
        const currentFrameObserver=new MutationObserver(resizeWorkspaceFrame);
        currentFrameObserver.observe(document.body,{childList:true,subtree:true});
        window.addEventListener('resize',resizeWorkspaceFrame);
        requestAnimationFrame(resizeWorkspaceFrame);
        const synchronizeSidebarState=()=>{
            const currentSidebarElement=document.getElementById('management-sidebar');
            const currentToggleButton=currentSidebarElement?.querySelector('.toggle-button');
            if(!currentToggleButton)return false;
            currentToggleButton.setAttribute('aria-label','도구 탐색 열기 / 닫기');
            if(currentSidebarElement.classList.contains('open')===currentMediaQuery.matches)currentToggleButton.click();
            return true;
        };
        const currentMountObserver=new MutationObserver(()=>{if(synchronizeSidebarState())currentMountObserver.disconnect();});
        currentMountObserver.observe(document.body,{childList:true,subtree:true});
        requestAnimationFrame(()=>{if(synchronizeSidebarState())currentMountObserver.disconnect();});
        currentMediaQuery.addEventListener('change',synchronizeSidebarState);
        document.addEventListener('keydown',currentKeyboardEvent=>{
            if(currentKeyboardEvent.key!=='Escape'||!currentMediaQuery.matches)return;
            const currentSidebarElement=document.getElementById('management-sidebar');
            if(currentSidebarElement?.classList.contains('open')){
                const currentToggleButton=currentSidebarElement.querySelector('.toggle-button');
                currentToggleButton.click();currentToggleButton.focus();
            }
        });
    }""".replace('BREAKPOINT',str(MANAGEMENT_MOBILE_BREAKPOINT)).replace('MINHEIGHT',str(MANAGEMENT_FRAME_MIN_HEIGHT)).replace('BOTTOMGAP',str(MANAGEMENT_FRAME_BOTTOM_GAP))


def build_management_menu_interface(page_record_values, review_server_port):
    initial_page_identifier=page_record_values[0]['id'] if page_record_values else ''
    initial_selection_script=create_initial_selection_script(page_record_values)
    with gr.Blocks(title='SLIME 관리도구',fill_width=True) as interface_blocks_value:
        with gr.Sidebar(label='도구 탐색',width=MANAGEMENT_NAVIGATION_WIDTH,open=True,elem_id='management-sidebar'):
            gr.Markdown('### 도구 탐색')
            search_text_value=gr.Textbox(label='도구 검색',placeholder='이름, ID, 기능',info='검색 결과에서 도구를 선택하면 해당 주소로 이동합니다.',elem_id='management-tool-search')
            category_select_value=gr.Dropdown(choices=[(current_label_value,current_name_value) for current_name_value,current_label_value in sorted(CATEGORY_LABEL_VALUES.items(),key=lambda category_entry_value:(category_entry_value[0]!='all',category_entry_value[1]))],value='all',label='분류',elem_id='management-category-filter')
            tool_count_value=gr.Markdown(f'**{len(page_record_values)}개** 도구',elem_id='management-tool-count')
            page_select_value=gr.Dropdown(choices=create_tool_choice_values(page_record_values),value=initial_page_identifier,label='도구 목록',elem_id='management-tool-list')
            with gr.Row(elem_classes=['management-pagination']):
                previous_page_button_value=gr.Button('← 이전',scale=0,min_width=100)
                navigation_position_value=gr.Markdown(f'1 / {len(page_record_values)}',elem_classes=['management-pagination-position'])
                next_page_button_value=gr.Button('다음 →',scale=0,min_width=100)
        with gr.Row(elem_id='management-header'):
            gr.Markdown('## SLIME 관리도구',scale=3)
            gpu_status_value=gr.Markdown(render_gpu_status_card({}),elem_id='management-gpu-status',scale=2)
        with gr.Row(elem_id='management-shell'):
            with gr.Column(scale=3,min_width=280,elem_id='management-workspace'):
                selected_page_status_value=gr.Markdown(f"**{html.escape(page_record_values[0]['label'])}** · {html.escape(page_record_values[0]['description'])}" if page_record_values else '표시할 관리 화면이 없습니다.')
                page_preview_value=gr.HTML(create_page_preview_html(initial_page_identifier,page_record_values,review_server_port))
        def update_menu_choices(search_text_value,category_name_value,selected_page_identifier):
            filtered_page_records=filter_manager_page_records(page_record_values,search_text_value or '',category_name_value)
            filtered_identifier_values=[current_page_record['id'] for current_page_record in filtered_page_records]
            retained_identifier_value=selected_page_identifier if selected_page_identifier in filtered_identifier_values else (filtered_identifier_values[0] if filtered_identifier_values else None)
            selected_position_value=(filtered_identifier_values.index(retained_identifier_value)+1) if retained_identifier_value else 0
            selected_status_text,selected_preview_html=(gr.skip(),gr.skip()) if retained_identifier_value==selected_page_identifier else select_menu_page(retained_identifier_value)
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
        for current_filter_component in (search_text_value,category_select_value):current_filter_component.input(update_menu_choices,[search_text_value,category_select_value,page_select_value],[page_select_value,tool_count_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
        page_select_value.input(select_menu_page,page_select_value,[selected_page_status_value,page_preview_value],queue=False)
        filter_navigation_script=create_menu_navigation_script(page_record_values,'replaceState')
        page_navigation_script=create_menu_navigation_script(page_record_values,'pushState')
        for current_filter_component in (search_text_value,category_select_value):
            current_filter_component.input(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=filter_navigation_script,queue=False)
        page_select_value.input(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=page_navigation_script,queue=False)
        search_text_value.submit(lambda search_text_value,category_name_value: update_menu_choices(search_text_value,category_name_value,None),[search_text_value,category_select_value],[page_select_value,tool_count_value,selected_page_status_value,page_preview_value,navigation_position_value],queue=False)
        page_select_value.input(lambda selected_page_identifier,search_text_value,category_name_value: move_menu_page(selected_page_identifier,search_text_value,category_name_value,0)[3],[page_select_value,search_text_value,category_select_value],navigation_position_value,queue=False)
        current_navigation_inputs=[search_text_value,category_select_value,page_select_value]
        current_page_outputs=[page_select_value,selected_page_status_value,page_preview_value,navigation_position_value]
        for current_navigation_button,current_navigation_step in ((previous_page_button_value,-1),(next_page_button_value,1)):
            current_navigation_button.click(lambda current_page_identifier,current_search_text,current_category_name,current_step_value=current_navigation_step:move_menu_page(current_page_identifier,current_search_text,current_category_name,current_step_value),[page_select_value,search_text_value,category_select_value],current_page_outputs,queue=False).then(fn=None,inputs=current_navigation_inputs,js=page_navigation_script,queue=False)
        def initialize_menu_selection(current_search_text,current_category_name,current_page_identifier):
            if current_category_name not in CATEGORY_LABEL_VALUES:current_category_name='all'
            current_selected_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==current_page_identifier),None)
            if current_selected_record and current_selected_record not in filter_manager_page_records(page_record_values,current_search_text,current_category_name):
                current_search_text,current_category_name='','all'
            current_selection_updates=list(update_menu_choices(current_search_text,current_category_name,current_page_identifier))
            current_selection_updates[2:4]=select_menu_page(current_selection_updates[0]['value'])
            return [current_search_text,current_category_name,*current_selection_updates]
        interface_blocks_value.load(initialize_menu_selection,current_navigation_inputs,[search_text_value,category_select_value,page_select_value,tool_count_value,selected_page_status_value,page_preview_value,navigation_position_value],js=initial_selection_script,queue=False)
        interface_blocks_value.load(fn=None,js=create_sidebar_responsive_script())
        interface_blocks_value.load(lambda:render_gpu_status_card(read_gpu_status()),outputs=gpu_status_value,queue=False)
        if hasattr(gr,'Timer'):gr.Timer(3).tick(lambda:render_gpu_status_card(read_gpu_status()),outputs=gpu_status_value,show_progress='hidden')
    return interface_blocks_value,initial_selection_script

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
    interface_blocks_value,initial_selection_script=build_management_menu_interface(load_manager_page_records(parsed_argument_values.source_file),parsed_argument_values.review_port)
    interface_blocks_value.queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,allowed_paths=[])
