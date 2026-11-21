"""기존 관리 화면을 연결하는 Gradio 메뉴 클라이언트."""
import argparse
import html
import json
import os
from pathlib import Path
import sys
import threading
import time

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[5]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.management.common.gpu_status import read_gpu_status
from tools.management.common.gradio_error_trace import trace_management_callback

from tools.management.common.management_catalog import (
    ARCHIVED_IMAGE_PAGE_IDENTIFIERS, CATEGORY_LABEL_VALUES, DEFAULT_PAGE_RECORDS,
    LEGACY_PAGE_IDENTIFIER_VALUES, LEGACY_SOUND_CATEGORY_NAMES, MANAGEMENT_FRAME_IDENTIFIER_VALUES,
    MANAGEMENT_FRAME_PATH_PREFIX, NATIVE_MANAGEMENT_APPLICATIONS, create_tool_choice_values,
    filter_manager_page_records, load_manager_page_records, resolve_management_page_path,
    serialize_manager_navigation,
)

DEFAULT_MANAGER_SOURCE_PATH=WORKFLOW_ROOT_DIRECTORY/'.tmp/manager-current/manager-source.json'


def format_gpu_status(gpu_status_record):
    if gpu_status_record.get('status')=='busy':
        process_status_values=[]
        for current_process_record in gpu_status_record.get('processes',[]):
            identifier_text_value=current_process_record.get('id') or f"PID {current_process_record.get('pid','?')}"
            current_process_memory=[f"{current_domain_name.upper()} {current_process_record[f'{current_domain_name}_memory_mib']:,} MiB" for current_domain_name in ('gtt','vram') if isinstance(current_process_record.get(f'{current_domain_name}_memory_mib'),int)]
            memory_text_value=' · '+' · '.join(current_process_memory) if current_process_memory else (f" · {current_process_record['memory_mib']} MiB" if current_process_record.get('memory_mib') is not None else '')
            process_status_values.append(f"{current_process_record.get('command','외부 GPU 작업')} · {identifier_text_value}{memory_text_value}")
        return 'GPU 사용 중 · '+' / '.join(process_status_values)
    if gpu_status_record.get('status')=='idle':return 'GPU · 실행 중인 연산 작업 없음'
    return 'GPU · 상태 확인 불가'


def build_gpu_process_groups(gpu_status_record):
    """GPU 프로세스 간 실제 조상 관계만 연결한다."""
    current_process_records = gpu_status_record.get('processes', [])
    current_pid_records = {current_record.get('pid'): current_record for current_record in current_process_records if type(current_record.get('pid')) is int}
    current_groups = {}
    for current_record in current_process_records:
        current_root_record = current_record
        current_seen_pids = set()
        while current_root_record.get('gpu_parent_pid') in current_pid_records and current_root_record.get('gpu_parent_pid') not in current_seen_pids:
            current_seen_pids.add(current_root_record.get('pid'))
            current_root_record = current_pid_records[current_root_record['gpu_parent_pid']]
        current_group_key = current_root_record.get('pid')
        current_groups.setdefault(current_group_key, {'root':current_root_record, 'processes':[]})['processes'].append(current_record)
    return list(current_groups.values())


def format_gpu_group_summary(current_group_record):
    current_root_record = current_group_record['root']
    current_process_records = current_group_record['processes']
    current_summary_parts = [str(current_root_record.get('command') or '외부 GPU 작업')]
    for current_domain_name in ('vram','gtt'):
        current_memory_values = [current_record.get(f'{current_domain_name}_memory_mib') for current_record in current_process_records]
        current_known_values = [current_value for current_value in current_memory_values if type(current_value) is int and current_value >= 0]
        current_memory_text = f'{sum(current_known_values):,} MiB' if len(current_known_values) == len(current_memory_values) else '일부 미측정' if current_known_values else '미측정'
        current_summary_parts.append(f'{current_domain_name.upper()} 합 {current_memory_text}')
    current_summary_parts.append(f'{len(current_process_records)}개 프로세스')
    return ' · '.join(current_summary_parts)


