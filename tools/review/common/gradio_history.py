"""생성이력 수동 초기화의 공용 UI와 명령 연결."""
import gradio as gr
from pathlib import Path
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation


HISTORY_SUMMARY_FIELD_NAMES=('tag','tile_type','motion','action','start_frame','end_frame','directions','width','height','resolution','target_fps','speed','steps','seed')
HISTORY_SUMMARY_LABELS={'tag':'태그','tile_type':'타일','motion':'모션','action':'동작','width':'너비','height':'높이','resolution':'해상도','target_fps':'타겟 FPS','speed':'배속','steps':'스텝','seed':'시드'}
HISTORY_STATUS_LABELS={'queued':'GPU 대기 중','running':'생성 중','completed':'완료','cancelled':'중지됨','failed':'실패','missing':'기록 누락','unknown':'상태 미상'}
HISTORY_PROGRESS_STAGE_LABELS={'queued':'GPU 대기 중','starting':'생성 준비 중','load':'모델 로딩 중','inference':'추론 중','saving':'결과 저장 중','completed':'완료','failed':'실패'}
HISTORY_CARD_SELECTION_SCRIPT="""()=>{if(window.__slimeHistoryCardSelectionBound)return;window.__slimeHistoryCardSelectionBound=true;document.addEventListener('click',(clickEvent)=>{const selectedCardElement=clickEvent.target.closest('[data-job-id]');if(!selectedCardElement)return;const selectedJobIdentifier=selectedCardElement.dataset.jobId;const selectionInputElement=[...document.querySelectorAll('#generation-history-selection input')].find((inputElement)=>inputElement.value===selectedJobIdentifier);selectionInputElement?.click();});}"""


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


def format_history_choice_label(current_history_record):
    current_status_record=current_history_record.get('status',{})
    current_status_label=current_status_record.get('status','unknown') if isinstance(current_status_record,dict) else current_status_record
    current_request_record=current_history_record.get('request',{})
    current_created_text=format_history_created_time(current_history_record)
    current_summary_text=format_history_request_summary(current_request_record)
    current_status_label=HISTORY_STATUS_LABELS.get(current_status_label,current_status_label)
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
    current_status_text=HISTORY_STATUS_LABELS.get(current_status_label,current_status_label)
    return f"**선택한 생성 이력**\n\n상태: **{current_status_text}** · 생성 시각: {current_created_text}\n\nID: `{current_history_record['id']}`\n\n설정: {current_summary_text}"


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
        return f'{current_label_value} {current_percent_value:g}% · {current_completed_value}/{current_total_value}'+current_progress_record.get('unit','스텝')
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


