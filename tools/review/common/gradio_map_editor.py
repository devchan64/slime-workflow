"""맵 검수에 합성하는 표준 Gradio 배치·지형 편집 패널."""
import copy
import json
import gradio as gr
from tools.review.common.management_client import execute_remote_management_command


def load_map_edit_draft(current_map_identifier,current_editor_state):
    if current_editor_state and current_editor_state.get('history'):raise gr.Error('미저장 초안이 있습니다. 저장하거나 초안 버리기를 실행하세요.')
    current_snapshot_record=execute_remote_management_command('map-assets','map-edit-load',{'map':current_map_identifier})
    current_draft_payload={'map':current_map_identifier,'revision':current_snapshot_record['revision'],'cells':[],'objects':[current_record for current_record in current_snapshot_record['tiles'].get('objects',[]) if current_record['kind']=='decoration']}
    current_editor_state={'snapshot':current_snapshot_record,'draft':current_draft_payload,'history':[],'future':[]}
    return current_editor_state,gr.update(choices=[(current_name+' · '+current_code,current_code) for current_code,current_name in current_snapshot_record['codes'].items()],value=None),gr.update(choices=current_snapshot_record['textures'],value=None),gr.update(choices=[current_record['id'] for current_record in current_draft_payload['objects']],value=None),f'{current_map_identifier} 편집 준비 완료. 맵에서 셀을 클릭한 뒤 선택 셀 가져오기를 누르세요.',current_snapshot_record['render']


def read_map_edit_cell(current_editor_state,current_cell_column,current_cell_row):
    if not current_editor_state:return gr.skip(),gr.skip(),gr.skip(),'편집 원본을 먼저 불러온 뒤 맵에서 셀을 선택하세요.'
    if current_cell_column is None or current_cell_row is None:return gr.skip(),gr.skip(),gr.skip(),'선택한 셀이 없습니다. 맵에서 셀을 클릭한 뒤 선택 셀 가져오기를 누르세요.'
    current_snapshot_record=current_editor_state['snapshot']
    current_column_index=int(current_cell_column);current_row_index=int(current_cell_row)
    if not 0<=current_column_index<current_snapshot_record['terrain']['columns'] or not 0<=current_row_index<current_snapshot_record['terrain']['rows']:raise gr.Error('맵 범위 밖 좌표입니다.')
    current_cell_record=next((current_record for current_record in current_editor_state['draft']['cells'] if (current_record['column'],current_record['row'])==(current_column_index,current_row_index)),None)
    if current_cell_record is None:current_cell_record={'tile':current_snapshot_record['tiles']['rows'][current_row_index][current_column_index],'height':current_snapshot_record['terrain']['elevations'][current_row_index][current_column_index],'blocked':[current_column_index,current_row_index] in current_snapshot_record['terrain']['blocked']}
    current_object_identifiers=[current_record['id'] for current_record in current_editor_state['draft']['objects'] if current_record['position']=={'column':current_column_index,'row':current_row_index}]
    return current_cell_record['tile'],current_cell_record['height'],current_cell_record['blocked'],f'선택 셀 ({current_column_index}, {current_row_index}) · 빌보드: '+(', '.join(current_object_identifiers) or '없음')