def render_gpu_process_tree(current_group_record):
    current_process_records = current_group_record['processes']
    current_group_pids = {current_record.get('pid') for current_record in current_process_records}
    current_tree_lines = []
    current_rendered_records = set()
    def append_process_branch(current_record, current_depth_value):
        if id(current_record) in current_rendered_records:
            return
        current_rendered_records.add(id(current_record))
        current_role_text = html.escape(str(current_record.get('process_role') or ('부모 프로세스' if current_depth_value == 0 else '자식 프로세스')))
        current_pid_value = current_record.get('pid')
        current_memory_parts = [f"{current_domain_name.upper()} {current_record[f'{current_domain_name}_memory_mib']:,} MiB" for current_domain_name in ('vram','gtt') if type(current_record.get(f'{current_domain_name}_memory_mib')) is int and current_record[f'{current_domain_name}_memory_mib'] >= 0]
        memory_text = ''
        if len(current_process_records) > 1:
            memory_text = ' · ' + (' · '.join(current_memory_parts) or '메모리 미측정')
        current_tree_lines.append('  ' * current_depth_value + f"- {current_role_text} · PID {current_pid_value if type(current_pid_value) is int else '?'}" + memory_text)
        for current_child_record in current_process_records:
            if current_child_record.get('gpu_parent_pid') == current_pid_value and current_child_record.get('pid') in current_group_pids and current_child_record is not current_record:
                append_process_branch(current_child_record, current_depth_value+1)
    append_process_branch(current_group_record['root'], 0)
    return '\n'.join(current_tree_lines)


def render_gpu_status_card(gpu_status_record):
    """동시에 실행 중인 프로세스를 각각 구분하고 메모리 풀을 표시한다."""
    if gpu_status_record.get('status') == 'busy':
        current_process_values = gpu_status_record.get('processes', [])
        current_status_lines = [f'**GPU 사용 중 · {len(current_process_values)}개 프로세스**']
        for current_process_record in current_process_values:
            current_command_text = html.escape(str(current_process_record.get('command') or '외부 GPU 작업'))
            current_process_identifier = current_process_record.get('pid')
            current_pid_text = str(current_process_identifier) if type(current_process_identifier) is int else '?'
            current_job_identifier = current_process_record.get('id')
            current_job_text = f" · 작업 {html.escape(str(current_job_identifier))}" if current_job_identifier else ''
            current_process_memory = [f"{current_domain_name.upper()} {current_process_record[f'{current_domain_name}_memory_mib']:,} MiB" for current_domain_name in ('vram','gtt') if type(current_process_record.get(f'{current_domain_name}_memory_mib')) is int and current_process_record[f'{current_domain_name}_memory_mib'] >= 0]
            if not current_process_memory and type(current_process_record.get('memory_mib')) is int:
                current_process_memory = [f"메모리 {current_process_record['memory_mib']:,} MiB"]
            current_status_lines.append(f"- **{current_command_text}** · PID {current_pid_text}{current_job_text}" + ('  \n  ' + ' · '.join(current_process_memory) if current_process_memory else ''))
        current_status_text = '\n\n'.join(current_status_lines)
    else:
        current_status_text=format_gpu_status(gpu_status_record)
    for current_domain_name in ('gtt','vram'):
        current_memory_values=[gpu_status_record.get(f'{current_domain_name}_{current_measure_name}_mib') for current_measure_name in ('used','free','total')]
        if all(isinstance(current_memory_value,int) and current_memory_value>=0 for current_memory_value in current_memory_values):
            current_status_text+='\n\n'+current_domain_name.upper()+' · '+ ' · '.join(f'{current_memory_label} {current_memory_value:,} MiB' for current_memory_label,current_memory_value in zip(('사용','여유','총'),current_memory_values))
    if 'gtt_total_mib' not in gpu_status_record:
        current_memory_values=[gpu_status_record.get(current_field_name) for current_field_name in ('memory_used_mib','memory_free_mib','memory_total_mib')]
        if all(isinstance(current_memory_value,int) and current_memory_value>=0 for current_memory_value in current_memory_values):
            current_status_text+='\n\n'+ ' · '.join(f'{current_memory_label} {current_memory_value:,} MiB' for current_memory_label,current_memory_value in zip(('사용','여유','총'),current_memory_values))
    return current_status_text