def render_history_detail_cards(history_record_values, selected_history_identifier=None, server_base_address=""):
    """저장값을 이스케이프하여 선택 가능한 상세 카드로 표시한다."""
    import html
    card_html_values=[]
    for current_history_record in history_record_values:
        current_job_identifier=current_history_record['id']
        current_status_record=current_history_record.get('status',{})
        current_status_name=current_status_record.get('status','unknown') if isinstance(current_status_record,dict) else current_status_record
        current_request_record=current_history_record.get('request',{})
        current_action_name=current_request_record.get('action')
        if current_action_name in ('generate','prepare'):
            current_action_name=None
        current_task_name=current_request_record.get('motion') or current_action_name or current_request_record.get('tile_type') or ('이미지 생성' if current_request_record.get('prompt') else '생성 작업')
        current_tag_name=current_request_record.get('tag')
        current_card_title=(str(current_tag_name)+' · '+str(current_task_name)) if isinstance(current_tag_name,str) and current_tag_name.strip() else current_task_name
        current_created_text=format_history_created_time(current_history_record).split('.')[0]
        current_detail_values=[]
        for current_field_name in HISTORY_SUMMARY_FIELD_NAMES:
            if current_field_name not in current_request_record or current_field_name in ('motion','action','tile_type','end_frame'):continue
            current_field_value=current_request_record[current_field_name]
            if current_field_name=='start_frame':current_field_value=f"{current_field_value}–{current_request_record.get('end_frame',current_field_value)}"
            if current_field_name=='directions' and isinstance(current_field_value,list):current_field_value=f'{len(current_field_value)}방향'
            current_field_label={'start_frame':'프레임','directions':'방향'}.get(current_field_name,HISTORY_SUMMARY_LABELS.get(current_field_name,current_field_name))
            current_detail_values.append(f'<div><dt>{html.escape(current_field_label)}</dt><dd>{html.escape(str(current_field_value))}</dd></div>')
        current_selected_flag=current_job_identifier==selected_history_identifier
        current_image_path=current_history_record.get('image')
        if current_image_path:
            current_image_url=current_image_path if current_image_path.startswith(('http://','https://')) else server_base_address.rstrip('/')+'/'+current_image_path.lstrip('/')
            current_thumbnail_html=f'<img class="history-card-thumbnail" src="{html.escape(current_image_url,quote=True)}" alt="생성 결과 미리보기" loading="lazy" decoding="async">'
        else:
            current_thumbnail_html='<span class="history-card-thumbnail history-card-placeholder">'+('결과 준비 중' if current_status_name in ('queued','running') else '이미지 없음')+'</span>'
        progress_html_value = ''
        progress_record_value=current_history_record.get('progress') or (current_status_record.get('progress') if isinstance(current_status_record,dict) else None)
        if progress_record_value:
            progress_percent_raw_value=progress_record_value.get('percent')
            progress_percent_value=max(0,min(100,float(progress_percent_raw_value))) if isinstance(progress_percent_raw_value,(int,float)) else None
            progress_title_value=progress_record_value.get('label',HISTORY_PROGRESS_STAGE_LABELS.get(progress_record_value.get('stage','starting'),'진행 상태'))
            progress_label_value=format_history_progress(progress_record_value)
            if progress_record_value.get('current_source_frame') is not None:
                progress_label_value += f" · Fra:{progress_record_value['current_source_frame']}"
            if progress_record_value.get('detail'):
                progress_label_value += ' · '+progress_record_value['detail']
            progress_bar_html_value=f'<progress style="width:100%" value="{progress_percent_value}" max="100" aria-label="{html.escape(progress_title_value,quote=True)} 진행률"></progress>' if progress_percent_value is not None else ''
            progress_html_value = f'<span class="history-card-progress">{html.escape(progress_label_value)}{progress_bar_html_value}</span>'
        card_html_values.append(f'<button type="button" class="generation-detail-card" data-job-id="{html.escape(current_job_identifier,quote=True)}" aria-pressed="{str(current_selected_flag).lower()}"><span class="history-card-content">{current_thumbnail_html}<span class="history-card-fields"><span class="history-card-heading"><strong>{html.escape(str(current_card_title))}</strong><span class="history-card-state">{html.escape(HISTORY_STATUS_LABELS.get(current_status_name,current_status_name))}</span></span><time>{html.escape(current_created_text)}</time><dl>{"".join(current_detail_values)}</dl></span></span>{progress_html_value}<span class="history-card-id">ID · {html.escape(current_job_identifier)}</span><span class="history-card-select">{"선택됨" if current_selected_flag else "이 작업 선택"}</span></button>')
    return '<div class="generation-detail-cards">'+''.join(card_html_values)+'</div>'


def render_generation_images(current_status_record, server_base_address):
    """저장된 원본·보더 크롭을 이름과 함께 공용 결과 영역에 표시한다."""
    import html
    result_image_sections=[]
    for result_field_name,result_image_label in (('image','생성 원본'),('separated_image','최종 · 단일 타일 생성'),('detected_image','사각형 검출'),('extracted_image','2행 2열 중앙 타일'),('rectified_image','정사각형 보정·크롭'),('cropped_image','보더 크롭 결과')):
        current_image_path=current_status_record.get(result_field_name)
        if not current_image_path:
            continue
        current_image_url=server_base_address.rstrip('/')+current_image_path
        escaped_image_url=html.escape(current_image_url,quote=True)
        result_image_sections.append(f'<section><h3>{result_image_label}</h3><a href="{escaped_image_url}" target="_blank" rel="noopener"><img src="{escaped_image_url}" alt="{result_image_label}"></a></section>')
    return '<div class="generation-result-images">'+''.join(result_image_sections)+'</div>' if result_image_sections else '<p>아직 생성된 결과 이미지가 없습니다.</p>'