def select_map_editor_cell(current_map_identifier,current_editor_state,current_cell_column,current_cell_row):
    """선택 좌표와 셀 속성을 한 응답으로 갱신한다."""
    if not current_editor_state:
        current_editor_state=load_map_edit_draft(current_map_identifier,{})[0]
    if current_editor_state['draft']['map']!=current_map_identifier:
        raise gr.Error('불러온 초안과 표시 중인 맵이 다릅니다. 초안을 보관한 뒤 편집 원본을 불러오세요.')
    current_tile_value,current_height_value,current_blocked_value,current_status_text=read_map_edit_cell(current_editor_state,current_cell_column,current_cell_row)
    current_snapshot_record=current_editor_state['snapshot']
    current_object_records=current_editor_state['draft']['objects']
    current_selected_identifier=next((current_record['id'] for current_record in current_object_records if current_record['position']=={'column':current_cell_column,'row':current_cell_row}),None)
    current_tile_update=gr.update(choices=[(current_name+' · '+current_code,current_code) for current_code,current_name in current_snapshot_record['codes'].items()])
    if isinstance(current_tile_value,str):current_tile_update['value']=current_tile_value
    return current_editor_state,current_cell_column,current_cell_row,current_tile_update,current_height_value,current_blocked_value,current_status_text,gr.update(choices=current_snapshot_record['textures']),gr.update(choices=[current_record['id'] for current_record in current_object_records],value=current_selected_identifier)


def change_map_edit_draft(current_editor_state,current_action_name,current_cell_column,current_cell_row,current_tile_code,current_height_value,current_blocked_value,current_object_identifier,current_texture_identifier):
    if not current_editor_state:raise gr.Error('편집 원본을 먼저 불러오세요.')
    current_next_state=copy.deepcopy(current_editor_state)
    current_draft_payload=current_next_state['draft']
    current_previous_draft=copy.deepcopy(current_draft_payload)
    if current_action_name=='undo':
        if not current_next_state['history']:raise gr.Error('되돌릴 변경이 없습니다.')
        current_next_state.setdefault('future',[]).append(current_previous_draft)
        current_next_state['draft']=current_next_state['history'].pop()
    elif current_action_name=='redo':
        if not current_next_state.get('future'):raise gr.Error('다시 실행할 변경이 없습니다.')
        current_next_state['history'].append(current_previous_draft)
        current_next_state['draft']=current_next_state['future'].pop()
    else:
        if current_action_name in ('cell','add','move','delete-cell'):
            if current_cell_column is None or current_cell_row is None:raise gr.Error('맵에서 셀을 선택하거나 좌표를 입력하세요.')
            if int(current_cell_column)!=current_cell_column or int(current_cell_row)!=current_cell_row:raise gr.Error('셀 좌표는 정수로 입력하세요.')
            current_column_index=int(current_cell_column);current_row_index=int(current_cell_row)
            if not 0<=current_column_index<current_next_state['snapshot']['terrain']['columns'] or not 0<=current_row_index<current_next_state['snapshot']['terrain']['rows']:raise gr.Error('맵 범위 밖 좌표입니다.')
        if current_action_name=='cell':
            if current_tile_code not in current_next_state['snapshot']['codes'] or current_height_value is None or int(current_height_value)!=current_height_value or not 0<=current_height_value<=20:raise gr.Error('타일과 0~20 정수 높이를 선택하세요.')
            current_existing_wall=next((current_record['wall'] for current_record in current_draft_payload['cells'] if (current_record['column'],current_record['row'])==(current_column_index,current_row_index) and 'wall' in current_record),None)
            current_draft_payload['cells']=[current_record for current_record in current_draft_payload['cells'] if (current_record['column'],current_record['row'])!=(current_column_index,current_row_index)]
            current_draft_payload['cells'].append({'column':current_column_index,'row':current_row_index,'tile':current_tile_code,'height':int(current_height_value),'blocked':current_blocked_value,**({'wall':current_existing_wall} if current_existing_wall is not None else {})})
        elif current_action_name=='delete-cell':
            current_cell_objects=[current_record for current_record in current_draft_payload['objects'] if current_record['position']=={'column':current_column_index,'row':current_row_index}]
            if not current_cell_objects:raise gr.Error('선택한 타일에 배치된 빌보드가 없습니다. 좌표의 셀 읽기로 대상을 확인하세요.')
            current_draft_payload['objects']=[current_record for current_record in current_draft_payload['objects'] if current_record not in current_cell_objects]
        elif current_action_name=='add':
            if current_texture_identifier not in current_next_state['snapshot']['textures']:raise gr.Error('추가할 빌보드 에셋을 선택하세요.')
            current_next_index=1
            current_used_identifiers={current_record['id'] for current_record in current_draft_payload['objects']}
            while f'editor-billboard-{current_next_index}' in current_used_identifiers:current_next_index+=1
            current_draft_payload['objects'].append({'id':f'editor-billboard-{current_next_index}','kind':'decoration','position':{'column':current_column_index,'row':current_row_index},'textureKey':current_texture_identifier,'tileAnchor':'center'})
        elif current_action_name in ('move','delete'):
            current_selected_record=next((current_record for current_record in current_draft_payload['objects'] if current_record['id']==current_object_identifier),None)
            if current_selected_record is None:raise gr.Error('편집할 배치 ID를 선택하세요.')
            if current_action_name=='delete':current_draft_payload['objects'].remove(current_selected_record)
            else:current_selected_record['position']={'column':current_column_index,'row':current_row_index}
        else:raise gr.Error('지원하지 않는 편집 작업')
        if current_draft_payload!=current_previous_draft:
            current_next_state['history'].append(current_previous_draft)
            current_next_state['future']=[]
    return current_next_state,gr.update(choices=[current_record['id'] for current_record in current_next_state['draft']['objects']],value=None),f"초안 {len(current_next_state['history'])}단계 · 아직 저장하지 않았습니다. 검증·미리보기로 확인하세요.",{},gr.update(interactive=False)


