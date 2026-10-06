"""생성이력 수동 초기화의 공용 UI와 명령 연결."""
import json
import gradio as gr
from pathlib import Path
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_results import build_generation_gallery
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation


HISTORY_SUMMARY_FIELD_NAMES=('tag','tile_type','motion','action','start_frame','end_frame','directions','width','height','resolution','target_fps','speed','steps','seed')
HISTORY_SUMMARY_LABELS={'tag':'태그','tile_type':'타일','motion':'모션','action':'동작','width':'너비','height':'높이','resolution':'해상도','target_fps':'타겟 FPS','speed':'배속','steps':'스텝','seed':'시드'}
HISTORY_STATUS_LABELS={'paused':'검수 대기', 'queued':'GPU 대기 중','running':'생성 중','completed':'완료','cancelled':'중지됨','failed':'실패','missing':'기록 누락','unknown':'상태 미상'}
HISTORY_PROGRESS_STAGE_LABELS={'paused':'검수 대기', 'queued':'GPU 대기 중','starting':'생성 준비 중','load':'모델 로딩 중','inference':'추론 중','saving':'결과 저장 중','completed':'완료','failed':'실패'}



def build_history_selection_panel(allow_restore_inputs=False, allow_history_delete=False):
    """선택 이력의 ID 복사·상태·명령 버튼을 공용 패널로 구성한다."""
    with gr.Column(visible=False,variant='panel') as history_selected_panel:
        selected_identifier_value=build_generation_identifier('생성 ID')
        history_selection_summary=gr.Markdown('목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.')
        with gr.Row(equal_height=True):
            result_lookup_button=gr.Button('결과 조회',variant='primary',interactive=False)
            if allow_restore_inputs:
                restore_input_button=gr.Button('입력값 불러오기',interactive=False)
            else:
                restore_input_button=gr.Button('입력 복원 미지원',interactive=False)
            history_resume_button=gr.Button('생성 재개',interactive=False)
            history_cancel_button=gr.Button('작업 중지',interactive=False)
            history_delete_button=None
            if allow_history_delete:
                history_delete_button=gr.Button('선택 이력 삭제',interactive=False)
    return (history_selected_panel, history_selection_summary, selected_identifier_value, result_lookup_button, restore_input_button, history_resume_button, history_cancel_button, history_delete_button)


def build_history_input_controls(history_selection_component, read_input_callback,
                                 restore_input_callback, restore_output_components):
    """저장된 입력 조회와 사용자 입력 복원을 별도 명시적 동작으로 연결한다."""
    with gr.Accordion('생성 당시 입력값', open=False):
        gr.Markdown('이력을 먼저 선택하세요. 조회는 현재 설정을 바꾸지 않으며, 불러오기는 입력란만 변경합니다. 생성은 시작하지 않습니다.')
        with gr.Row():
            input_lookup_button = gr.Button('입력값 조회')
            input_restore_button = gr.Button('입력값 불러오기')
        saved_input_display = gr.JSON(label='선택한 이력의 저장된 입력값')
        input_restore_status = gr.Markdown()
    input_lookup_button.click(read_input_callback, history_selection_component, saved_input_display, queue=False)
    input_restore_button.click(restore_input_callback, history_selection_component,
                               [*restore_output_components, input_restore_status], queue=False)
    return saved_input_display



def format_generation_status(current_status_record):
    """저장된 실패 원인으로 OOM을 구분하되 작업 상태 계약은 유지한다."""
    current_status_name = current_status_record.get('status', 'unknown') if isinstance(current_status_record, dict) else current_status_record
    if current_status_name == 'failed' and isinstance(current_status_record, dict):
        current_error_text = str(current_status_record.get('error', '')).lower()
        if any(current_marker_text in current_error_text for current_marker_text in ('cuda out of memory', 'cuda error: out of memory', 'torch.outofmemoryerror')):
            return 'OOM 실패 · GPU 메모리 부족'
    return HISTORY_STATUS_LABELS.get(current_status_name, current_status_name)

