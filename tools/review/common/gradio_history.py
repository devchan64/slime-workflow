"""생성이력 수동 초기화의 공용 UI와 명령 연결."""
import gradio as gr


HISTORY_SUMMARY_FIELD_NAMES=('tile_type','motion','action','directions','width','height','resolution','steps','seed')


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
    current_created_text=current_history_record.get('created_at') or current_history_record.get('createdAt') or '시각 없음'
    current_summary_values=[f'{current_field_name}={current_request_record[current_field_name]}' for current_field_name in HISTORY_SUMMARY_FIELD_NAMES if current_field_name in current_request_record]
    current_summary_text=' · '.join(current_summary_values) or '설정 요약 없음'
    return f"{current_status_label} · {current_created_text} · {current_history_record['id']} · {current_summary_text}"


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
        execute_service_command('history-reset',{})
        history_update_values=refresh_history_callback()
        if not isinstance(history_update_values,(list,tuple)):
            history_update_values=[history_update_values]
        return [*history_update_values,False,gr.update(interactive=False),'생성 이력을 초기화했습니다.']
    reset_button_value.click(execute_confirmed_reset,confirmation_checkbox_value,[*history_output_components,confirmation_checkbox_value,reset_button_value,reset_status_value])
    return execute_confirmed_reset


def build_generation_history_view(execute_service_command,server_base_address,deletion_scope_text,restore_input_callback=None,restore_output_components=None,result_renderer_callback=None,record_folder_route=None):
    """목록·페이지·명시적 조회·결과·입력·로그·초기화를 묶은 공용 영역."""
    import html
    from tools.review.common.gradio_logs import build_execution_logs,create_copyable_log_textbox
    with gr.Column(elem_classes=['generation-history-workspace']):
        with gr.Tabs():
            with gr.Tab('생성 이력 · 결과 조회'):
                history_selection_value=gr.Radio(choices=[],label='생성 이력')
                with gr.Row():
                    history_page_value=gr.Number(value=1,minimum=1,precision=0,label='페이지')
                    history_refresh_button=gr.Button('이력 새로고침')
                    result_lookup_button=gr.Button('선택 결과 조회',variant='primary')
                if restore_input_callback is not None:
                    restore_input_button=gr.Button('입력값 다시 불러오기')
                history_count_value=gr.Markdown()
                reset_control_values=build_history_reset_controls(deletion_scope_text)
        result_identifier_value=create_copyable_log_textbox(label='조회한 생성 ID',interactive=False)
        result_path_value=create_copyable_log_textbox(label='기록 폴더 절대 경로 · 복사 가능',interactive=False)
        folder_open_status_value=gr.Markdown()
        folder_open_button_value=gr.Button('기록 폴더 열기',interactive=record_folder_route is not None)
        result_status_value=gr.Markdown('이력을 선택한 뒤 결과 조회를 누르세요.')
        result_image_value=gr.HTML()
        with gr.Accordion('저장된 입력값 · 기록',open=False):
            result_record_value=gr.JSON(label='생성 기록')
        log_output_value,log_refresh_value,log_panel_value=build_execution_logs()

    def read_history_page(current_page_number,current_selected_identifier=None):
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_page_count=max(1,(len(current_history_records)+7)//8)
        current_page_number=max(1,min(int(current_page_number or 1),current_page_count))
        current_page_records=current_history_records[(current_page_number-1)*8:current_page_number*8]
        current_choice_values=[]
        for current_history_record in current_page_records:
            current_choice_values.append((format_history_choice_label(current_history_record),current_history_record['id']))
        selected_history_identifier=current_selected_identifier if current_selected_identifier in [value for _,value in current_choice_values] else None
        return gr.update(choices=current_choice_values,value=selected_history_identifier),f'{len(current_history_records)}개 · {current_page_number} / {current_page_count}페이지',current_page_number

    def read_selected_result(current_selected_identifier):
        if not current_selected_identifier:raise gr.Error('조회할 생성 이력을 선택하세요.')
        current_status_record=execute_service_command('status',{'id':current_selected_identifier})
        current_history_records=execute_service_command('history',{}).get('records',[])
        current_history_record=next((value for value in current_history_records if value['id']==current_selected_identifier),{})
        current_image_html=result_renderer_callback(current_selected_identifier,current_status_record,server_base_address) if result_renderer_callback is not None else '<p>아직 생성된 결과 이미지가 없습니다.</p>'
        if result_renderer_callback is None:
            current_image_path=current_status_record.get('image')
            if current_image_path:
                current_image_url=server_base_address.rstrip('/')+current_image_path
                current_image_html=f'<a href="{html.escape(current_image_url,quote=True)}" target="_blank" rel="noopener"><img src="{html.escape(current_image_url,quote=True)}" alt="생성 결과" style="width:100%;max-height:620px;object-fit:contain"></a>'
        return current_selected_identifier,current_history_record.get('path','기록 경로가 없습니다.'),'상태: '+str(current_status_record.get('status','unknown')),current_image_html,current_history_record,gr.update(value=current_status_record.get('log') or '기록된 로그가 없습니다.',label='실행 로그 · '+current_selected_identifier)

    if restore_input_callback is not None:
        def restore_selected_inputs(current_selected_identifier):
            if not current_selected_identifier:raise gr.Error('입력값을 불러올 이력을 선택하세요.')
            current_history_records=execute_service_command('history',{}).get('records',[])
            current_history_record=next((value for value in current_history_records if value['id']==current_selected_identifier),None)
            if current_history_record is None:raise gr.Error('선택한 이력을 찾을 수 없습니다. 목록을 새로고침하세요.')
            return restore_input_callback(current_history_record)
        restore_input_button.click(restore_selected_inputs,history_selection_value,restore_output_components,queue=False)
    history_refresh_button.click(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value],queue=False)
    history_page_value.change(read_history_page,[history_page_value,history_selection_value],[history_selection_value,history_count_value,history_page_value],queue=False)
    result_lookup_button.click(read_selected_result,history_selection_value,[result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value],queue=False)
    if record_folder_route is not None:
        folder_open_script=f"""async(identifierValue)=>{{if(!identifierValue)throw new Error('먼저 생성 이력을 선택하세요.');const responseValue=await fetch('/management/record-folder/open',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{route:{record_folder_route!r},id:identifierValue}})}});const payloadValue=await responseValue.json();if(!responseValue.ok)throw new Error(payloadValue.error);return payloadValue.message;}}"""
        folder_open_button_value.click(fn=None,inputs=result_identifier_value,outputs=folder_open_status_value,js=folder_open_script,queue=False)
    def refresh_selected_logs(current_selected_identifier,current_refresh_enabled):
        if not current_selected_identifier or not current_refresh_enabled:return gr.skip()
        return execute_service_command('status',{'id':current_selected_identifier}).get('log') or '기록된 로그가 없습니다.'
    log_panel_value.expand(refresh_selected_logs,[result_identifier_value,log_refresh_value],log_output_value,queue=False)
    if hasattr(gr,'Timer'):gr.Timer(3).tick(refresh_selected_logs,[result_identifier_value,log_refresh_value],log_output_value,queue=False)
    def reset_view_values():
        return [*read_history_page(1),'','초기화했습니다.','', '',{},gr.update(value='',label='작업을 선택하세요')]
    bind_history_reset_action(reset_control_values,execute_service_command,reset_view_values,[history_selection_value,history_count_value,history_page_value,result_identifier_value,result_path_value,result_status_value,result_image_value,result_record_value,log_output_value])
    return read_history_page,[history_selection_value,history_count_value,history_page_value]
