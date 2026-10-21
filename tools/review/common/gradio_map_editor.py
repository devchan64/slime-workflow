"""맵 검수에 합성하는 표준 Gradio 배치·지형 편집 패널."""
import copy
import json
import gradio as gr
from tools.review.common.management_client import execute_remote_management_command


def load_map_edit_draft(current_map_identifier,current_editor_state):
    if current_editor_state and current_editor_state.get('history'):raise gr.Error('미저장 초안이 있습니다. 저장하거나 초안 버리기를 실행하세요.')
    current_snapshot_record=execute_remote_management_command('map-assets','map-edit-load',{'map':current_map_identifier})
    current_draft_payload={'map':current_map_identifier,'revision':current_snapshot_record['revision'],'cells':[],'objects':[current_record for current_record in current_snapshot_record['tiles'].get('objects',[]) if current_record['kind']=='decoration']}
    current_editor_state={'snapshot':current_snapshot_record,'draft':current_draft_payload,'history':[]}
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
    if current_action_name=='undo':
        if not current_next_state['history']:raise gr.Error('되돌릴 변경이 없습니다.')
        current_next_state['draft']=current_next_state['history'].pop()
    else:
        if current_action_name in ('cell','add','move','delete-cell'):
            if current_cell_column is None or current_cell_row is None:raise gr.Error('맵에서 셀을 선택하거나 좌표를 입력하세요.')
            if int(current_cell_column)!=current_cell_column or int(current_cell_row)!=current_cell_row:raise gr.Error('셀 좌표는 정수로 입력하세요.')
            current_column_index=int(current_cell_column);current_row_index=int(current_cell_row)
            if not 0<=current_column_index<current_next_state['snapshot']['terrain']['columns'] or not 0<=current_row_index<current_next_state['snapshot']['terrain']['rows']:raise gr.Error('맵 범위 밖 좌표입니다.')
        current_next_state['history'].append(copy.deepcopy(current_draft_payload))
        if current_action_name=='cell':
            if current_tile_code not in current_next_state['snapshot']['codes'] or current_height_value is None or int(current_height_value)!=current_height_value or not 0<=current_height_value<=20:raise gr.Error('타일과 0~20 정수 높이를 선택하세요.')
            current_draft_payload['cells']=[current_record for current_record in current_draft_payload['cells'] if (current_record['column'],current_record['row'])!=(current_column_index,current_row_index)]
            current_draft_payload['cells'].append({'column':current_column_index,'row':current_row_index,'tile':current_tile_code,'height':int(current_height_value),'blocked':current_blocked_value})
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
    current_next_state=copy.deepcopy(current_editor_state);current_next_state['snapshot']=current_snapshot_record;current_next_state['draft']['revision']=current_snapshot_record['revision'];current_next_state['draft']['cells']=[];current_next_state['history']=[]
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