def format_history_choice_label(current_history_record):
    current_status_record=current_history_record.get('status',{})
    current_status_label=current_status_record.get('status','unknown') if isinstance(current_status_record,dict) else current_status_record
    current_request_record=current_history_record.get('request',{})
    current_created_text=format_history_created_time(current_history_record)
    current_summary_text=format_history_request_summary(current_request_record)
    current_status_label=format_generation_status(current_status_record)
    return f"{current_status_label} · {current_created_text}\n{current_summary_text}\nID · {current_history_record['id']}"


def format_history_created_time(current_history_record):
    created_time_value=current_history_record.get('created_at') or current_history_record.get('createdAt') or '시각 없음'
    return created_time_value.replace('T',' ').split('+',1)[0].split('.',1)[0] if isinstance(created_time_value,str) else '시각 없음'


def format_history_request_summary(current_request_record):
    summary_text_values=[]
    for current_field_name in HISTORY_SUMMARY_FIELD_NAMES:
        if current_field_name not in current_request_record:
            continue
        current_field_value=current_request_record[current_field_name]
        if current_field_name=='action' and current_field_value in ('generate','prepare'):
            continue
        if current_field_name=='directions' and isinstance(current_field_value,list):
            summary_text_values.append(f'방향 {len(current_field_value)}개')
        elif current_field_name=='start_frame' and 'end_frame' in current_request_record:
            summary_text_values.append(f'프레임 {current_field_value}–{current_request_record["end_frame"]}')
        elif current_field_name=='end_frame' and 'start_frame' in current_request_record:
            continue
        else:
            summary_text_values.append(f'{HISTORY_SUMMARY_LABELS.get(current_field_name,current_field_name)} {current_field_value}')
    return ' · '.join(summary_text_values) or '설정 요약 없음'


def format_history_selection_summary(current_history_record):
    """목록 선택 직후 판단할 수 있는 짧은 이력 상태 요약을 만든다."""
    current_status_record=current_history_record.get('status',{})
    current_status_label=current_status_record.get('status','unknown') if isinstance(current_status_record,dict) else current_status_record
    current_request_record=current_history_record.get('request',{})
    current_created_text=format_history_created_time(current_history_record)
    current_summary_text=format_history_request_summary(current_request_record)
    current_status_text=format_generation_status(current_status_record)
    return f"**선택한 생성 이력**\n\n상태: **{current_status_text}** · 생성 시각: {current_created_text}\n\n설정: {current_summary_text}"


def format_history_progress(current_progress_record):
    """로그에서 확인 가능한 진행 정보만 카드용 문구로 만든다."""
    if not isinstance(current_progress_record,dict):
        return ''
    current_stage_value=current_progress_record.get('stage','starting')
    current_label_value=HISTORY_PROGRESS_STAGE_LABELS.get(current_stage_value,current_stage_value)
    current_percent_value=current_progress_record.get('percent')
    current_completed_value=current_progress_record.get('completed_frames',current_progress_record.get('step'))
    current_total_value=current_progress_record.get('total_frames',current_progress_record.get('total'))
    if isinstance(current_percent_value,(int,float)) and current_total_value:
        return f'{current_label_value} {current_percent_value:g}% · {current_completed_value}/{current_total_value}'+current_progress_record.get('unit','프레임 저장' if 'completed_frames' in current_progress_record else '스텝')
    current_queue_position=current_progress_record.get('queue_position')
    return current_label_value+(f' · 대기 순서 {current_queue_position}' if current_queue_position else '')


def collect_image_history_thumbnails(history_record_values, server_base_address):
    """결과 이미지가 있는 이력만 갤러리 항목과 선택 ID로 만든다."""
    thumbnail_item_values=[]
    thumbnail_identifier_values=[]
    for current_history_record in history_record_values:
        current_image_path=current_history_record.get('image')
        if not isinstance(current_image_path,str) or not current_image_path:
            continue
        current_image_url=current_image_path if current_image_path.startswith(('http://','https://')) else server_base_address.rstrip('/')+current_image_path
        current_status_record=current_history_record.get('status',{})
        current_status_value=current_status_record.get('status','unknown') if isinstance(current_status_record,dict) else current_status_record
        thumbnail_item_values.append((current_image_url,f'{current_status_value} · {current_history_record["id"]}'))
        thumbnail_identifier_values.append(current_history_record['id'])
    return thumbnail_item_values,thumbnail_identifier_values


