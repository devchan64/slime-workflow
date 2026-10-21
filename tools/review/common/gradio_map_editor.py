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


def change_map_edit_draft(current_editor_state,current_action_name,current_cell_column,current_cell_row,current_tile_code,current_height_value,current_blocked_value,current_object_identifier,current_texture_identifier):
    if not current_editor_state:raise gr.Error('편집 원본을 먼저 불러오세요.')
    current_next_state=copy.deepcopy(current_editor_state)
    current_draft_payload=current_next_state['draft']
    if current_action_name=='undo':
        if not current_next_state['history']:raise gr.Error('되돌릴 변경이 없습니다.')
        current_next_state['draft']=current_next_state['history'].pop()
    else:
        if current_action_name in ('cell','add','move'):
            if current_cell_column is None or current_cell_row is None:raise gr.Error('맵에서 셀을 선택하거나 좌표를 입력하세요.')
            if int(current_cell_column)!=current_cell_column or int(current_cell_row)!=current_cell_row:raise gr.Error('셀 좌표는 정수로 입력하세요.')
            current_column_index=int(current_cell_column);current_row_index=int(current_cell_row)
            if not 0<=current_column_index<current_next_state['snapshot']['terrain']['columns'] or not 0<=current_row_index<current_next_state['snapshot']['terrain']['rows']:raise gr.Error('맵 범위 밖 좌표입니다.')
        current_next_state['history'].append(copy.deepcopy(current_draft_payload))
        if current_action_name=='cell':
            if current_tile_code not in current_next_state['snapshot']['codes'] or current_height_value is None or int(current_height_value)!=current_height_value or not 0<=current_height_value<=20:raise gr.Error('타일과 0~20 정수 높이를 선택하세요.')
            current_draft_payload['cells']=[current_record for current_record in current_draft_payload['cells'] if (current_record['column'],current_record['row'])!=(current_column_index,current_row_index)]
            current_draft_payload['cells'].append({'column':current_column_index,'row':current_row_index,'tile':current_tile_code,'height':int(current_height_value),'blocked':current_blocked_value})
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


