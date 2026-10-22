"""캔버스 반복 편집 도구와 Gradio 초안 연결."""
import copy
import json
from pathlib import Path
import gradio as gr
from tools.review.common.map_asset_sources import MAP_BLOCKED_TERRAIN_NAMES
from tools.review.maintenance.sync_billboard_catalog import load_unique_yaml_document

MAP_BRUSH_TOOL_LABELS=(('pan','화면 이동'),('floor','바닥 페인팅'),('wall','옆면 페인팅'),('place','빌보드 배치'),('delete','빌보드 삭제'),('raise','높이 +1'),('lower','높이 −1'))


def build_map_brush_toolbar():
    """도구 재선택은 기본 화면 이동으로 돌아간다."""
    current_catalog_path=Path(__file__).resolve().parents[1]/'ui/map/config/tile-catalog.yaml'
    current_catalog_record=load_unique_yaml_document(current_catalog_path)
    current_wall_choices=[current_tile_record['id'] for current_tile_record in current_catalog_record['tiles'] if current_tile_record['category']=='wall']
    from tools.review.common.gradio_map_picker import build_map_asset_picker
    with gr.Group(visible=False) as current_brush_group:
        with gr.Row():
            current_tool_buttons=[gr.Button(current_tool_label,variant='primary' if current_tool_name=='pan' else 'secondary') for current_tool_name,current_tool_label in MAP_BRUSH_TOOL_LABELS]
        current_brush_status=gr.Markdown('화면 이동 · 드래그로 이동합니다. 도구를 다시 누르면 화면 이동으로 돌아갑니다.')
        with gr.Row():
            current_floor_choice=gr.Dropdown(label='페인팅할 바닥 타일',choices=[],info='바닥 도구에서 썸네일 선택기를 여세요.',interactive=False,visible=False)
            current_wall_choice=gr.Dropdown(label='페인팅할 옆면 타일',choices=current_wall_choices,value=current_wall_choices[0] if current_wall_choices else None,interactive=False,visible=False)
        current_billboard_choice=gr.Dropdown(label='배치할 빌보드',choices=[],interactive=False,visible=False,info='빌보드 선택기에서 에셋을 선택한 뒤 맵을 클릭하거나 드래그하세요.')
        current_billboard_picker=build_map_asset_picker('빌보드',gr.Button('빌보드 선택기 열기',visible=False))
        current_floor_picker=build_map_asset_picker('바닥 타일',gr.Button('바닥 타일 선택기 열기',visible=False))
        current_wall_picker=build_map_asset_picker('옆면 타일',gr.Button('옆면 타일 선택기 열기',visible=False))
        current_brush_bridge=gr.HTML('',js_on_load="window.mapReviewBrushListener?.abort();window.mapReviewBrushListener=new AbortController();window.addEventListener('map-editor-brush',()=>trigger('click'),{signal:window.mapReviewBrushListener.signal});",min_height=0)
    for current_tool_button,(current_tool_name,current_tool_label) in zip(current_tool_buttons,MAP_BRUSH_TOOL_LABELS):
        current_tool_button.click(fn=None,outputs=[*current_tool_buttons,current_brush_status,current_floor_choice,current_wall_choice,current_billboard_choice,current_floor_picker[0],current_wall_picker[0],current_billboard_picker[0],current_floor_picker[1],current_wall_picker[1],current_billboard_picker[1]],queue=False,js="()=>{const currentToolNames="+json.dumps([current_tool_name for current_tool_name,_ in MAP_BRUSH_TOOL_LABELS])+";const currentToolLabels="+json.dumps(dict(MAP_BRUSH_TOOL_LABELS),ensure_ascii=False)+";const currentRequestedTool="+json.dumps(current_tool_name)+";window.mapReviewClearHover?.();window.mapReviewBrushTool=window.mapReviewBrushTool===currentRequestedTool?'pan':currentRequestedTool;return [...currentToolNames.map(currentToolName=>({__type__:'update',variant:currentToolName===window.mapReviewBrushTool?'primary':'secondary'})),currentToolLabels[window.mapReviewBrushTool]+' · 클릭하거나 드래그하여 반복 적용합니다. 같은 도구를 다시 누르면 화면 이동으로 전환됩니다.',...['floor','wall','place','floor','wall','place'].map(currentPickerTool=>({__type__:'update',visible:window.mapReviewBrushTool===currentPickerTool})),{__type__:'update',visible:false},{__type__:'update',visible:false},{__type__:'update',visible:false}];}")
    return current_brush_group,current_brush_bridge,current_floor_choice,current_wall_choice,current_floor_picker,current_wall_picker,current_billboard_choice,current_billboard_picker


