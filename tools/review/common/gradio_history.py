"""생성이력 수동 초기화의 공용 UI와 명령 연결."""
import gradio as gr
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_results import build_generation_gallery
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation


HISTORY_SUMMARY_FIELD_NAMES=('tag','tile_type','motion','action','start_frame','end_frame','directions','width','height','resolution','target_fps','speed','steps','seed')
HISTORY_SUMMARY_LABELS={'tag':'태그','tile_type':'타일','motion':'모션','action':'동작','width':'너비','height':'높이','resolution':'해상도','target_fps':'타겟 FPS','speed':'배속','steps':'스텝','seed':'시드'}
HISTORY_SUMMARY_FIELD_NAMES += ('duration_seconds',)
HISTORY_SUMMARY_LABELS['duration_seconds'] = '모션 길이(초)'
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


def render_history_selection_table(current_history_records,current_selected_identifier=None,server_base_address=''):
    """첫 열 선택과 결과 썸네일을 한 행에 표시한다."""
    import html
    current_table_rows=build_history_table_rows(current_history_records)
    if not current_table_rows:return '<p>생성 이력이 없습니다.</p>'
    current_header_names=('선택','썸네일','상태','생성 시각','설정','진행','ID')
    current_header_markup=''.join('<th scope="col">'+html.escape(current_header_name)+'</th>' for current_header_name in current_header_names)
    current_row_markup=[]
    for current_history_record,current_table_row in zip(current_history_records,current_table_rows):
        current_job_identifier=str(current_table_row[-1])
        current_checked_markup=' checked' if current_job_identifier==current_selected_identifier else ''
        current_radio_markup='<input type="radio" name="generation-history-job" value="'+html.escape(current_job_identifier,quote=True)+'" aria-label="'+html.escape(current_job_identifier+' 선택',quote=True)+'"'+current_checked_markup+'>'
        current_image_path=current_history_record.get('image')
        if isinstance(current_image_path,str) and current_image_path:
            current_image_url=current_image_path if current_image_path.startswith(('http://','https://')) else server_base_address.rstrip('/')+current_image_path
            current_thumbnail_markup='<img class="generation-history-table-thumbnail" src="'+html.escape(current_image_url,quote=True)+'" alt="'+html.escape(current_job_identifier+' 결과 썸네일',quote=True)+'" loading="lazy" decoding="async">'
        else:
            current_thumbnail_markup='<span class="generation-history-table-thumbnail is-empty" aria-label="결과 없음">결과 없음</span>'
        current_cell_markup=''.join('<td>'+html.escape(str(current_cell_value))+'</td>' for current_cell_value in current_table_row)
        current_row_markup.append('<tr><td>'+current_radio_markup+'</td><td>'+current_thumbnail_markup+'</td>'+current_cell_markup+'</tr>')
    return '<div style="overflow-x:auto"><table><caption>현재 페이지의 생성 이력</caption><thead><tr>'+current_header_markup+'</tr></thead><tbody>'+''.join(current_row_markup)+'</tbody></table></div>'


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