def build_history_reset_controls(deletion_scope_text):
    with gr.Accordion('생성 이력 초기화',open=False):
        gr.Markdown(deletion_scope_text)
        confirmation_checkbox_value=gr.Checkbox(value=False,label='초기화 범위를 확인했습니다.')
        reset_button_value=gr.Button('생성 이력 초기화',interactive=False)
        reset_status_value=gr.Markdown()
    confirmation_checkbox_value.change(lambda current_confirm_value:gr.update(interactive=bool(current_confirm_value)),confirmation_checkbox_value,reset_button_value,queue=False)
    return confirmation_checkbox_value,reset_button_value,reset_status_value


def bind_history_reset_action(control_component_values,execute_service_command,refresh_history_callback,history_output_components):
    confirmation_checkbox_value,reset_button_value,reset_status_value=control_component_values
    def execute_confirmed_reset(current_confirm_value):
        if current_confirm_value is not True:
            raise gr.Error('초기화 범위를 확인해 주세요.')
        # 삭제 정책과 실행 중 작업 보호는 기존 서비스가 담당한다.
        try:
            execute_service_command('history-reset',{'action':'reset'})
        except (ValueError, OSError) as history_reset_error:
            raise gr.Error(str(history_reset_error)) from history_reset_error
        history_update_values=refresh_history_callback()
        if not isinstance(history_update_values,(list,tuple)):
            history_update_values=[history_update_values]
        return [*history_update_values,False,gr.update(interactive=False),'생성 이력을 초기화했습니다.']
    reset_button_value.click(execute_confirmed_reset,confirmation_checkbox_value,[*history_output_components,confirmation_checkbox_value,reset_button_value,reset_status_value])
    return execute_confirmed_reset


def build_history_table_rows(current_history_records):
    """기본 Dataframe에 전달할 이력·진행 정보를 만든다."""
    current_table_rows=[]
    for current_history_record in current_history_records:
        current_status_record=current_history_record.get('status',{})
        current_progress_record=current_history_record.get('progress') or (current_status_record.get('progress',{}) if isinstance(current_status_record,dict) else {})
        current_progress_text=format_history_progress(current_progress_record) if current_progress_record else ''
        if current_progress_record.get('current_source_frame') is not None:
            current_progress_text+=f" · Fra:{current_progress_record['current_source_frame']}"
        if current_progress_record.get('detail'):
            current_progress_text+=' · '+str(current_progress_record['detail'])
        current_table_rows.append([format_generation_status(current_status_record),format_history_created_time(current_history_record),format_history_request_summary(current_history_record.get('request',{})),current_progress_text,current_history_record['id']])
    return current_table_rows


def collect_history_result_images(current_status_record, server_base_address):
    """저장된 원본·보더 크롭을 이름과 함께 공용 결과 영역에 표시한다."""
    result_image_sections=[]
    for result_field_name,result_image_label in (('image','생성 원본'),('repeated_image','추출 타일 반복 검수'),('separated_image','최종 · 단일 타일 생성'),('detected_image','사각형 검출'),('extracted_image','2행 2열 중앙 타일'),('rectified_image','정사각형 보정·크롭'),('cropped_image','보더 크롭 결과')):
        current_image_path=current_status_record.get(result_field_name)
        if not current_image_path:
            continue
        current_image_url=server_base_address.rstrip('/')+current_image_path
        result_image_sections.append((current_image_url,result_image_label))
    return result_image_sections


def render_generation_images(current_status_record, server_base_address):
    """기존 기능용 HTML 결과 렌더러의 호환 표현."""
    import html
    current_result_items=collect_history_result_images(current_status_record,server_base_address)
    return ''.join(f'<section><h3>{html.escape(current_image_label)}</h3><img width="100%" src="{html.escape(current_image_url,quote=True)}" alt="{html.escape(current_image_label)}"></section>' for current_image_url,current_image_label in current_result_items) or '<p>아직 생성된 결과 이미지가 없습니다.</p>'