def render_gpu_capacity_summary(gpu_status_record):
    current_memory_lines = []
    for current_domain_name in ('gtt', 'vram'):
        current_memory_values = [gpu_status_record.get(f'{current_domain_name}_{current_measure_name}_mib') for current_measure_name in ('used','free','total')]
        if all(type(current_memory_value) is int and current_memory_value >= 0 for current_memory_value in current_memory_values):
            current_memory_lines.append(current_domain_name.upper()+' · '+' · '.join(f'{current_memory_label} {current_memory_value:,} MiB' for current_memory_label,current_memory_value in zip(('사용','여유','총'),current_memory_values)))
    return '\n\n'.join(current_memory_lines)

def build_conversation_tool_explorer(conversation_prompt, session_control, current_source_path=None):
    """선택한 도구를 작성 중인 대화 요청에 포함한다."""
    current_source_path = Path(current_source_path or os.environ.get('SLIME_MANAGEMENT_MENU_SOURCE', str(DEFAULT_MANAGER_SOURCE_PATH)))
    records = [record for record in load_manager_page_records(current_source_path)
               if record['id'] != 'hermes-agent']
    by_id = {record['id']: record for record in records}

    def attach_tool(session_id, identifier, draft):
        record = by_id.get(identifier)
        if record is None:
            raise gr.Error('대화에 사용할 도구를 선택하세요.')
        context = f"사용할 도구: {record['label']} ({identifier})"
        draft = draft or ''
        if context in draft.splitlines():
            return draft
        return draft + ('\n' if draft and not draft.endswith('\n') else '') + context + '\n'

    with gr.Accordion('도구 탐색', open=False, elem_id='hermes-tool-explorer'):
        choices = [(f"{r['label']} · {CATEGORY_LABEL_VALUES.get(r['category'], r['category'])} · {r['id']} · {r['description']}", r['id']) for r in records]
        selection = gr.Dropdown(label='도구 검색', choices=choices, value=None, interactive=True,
                                filterable=True, info='이름·분류·ID·기능을 입력하고 대화에 사용할 도구를 선택하세요.')
        session_control.change(lambda: gr.update(value=None), outputs=selection, queue=False)
        attach_event = gr.Button('현재 요청에 추가').click(attach_tool, [session_control, selection, conversation_prompt], conversation_prompt, queue=False)
        attach_event.success(fn=None, js="""() => {
            document.querySelector('#hermes-tool-explorer > button.open')?.click();
            const input = document.querySelector('#hermes-request-input textarea');
            if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
        }""", queue=False)


def compose_management_interface(current_tool_interface,current_review_port,current_source_path=None):
    """도구 이벤트와 공용 메뉴를 한 Blocks 문서로 합성한다."""
    current_manager_source=Path(current_source_path or os.environ.get('SLIME_MANAGEMENT_MENU_SOURCE',str(DEFAULT_MANAGER_SOURCE_PATH)))
    current_page_records=load_manager_page_records(current_manager_source)
    current_shell_interface,_=build_management_menu_interface(current_page_records,current_review_port,current_tool_interface)
    return current_shell_interface


def create_page_preview_html(selected_page_identifier, page_record_values, review_server_port):
    selected_page_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==selected_page_identifier),None)
    if selected_page_record is None:return '<div class="menu-empty-state">표시할 관리 화면을 선택하세요.</div>'
    current_native_path=resolve_management_page_path(selected_page_record)
    if current_native_path:
        return '<a href="'+html.escape(current_native_path,quote=True)+'">'+html.escape(selected_page_record['label'])+' 열기</a>'
    current_document_path=html.escape('/'+selected_page_record['path'].lstrip('/'),quote=True)
    return '<a href="'+current_document_path+'">독립 검수 문서 열기 · '+html.escape(selected_page_record['label'])+'</a>'