def preview_map_edit_draft(current_editor_state):
    if not current_editor_state:raise gr.Error('편집 원본을 먼저 불러오세요.')
    try:current_preview_record=execute_remote_management_command('map-assets','map-edit-preview',current_editor_state['draft'])
    except Exception as current_preview_error:return {},{},'검증 실패 · 초안은 유지됩니다. '+str(current_preview_error),gr.update(interactive=False)
    return current_preview_record,current_preview_record['render'],('검증 완료' if current_preview_record['changed'] else '변경 없음 · 저장하지 않습니다')+f" · 변경 셀 {current_preview_record['cells']}개 · 장식 {current_preview_record['objects']}개 · 도달 가능 {current_preview_record['reachable']}칸. 미리보기를 확인한 뒤 저장하세요.",gr.update(interactive=current_preview_record['changed'])


def save_map_edit_draft(current_editor_state,current_preview_record):
    if not current_editor_state or not current_preview_record.get('token'):raise gr.Error('초안을 먼저 검증하세요.')
    try:execute_remote_management_command('map-assets','map-edit-save',{**current_editor_state['draft'],'token':current_preview_record['token']})
    except Exception as current_save_error:return current_editor_state,'저장 실패 · 초안은 유지됩니다. '+str(current_save_error),gr.update(interactive=False)
    current_snapshot_record=execute_remote_management_command('map-assets','map-edit-load',{'map':current_editor_state['draft']['map']})
    current_next_state=copy.deepcopy(current_editor_state);current_next_state['snapshot']=current_snapshot_record;current_next_state['draft']['revision']=current_snapshot_record['revision'];current_next_state['draft']['cells']=[];current_next_state['history']=[];current_next_state['future']=[]
    return current_next_state,'저장 완료 · 맵 원본·등록부·소비자 해시를 갱신했습니다.',gr.update(interactive=False)