def build_generation_history_view(execute_service_command,server_base_address,deletion_scope_text,restore_input_callback=None,restore_output_components=None,result_renderer_callback=None,record_folder_route=None,allow_individual_delete=False):
    """목록·페이지·명시적 조회·결과·입력·로그·초기화를 묶은 공용 영역."""
    import html
    from tools.review.common.gradio_logs import build_execution_logs,create_copyable_log_textbox
    with gr.Column(elem_classes=['generation-history-workspace']):
        gr.Markdown('### 생성 이력',elem_classes=['generation-history-heading'])
        with gr.Row(elem_classes=['generation-history-toolbar']):
            with gr.Column(scale=3,min_width=0):
                history_count_value=gr.Markdown('이력을 불러오는 중입니다.')
            history_refresh_button=gr.Button('새로고침',variant='secondary',scale=0,min_width=90)
            history_previous_button=gr.Button('← 이전',scale=0,min_width=80,interactive=False)
            history_page_value=gr.Number(value=1,minimum=1,precision=0,label='페이지 이동',show_label=False,container=False,scale=0,min_width=60,elem_classes=['generation-history-page'])
            history_next_button=gr.Button('다음 →',scale=0,min_width=80,interactive=False)
        history_selection_value=gr.Radio(choices=[],label='이력 선택',interactive=True,elem_id='generation-history-selection',elem_classes=['generation-history-selection-input'])
        history_cards_value=gr.HTML(render_history_detail_cards([]),elem_id='generation-history-cards')
        with gr.Column(visible=False,elem_classes=['generation-history-selected-actions']) as history_selected_panel:
            history_selection_summary=gr.Markdown('목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.')
            with gr.Row(elem_classes=['generation-history-actions']+(['generation-history-actions-five'] if allow_individual_delete else [])):
                result_lookup_button=gr.Button('결과 조회',variant='primary',interactive=False)
                if restore_input_callback is not None:
                    restore_input_button=gr.Button('입력값 불러오기',interactive=False)
                else:
                    gr.Button('입력 복원 미지원',interactive=False)
                history_resume_button=gr.Button('생성 재개',interactive=False)
                history_cancel_button=gr.Button('작업 중지',interactive=False)
                if allow_individual_delete:
                    history_delete_button=gr.Button('선택 이력 삭제',interactive=False)
        history_remaining_cards=gr.HTML('',elem_id='generation-history-remaining-cards')
        result_identifier_value=create_copyable_log_textbox(label='조회한 생성 ID',interactive=False,elem_id='generation-history-result-anchor')
        result_status_value=gr.Markdown('')
        result_image_value=gr.HTML(visible=False)
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
        current_status_value=execute_service_command('status',{'id':current_selected_identifier}).get('status')
        return gr.update(interactive=current_status_value in ('running','queued')),gr.update(interactive=current_status_value in ('failed','cancelled'))
    history_selection_value.change(refresh_history_controls,history_selection_value,[history_cancel_button,history_resume_button],queue=False)
    if hasattr(gr,'Timer'):
        gr.Timer(3).tick(refresh_history_controls,history_selection_value,[history_cancel_button,history_resume_button],queue=False)

    def read_history_page(current_page_number,current_selected_identifier=None):
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_page_count=max(1,(len(current_history_records)+7)//8)
        current_page_number=max(1,min(int(current_page_number or 1),current_page_count))
        current_page_records=current_history_records[(current_page_number-1)*8:current_page_number*8]
        current_choice_values=[]
        for current_history_record in current_page_records:
            current_choice_values.append((format_history_choice_label(current_history_record),current_history_record['id']))
        selected_history_identifier=current_selected_identifier if current_selected_identifier in [value for _,value in current_choice_values] else None
        selected_card_end=next((index+1 for index,record in enumerate(current_page_records) if record['id']==selected_history_identifier),len(current_page_records))
        return gr.update(choices=current_choice_values,value=selected_history_identifier),f'총 {len(current_history_records)}건 · {current_page_number} / {current_page_count}페이지' if current_history_records else '생성 이력이 없습니다. 위 설정에서 생성을 시작하세요.',gr.update(value=current_page_number,maximum=current_page_count,interactive=current_page_count>1),render_history_detail_cards(current_page_records[:selected_card_end],selected_history_identifier,server_base_address),gr.update(interactive=current_page_number>1),gr.update(interactive=current_page_number<current_page_count),render_history_detail_cards(current_page_records[selected_card_end:],None,server_base_address),gr.update(visible=bool(selected_history_identifier))

    def update_selected_card_layout(current_page_number,current_selected_identifier):
        current_page_updates=read_history_page(current_page_number,current_selected_identifier)
        return [current_page_updates[index] for index in (3,6,7)]

    history_selection_value.change(update_selected_card_layout,[history_page_value,history_selection_value],[history_cards_value,history_remaining_cards,history_selected_panel],queue=False)

    def read_selected_result(current_selected_identifier):
        if not current_selected_identifier:raise gr.Error('목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.')
        current_status_record=execute_service_command('status',{'id':current_selected_identifier})
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_history_record=next((value for value in current_history_records if value['id']==current_selected_identifier),{})
        current_image_html=result_renderer_callback(current_selected_identifier,current_status_record,server_base_address) if result_renderer_callback is not None else render_generation_images(current_status_record,server_base_address)
        return current_selected_identifier,current_history_record.get('path','기록 경로가 없습니다.'),'상태: '+str(current_status_record.get('status','unknown'))+' · '+str(current_status_record.get('message',''))+(' · 대기 순서 '+str(current_status_record['queue_position']) if 'queue_position' in current_status_record else ''),gr.update(value=current_image_html,visible=True),current_history_record,gr.update(value=current_status_record.get('log') or '기록된 로그가 없습니다.',label='실행 로그 · '+current_selected_identifier)

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
    history_selection_output_values=[history_selection_summary,result_lookup_button]
    if restore_input_callback is not None:history_selection_output_values.append(restore_input_button)
    history_selection_value.change(describe_selected_history,history_selection_value,history_selection_output_values,queue=False)
    if hasattr(gr,'Timer'):
        gr.Timer(3).tick(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],queue=False)
    history_refresh_button.click(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],queue=False)
    history_previous_button.click(lambda current_page_number,current_selected_identifier:read_history_page((current_page_number or 1)-1,current_selected_identifier),[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],queue=False)
    history_next_button.click(lambda current_page_number,current_selected_identifier:read_history_page((current_page_number or 1)+1,current_selected_identifier),[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],queue=False)
    history_page_value.change(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel],queue=False)
    result_lookup_button.click(read_selected_result,history_selection_value,[result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value],queue=False).success(fn=None,js="()=>{requestAnimationFrame(()=>{document.getElementById('generation-history-result-anchor')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});});}")
    if record_folder_route is not None:
        folder_open_script=f"""async(identifierValue)=>{{if(!identifierValue)throw new Error('먼저 생성 이력을 선택하세요.');const responseValue=await fetch('/management/record-folder/open',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{route:{record_folder_route!r},id:identifierValue}})}});const payloadValue=await responseValue.json();if(!responseValue.ok)throw new Error(payloadValue.error);return payloadValue.message;}}"""
        folder_open_button_value.click(fn=None,inputs=result_identifier_value,outputs=folder_open_status_value,js=folder_open_script,queue=False)
    def refresh_selected_logs(current_selected_identifier,current_refresh_enabled):
        if not current_selected_identifier or not current_refresh_enabled:return gr.skip()
        return execute_service_command('status',{'id':current_selected_identifier}).get('log') or '기록된 로그가 없습니다.'
    if hasattr(log_panel_value,'expand'):
        log_panel_value.expand(refresh_selected_logs,[result_identifier_value,log_refresh_value],log_output_value,queue=False)
    if hasattr(gr,'Timer'):gr.Timer(3).tick(refresh_selected_logs,[result_identifier_value,log_refresh_value],log_output_value,queue=False)
    def reset_view_values():
        reset_output_values=[*read_history_page(1),'','','',gr.update(value='',visible=False),{},gr.update(value='',label='작업을 선택하세요'),'목록에서 작업을 선택하세요. 결과 조회·입력 재사용·중지·재개를 할 수 있습니다.',gr.update(interactive=False)]
        if restore_input_callback is not None:reset_output_values.append(gr.update(interactive=False))
        return reset_output_values
    reset_output_components=[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel,result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value,history_selection_summary,result_lookup_button]
    if restore_input_callback is not None:reset_output_components.append(restore_input_button)
    if allow_individual_delete:
        history_delete_confirmation=gr.Checkbox(value=False,visible=False)
        history_selection_value.change(lambda identifier:gr.update(interactive=bool(identifier)),history_selection_value,history_delete_button,queue=False)
        def delete_selected_history(selected_job_identifier,confirmed_delete_value):
            if confirmed_delete_value is not True:
                return [gr.skip() for _ in reset_output_components]
            if not selected_job_identifier:raise gr.Error('삭제할 이력을 선택하세요.')
            execute_service_command('history-delete',{'id':selected_job_identifier})
            return reset_view_values()
        history_delete_button.click(delete_selected_history,[history_selection_value,history_delete_confirmation],reset_output_components,js=(Path(__file__).resolve().parents[1]/'ui/shared/history-delete-confirmation.js').read_text(),trigger_mode='once')
    bind_history_reset_action(reset_control_values,execute_service_command,reset_view_values,reset_output_components)
    return read_history_page,[history_selection_value,history_count_value,history_page_value,history_cards_value,history_previous_button,history_next_button,history_remaining_cards,history_selected_panel]