def build_generation_history_view(execute_service_command,server_base_address,deletion_scope_text,restore_input_callback=None,restore_output_components=None,result_renderer_callback=None,record_folder_route=None,allow_individual_delete=False,result_component_factory=None,individual_delete_scope_text=None):
    """목록·페이지·명시적 조회·결과·입력·로그·초기화를 묶은 공용 영역."""
    import html
    from tools.review.common.gradio_logs import build_execution_logs,create_copyable_log_textbox,bind_execution_log_updates
    with gr.Column():
        gr.Markdown('### 생성 이력',elem_classes=['generation-history-heading'])
        history_count_value=gr.Markdown('이력을 불러오는 중입니다.')
        with gr.Row(equal_height=True):
            history_refresh_button=gr.Button('새로고침',variant='secondary',scale=0,min_width=120)
            history_previous_button=gr.Button('← 이전',scale=0,min_width=120,interactive=False)
            history_page_value=gr.Number(value=1,minimum=1,precision=0,label='페이지 이동',show_label=False,container=False,scale=0,min_width=60,elem_classes=['generation-history-page'])
            history_next_button=gr.Button('다음 →',scale=0,min_width=120,interactive=False)
        history_selection_value=gr.Dropdown(choices=[],value=None,label='이력 선택',info='작업을 선택한 뒤 결과 조회·입력값 불러오기·중지·재개를 사용하세요.',interactive=True,visible=False,elem_id='generation-history-selection')
        gr.Markdown('첫 번째 열에서 작업을 선택한 뒤 결과 조회·입력값 불러오기·삭제를 사용하세요. 입력값을 불러오면 설정을 확인한 뒤 다시 생성할 수 있습니다.')
        history_cards_value=gr.HTML(value='',elem_id='generation-history-cards',js_on_load="watch('value',()=>{element.querySelectorAll('input[type=radio]').forEach(currentRadioInput=>{currentRadioInput.checked=currentRadioInput.hasAttribute('checked');});});element.addEventListener('change',(currentChangeEvent)=>{const currentRadioInput=currentChangeEvent.target;if(currentRadioInput.matches('input[type=radio]'))trigger('click',{identifier:currentRadioInput.value});});")
        (history_selected_panel, history_selection_summary, selected_identifier_value, result_lookup_button, restore_input_button, history_resume_button, history_cancel_button, history_delete_button)=build_history_selection_panel(restore_input_callback is not None, allow_individual_delete)
        if allow_individual_delete:
            current_delete_identifier=gr.State('')
            with gr.Group(visible=False) as current_delete_panel:
                gr.Markdown('### 선택한 생성 이력을 삭제할까요?')
                current_delete_display=build_generation_identifier('삭제할 생성 ID')
                gr.Markdown('선택 이력 삭제: '+(individual_delete_scope_text or deletion_scope_text)+' 개별 삭제는 위 ID의 작업에만 적용됩니다.')
                with gr.Row():
                    current_delete_cancel=gr.Button('취소')
                    current_delete_confirm=gr.Button('이력 삭제',variant='stop')
        result_identifier_value=build_generation_identifier('조회한 생성 ID', 'generation-history-result-anchor')
        result_status_value=gr.Markdown('')
        result_image_value=result_component_factory() if result_component_factory is not None else gr.HTML(visible=False) if result_renderer_callback is not None else build_generation_gallery('조회한 생성 결과')
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
    # 라디오 선택과 수동 목록 변경을 같은 선택 상태에 반영한다. 전체 목록은 주기적으로 갱신하지 않는다.
    history_selection_value.change(refresh_history_controls,history_selection_value,[history_cancel_button,history_resume_button],queue=False)
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
        return gr.update(**selection_update_values),f'총 {len(current_history_records)}건 · {current_page_number} / {current_page_count}페이지' if current_history_records else '생성 이력이 없습니다. 위 설정에서 생성을 시작하세요.',gr.update(value=current_page_number,maximum=current_page_count,interactive=current_page_count>1),render_history_selection_table(current_page_records,selected_history_identifier,server_base_address),gr.update(interactive=current_page_number>1),gr.update(interactive=current_page_number<current_page_count),gr.update(visible=bool(selected_history_identifier))

    def update_selected_card_layout(current_page_number,current_selected_identifier):
        current_page_updates=read_history_page(current_page_number,current_selected_identifier)
        return [current_page_updates[index] for index in (3,6)]

    def select_history_table_record(current_selection_event:gr.EventData):
        current_job_identifier=current_selection_event.identifier
        current_history_records=execute_service_command('history',{}).get('records',[])
        if current_job_identifier not in [current_record_value['id'] for current_record_value in current_history_records]:
            raise gr.Error('선택한 이력이 없습니다. 목록을 새로고침하세요.')
        return gr.update(value=current_job_identifier)
    history_cards_value.click(select_history_table_record,outputs=history_selection_value,queue=False)

    history_selection_value.change(update_selected_card_layout,[history_page_value,history_selection_value],[history_cards_value,history_selected_panel],queue=False)

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
    history_selection_value.change(lambda selected_history_identifier: selected_history_identifier or '',history_selection_value,selected_identifier_value,queue=False)
    history_selection_output_values=[history_selection_summary,result_lookup_button]
    if restore_input_callback is not None:history_selection_output_values.append(restore_input_button)
    history_selection_value.change(describe_selected_history,history_selection_value,history_selection_output_values,queue=False)
    # 전체 목록은 수동 갱신한다. 주기적 재렌더링은 썸네일 로딩과 선택 UI를 흔든다.
    history_refresh_button.click(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_selected_panel],preprocess=False,queue=False)
    history_previous_button.click(lambda current_page_number,current_selected_identifier:read_history_page((current_page_number or 1)-1,current_selected_identifier),[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_selected_panel],preprocess=False,queue=False)
    history_next_button.click(lambda current_page_number,current_selected_identifier:read_history_page((current_page_number or 1)+1,current_selected_identifier),[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_selected_panel],preprocess=False,queue=False)
    history_page_value.input(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_selected_panel],preprocess=False,queue=False)
    result_lookup_button.click(read_selected_result,history_selection_value,[result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value],queue=False).success(fn=None,js="()=>{requestAnimationFrame(()=>{document.getElementById('generation-history-result-anchor')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});});}")
    if record_folder_route is not None:
        folder_open_script=f"""async(identifierValue)=>{{if(!identifierValue)throw new Error('먼저 생성 이력을 선택하세요.');const responseValue=await fetch('/management/record-folder/open',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{route:{record_folder_route!r},id:identifierValue}})}});const payloadValue=await responseValue.json();if(!responseValue.ok)throw new Error(payloadValue.error);return payloadValue.message;}}"""
        folder_open_button_value.click(fn=None,inputs=result_identifier_value,outputs=folder_open_status_value,js=folder_open_script,queue=False)
    bind_execution_log_updates(execute_service_command,result_identifier_value,log_refresh_value,log_output_value,log_panel_value)
    def reset_view_values():
        reset_output_values=[*read_history_page(1),'','','',gr.update(value='' if result_renderer_callback is not None else [],visible=False),{},gr.update(value='',label='작업을 선택하세요'),'목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.',gr.update(interactive=False)]
        if restore_input_callback is not None:reset_output_values.append(gr.update(interactive=False))
        reset_output_values.append('')
        return reset_output_values
    reset_output_components=[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_selected_panel,result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value,history_selection_summary,result_lookup_button]
    if restore_input_callback is not None:reset_output_components.append(restore_input_button)
    reset_output_components.append(selected_identifier_value)
    if allow_individual_delete:
        history_selection_value.change(lambda identifier:gr.update(interactive=bool(identifier)),history_selection_value,history_delete_button,queue=False)
        def close_delete_confirmation():
            return gr.update(visible=False),'',''
        current_delete_outputs=[current_delete_panel,current_delete_identifier,current_delete_display]
        def open_delete_confirmation(current_selected_identifier):
            if not current_selected_identifier:raise gr.Error('삭제할 이력을 선택하세요.')
            return gr.update(visible=True),current_selected_identifier,current_selected_identifier
        def delete_selected_history(current_selected_identifier,current_confirmed_identifier):
            if not current_confirmed_identifier or current_selected_identifier!=current_confirmed_identifier:
                raise gr.Error('삭제 대상이 변경되었습니다. 이력 삭제를 다시 선택하세요.')
            try:
                execute_service_command('history-delete',{'id':current_confirmed_identifier})
            except (ValueError,RuntimeError) as current_delete_error:
                raise gr.Error(str(current_delete_error)) from current_delete_error
            return [*reset_view_values(),*close_delete_confirmation()]
        history_delete_button.click(open_delete_confirmation,history_selection_value,current_delete_outputs,queue=False)
        current_delete_cancel.click(close_delete_confirmation,outputs=current_delete_outputs,queue=False)
        history_selection_value.change(close_delete_confirmation,outputs=current_delete_outputs,queue=False)
        current_delete_confirm.click(delete_selected_history,[history_selection_value,current_delete_identifier],[*reset_output_components,*current_delete_outputs],trigger_mode='once')
    bind_history_reset_action(reset_control_values,execute_service_command,reset_view_values,reset_output_components)
    return read_history_page,[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_selected_panel]