def summarize_map_editor_changes(current_editor_state):
    """저장 전 변경 내역을 작업 결과로 표시한다."""
    if not current_editor_state:return '저장할 변경이 없습니다.'
    current_original_records={current_record['id']:current_record for current_record in current_editor_state['snapshot']['tiles'].get('objects',[]) if current_record['kind']=='decoration'}
    current_draft_records={current_record['id']:current_record for current_record in current_editor_state['draft']['objects']}
    current_added_identifiers=current_draft_records.keys()-current_original_records.keys()
    current_removed_identifiers=current_original_records.keys()-current_draft_records.keys()
    current_moved_identifiers=[current_identifier for current_identifier in current_draft_records.keys() & current_original_records.keys() if current_draft_records[current_identifier]!=current_original_records[current_identifier]]
    current_change_count=len(current_editor_state['draft']['cells'])+len(current_added_identifiers)+len(current_removed_identifiers)+len(current_moved_identifiers)
    if not current_change_count:return '저장할 변경이 없습니다.'
    current_summary_text=f"**미저장 변경** · 타일 {len(current_editor_state['draft']['cells'])}곳 · 빌보드 추가 {len(current_added_identifiers)}개 / 이동 {len(current_moved_identifiers)}개 / 삭제 {len(current_removed_identifiers)}개"
    if current_removed_identifiers:current_summary_text+='\n\n삭제 대상: '+', '.join(sorted(current_removed_identifiers))
    return current_summary_text


def describe_map_editor_history(current_editor_state):
    """현재 이력 위치와 실행 가능한 방향을 함께 표시한다."""
    current_history_records=(current_editor_state or {}).get('history',[])
    current_future_records=(current_editor_state or {}).get('future',[])
    current_history_count=len(current_history_records)
    current_future_count=len(current_future_records)
    current_history_text=f'**편집 이력 · {current_history_count} / {current_history_count+current_future_count}단계** · 되돌리기 {current_history_count}개 · 다시 실행 {current_future_count}개'
    if not current_history_count:current_history_text+='\n\n되돌릴 변경이 없습니다. 타일 또는 빌보드를 수정하면 사용할 수 있습니다.'
    if not current_future_count:current_history_text+='\n\n다시 실행할 변경이 없습니다. 먼저 한 단계 되돌리기를 사용하세요.'
    current_history_text+='\n\n드래그 한 번은 한 단계입니다. 새 편집을 하면 이후 이력을 비웁니다. 저장하면 현재 결과가 새 기준이 됩니다.'
    return gr.update(interactive=bool(current_history_count)),gr.update(interactive=bool(current_future_count)),current_history_text