def apply_map_brush_batch(current_map_identifier,current_editor_state,current_brush_events):
    """한 번의 스트로크를 하나의 되돌리기 단위로 초안에 반영한다."""
    from tools.review.common.gradio_map_editor import load_map_edit_draft,read_map_edit_cell,preview_map_edit_draft
    if not current_editor_state:current_editor_state=load_map_edit_draft(current_map_identifier,{})[0]
    if current_editor_state['draft']['map']!=current_map_identifier:raise ValueError('표시 중인 맵과 초안이 다릅니다.')
    if not isinstance(current_brush_events,list) or len(current_brush_events)>4096:raise ValueError('페인팅 입력 목록 오류')
    current_next_state=copy.deepcopy(current_editor_state)
    current_previous_draft=copy.deepcopy(current_next_state['draft'])
    for current_brush_record in current_brush_events:
        current_tool_name=current_brush_record['tool']
        current_column_index=current_brush_record['column'];current_row_index=current_brush_record['row']
        if type(current_column_index) is not int or type(current_row_index) is not int:raise ValueError('페인팅 좌표는 정수여야 합니다.')
        current_tile_value,current_height_value,current_blocked_value,_=read_map_edit_cell(current_next_state,current_column_index,current_row_index)
        current_draft_payload=current_next_state['draft']
        if current_tool_name=='place':
            from tools.review.common.gradio_map_editor import append_map_billboard_draft
            append_map_billboard_draft(current_next_state,current_column_index,current_row_index,current_brush_record.get('texture'))
            continue
        if current_tool_name in ('delete','delete-cell'):
            current_draft_payload['objects']=[current_object_record for current_object_record in current_draft_payload['objects'] if not (current_object_record['id']==current_brush_record.get('object') if current_tool_name=='delete' else current_object_record['position']=={'column':current_column_index,'row':current_row_index})]
            continue
        current_cell_record=next((current_cell_record for current_cell_record in current_draft_payload['cells'] if (current_cell_record['column'],current_cell_record['row'])==(current_column_index,current_row_index)),None)
        if current_cell_record is None:
            current_cell_record={'column':current_column_index,'row':current_row_index,'tile':current_tile_value,'height':current_height_value,'blocked':current_blocked_value}
            current_draft_payload['cells'].append(current_cell_record)
        if current_tool_name=='floor':
            current_tile_code=current_brush_record['tile']
            if current_tile_code not in current_next_state['snapshot']['codes']:raise ValueError('페인팅할 바닥 타일을 선택하세요.')
            current_cell_record['tile']=current_tile_code
            if current_next_state['snapshot']['codes'][current_tile_code] in MAP_BLOCKED_TERRAIN_NAMES:current_cell_record['blocked']=True
        elif current_tool_name=='wall':
            from tools.review.common.map_asset_sources import validate_map_cliff_texture
            current_cell_record['wall']=validate_map_cliff_texture(current_brush_record['wall'])
        elif current_tool_name in ('raise','lower'):
            current_next_height=current_height_value+(1 if current_tool_name=='raise' else -1)
            if not 0<=current_next_height<=20:raise ValueError('높이는 0~20 범위입니다.')
            current_cell_record['height']=current_next_height
        else:raise ValueError('지원하지 않는 페인팅 도구입니다.')
    if current_next_state['draft']!=current_previous_draft:
        current_next_state['history'].append(current_previous_draft)
        current_next_state['future']=[]
    current_preview_record,current_render_record,current_feedback_text,current_save_update=preview_map_edit_draft(current_next_state)
    return current_next_state,current_preview_record,current_render_record,current_feedback_text,current_save_update