def create_menu_navigation_script(page_record_values, history_method_name, current_inline_mode=False):
    """선택 도구와 탐색 필터를 하나의 공개 URL 상태로 동기화한다."""
    serialized_page_records=serialize_manager_navigation(page_record_values)
    current_inline_value=json.dumps(current_inline_mode)
    return f"""(searchTextValue,categoryNameValue,selectedPageIdentifier)=>{{
        const pageRecords={serialized_page_records};
        const searchTokenValues=String(searchTextValue||'').toLocaleLowerCase().trim().split(/\\s+/).filter(Boolean);
        const filteredPageRecords=pageRecords.filter(pageRecord=>{{
            const pageTextValue=`${{pageRecord.label}} ${{pageRecord.description}} ${{pageRecord.id}}`.toLocaleLowerCase();
            return(categoryNameValue==='all'||pageRecord.category===categoryNameValue)&&searchTokenValues.every(searchTokenValue=>pageTextValue.includes(searchTokenValue));
        }});
        const selectedPageRecord=filteredPageRecords.find(pageRecord=>pageRecord.id===selectedPageIdentifier)||filteredPageRecords[0];
        const nextUrlValue=new URL(window.top.location.href);
        if(selectedPageRecord&&{json.dumps(not current_inline_mode or history_method_name!='replaceState')}){{nextUrlValue.pathname='/';nextUrlValue.searchParams.set('tool',selectedPageRecord.id);}}
        for(const [parameterName,parameterValue,defaultValue] of [['search',searchTextValue,''],['category',categoryNameValue,'all']]){{
            if(parameterValue&&parameterValue!==defaultValue)nextUrlValue.searchParams.set(parameterName,parameterValue);
            else nextUrlValue.searchParams.delete(parameterName);
        }}
        nextUrlValue.searchParams.delete('view');
        if({json.dumps(history_method_name=='replaceState')}){{window.top.history.replaceState(window.history.state,'',nextUrlValue.href);return;}}
        if(!selectedPageRecord){{window.top.history.replaceState(window.history.state,'',nextUrlValue.href);return;}}
        const currentInlineMode={current_inline_value};
        const currentActiveTool=new URL(window.location.href).searchParams.get('tool')||new URL(window.location.href).searchParams.get('review');
        if(currentInlineMode&&selectedPageRecord.id===currentActiveTool){{nextUrlValue.pathname=window.location.pathname;}}
        else if(currentInlineMode||selectedPageRecord.nativePath){{
            const currentTargetLocation=new URL(selectedPageRecord.nativePath||'/',window.location.href);
            for(const currentParameterName of Array.from(nextUrlValue.searchParams.keys())){{
                if(!['tool','search','category'].includes(currentParameterName))nextUrlValue.searchParams.delete(currentParameterName);
            }}
            nextUrlValue.pathname=currentTargetLocation.pathname;
            for(const [currentParameterName,currentParameterValue] of currentTargetLocation.searchParams)nextUrlValue.searchParams.set(currentParameterName,currentParameterValue);
            window.location.{('replace' if history_method_name=='replaceState' else 'assign')}(nextUrlValue.href);return;
        }}
        window.top.history.{history_method_name}({{managementTool:selectedPageRecord.id,managementFilters:{{search:searchTextValue||'',category:categoryNameValue||'all'}}}},'',nextUrlValue.pathname+nextUrlValue.search+nextUrlValue.hash);
    }}"""