def build_map_editor_panel(current_map_choice,current_interaction_mode=None,current_brush_controls=None,current_brush_mode=None):
    from tools.review.common.gradio_map_picker import build_map_asset_picker,bind_map_asset_picker
    with gr.Accordion('맵 편집 · 야외필드 타일·높이·빌보드',open=True):
        gr.Markdown('### 1. 편집할 타일 선택\n맵에서 타일을 클릭하고 **선택 셀 가져오기**를 누르세요. 직접 좌표를 입력한 뒤 **좌표의 셀 읽기**로 선택할 수도 있습니다. 편집 원본은 자동으로 준비됩니다.')
        current_editor_state=gr.State({});current_preview_state=gr.State({});current_render_data=gr.JSON(visible=False)
        from tools.review.common.gradio_map_autosave import MAP_AUTOSAVE_WRITE_SCRIPT,restore_map_autosave_state
        current_autosave_status=gr.Markdown('임시저장 대기 · 변경 시 현재 탭에 초안과 편집 이력을 자동 보관합니다.')
        current_autosave_data=gr.JSON(visible=False)
        current_loaded_map_id=gr.Textbox(value='',visible=False)
        with gr.Row():
            current_cell_column=gr.Number(label='선택 열',value=None,precision=0)
            current_cell_row=gr.Number(label='선택 행',value=None,precision=0)
            current_pick_button=gr.Button('선택 셀 가져오기',variant='primary')
            current_read_button=gr.Button('좌표의 셀 읽기')
        current_cell_status=gr.Markdown('아직 선택한 타일이 없습니다. 위 맵에서 타일을 클릭하세요.')
        gr.Markdown('### 2. 선택 대상 편집\n작업 버튼을 누르면 자동으로 검증하고 맵 미리보기를 갱신합니다. **저장 전까지는 초안**입니다. 검증 실패 시 마지막 정상 미리보기를 유지합니다.')
        current_object_choice=gr.Dropdown(label='배치된 빌보드 ID',choices=[],interactive=False,info='타일을 읽으면 해당 위치의 ID가 선택됩니다. 선택기에서 이름·ID로 검색한 뒤 삭제하거나 이동할 수 있습니다.')
        current_placed_picker=build_map_asset_picker('배치된 빌보드')
        bind_map_asset_picker(current_placed_picker,current_editor_state,'placed',current_object_choice)
        with gr.Tabs():
            with gr.Tab('지형 · 타일과 높이'):
                with gr.Row():
                    current_tile_code=gr.Dropdown(label='지면 타일',choices=[],interactive=False)
                    current_height_value=gr.Number(label='지형 높이',value=0,precision=0,minimum=0,maximum=20)
                    current_blocked_value=gr.Checkbox(label='통행 차단',value=False)
                current_detail_floor_picker=build_map_asset_picker('선택 셀 바닥 타일')
                bind_map_asset_picker(current_detail_floor_picker,current_editor_state,'floor',current_tile_code)
                current_cell_button=gr.Button('셀 변경을 초안에 반영')
                gr.Markdown('높이는 0~20입니다. 통로·출구를 끊거나 빌보드 접지 높이를 바꾸면 검증에 실패할 수 있습니다.')
            with gr.Tab('빌보드 삭제'):
                current_delete_cell_button=gr.Button('선택 타일의 빌보드 삭제 · 초안')
                gr.Markdown('위 선택 셀 안내에 표시된 빌보드를 모두 제거합니다. 해당 좌표를 배치 기준점으로 사용하는 대상만 삭제하며, 옆 타일에서 걸쳐 보이는 빌보드는 포함하지 않습니다.')
                current_delete_button=gr.Button('선택 ID 삭제 · 초안')
                gr.Markdown('하나만 삭제하려면 ID를 선택하세요. 목록은 맵 전체 빌보드이며, 타일을 읽으면 해당 위치의 ID가 자동 선택됩니다.')
            with gr.Tab('빌보드 추가'):
                current_texture_choice=gr.Dropdown(label='추가할 빌보드 에셋',choices=[],interactive=False)
                current_billboard_picker=build_map_asset_picker('추가할 빌보드')
                bind_map_asset_picker(current_billboard_picker,current_editor_state,'billboard',current_texture_choice)
                current_add_button=gr.Button('선택 좌표에 추가')
                gr.Markdown('에셋 이름을 검색해 선택하면 위 선택 열·행에 추가합니다. 접지·충돌 검증이 통과해야 미리보기에 표시됩니다.')
            with gr.Tab('빌보드 이동'):
                gr.Markdown('위 **배치된 빌보드 ID** 목록에서 이동할 대상을 선택한 뒤 목적지를 입력하세요. 위 선택 셀 좌표와 이동 목적지는 별개입니다.')
                with gr.Row():
                    current_move_column=gr.Number(label='이동 목적지 열',value=None,precision=0)
                    current_move_row=gr.Number(label='이동 목적지 행',value=None,precision=0)
                current_move_button=gr.Button('선택 ID를 좌표로 이동')
        gr.Markdown('### 3. 변경 확인 · 저장')
        current_change_summary=gr.Markdown('저장할 변경이 없습니다.')
        current_feedback_text=gr.Markdown('타일 선택부터 시작하세요. 수정 내용은 자동 검증되며, 검증을 통과하면 저장 버튼이 활성화됩니다.')
        with gr.Row():
            current_undo_button=gr.Button('한 단계 되돌리기',interactive=False)
            current_redo_button=gr.Button('한 단계 다시 실행',interactive=False)
            current_preview_button=gr.Button('검증·미리보기')
            current_save_button=gr.Button('검증한 변경 저장',variant='primary',interactive=False)
        current_history_status=gr.Markdown('편집 이력이 없습니다. 타일 또는 빌보드를 수정하면 되돌릴 수 있습니다.')
        gr.Markdown('저장 버튼이 꺼져 있으면 위 상태를 확인하세요. 검증 실패는 값을 수정하거나 되돌린 뒤 다시 검증하세요. 변경이 없으면 저장하지 않습니다.')
        with gr.Accordion('원본 다시 읽기 · 초안 보관과 취소',open=False):
            gr.Markdown('현재 야외필드만 지원합니다. 변경과 편집 이력은 현재 탭에 임시저장됩니다. 새로고침 후 맵을 불러오고 편집 모드로 전환하면 복구합니다. 탭을 닫기 전에는 원본 저장 또는 JSON 보관을 사용하세요.')
            current_load_button=gr.Button('편집 원본 불러오기')
            current_export_button=gr.Button('초안 JSON 표시');current_export_json=gr.JSON(label='보관할 초안',value={})
            current_stored_button=gr.Button('임시저장 JSON 표시')
            current_stored_clear_check=gr.Checkbox(label='보관한 임시본을 삭제합니다',value=False)
            current_stored_clear_button=gr.Button('임시본만 삭제')
            current_discard_check=gr.Checkbox(label='미저장 초안을 버립니다',value=False)
            current_discard_button=gr.Button('초안 버리고 원본으로 복원')
        current_load_button.click(load_map_edit_draft,[current_loaded_map_id,current_editor_state],[current_editor_state,current_tile_code,current_texture_choice,current_object_choice,current_feedback_text,current_render_data],js="(currentMapIdentifier,currentDraftState)=>{if(!window.mapReviewControlOptions)throw Error('먼저 맵 불러오기를 실행하세요.');return [window.mapReviewControlOptions().selected,currentDraftState];}").success(fn=None,inputs=current_render_data,outputs=current_cell_status,js="async(currentRenderRecord)=>{if(!window.mapReviewApplyDraft)throw Error('먼저 맵 불러오기를 실행하세요.');await window.mapReviewApplyDraft(currentRenderRecord);window.mapReviewEditingEnabled=true;window.mapReviewSelectedCell=null;return '셀 선택 모드 · 맵에서 셀을 클릭하세요.';}")
        current_selection_inputs=[current_loaded_map_id,current_editor_state,current_cell_column,current_cell_row]
        current_selection_outputs=[current_editor_state,current_cell_column,current_cell_row,current_tile_code,current_height_value,current_blocked_value,current_cell_status,current_texture_choice,current_object_choice]
        current_pick_button.click(select_map_editor_cell,current_selection_inputs,current_selection_outputs,js="(currentMapIdentifier,currentDraftState,currentColumnValue,currentRowValue)=>{const currentSelectedCell=window.mapReviewSelectedCell;window.mapReviewEditingEnabled=true;return [window.mapReviewControlOptions().selected,currentDraftState,currentSelectedCell?currentSelectedCell.column:null,currentSelectedCell?currentSelectedCell.row:null];}",show_progress='minimal')
        current_read_button.click(select_map_editor_cell,current_selection_inputs,current_selection_outputs,js="(currentMapIdentifier,currentDraftState,currentColumnValue,currentRowValue)=>{window.mapReviewEditingEnabled=true;return [window.mapReviewControlOptions().selected,currentDraftState,currentColumnValue,currentRowValue];}",show_progress='minimal')
        if current_interaction_mode is not None:
            for current_selection_button in (current_pick_button,current_read_button,current_load_button):
                current_selection_button.click(fn=None,outputs=current_interaction_mode,js="()=> 'edit'",queue=False)
        for current_action_button,current_action_name in [(current_cell_button,'cell'),(current_delete_cell_button,'delete-cell'),(current_add_button,'add'),(current_move_button,'move'),(current_delete_button,'delete'),(current_undo_button,'undo'),(current_redo_button,'redo')]:
            current_action_button.click(change_map_edit_draft,[current_editor_state,gr.State(current_action_name),current_move_column if current_action_name=='move' else current_cell_column,current_move_row if current_action_name=='move' else current_cell_row,current_tile_code,current_height_value,current_blocked_value,current_object_choice,current_texture_choice],[current_editor_state,current_object_choice,current_feedback_text,current_preview_state,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1).success(preview_map_edit_draft,current_editor_state,[current_preview_state,current_render_data,current_feedback_text,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1).success(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}")
        current_preview_button.click(preview_map_edit_draft,current_editor_state,[current_preview_state,current_render_data,current_feedback_text,current_save_button]).then(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}")
        current_save_button.click(save_map_edit_draft,[current_editor_state,current_preview_state],[current_editor_state,current_feedback_text,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1).success(lambda current_draft_state:current_draft_state,current_editor_state,current_autosave_data).success(fn=None,inputs=current_autosave_data,outputs=current_autosave_status,js="currentEditorState=>{if(currentEditorState?.draft&&!currentEditorState.history.length&&!currentEditorState.future?.length){sessionStorage.removeItem('slime-map-editor-draft-v1:'+currentEditorState.draft.map);return '원본 저장 완료 · 임시본을 정리했습니다.';}return '원본 저장 실패 · 임시본을 유지합니다.';}")
        current_editor_state.change(lambda current_draft_state:current_draft_state,current_editor_state,current_autosave_data,show_progress='hidden').success(fn=None,inputs=current_autosave_data,outputs=current_autosave_status,queue=False,js=MAP_AUTOSAVE_WRITE_SCRIPT)
        current_editor_state.change(describe_map_editor_history,current_editor_state,[current_undo_button,current_redo_button,current_history_status],show_progress='hidden')
        current_editor_state.change(summarize_map_editor_changes,current_editor_state,current_change_summary,show_progress='hidden')
        current_stored_button.click(fn=None,outputs=current_export_json,js="()=>{const currentSavedText=sessionStorage.getItem('slime-map-editor-draft-v1:'+window.mapReviewControlOptions().selected);return currentSavedText?JSON.parse(currentSavedText):{};}")
        current_stored_clear_button.click(fn=None,inputs=current_stored_clear_check,outputs=current_autosave_status,js="currentConfirmedValue=>{if(!currentConfirmedValue)return '임시본 삭제 확인란을 선택하세요. JSON을 먼저 보관할 수 있습니다.';sessionStorage.removeItem('slime-map-editor-draft-v1:'+window.mapReviewControlOptions().selected);return '임시본을 삭제했습니다. 화면의 초안은 유지되며 다음 변경부터 다시 임시저장합니다.';}")
        current_export_button.click(lambda current_draft_state:current_draft_state.get('draft',{}),current_editor_state,current_export_json)
        def discard_map_edit_draft(current_discard_value,current_draft_state):
            if not current_discard_value:raise gr.Error('초안 버리기 확인란을 선택하세요.')
            if not current_draft_state:raise gr.Error('불러온 초안이 없습니다.')
            return {},{},current_draft_state['snapshot']['render'],'초안을 버렸습니다. 다시 편집하려면 원본을 불러오세요.',gr.update(interactive=False),False
        current_discard_button.click(discard_map_edit_draft,[current_discard_check,current_editor_state],[current_editor_state,current_preview_state,current_render_data,current_feedback_text,current_save_button,current_discard_check]).success(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{await window.mapReviewApplyDraft(currentRenderRecord);window.mapReviewEditingEnabled=false;sessionStorage.removeItem('slime-map-editor-draft-v1:'+currentRenderRecord.id);}")

        if current_brush_controls is not None:
            from tools.review.common.gradio_map_brushes import apply_map_brush_batch
            _,current_brush_bridge,current_floor_choice,current_wall_choice,current_floor_picker,current_wall_picker=current_brush_controls
            bind_map_asset_picker(current_floor_picker,current_editor_state,'floor',current_floor_choice)
            bind_map_asset_picker(current_wall_picker,current_editor_state,'wall',current_wall_choice)
            def prepare_map_brush_state(current_map_identifier,current_draft_state,current_saved_record):
                try:
                    current_draft_state=restore_map_autosave_state(current_map_identifier,current_draft_state,current_saved_record,load_map_edit_draft)
                    if current_draft_state['draft']['map']!=current_map_identifier:raise ValueError('초안의 맵이 다릅니다. 먼저 초안을 보관하세요.')
                    return current_draft_state,gr.update(choices=[(current_name+' · '+current_code,current_code) for current_code,current_name in current_draft_state['snapshot']['codes'].items()]),'편집 준비 완료 · 상단 도구와 재질을 선택한 뒤 맵에 클릭·드래그하세요.'
                except Exception as current_prepare_error:raise gr.Error('편집 준비 실패 · '+str(current_prepare_error)) from current_prepare_error
            current_brush_mode.input(prepare_map_brush_state,[current_loaded_map_id,current_editor_state,gr.JSON(value=None,visible=False)],[current_editor_state,current_floor_choice,current_feedback_text],js="(currentMapIdentifier,currentDraftState,currentSavedRecord)=>{const currentMapId=window.mapReviewControlOptions().selected;const currentSavedText=sessionStorage.getItem('slime-map-editor-draft-v1:'+currentMapId);return [currentMapId,currentDraftState,currentSavedText?JSON.parse(currentSavedText):null];}",concurrency_id='map-editor-draft',concurrency_limit=1).success(preview_map_edit_draft,current_editor_state,[current_preview_state,current_render_data,current_feedback_text,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1).success(fn=None,inputs=current_render_data,outputs=None,js="async currentRenderRecord=>{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}")
            def submit_map_brush_events(current_map_identifier,current_draft_state,current_brush_events,current_wall_texture):
                try:
                    current_next_state,current_preview_record,current_render_record,current_status_text,current_save_update=apply_map_brush_batch(current_map_identifier,current_draft_state,current_brush_events)
                    return current_next_state,current_preview_record,current_render_record,current_status_text,current_save_update,gr.update(choices=[current_object_record['id'] for current_object_record in current_next_state['draft']['objects']],value=None)
                except Exception as current_brush_error:return gr.skip(),{}, {},'도구 적용 실패 · '+str(current_brush_error),gr.update(interactive=False),gr.skip()
            current_floor_choice.change(fn=None,inputs=current_floor_choice,queue=False,js="currentTileCode=>{window.mapReviewBrushTile=currentTileCode;}")
            current_wall_choice.change(fn=None,inputs=current_wall_choice,queue=False,js="currentWallTexture=>{window.mapReviewBrushWall=currentWallTexture;}")
            current_brush_bridge.click(submit_map_brush_events,[current_loaded_map_id,current_editor_state,gr.JSON(value=[],visible=False),current_wall_choice],[current_editor_state,current_preview_state,current_render_data,current_feedback_text,current_save_button,current_object_choice],js="(currentMapIdentifier,currentDraftState,currentBrushEvents,currentWallTexture)=>[window.mapReviewControlOptions().selected,currentDraftState,(window.mapReviewBrushQueue[0]||[]).map(currentBrushRecord=>({...currentBrushRecord,wall:currentBrushRecord.wall||currentWallTexture})),currentWallTexture]",concurrency_id='map-editor-draft',concurrency_limit=1,show_progress='minimal').success(fn=None,inputs=current_render_data,outputs=None,js="async currentRenderRecord=>{try{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}finally{window.mapReviewBrushQueue.shift();window.mapReviewBrushBusy=false;window.mapReviewFlushBrushQueue?.();}}").failure(fn=None,outputs=current_feedback_text,queue=False,js="()=>{window.mapReviewBrushBusy=false;return '도구 전송 실패 · 대기 입력을 유지했습니다. 연결 후 다시 맵에 적용하면 재시도합니다.';}")
