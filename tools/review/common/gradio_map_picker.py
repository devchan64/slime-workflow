"""맵 도구별 검색·페이지 이동·썸네일 선택 공용 UI."""
import math
from pathlib import Path
import gradio as gr
from PIL import Image
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
from tools.review.maintenance.sync_billboard_catalog import load_unique_yaml_document

MAP_PICKER_COLUMN_COUNT=5
MAP_PICKER_ROW_COUNT=1
MAP_PICKER_PAGE_SIZE=MAP_PICKER_COLUMN_COUNT*MAP_PICKER_ROW_COUNT
MAP_PICKER_THUMBNAIL_SIZE=(160,160)
MAP_PICKER_CATALOG_PATH=Path(__file__).resolve().parents[1]/'ui/map/config/tile-catalog.yaml'


def load_map_picker_records(current_editor_state,current_picker_kind,current_source_mapping):
    if not current_editor_state:raise gr.Error('맵을 불러오고 편집 모드 준비가 끝난 뒤 선택기를 여세요.')
    current_snapshot_record=current_editor_state['snapshot']
    if current_picker_kind in ('billboard','placed'):
        current_asset_records=execute_remote_management_command('map-assets','asset-list',{})['assets']
        current_asset_mapping={current_asset_record['texture']:current_asset_record for current_asset_record in current_asset_records}
        if current_picker_kind=='billboard':return [{'value':current_asset_record['texture'],'name':current_asset_record['name'],'image':current_asset_record['image']} for current_asset_record in current_asset_records if current_asset_record['texture'] in current_snapshot_record['textures']]
        return [{'value':current_object_record['id'],'name':current_object_record['textureKey']+' · '+str(current_object_record['position']),'image':current_asset_mapping[current_object_record['textureKey']]['image']} for current_object_record in current_editor_state['draft']['objects']]
    current_asset_root,current_registered_assets=load_registered_tiles()
    if current_picker_kind=='floor':
        current_picker_records=[{'value':current_code_value,'name':current_terrain_name,'source':current_source_mapping[current_terrain_name]} for current_code_value,current_terrain_name in current_snapshot_record['codes'].items()]
    elif current_picker_kind=='wall':
        current_picker_records=[{'value':current_tile_record['id'],'name':'옆면','source':current_tile_record['asset']} for current_tile_record in load_unique_yaml_document(MAP_PICKER_CATALOG_PATH)['tiles'] if current_tile_record['category']=='wall']
    else:raise ValueError('지원하지 않는 맵 선택기입니다.')
    return [{'value':current_picker_record['value'],'name':current_picker_record['name'],'image':str(resolve_registered_asset(current_picker_record['source'],current_asset_root,current_registered_assets,'assets/tiles')[0])} for current_picker_record in current_picker_records]


def load_map_picker_thumbnail(current_image_path):
    with Image.open(current_image_path) as current_source_image:
        current_thumbnail_image=current_source_image.convert('RGBA')
        current_thumbnail_image.thumbnail(MAP_PICKER_THUMBNAIL_SIZE)
        return current_thumbnail_image


def paginate_map_picker_records(current_asset_records,current_search_text,current_page_number):
    current_search_terms=(current_search_text or '').casefold().split()
    current_filtered_records=[current_asset_record for current_asset_record in current_asset_records if all(current_search_term in (current_asset_record['value']+' '+current_asset_record['name']).casefold() for current_search_term in current_search_terms)]
    current_page_count=max(1,math.ceil(len(current_filtered_records)/MAP_PICKER_PAGE_SIZE))
    current_page_number=max(1,min(int(current_page_number),current_page_count))
    current_page_records=current_filtered_records[(current_page_number-1)*MAP_PICKER_PAGE_SIZE:current_page_number*MAP_PICKER_PAGE_SIZE]
    return [(load_map_picker_thumbnail(current_asset_record['image']),current_asset_record['name']+' · '+current_asset_record['value']) for current_asset_record in current_page_records],current_page_records,current_page_number,f'{len(current_filtered_records)}개 · {current_page_number}/{current_page_count}페이지 · 첫·마지막 페이지에서는 해당 방향 이동이 꺼집니다.' if current_filtered_records else '검색 결과가 없습니다. 검색어를 줄이거나 지우세요.',gr.update(interactive=current_page_number>1),gr.update(interactive=current_page_number<current_page_count)