def build_generation_history_view(execute_service_command,server_base_address,deletion_scope_text,restore_input_callback=None,restore_output_components=None,result_renderer_callback=None,record_folder_route=None,allow_individual_delete=False):
    """목록·페이지·명시적 조회·결과·입력·로그·초기화를 묶은 공용 영역."""
    import html
    from tools.review.common.gradio_logs import build_execution_logs,create_copyable_log_textbox
    with gr.Column():
        gr.Markdown('### 생성 이력',elem_classes=['generation-history-heading'])
        history_count_value=gr.Markdown('이력을 불러오는 중입니다.')
        with gr.Row(equal_height=True):
            history_refresh_button=gr.Button('새로고침',variant='secondary',scale=0,min_width=120)
            history_previous_button=gr.Button('← 이전',scale=0,min_width=120,interactive=False)
            history_page_value=gr.Number(value=1,minimum=1,precision=0,label='페이지 이동',show_label=False,container=False,scale=0,min_width=60,elem_classes=['generation-history-page'])
            history_next_button=gr.Button('다음 →',scale=0,min_width=120,interactive=False)
        history_selection_value=gr.Dropdown(choices=[],value=None,label='이력 선택',info='작업을 선택한 뒤 결과 조회·입력값 불러오기·중지·재개를 사용하세요.',interactive=True,elem_id='generation-history-selection')
        history_cards_value=gr.Dataframe(headers=['상태','생성 시각','설정','진행','ID'],value=[],datatype='str',type='array',interactive=False,wrap=True,label='현재 페이지의 생성 이력',elem_id='generation-history-cards')
        (history_selected_panel, history_selection_summary, selected_identifier_value, result_lookup_button, restore_input_button, history_resume_button, history_cancel_button, history_delete_button)=build_history_selection_panel(restore_input_callback is not None, allow_individual_delete)
        history_remaining_cards=gr.Gallery(value=[],label='현재 페이지의 결과 미리보기',columns=2,object_fit='contain',interactive=False,visible=False,elem_id='generation-history-remaining-cards')
        result_identifier_value=build_generation_identifier('조회한 생성 ID', 'generation-history-result-anchor')
        result_status_value=gr.Markdown('')
        result_image_value=gr.HTML(visible=False) if result_renderer_callback is not None else build_generation_gallery('조회한 생성 결과')
        with gr.Accordion('기록 위치 · 저장 입력',open=False):
            result_path_value=create_copyable_log_textbox(label='기록 폴더 절대 경로',interactive=False)
            folder_open_button_value=gr.Button('기록 폴더 열기',interactive=record_folder_route is not None,size='sm')
            folder_open_status_value=gr.Markdown()
            result_record_value=gr.JSON(label='저장된 입력 · 생성 기록')
        log_output_value,log_refresh_value,log_panel_value=build_execution_logs()
        reset_control_values=build_history_reset_controls(deletion_scope_text)

    def update_selected_generation(current_selected_identifier, selected_operation_name):
        if not current_selected_identifier:raise gr.Error('이력을 선택하세요.')
        try:
            selected_operation_result=execute_service_command(selected_operation_name,{'id':current_selected_identifier})
        except (ValueError,RuntimeError) as selected_operation_error:
            raise gr.Error(str(selected_operation_error))
        return '중지를 요청했습니다.' if selected_operation_name=='cancel' else '재개 요청을 접수했습니다. GPU 여유가 생기면 실행합니다.'
    history_cancel_button.click(lambda selected_job_identifier:update_selected_generation(selected_job_identifier,'cancel'),history_selection_value,result_status_value,queue=False)
    bind_gpu_generation_confirmation(history_resume_button,lambda selected_job_identifier:update_selected_generation(selected_job_identifier,'resume'),history_selection_value,result_status_value)

    def refresh_history_controls(current_selected_identifier):
        if not current_selected_identifier:return gr.update(interactive=False),gr.update(interactive=False)
        current_status_record=execute_service_command('status',{'id':current_selected_identifier})
        current_status_value=current_status_record.get('status')
        generation_resume_allowed=current_status_record.get('resume_allowed',True)
        return gr.update(interactive=current_status_value in ('running','queued','paused')),gr.update(interactive=generation_resume_allowed and current_status_value in ('failed','cancelled','paused'),value=('다음 단계' if current_status_value=='paused' else '생성 재개') if generation_resume_allowed else current_status_record['resume_block_reason'])
    # 자동 목록 갱신은 선택 처리 이벤트를 재실행하지 않는다. 사용자 선택만 처리한다.
    history_selection_value.input(refresh_history_controls,history_selection_value,[history_cancel_button,history_resume_button],queue=False)
    if hasattr(gr,'Timer'):
        gr.Timer(3).tick(refresh_history_controls,history_selection_value,[history_cancel_button,history_resume_button],queue=False,show_progress='hidden')

    def read_history_page(current_page_number,current_selected_identifier=None):
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_page_count=max(1,(len(current_history_records)+7)//8)
        current_page_number=max(1,min(int(current_page_number or 1),current_page_count))
        current_page_records=current_history_records[(current_page_number-1)*8:current_page_number*8]
        current_choice_values=[]
        for current_history_record in current_page_records:
            current_choice_values.append((format_history_choice_label(current_history_record),current_history_record['id']))
        selected_history_identifier=current_selected_identifier if current_selected_identifier in [value for _,value in current_choice_values] else None
        # 목록과 선택값을 함께 갱신하여 브라우저와 서버의 선택 상태를 맞춘다.
        selection_update_values = {'choices':current_choice_values, 'value':selected_history_identifier}
        current_thumbnail_items=collect_image_history_thumbnails(current_page_records,server_base_address)[0]
        return gr.update(**selection_update_values),f'총 {len(current_history_records)}건 · {current_page_number} / {current_page_count}페이지' if current_history_records else '생성 이력이 없습니다. 위 설정에서 생성을 시작하세요.',gr.update(value=current_page_number,maximum=current_page_count,interactive=current_page_count>1),build_history_table_rows(current_page_records),gr.update(interactive=current_page_number>1),gr.update(interactive=current_page_number<current_page_count),gr.update(value=current_thumbnail_items,visible=bool(current_thumbnail_items)),gr.update(visible=bool(selected_history_identifier))

    def update_selected_card_layout(current_page_number,current_selected_identifier):
        current_page_updates=read_history_page(current_page_number,current_selected_identifier)
        return [current_page_updates[index] for index in (3,6,7)]

    history_selection_value.input(update_selected_card_layout,[history_page_value,history_selection_value],[history_cards_value,history_remaining_cards,history_selected_panel],queue=False)

    def read_selected_result(current_selected_identifier):
        if not current_selected_identifier:raise gr.Error('목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.')
        current_status_record=execute_service_command('status',{'id':current_selected_identifier})
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_history_record=next((value for value in current_history_records if value['id']==current_selected_identifier),{})
        current_image_html=result_renderer_callback(current_selected_identifier,current_status_record,server_base_address) if result_renderer_callback is not None else collect_history_result_images(current_status_record,server_base_address)
        return current_selected_identifier,current_history_record.get('path','기록 경로가 없습니다.'),'상태: '+format_generation_status(current_status_record)+' · '+str(current_status_record.get('message',''))+(' · 대기 순서 '+str(current_status_record['queue_position']) if 'queue_position' in current_status_record else ''),gr.update(value=current_image_html,visible=True),current_history_record,gr.update(value=current_status_record.get('log') or '기록된 로그가 없습니다.',label='실행 로그 · '+current_selected_identifier)

    def describe_selected_history(current_selected_identifier):
        if not current_selected_identifier:
            disabled_update_value=gr.update(interactive=False)
            return ['목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.',disabled_update_value,*([disabled_update_value] if restore_input_callback is not None else [])]
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_history_record=next((record_value for record_value in current_history_records if record_value['id']==current_selected_identifier),None)
        if current_history_record is None:
            disabled_update_value=gr.update(interactive=False)
            return ['선택한 이력을 찾을 수 없습니다. 목록을 새로고침하세요.',disabled_update_value,*([disabled_update_value] if restore_input_callback is not None else [])]
        enabled_update_value=gr.update(interactive=True)
        return [format_history_selection_summary(current_history_record),enabled_update_value,*([enabled_update_value] if restore_input_callback is not None else [])]

    if restore_input_callback is not None:
        def restore_selected_inputs(current_selected_identifier):
            if not current_selected_identifier:raise gr.Error('입력값을 불러올 이력을 선택하세요.')
            current_history_records=execute_service_command('history',{}).get('records',[])
            current_history_record=next((value for value in current_history_records if value['id']==current_selected_identifier),None)
            if current_history_record is None:raise gr.Error('선택한 이력을 찾을 수 없습니다. 목록을 새로고침하세요.')
            return restore_input_callback(current_history_record)
        restore_input_button.click(restore_selected_inputs,history_selection_value,restore_output_components,queue=False)
    history_selection_value.input(lambda selected_history_identifier: selected_history_identifier or '',history_selection_value,selected_identifier_value,queue=False)
    history_selection_output_values=[history_selection_summary,result_lookup_button]
    if restore_input_callback is not None:history_selection_output_values.append(restore_input_button)
    history_selection_value.input(describe_selected_history,history_selection_value,history_selection_output_values,queue=False)
    # 전체 목록은 수동 갱신한다. 주기적 재렌더링은 썸네일 로딩과 선택 UI를 흔든다.
    history_refresh_button.click(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],preprocess=False,queue=False)
    history_previous_button.click(lambda current_page_number,current_selected_identifier:read_history_page((current_page_number or 1)-1,current_selected_identifier),[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],preprocess=False,queue=False)
    history_next_button.click(lambda current_page_number,current_selected_identifier:read_history_page((current_page_number or 1)+1,current_selected_identifier),[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],preprocess=False,queue=False)
    history_page_value.input(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],preprocess=False,queue=False)
    result_lookup_button.click(read_selected_result,history_selection_value,[result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value],queue=False).success(fn=None,js="()=>{requestAnimationFrame(()=>{document.getElementById('generation-history-result-anchor')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});});}")
    if record_folder_route is not None:
        folder_open_script=f"""async(identifierValue)=>{{if(!identifierValue)throw new Error('먼저 생성 이력을 선택하세요.');const responseValue=await fetch('/management/record-folder/open',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{route:{record_folder_route!r},id:identifierValue}})}});const payloadValue=await responseValue.json();if(!responseValue.ok)throw new Error(payloadValue.error);return payloadValue.message;}}"""
        folder_open_button_value.click(fn=None,inputs=result_identifier_value,outputs=folder_open_status_value,js=folder_open_script,queue=False)
    def refresh_selected_logs(current_selected_identifier,current_refresh_enabled):
        if not current_selected_identifier or not current_refresh_enabled:return gr.skip()
        return execute_service_command('status',{'id':current_selected_identifier}).get('log') or '기록된 로그가 없습니다.'
    if hasattr(log_panel_value,'expand'):
        log_panel_value.expand(refresh_selected_logs,[result_identifier_value,log_refresh_value],log_output_value,queue=False)
    if hasattr(gr,'Timer'):gr.Timer(3).tick(refresh_selected_logs,[result_identifier_value,log_refresh_value],log_output_value,queue=False,show_progress='hidden')
    def reset_view_values():
        reset_output_values=[*read_history_page(1),'','','',gr.update(value='' if result_renderer_callback is not None else [],visible=False),{},gr.update(value='',label='작업을 선택하세요'),'목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.',gr.update(interactive=False)]
        if restore_input_callback is not None:reset_output_values.append(gr.update(interactive=False))
        reset_output_values.append('')
        return reset_output_values
    reset_output_components=[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel,result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value,history_selection_summary,result_lookup_button]
    if restore_input_callback is not None:reset_output_components.append(restore_input_button)
    reset_output_components.append(selected_identifier_value)
    if allow_individual_delete:
        history_delete_confirmation=gr.Checkbox(value=False,visible=False)
        history_selection_value.input(lambda identifier:gr.update(interactive=bool(identifier)),history_selection_value,history_delete_button,queue=False)
        def delete_selected_history(selected_job_identifier,confirmed_delete_value):
            if confirmed_delete_value is not True:
                return [gr.skip() for _ in reset_output_components]
            if not selected_job_identifier:raise gr.Error('삭제할 이력을 선택하세요.')
            execute_service_command('history-delete',{'id':selected_job_identifier})
            return reset_view_values()
        history_delete_button.click(delete_selected_history,[history_selection_value,history_delete_confirmation],reset_output_components,js=(Path(__file__).resolve().parents[1]/'ui/shared/history-delete-confirmation.js').read_text().replace('__DELETION_SCOPE_TEXT__',json.dumps(deletion_scope_text,ensure_ascii=False)),trigger_mode='once')
    bind_history_reset_action(reset_control_values,execute_service_command,reset_view_values,reset_output_components)
    return read_history_page,[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel]