def create_initial_selection_script(page_record_values):
    """Gradio load 입력으로 URL 상태를 전달하고 DOM 클릭을 사용하지 않는다."""
    serialized_page_records=serialize_manager_navigation(page_record_values)
    return f"""()=>{{
        const pageRecords={serialized_page_records};
        const currentUrlValue=new URL(window.location.href);
        if(currentUrlValue.pathname.replace(/\/$/,'')==='/management/frame/hermes-agent')return ['', 'all', 'hermes-agent'];
        if(currentUrlValue.pathname.replace(/\/$/,'')==='/management/frame/operations-history')return ['', 'all', 'operations-history'];
        if(currentUrlValue.pathname.replace(/\/$/,'')==='/management/frame/hermes-direct')return ['', 'all', 'hermes-direct'];
        if(['field-map-review','town-map-review'].includes(currentUrlValue.searchParams.get('category'))){{currentUrlValue.searchParams.set('category','map-review');window.history.replaceState(window.history.state,'',currentUrlValue.href);}}
        if({json.dumps(LEGACY_SOUND_CATEGORY_NAMES)}.includes(currentUrlValue.searchParams.get('category'))){{currentUrlValue.searchParams.set('category','sound-management');window.history.replaceState(window.history.state,'',currentUrlValue.href);}}
        const requestedPageIdentifier=currentUrlValue.searchParams.get('review')||currentUrlValue.searchParams.get('tool');
        if(currentUrlValue.searchParams.get('category')==='animation'){{currentUrlValue.searchParams.set('category','animation-tool');window.history.replaceState(window.history.state,'',currentUrlValue.href);}}
        const currentCatalogRecord=pageRecords.find(record=>record.reviewAliases?.includes(requestedPageIdentifier));
        const resolvedPageIdentifier=currentCatalogRecord?.id||{json.dumps(LEGACY_PAGE_IDENTIFIER_VALUES)}[requestedPageIdentifier]||requestedPageIdentifier;
        if(resolvedPageIdentifier&&!pageRecords.some(record=>record.id===resolvedPageIdentifier)){{
            return [currentUrlValue.searchParams.get('search')||'',currentUrlValue.searchParams.get('category')||'all',resolvedPageIdentifier];
        }}
        const currentMapPage=currentUrlValue.pathname.replace(/\/$/,'')==='/management/frame/map-review'?pageRecords.find(record=>record.nativePath&&new URL(record.nativePath,currentUrlValue).pathname.replace(/\/$/,'')==='/management/frame/map-review'):null;
        const selectedPageRecord=pageRecords.find(record=>record.id===resolvedPageIdentifier)||pageRecords.find(record=>record.path===currentUrlValue.pathname)||currentMapPage||pageRecords.find(record=>{{if(!record.nativePath)return false;const currentTargetUrl=new URL(record.nativePath,currentUrlValue);return currentTargetUrl.pathname===currentUrlValue.pathname&&Array.from(currentTargetUrl.searchParams).every(([currentParameterName,currentParameterValue])=>currentUrlValue.searchParams.get(currentParameterName)===currentParameterValue);}})||pageRecords[0];
        if(selectedPageRecord?.nativePath){{
            const currentTargetUrl=new URL(selectedPageRecord.nativePath,currentUrlValue);
            if(currentUrlValue.pathname!==currentTargetUrl.pathname){{
                currentUrlValue.pathname=currentTargetUrl.pathname;
                for(const [currentParameterName,currentParameterValue] of currentTargetUrl.searchParams)currentUrlValue.searchParams.set(currentParameterName,currentParameterValue);
                currentUrlValue.searchParams.set('tool',selectedPageRecord.id);window.location.replace(currentUrlValue.href);
            }}else if(!currentUrlValue.searchParams.has('tool')){{currentUrlValue.searchParams.set('tool',selectedPageRecord.id);window.history.replaceState(window.history.state,'',currentUrlValue.href);}}
        }}
        return [currentUrlValue.searchParams.get('search')||'',currentUrlValue.searchParams.get('category')||'all',selectedPageRecord?.id||null];
    }}"""


MANAGEMENT_NAVIGATION_WIDTH = 320
MANAGEMENT_MOBILE_BREAKPOINT = 768
MANAGEMENT_GPU_REFRESH_SECONDS = 30


def create_sidebar_responsive_script(current_inline_mode=False):
    """Gradio 기본 슬라이딩 동작에 화면 폭 전환과 접근성 이름만 연결한다."""
    current_sidebar_script="""()=>{
        const initializeGpuPanelAccessibility=()=>{
            const currentPanelElement=document.getElementById('management-gpu-floating');
            const currentPanelButton=currentPanelElement?.querySelector('button');
            const currentPanelContent=currentPanelElement?.querySelector('[data-testid="accordion-content"]');
            if(!currentPanelButton||!currentPanelContent)return false;
            if(currentPanelButton.getAttribute('aria-controls')==='management-gpu-panel-content')return true;
            currentPanelContent.id='management-gpu-panel-content';
            currentPanelButton.setAttribute('aria-controls',currentPanelContent.id);
            const synchronizeGpuPanelState=()=>currentPanelButton.setAttribute('aria-expanded',String(currentPanelButton.classList.contains('open')));
            new MutationObserver(synchronizeGpuPanelState).observe(currentPanelButton,{attributes:true,attributeFilter:['class']});
            synchronizeGpuPanelState();
            return true;
        };
        const currentGpuPanelObserver=new MutationObserver(()=>{if(initializeGpuPanelAccessibility())currentGpuPanelObserver.disconnect();});
        currentGpuPanelObserver.observe(document.body,{childList:true,subtree:true});
        requestAnimationFrame(()=>{if(initializeGpuPanelAccessibility())currentGpuPanelObserver.disconnect();});
        const synchronizeGalleryOverflow=()=>{
            document.querySelectorAll('.gallery-container .grid-wrap').forEach(currentGalleryElement=>{
                if(currentGalleryElement.style.height==='max-content'&&currentGalleryElement.style.overflow!=='visible')currentGalleryElement.style.overflow='visible';
            });
        };
        const currentGalleryObserver=new MutationObserver(synchronizeGalleryOverflow);
        currentGalleryObserver.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});
        synchronizeGalleryOverflow();
        const currentMediaQuery=window.matchMedia('(max-width: BREAKPOINTpx)');
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
    }""".replace('BREAKPOINT',str(MANAGEMENT_MOBILE_BREAKPOINT))
    return current_sidebar_script