def build_map_editor_panel(current_map_choice,current_interaction_mode=None):
    with gr.Accordion('맵 편집 · 야외필드 타일·높이·빌보드',open=True):
        gr.Markdown('### 1. 편집할 타일 선택\n맵에서 타일을 클릭하고 **선택 셀 가져오기**를 누르세요. 직접 좌표를 입력한 뒤 **좌표의 셀 읽기**로 선택할 수도 있습니다. 편집 원본은 자동으로 준비됩니다.')
        current_editor_state=gr.State({});current_preview_state=gr.State({});current_render_data=gr.JSON(visible=False)
        current_loaded_map_id=gr.Textbox(value='',visible=False)
        with gr.Row():
            current_cell_column=gr.Number(label='선택 열',value=None,precision=0)
            current_cell_row=gr.Number(label='선택 행',value=None,precision=0)
            current_pick_button=gr.Button('선택 셀 가져오기',variant='primary')
            current_read_button=gr.Button('좌표의 셀 읽기')
        current_cell_status=gr.Markdown('아직 선택한 타일이 없습니다. 위 맵에서 타일을 클릭하세요.')
        gr.Markdown('### 2. 선택 대상 편집\n작업 버튼을 누르면 자동으로 검증하고 맵 미리보기를 갱신합니다. **저장 전까지는 초안**입니다. 검증 실패 시 마지막 정상 미리보기를 유지합니다.')
        current_object_choice=gr.Dropdown(label='배치된 빌보드 ID',choices=[],info='타일을 읽으면 해당 위치의 ID가 선택됩니다. 다른 ID를 직접 검색해 삭제하거나 이동할 수 있습니다.')
        with gr.Tabs():
            with gr.Tab('지형 · 타일과 높이'):
                with gr.Row():
                    current_tile_code=gr.Dropdown(label='지면 타일',choices=[])
                    current_height_value=gr.Number(label='지형 높이',value=0,precision=0,minimum=0,maximum=20)
                    current_blocked_value=gr.Checkbox(label='통행 차단',value=False)
                current_cell_button=gr.Button('셀 변경을 초안에 반영')
                gr.Markdown('높이는 0~20입니다. 통로·출구를 끊거나 빌보드 접지 높이를 바꾸면 검증에 실패할 수 있습니다.')
            with gr.Tab('빌보드 삭제'):
                current_delete_cell_button=gr.Button('선택 타일의 빌보드 삭제 · 초안')
                gr.Markdown('위 선택 셀 안내에 표시된 빌보드를 모두 제거합니다. 해당 좌표를 배치 기준점으로 사용하는 대상만 삭제하며, 옆 타일에서 걸쳐 보이는 빌보드는 포함하지 않습니다.')
                current_delete_button=gr.Button('선택 ID 삭제 · 초안')
                gr.Markdown('하나만 삭제하려면 ID를 선택하세요. 목록은 맵 전체 빌보드이며, 타일을 읽으면 해당 위치의 ID가 자동 선택됩니다.')
            with gr.Tab('빌보드 추가'):
                current_texture_choice=gr.Dropdown(label='추가할 빌보드 에셋',choices=[])
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
            current_undo_button=gr.Button('한 단계 되돌리기')
            current_preview_button=gr.Button('검증·미리보기')
            current_save_button=gr.Button('검증한 변경 저장',variant='primary',interactive=False)
        gr.Markdown('저장 버튼이 꺼져 있으면 위 상태를 확인하세요. 검증 실패는 값을 수정하거나 되돌린 뒤 다시 검증하세요. 변경이 없으면 저장하지 않습니다.')
        with gr.Accordion('원본 다시 읽기 · 초안 보관과 취소',open=False):
            gr.Markdown('현재 야외필드만 지원합니다. 새로고침하거나 화면을 닫기 전 저장하세요. 미저장 초안이 있으면 원본을 다시 읽을 수 없습니다.')
            current_load_button=gr.Button('편집 원본 불러오기')
            current_export_button=gr.Button('초안 JSON 표시');current_export_json=gr.JSON(label='보관할 초안',value={})
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
        for current_action_button,current_action_name in [(current_cell_button,'cell'),(current_delete_cell_button,'delete-cell'),(current_add_button,'add'),(current_move_button,'move'),(current_delete_button,'delete'),(current_undo_button,'undo')]:
            current_action_button.click(change_map_edit_draft,[current_editor_state,gr.State(current_action_name),current_move_column if current_action_name=='move' else current_cell_column,current_move_row if current_action_name=='move' else current_cell_row,current_tile_code,current_height_value,current_blocked_value,current_object_choice,current_texture_choice],[current_editor_state,current_object_choice,current_feedback_text,current_preview_state,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1).success(preview_map_edit_draft,current_editor_state,[current_preview_state,current_render_data,current_feedback_text,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1).success(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}")
        current_preview_button.click(preview_map_edit_draft,current_editor_state,[current_preview_state,current_render_data,current_feedback_text,current_save_button]).then(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}")
        current_save_button.click(save_map_edit_draft,[current_editor_state,current_preview_state],[current_editor_state,current_feedback_text,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1)
        current_editor_state.change(summarize_map_editor_changes,current_editor_state,current_change_summary,show_progress='hidden')
        current_export_button.click(lambda current_draft_state:current_draft_state.get('draft',{}),current_editor_state,current_export_json)
        def discard_map_edit_draft(current_discard_value,current_draft_state):
            if not current_discard_value:raise gr.Error('초안 버리기 확인란을 선택하세요.')
            if not current_draft_state:raise gr.Error('불러온 초안이 없습니다.')
            return {},{},current_draft_state['snapshot']['render'],'초안을 버렸습니다. 다시 편집하려면 원본을 불러오세요.',gr.update(interactive=False),False
        current_discard_button.click(discard_map_edit_draft,[current_discard_check,current_editor_state],[current_editor_state,current_preview_state,current_render_data,current_feedback_text,current_save_button,current_discard_check]).success(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{await window.mapReviewApplyDraft(currentRenderRecord);window.mapReviewEditingEnabled=false;}")