def build_map_editor_panel(current_map_choice):
    with gr.Accordion('맵 편집 · 야외필드 타일·높이·빌보드',open=False):
        gr.Markdown('편집 원본 불러오기 → 맵 클릭·선택 셀 가져오기 → 초안 수정 → 검증·미리보기 → 저장. 높이는 0~20입니다. 도시·전투필드는 아직 편집하지 않습니다. 저장 전에는 원본을 변경하지 않습니다.')
        current_editor_state=gr.State({});current_preview_state=gr.State({});current_render_data=gr.JSON(visible=False)
        current_loaded_map_id=gr.Textbox(value='',visible=False)
        current_load_button=gr.Button('편집 원본 불러오기')
        with gr.Row():
            current_cell_column=gr.Number(label='선택 열',value=0,precision=0)
            current_cell_row=gr.Number(label='선택 행',value=0,precision=0)
            current_pick_button=gr.Button('선택 셀 가져오기')
            current_read_button=gr.Button('좌표의 셀 읽기')
        current_cell_status=gr.Markdown('맵에서 클릭한 셀을 가져오거나 좌표를 입력하세요.')
        with gr.Row():
            current_tile_code=gr.Dropdown(label='지면 타일',choices=[])
            current_height_value=gr.Number(label='지형 높이',value=0,precision=0,minimum=0,maximum=20)
            current_blocked_value=gr.Checkbox(label='통행 차단',value=False)
        current_cell_button=gr.Button('셀 변경을 초안에 반영')
        with gr.Row():
            current_object_choice=gr.Dropdown(label='배치된 빌보드 ID',choices=[])
            current_texture_choice=gr.Dropdown(label='추가할 빌보드 에셋',choices=[])
        with gr.Row():
            current_add_button=gr.Button('선택 좌표에 추가')
            current_move_button=gr.Button('선택 ID를 좌표로 이동')
            current_delete_button=gr.Button('선택 ID 삭제 · 초안')
        with gr.Row():
            current_undo_button=gr.Button('한 단계 되돌리기')
            current_preview_button=gr.Button('검증·미리보기')
            current_save_button=gr.Button('검증한 변경 저장',variant='primary',interactive=False)
        gr.Markdown('저장 버튼은 변경된 초안의 검증이 통과하면 활성화됩니다. 검증에 실패하면 좌표·고도·접지를 수정한 뒤 다시 검증하세요.')
        current_feedback_text=gr.Markdown('편집할 야외필드 맵을 선택하고 원본을 불러오세요.')
        with gr.Accordion('초안 보관·버리기',open=False):
            current_export_button=gr.Button('초안 JSON 표시');current_export_json=gr.JSON(label='보관할 초안',value={})
            current_discard_check=gr.Checkbox(label='미저장 초안을 버립니다',value=False)
            current_discard_button=gr.Button('초안 버리고 원본으로 복원')
        current_load_button.click(load_map_edit_draft,[current_loaded_map_id,current_editor_state],[current_editor_state,current_tile_code,current_texture_choice,current_object_choice,current_feedback_text,current_render_data],js="(currentMapIdentifier,currentDraftState)=>{if(!window.mapReviewControlOptions)throw Error('먼저 맵 불러오기를 실행하세요.');return [window.mapReviewControlOptions().selected,currentDraftState];}").success(fn=None,inputs=current_render_data,outputs=current_cell_status,js="async(currentRenderRecord)=>{if(!window.mapReviewApplyDraft)throw Error('먼저 맵 불러오기를 실행하세요.');await window.mapReviewApplyDraft(currentRenderRecord);window.mapReviewEditingEnabled=true;window.mapReviewSelectedCell=null;return '셀 선택 모드 · 맵에서 셀을 클릭하세요.';}")
        current_pick_button.click(fn=None,outputs=[current_cell_column,current_cell_row],js="()=>{const currentSelectedCell=window.mapReviewEditingEnabled?window.mapReviewSelectedCell:null;return currentSelectedCell?[currentSelectedCell.column,currentSelectedCell.row]:[null,null];}").then(read_map_edit_cell,[current_editor_state,current_cell_column,current_cell_row],[current_tile_code,current_height_value,current_blocked_value,current_cell_status])
        current_read_button.click(read_map_edit_cell,[current_editor_state,current_cell_column,current_cell_row],[current_tile_code,current_height_value,current_blocked_value,current_cell_status])
        for current_action_button,current_action_name in [(current_cell_button,'cell'),(current_add_button,'add'),(current_move_button,'move'),(current_delete_button,'delete'),(current_undo_button,'undo')]:
            current_action_button.click(change_map_edit_draft,[current_editor_state,gr.State(current_action_name),current_cell_column,current_cell_row,current_tile_code,current_height_value,current_blocked_value,current_object_choice,current_texture_choice],[current_editor_state,current_object_choice,current_feedback_text,current_preview_state,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1)
        current_preview_button.click(preview_map_edit_draft,current_editor_state,[current_preview_state,current_render_data,current_feedback_text,current_save_button]).then(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{if(currentRenderRecord.id)await window.mapReviewApplyDraft(currentRenderRecord);}")
        current_save_button.click(save_map_edit_draft,[current_editor_state,current_preview_state],[current_editor_state,current_feedback_text,current_save_button],concurrency_id='map-editor-draft',concurrency_limit=1)
        current_export_button.click(lambda current_draft_state:current_draft_state.get('draft',{}),current_editor_state,current_export_json)
        def discard_map_edit_draft(current_discard_value,current_draft_state):
            if not current_discard_value:raise gr.Error('초안 버리기 확인란을 선택하세요.')
            if not current_draft_state:raise gr.Error('불러온 초안이 없습니다.')
            return {},{},current_draft_state['snapshot']['render'],'초안을 버렸습니다. 다시 편집하려면 원본을 불러오세요.',gr.update(interactive=False),False
        current_discard_button.click(discard_map_edit_draft,[current_discard_check,current_editor_state],[current_editor_state,current_preview_state,current_render_data,current_feedback_text,current_save_button,current_discard_check]).success(fn=None,inputs=current_render_data,outputs=None,js="async(currentRenderRecord)=>{await window.mapReviewApplyDraft(currentRenderRecord);window.mapReviewEditingEnabled=false;}")