def build_map_asset_picker(current_picker_label,current_open_button=None):
    current_open_button=current_open_button or gr.Button(current_picker_label+' 선택기 열기')
    with gr.Group(visible=False) as current_picker_group:
        gr.Markdown('### '+current_picker_label+' 선택\n썸네일을 누르면 선택하고 닫습니다. 선택만으로 맵을 변경하지 않습니다.')
        current_search_input=gr.Textbox(label=current_picker_label+' 검색',placeholder='이름 또는 ID 검색')
        current_asset_gallery=gr.Gallery(value=[],label=current_picker_label+' 목록',columns=MAP_PICKER_COLUMN_COUNT,rows=MAP_PICKER_ROW_COUNT,object_fit='contain',height='auto',allow_preview=False,interactive=False)
        current_page_status=gr.Markdown()
        with gr.Row():
            current_previous_button=gr.Button('이전 페이지',interactive=False)
            current_next_button=gr.Button('다음 페이지',interactive=False)
            current_close_button=gr.Button('선택기 닫기')
        current_all_records=gr.State([]);current_page_records=gr.State([]);current_page_number=gr.State(1)
    current_close_button.click(lambda:gr.update(visible=False),outputs=current_picker_group)
    current_page_outputs=[current_asset_gallery,current_page_records,current_page_number,current_page_status,current_previous_button,current_next_button]
    current_search_input.input(lambda current_asset_records,current_search_text:paginate_map_picker_records(current_asset_records,current_search_text,1),[current_all_records,current_search_input],current_page_outputs)
    current_previous_button.click(lambda current_asset_records,current_search_text,current_page_number:paginate_map_picker_records(current_asset_records,current_search_text,current_page_number-1),[current_all_records,current_search_input,current_page_number],current_page_outputs)
    current_next_button.click(lambda current_asset_records,current_search_text,current_page_number:paginate_map_picker_records(current_asset_records,current_search_text,current_page_number+1),[current_all_records,current_search_input,current_page_number],current_page_outputs)
    return current_open_button,current_picker_group,current_search_input,current_asset_gallery,current_all_records,current_page_records,current_page_outputs


def bind_map_asset_picker(current_picker_controls,current_editor_state,current_picker_kind,current_target_choice):
    current_open_button,current_picker_group,current_search_input,current_asset_gallery,current_all_records,current_page_records,current_page_outputs=current_picker_controls
    def open_map_asset_picker(current_draft_state,current_source_mapping):
        current_asset_records=load_map_picker_records(current_draft_state,current_picker_kind,current_source_mapping)
        return gr.update(visible=True),'',current_asset_records,*paginate_map_picker_records(current_asset_records,'',1),gr.update(choices=[(current_asset_record['name']+' · '+current_asset_record['value'],current_asset_record['value']) for current_asset_record in current_asset_records])
    current_picker_codes=gr.JSON(value={},visible=False)
    current_open_button.click(lambda current_draft_state:current_draft_state.get('snapshot',{}).get('codes',{}),current_editor_state,current_picker_codes).success(open_map_asset_picker,[current_editor_state,current_picker_codes],[current_picker_group,current_search_input,current_all_records,*current_page_outputs,current_target_choice],js="(currentEditorState,currentSourceMapping)=>[currentEditorState,window.mapReviewPickerSources?.(currentSourceMapping)||{}]")
    def select_map_picker_asset(current_visible_records,current_selection_event:gr.SelectData):
        if not current_selection_event.selected:return gr.skip(),gr.skip()
        current_selected_index=current_selection_event.index
        if type(current_selected_index) is not int or not 0<=current_selected_index<len(current_visible_records):raise gr.Error('선택 목록이 바뀌었습니다. 다시 선택하세요.')
        current_selected_record=current_visible_records[current_selected_index]
        return gr.update(value=current_selected_record['value']),gr.update(visible=False)
    current_asset_gallery.select(select_map_picker_asset,current_page_records,[current_target_choice,current_picker_group])