def build_management_menu_interface(page_record_values, review_server_port, current_inline_interface=None):
    current_inline_mode=current_inline_interface is not None
    page_record_values=[current_page_record for current_page_record in page_record_values if current_page_record['id'] != 'hermes-agent']
    initial_page_identifier=page_record_values[0]['id'] if page_record_values else ''
    initial_selection_script=create_initial_selection_script(page_record_values)
    with gr.Blocks(title='SLIME 관리도구',fill_width=True) as interface_blocks_value:
        with gr.Row(elem_id='management-header'):
            gr.Markdown('## SLIME 관리도구',scale=3)
            gr.HTML('<a href="/management/frame/hermes-agent/" target="_self">운영 대화로 돌아가기</a>', scale=1, elem_id='management-return-conversation')
            gr.HTML('<a href="/management/frame/operations-history/" target="_blank" rel="noopener">운영 이력</a>', scale=1, elem_id='management-open-history')
        with gr.Accordion('GPU 프로세스 정보',open=False,elem_id='management-gpu-floating') as current_gpu_panel:
            # GPU 표시 상태는 페이지 내부에서만 사용한다. gr.State는 각 탭에
            # 상시 heartbeat 연결을 만들어 브라우저의 연결 한도를 점유한다.
            gpu_status_value=gr.JSON(value={},visible=False)
            @gr.render(inputs=gpu_status_value, queue=False)
            def render_gpu_process_groups(current_gpu_status):
                current_group_records = build_gpu_process_groups(current_gpu_status)
                current_status_text = f"GPU 사용 중 · {len(current_group_records)}개 프로세스 그룹 · {len(current_gpu_status.get('processes', []))}개 프로세스" if current_gpu_status.get('status') == 'busy' else format_gpu_status(current_gpu_status)
                gr.Markdown(current_status_text, elem_id='management-gpu-status')
                for current_group_record in current_group_records:
                    current_root_identifier = current_group_record['root'].get('pid')
                    with gr.Accordion(format_gpu_group_summary(current_group_record), open=False, key=f'gpu-process-{current_root_identifier}', preserved_by_key=['open']):
                        gr.Markdown(render_gpu_process_tree(current_group_record))
                        job_ids = dict.fromkeys(process['id'] for process in current_group_record['processes'] if process.get('id'))
                        for job_id in job_ids:
                            label = '작업 ID'
                            if len(job_ids) > 1 or any(not process.get('id') for process in current_group_record['processes']):
                                pids = ', '.join(str(process['pid']) for process in current_group_record['processes'] if process.get('id') == job_id)
                                label += f' · PID {pids}'
                            gr.Textbox(label=label, value=job_id, interactive=False, buttons=['copy'],
                                       key=f'gpu-job-id-{current_root_identifier}-{job_id}')
                current_capacity_text = render_gpu_capacity_summary(current_gpu_status)
                if current_capacity_text:
                    gr.Markdown(current_capacity_text)
        with gr.Row(elem_id='management-shell'):
            with gr.Column(scale=3,min_width=280,elem_id='management-workspace'):
                if current_inline_mode:current_inline_interface.render()
                else:
                    with gr.Column(visible=False):
                        search_text_value=gr.Textbox(label='도구 검색',placeholder='이름, ID, 기능',info='검색 결과에서 도구를 선택하면 해당 주소로 이동합니다.',elem_id='management-tool-search')
                        category_select_value=gr.Dropdown(choices=[(current_label_value,current_name_value) for current_name_value,current_label_value in sorted(CATEGORY_LABEL_VALUES.items(),key=lambda category_entry_value:(category_entry_value[0]!='all',category_entry_value[1]))],value='all',label='분류',elem_id='management-category-filter')
                        tool_count_value=gr.Markdown(f'**{len(page_record_values)}개** 도구',elem_id='management-tool-count')
                        page_select_value=gr.Dropdown(choices=create_tool_choice_values(page_record_values),value=initial_page_identifier,label='도구 목록',elem_id='management-tool-list')
                    selected_page_status_value=gr.Markdown(f"**{html.escape(page_record_values[0]['label'])}** · {html.escape(page_record_values[0]['description'])}" if page_record_values else '표시할 관리 화면이 없습니다.')
                    page_preview_value=gr.HTML('' if current_inline_mode else create_page_preview_html(initial_page_identifier,page_record_values,review_server_port),visible=not current_inline_mode)
        if not current_inline_mode:
            @trace_management_callback('도구 목록 필터')
            def update_menu_choices(search_text_value,category_name_value,selected_page_identifier):
                filtered_page_records=filter_manager_page_records(page_record_values,search_text_value or '',category_name_value)
                filtered_identifier_values=[current_page_record['id'] for current_page_record in filtered_page_records]
                retained_identifier_value=selected_page_identifier if selected_page_identifier in filtered_identifier_values else (filtered_identifier_values[0] if filtered_identifier_values else None)
                selected_status_text,selected_preview_html=(gr.skip(),gr.skip()) if current_inline_mode or retained_identifier_value==selected_page_identifier else select_menu_page(retained_identifier_value)
                return gr.update(choices=create_tool_choice_values(filtered_page_records),value=retained_identifier_value),f'**{len(filtered_page_records)}개** 도구 · 전체 {len(page_record_values)}개',selected_status_text,selected_preview_html
            @trace_management_callback('도구 선택')
            def select_menu_page(selected_page_identifier):
                selected_page_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==selected_page_identifier),None)
                if selected_page_record is None:return '표시할 관리 화면을 선택하세요.','<div class="menu-empty-state">검색 조건을 바꾸거나 메뉴를 선택하세요.</div>'
                return f"**{html.escape(selected_page_record['label'])}** · {html.escape(selected_page_record['description'])}",('' if current_inline_mode else create_page_preview_html(selected_page_identifier,page_record_values,review_server_port))
            for current_filter_component in (search_text_value,category_select_value):current_filter_component.input(update_menu_choices,[search_text_value,category_select_value,page_select_value],[page_select_value,tool_count_value,selected_page_status_value,page_preview_value],queue=False,preprocess=False)
            page_select_value.input(select_menu_page,page_select_value,[selected_page_status_value,page_preview_value],queue=False,preprocess=False)
            filter_navigation_script=create_menu_navigation_script(page_record_values,'replaceState',current_inline_mode)
            page_navigation_script=create_menu_navigation_script(page_record_values,'pushState',current_inline_mode)
            for current_filter_component in (search_text_value,category_select_value):
                current_filter_component.input(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=filter_navigation_script,queue=False)
            page_select_value.input(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=page_navigation_script,queue=False)
            search_text_value.submit(lambda search_text_value,category_name_value: update_menu_choices(search_text_value,category_name_value,None),[search_text_value,category_select_value],[page_select_value,tool_count_value,selected_page_status_value,page_preview_value],queue=False,preprocess=False).then(fn=None,inputs=[search_text_value,category_select_value,page_select_value],js=page_navigation_script,queue=False)
            current_navigation_inputs=[search_text_value,category_select_value,page_select_value]
            @trace_management_callback('메뉴 초기화')
            def initialize_menu_selection(current_search_text,current_category_name,current_page_identifier):
                if current_page_identifier == 'operations-history':
                    return ['', 'all', gr.update(choices=create_tool_choice_values(page_record_values),value=None), f'**{len(page_record_values)}개** 도구 · 전체 {len(page_record_values)}개', '운영 이력 · 지시와 GPU 대기 기록', gr.skip() if current_inline_mode else '']
                if current_page_identifier == 'hermes-direct':
                    return ['', 'all', gr.update(choices=create_tool_choice_values(page_record_values),value=None), f'**{len(page_record_values)}개** 도구 · 전체 {len(page_record_values)}개', '직접 조회와 작업', gr.skip() if current_inline_mode else '']
                if current_page_identifier == 'hermes-agent':
                    return ['', 'all', gr.update(choices=create_tool_choice_values(page_record_values),value=None), f'**{len(page_record_values)}개** 도구 · 전체 {len(page_record_values)}개', '운영 대화 · 관리 작업의 시작과 진행', gr.skip() if current_inline_mode else '']
                if current_page_identifier == 'building-generator':
                    current_page_identifier = 'billboard-generator'
                if current_category_name not in CATEGORY_LABEL_VALUES:current_category_name='all'
                current_selected_record=next((current_page_record for current_page_record in page_record_values if current_page_record['id']==current_page_identifier),None)
                if current_selected_record and current_selected_record not in filter_manager_page_records(page_record_values,current_search_text,current_category_name):
                    current_search_text,current_category_name='','all'
                current_selection_updates=list(update_menu_choices(current_search_text,current_category_name,current_page_identifier))
                if current_page_identifier and current_selected_record is None:
                    current_selection_updates[0]['value']=None
                    current_selection_updates[2]='등록되지 않은 관리도구 주소입니다. 도구 목록에서 다시 선택하세요.'
                    current_selection_updates[3]='' if not current_inline_mode else gr.skip()
                else:
                    current_selection_updates[2:4]=select_menu_page(current_selection_updates[0]['value'])
                return [current_search_text,current_category_name,*current_selection_updates]
            interface_blocks_value.load(initialize_menu_selection,current_navigation_inputs,[search_text_value,category_select_value,page_select_value,tool_count_value,selected_page_status_value,page_preview_value],js=initial_selection_script,queue=False,preprocess=False,show_progress='hidden')
        interface_blocks_value.load(fn=None,js="()=>{let tabSession=null;let recentSession=null;try{tabSession=sessionStorage.getItem('slime-management-session');}catch(e){}try{recentSession=localStorage.getItem('slime-management-session');}catch(e){}const currentUrl=new URL(window.location.href);const linkedSession=currentUrl.searchParams.get('session');const selectedSession=/^[a-f0-9]{32}$/.test(linkedSession || '')?linkedSession:/^[a-f0-9]{32}$/.test(tabSession || '')?tabSession:recentSession;const returnLink=document.querySelector('#management-return-conversation a');if(/^[a-f0-9]{32}$/.test(selectedSession || '')){if(returnLink)returnLink.setAttribute('href','/management/frame/hermes-agent/?session='+selectedSession);const historyLink=document.querySelector('#management-open-history a');if(historyLink)historyLink.setAttribute('href','/management/frame/operations-history/?session='+selectedSession);}if(typeof window.addEventListener==='function'&&!window.slimeSessionNavigationListener){window.slimeSessionNavigationListener=true;window.addEventListener('storage',(event)=>{let isTabStorage=false;try{isTabStorage=event.storageArea===sessionStorage;}catch(e){}if(!isTabStorage||event.key!=='slime-management-session'||!/^[a-f0-9]{32}$/.test(event.newValue||''))return;const returnLink=document.querySelector('#management-return-conversation a');const historyLink=document.querySelector('#management-open-history a');if(returnLink)returnLink.setAttribute('href','/management/frame/hermes-agent/?session='+event.newValue);if(historyLink)historyLink.setAttribute('href','/management/frame/operations-history/?session='+event.newValue);});}}")
        interface_blocks_value.load(read_gpu_status,outputs=gpu_status_value,queue=False)
        if hasattr(gr,'Timer'):
            current_gpu_refresh_timer=gr.Timer(MANAGEMENT_GPU_REFRESH_SECONDS,active=False)
            current_gpu_refresh_timer.tick(read_gpu_status,outputs=gpu_status_value,show_progress='hidden',queue=False)
            current_gpu_panel.expand(lambda: gr.update(active=True),outputs=current_gpu_refresh_timer,queue=False).then(read_gpu_status,outputs=gpu_status_value,queue=False)
            current_gpu_panel.collapse(lambda: gr.update(active=False),outputs=current_gpu_refresh_timer,queue=False)
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
