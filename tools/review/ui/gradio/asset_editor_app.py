"""공용 빌보드 일괄 조회·편집 GUI. 저장은 공용 게이트웨이를 사용한다."""
import argparse
import base64
import hashlib
from pathlib import Path
import sys
import gradio as gr

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_asset_editor import build_asset_source_gallery, build_selected_asset_panel, build_asset_preview_script, ASSET_RESOLUTION_CHOICES
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.sprite_display_properties import calculate_billboard_blocking_state, validate_sprite_display_properties, calculate_billboard_intersection_properties

EDITOR_RESOLUTION_CHOICES = ASSET_RESOLUTION_CHOICES
EDITOR_GALLERY_COLUMN_COUNT = 5
EDITOR_GALLERY_ROW_COUNT = 2
EDITOR_GALLERY_PAGE_SIZE = EDITOR_GALLERY_COLUMN_COUNT * EDITOR_GALLERY_ROW_COUNT

EDITOR_PROPERTY_FIELDS = ['anchorX','anchorY','groundFootprintColumns','groundFootprintRows','displayHeight','billboardPlacementAnchor','shadowOffsetColumn','shadowOffsetRow','shadowScaleX','shadowScaleY']
EDITOR_TABLE_HEADERS = ['에셋 ID','이름','앵커 X','앵커 Y','점유 열','점유 행','표시 높이','배치 top/bottom','그림자 열 이동','그림자 행 이동','그림자 열 길이 · 타일','그림자 행 길이 · 타일','통행 차단','사용 맵 수']


def load_asset_editor_catalog():
    current_catalog_record = execute_remote_management_command('map-assets','asset-list',{})
    current_table_values = [[current_asset_record['texture'],current_asset_record['name'],*[None]*11,len(current_asset_record['maps'])] if current_asset_record['properties'] is None else [current_asset_record['texture'],current_asset_record['name'],*[(('top' if current_asset_record['properties']['anchorY']<.5 else 'bottom') if current_field_name=='billboardPlacementAnchor' and current_asset_record['properties'].get('billboardAnchorMode')in ('tile-bottom-center','tile-intersection') else current_asset_record['properties'].get(current_field_name,0 if current_field_name.startswith('shadowOffset') else 1)) for current_field_name in EDITOR_PROPERTY_FIELDS],current_asset_record['properties'].get('billboardBlocksMovement',False),len(current_asset_record['maps'])] for current_asset_record in current_catalog_record['assets']]
    return current_catalog_record,current_table_values,f"{len(current_table_values)}종을 불러왔습니다. 선택 에셋 변경 반영 버튼으로 하나씩 저장합니다."


def filter_asset_editor_gallery(current_catalog_record,current_search_text,current_asset_type='all',current_page_number=1):
    current_search_terms = current_search_text.lower().split()
    current_matching_assets = [current_asset_record for current_asset_record in current_catalog_record.get('assets',[]) if (current_asset_type=='all' or current_asset_record['category']==current_asset_type) and all(current_search_term in (current_asset_record['texture']+' '+current_asset_record['name']+' '+str(current_asset_record['maps'])).lower() for current_search_term in current_search_terms)]
    current_page_count=max(1,(len(current_matching_assets)+EDITOR_GALLERY_PAGE_SIZE-1)//EDITOR_GALLERY_PAGE_SIZE)
    current_page_number=max(1,min(int(current_page_number),current_page_count))
    current_start_index=(current_page_number-1)*EDITOR_GALLERY_PAGE_SIZE
    current_visible_assets = current_matching_assets[current_start_index:current_start_index+EDITOR_GALLERY_PAGE_SIZE]
    return [(current_asset_record['image'],current_asset_record['texture']+(' · 설정 필요' if current_asset_record['properties'] is None else '')) for current_asset_record in current_visible_assets],current_visible_assets,f'검색 결과 {len(current_matching_assets)}종 · {current_page_number}/{current_page_count}페이지 · 페이지당 {EDITOR_GALLERY_PAGE_SIZE}개. 첫·마지막 페이지에서는 해당 방향으로 이동할 수 없습니다.',current_page_number,gr.update(interactive=current_page_number>1),gr.update(interactive=current_page_number<current_page_count)


def previous_asset_gallery_page(current_catalog_record,current_search_text,current_asset_type,current_page_number):
    return filter_asset_editor_gallery(current_catalog_record,current_search_text,current_asset_type,current_page_number-1)


def next_asset_gallery_page(current_catalog_record,current_search_text,current_asset_type,current_page_number):
    return filter_asset_editor_gallery(current_catalog_record,current_search_text,current_asset_type,current_page_number+1)


def select_asset_editor_record(current_visible_assets,current_table_values,current_select_event:gr.SelectData):
    current_asset_record = current_visible_assets[current_select_event.index]
    current_initial_setup=current_asset_record['properties'] is None
    if current_initial_setup:
        current_draft_properties=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,displayHeight=128,billboardAnchorMode='tile-intersection',shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,billboardBlocksMovement=False)
        current_asset_record={**current_asset_record,'properties':current_draft_properties}
    current_selected_row = next(current_table_row for current_table_row in current_table_values if current_table_row[0]==current_asset_record['texture'])
    if current_initial_setup:
        current_selected_row=[current_asset_record['texture'],current_asset_record['name'],0,0,1,1,128,'top',0,0,1,1,False,len(current_asset_record['maps'])]
    current_image_uri = 'data:image/png;base64,'+base64.b64encode(Path(current_asset_record['image']).read_bytes()).decode()
    current_detail_record = {**current_asset_record,'image':current_image_uri}
    current_modeling_values = current_asset_record['modeling']
    current_detail_text = '**'+current_asset_record['texture']+'** · '+str(current_asset_record['size'])+' px\n\n'+current_modeling_values.get('purpose','')+'\n\n'+current_modeling_values.get('composition','')+'\n\n사용 맵: '+(', '.join(Path(current_map_record['path']).stem for current_map_record in current_asset_record['maps']) or '없음')
    if current_initial_setup:
        current_detail_text+='\n\n**공용 속성 최초 설정 · 미저장 초안**. 초기 1×1·높이 128px는 편집 시작값입니다. 점유·크기·접지를 확인한 뒤 선택 에셋 변경 반영으로 저장하세요.'
    if current_asset_record['metadata']:
        current_detail_text += '\n\n별도 프레임 메타데이터가 있는 에셋입니다. 아래 원본 시트 표시는 단일 프레임 접지 판정용이 아닙니다.'
    return current_detail_record,*current_selected_row[2:13],current_detail_text


def update_asset_editor_row(current_detail_record,current_table_values,*current_property_values):
    if not current_detail_record:raise gr.Error('썸네일에서 에셋을 선택하세요.')
    current_updated_table = [list(current_table_row) for current_table_row in current_table_values]
    for current_table_row in current_updated_table:
        if current_table_row[0]==current_detail_record['texture']:
            current_table_row[2:13]=current_property_values
    return current_updated_table,'선택한 에셋의 값을 편집 표에 반영했습니다. 검증 후 저장하세요.'


def build_asset_editor_payload(current_catalog_record,current_table_values):
    current_baseline_records = {current_asset_record['texture']:current_asset_record['properties'] for current_asset_record in current_catalog_record['assets']}
    if len(current_table_values)!=len(current_baseline_records):raise ValueError('표 행 수가 변경되었습니다. 새로고침하세요.')
    current_change_records=[];current_seen_textures=set()
    for current_table_row in current_table_values:
        current_texture_key=current_table_row[0]
        if current_texture_key not in current_baseline_records or current_texture_key in current_seen_textures:raise ValueError('표의 에셋 ID 오류')
        current_seen_textures.add(current_texture_key)
        if current_baseline_records[current_texture_key] is None:
            if all(current_field_value is None for current_field_value in current_table_row[2:13]):continue
            current_initial_values=dict(zip(EDITOR_PROPERTY_FIELDS,current_table_row[2:12]))
            current_initial_values.pop('billboardPlacementAnchor')
            current_initial_values['billboardBlocksMovement']=current_table_row[12]
            validate_sprite_display_properties({current_texture_key:{**current_initial_values,'billboardAnchorMode':'tile-intersection'}})
            current_change_records.append({'texture':current_texture_key,'values':current_initial_values})
            continue
        current_property_values=dict(zip(EDITOR_PROPERTY_FIELDS,current_table_row[2:12]))
        for current_field_name in ('groundFootprintColumns','groundFootprintRows'):
            current_number_value=current_property_values[current_field_name]
            if isinstance(current_number_value,bool) or not isinstance(current_number_value,(int,float)) or current_number_value!=int(current_number_value):raise ValueError('점유 타일 크기는 정수여야 합니다.')
            current_property_values[current_field_name]=int(current_number_value)
        if current_baseline_records[current_texture_key].get('billboardAnchorMode')in ('tile-bottom-center','tile-intersection'):
            current_property_values.pop('billboardPlacementAnchor')
            current_property_values['billboardAnchorMode']=current_baseline_records[current_texture_key]['billboardAnchorMode']
        current_property_values=calculate_billboard_intersection_properties(current_property_values)
        validate_sprite_display_properties({current_texture_key:current_property_values})
        current_changed_values={current_field_name:current_property_values[current_field_name] for current_field_name in EDITOR_PROPERTY_FIELDS if current_field_name in current_property_values and current_property_values[current_field_name]!=current_baseline_records[current_texture_key].get(current_field_name,0 if current_field_name.startswith('shadowOffset') else 1)}
        if current_property_values['billboardBlocksMovement'] != current_baseline_records[current_texture_key].get('billboardBlocksMovement',False):
            current_changed_values['billboardBlocksMovement']=current_property_values['billboardBlocksMovement']
        if current_changed_values:current_change_records.append({'texture':current_texture_key,'values':current_changed_values})
    return {'revision':current_catalog_record['revision'],'changes':current_change_records}


def preview_asset_editor_changes(current_catalog_record,current_table_values):
    try:
        current_request_payload=build_asset_editor_payload(current_catalog_record,current_table_values)
        if not current_request_payload['changes']:
            return {},{},gr.update(visible=False),'변경된 값이 없습니다. 속성 입력을 수정했다면 먼저 선택 에셋 변경 반영을 누르세요.'
        current_latest_catalog=execute_remote_management_command('map-assets','asset-list',{})
        current_latest_records={current_asset_record['texture']:current_asset_record['properties'] for current_asset_record in current_latest_catalog['assets']}
        current_baseline_records={current_asset_record['texture']:current_asset_record['properties'] for current_asset_record in current_catalog_record['assets']}
        current_rebased_changes=[]
        current_conflict_records=[]
        for current_change_record in current_request_payload['changes']:
            current_texture_key=current_change_record['texture']
            if current_texture_key not in current_latest_records:
                raise ValueError('폐기되거나 제거된 편집 대상: '+current_texture_key+' · 다른 편집값은 유지됩니다.')
            current_changed_values={}
            for current_field_name,current_edited_value in current_change_record['values'].items():
                current_default_value=0 if current_field_name.startswith('shadowOffset') else 1
                current_latest_value=current_latest_records[current_texture_key].get(current_field_name,current_default_value)
                current_baseline_value=current_baseline_records[current_texture_key].get(current_field_name,current_default_value)
                if current_latest_value==current_edited_value:continue
                current_changed_values[current_field_name]=current_edited_value
                if current_latest_value!=current_baseline_value:
                    current_conflict_records.append({'texture':current_texture_key,'field':current_field_name,'editing_started':current_baseline_value,'latest':current_latest_value,'edited':current_edited_value})
            if current_changed_values:
                current_rebased_changes.append({'texture':current_texture_key,'values':current_changed_values})
        if not current_rebased_changes:
            return {},{},gr.update(visible=False),'편집값이 이미 최신 원본과 같습니다. 누적 편집값은 유지됩니다.'
        current_rebased_payload={'revision':current_latest_catalog['revision'],'changes':current_rebased_changes}
        current_preview_record=execute_remote_management_command('map-assets','asset-preview',current_rebased_payload)
        current_preview_record['conflicts']=current_conflict_records
    except ValueError as current_validation_error:
        return {},{},gr.update(visible=False),'변경 검증 실패 · 편집값은 유지됩니다.\n\n'+str(current_validation_error).replace('\n','  \n')
    return {**current_rebased_payload,'editing_payload':current_request_payload,'token':current_preview_record['token']},current_preview_record,gr.update(visible=True),f"변경 ID {len(current_rebased_changes)}종만 검증했습니다. 동일 속성 충돌 {len(current_conflict_records)}건은 아래 conflicts에서 확인하세요. 저장하면 해당 속성에 내 편집값을 적용합니다. 맵 경고 {len(current_preview_record.get('map_warnings',[]))}건은 저장을 차단하지 않습니다. 아래 변경 전후를 확인하고 저장하세요."


def save_asset_editor_changes(current_catalog_record,current_table_values,current_pending_record):
    current_request_payload=build_asset_editor_payload(current_catalog_record,current_table_values)
    if not current_pending_record or current_pending_record.get('editing_payload')!=current_request_payload:raise gr.Error('검증 이후 값이 변경되었습니다. 다시 검증하세요.')
    current_saved_record=execute_remote_management_command('map-assets','asset-save',{current_field_name:current_pending_record[current_field_name] for current_field_name in ('revision','changes','token')})
    current_saved_catalog,current_saved_table,_=load_asset_editor_catalog()
    return f"{current_saved_record['count']}종 저장 완료. 저장 기준을 갱신했습니다. 계속 편집하고 다시 검증할 수 있습니다.",{},gr.update(visible=False),current_saved_catalog,current_saved_table


def describe_selected_image_size(current_detail_record):
    if not current_detail_record:return '에셋을 선택하세요.'
    return '현재 원본: '+ ' × '.join(str(current_dimension_value) for current_dimension_value in current_detail_record['size'])+' px'


def select_nearest_image_resolution(current_detail_record):
    current_longest_dimension=max(current_detail_record['size']) if current_detail_record else 128
    return min(EDITOR_RESOLUTION_CHOICES,key=lambda current_resolution_value:abs(current_resolution_value-current_longest_dimension))


def load_selected_resolution_controls(current_detail_record):
    current_target_size=select_nearest_image_resolution(current_detail_record)
    return describe_selected_image_size(current_detail_record),current_target_size,update_resolution_save_button(current_detail_record,current_target_size),''


def update_resolution_save_button(current_detail_record,current_target_size):
    current_save_enabled=bool(current_detail_record) and current_target_size in EDITOR_RESOLUTION_CHOICES and current_target_size<max(current_detail_record['size'])
    return gr.update(interactive=current_save_enabled)


def resize_selected_asset_image(current_detail_record,current_target_size):
    if not current_detail_record:raise gr.Error('썸네일에서 에셋을 선택하세요.')
    if current_target_size not in EDITOR_RESOLUTION_CHOICES:raise gr.Error('128·256·384·512px 중 선택하세요.')
    current_catalog_record,current_table_values,_=load_asset_editor_catalog()
    current_asset_record=next((current_asset_record for current_asset_record in current_catalog_record['assets'] if current_asset_record['texture']==current_detail_record['texture']),None)
    if current_asset_record is None:raise gr.Error('폐기되거나 제거된 에셋입니다.')
    if current_asset_record['metadata']:raise gr.Error('프레임 메타데이터가 있는 이미지는 지원하지 않습니다.')
    if current_target_size==max(current_asset_record['size']):
        return gr.skip(),gr.skip(),gr.skip(),gr.skip(),'이미 같은 해상도이므로 저장하지 않았습니다.'
    if current_target_size>max(current_asset_record['size']):raise gr.Error('원본보다 작은 해상도를 선택하세요. 확대는 지원하지 않습니다.')
    current_image_path=Path(current_asset_record['image'])
    current_request_payload={'path':'assets/billboards/'+current_image_path.name,'sha256':hashlib.sha256(current_image_path.read_bytes()).hexdigest(),'size':int(current_target_size)}
    current_resize_record=execute_remote_management_command('map-assets','resize',current_request_payload)
    current_catalog_record,current_table_values,_=load_asset_editor_catalog()
    current_asset_record=next(current_asset_record for current_asset_record in current_catalog_record['assets'] if current_asset_record['texture']==current_detail_record['texture'])
    current_updated_detail={**current_asset_record,'image':'data:image/png;base64,'+base64.b64encode(Path(current_asset_record['image']).read_bytes()).decode()}
    return current_catalog_record,current_table_values,current_updated_detail,'**'+current_asset_record['texture']+'** · '+str(current_asset_record['size'])+' px\n\n'+current_asset_record['modeling'].get('purpose','')+'\n\n'+current_asset_record['modeling'].get('composition','')+'\n\n사용 맵: '+(', '.join(Path(current_map_record['path']).stem for current_map_record in current_asset_record['maps']) or '없음'),describe_selected_image_size(current_updated_detail)+' · 저장 완료. 축소 전 원본은 이력에 보관했습니다.'



def build_selected_crop_changes(current_catalog_record,current_detail_record,current_property_values):
    if not current_detail_record:raise gr.Error('썸네일에서 빌보드를 선택하세요.')
    current_saved_record=next((current_asset_record for current_asset_record in current_catalog_record['assets'] if current_asset_record['texture']==current_detail_record['texture']),None)
    if current_saved_record is None:raise gr.Error('선택한 에셋이 목록에 없습니다. 목록을 새로고침하세요.')
    current_selected_row=[current_detail_record['texture'],current_detail_record['name'],*current_property_values,0]
    return build_asset_editor_payload({'revision':current_catalog_record['revision'],'assets':[current_saved_record]},[current_selected_row])['changes']


def preview_selected_asset_crop(current_catalog_record,current_detail_record,*current_property_values):
    if build_selected_crop_changes(current_catalog_record,current_detail_record,current_property_values):raise gr.Error('편집 중인 속성을 먼저 선택 에셋 변경 반영으로 저장하세요.')
    current_request_payload={'revision':current_catalog_record['revision'],'texture':current_detail_record['texture']}
    current_preview_result=execute_remote_management_command('map-assets','asset-crop-preview',current_request_payload)
    if not current_preview_result['changed']:
        return {},gr.update(visible=False),'',gr.update(interactive=False),'제거할 투명 여백이 없습니다. 저장하지 않았습니다.'
    current_pending_record={**current_request_payload,'token':current_preview_result['token']}
    return current_pending_record,gr.update(visible=True),f"{current_detail_record['texture']} · {current_preview_result['before']} → {current_preview_result['after']} px. 표시 크기와 접지 위치를 유지하도록 높이·앵커를 함께 보정합니다. 저장하시겠습니까?",gr.update(interactive=True),'크롭 저장 또는 취소를 선택하세요.'


def confirm_selected_asset_crop(current_catalog_record,current_detail_record,current_pending_record,*current_property_values):
    if not current_pending_record or not current_detail_record or current_pending_record['texture']!=current_detail_record['texture']:
        raise gr.Error('선택 대상이 변경되었습니다. 크롭 범위를 다시 확인하세요.')
    if build_selected_crop_changes(current_catalog_record,current_detail_record,current_property_values):
        raise gr.Error('확인 후 속성이 변경되었습니다. 속성을 저장한 뒤 크롭 범위를 다시 확인하세요.')
    execute_remote_management_command('map-assets','asset-crop',current_pending_record)
    current_catalog_record,current_table_values,_=load_asset_editor_catalog()
    current_asset_record=next(current_asset_record for current_asset_record in current_catalog_record['assets'] if current_asset_record['texture']==current_detail_record['texture'])
    current_selection_values=select_asset_editor_record([current_asset_record],current_table_values,gr.SelectData(None,{'index':0,'value':None}))
    return current_catalog_record,current_table_values,{},gr.update(visible=False),'크롭 저장 완료. 크롭 전 원본과 속성은 이력에 보관했습니다.',*current_selection_values


def iterate_selected_asset_save(current_detail_record,*current_property_values):
    """최신 원본에서 선택 ID 하나만 검증하고 저장한다."""
    if not current_detail_record:raise gr.Error('썸네일에서 에셋을 선택하세요.')
    current_texture_key=current_detail_record['texture']
    yield gr.skip(),gr.skip(),f'{current_texture_key} · 원본 조회 중…'
    current_catalog_record,current_table_values,_=load_asset_editor_catalog()
    current_selected_record=next((current_asset_record for current_asset_record in current_catalog_record['assets'] if current_asset_record['texture']==current_texture_key),None)
    if current_selected_record is None:raise gr.Error('폐기되거나 제거된 에셋입니다: '+current_texture_key)
    current_selected_row=next(list(current_table_row) for current_table_row in current_table_values if current_table_row[0]==current_texture_key)
    current_selected_row[2:13]=current_property_values
    current_request_payload=build_asset_editor_payload({'revision':current_catalog_record['revision'],'assets':[current_selected_record]},[current_selected_row])
    if current_request_payload['changes']:
        yield gr.skip(),gr.skip(),f'{current_texture_key} · 변경 검증 중…'
        current_preview_record=execute_remote_management_command('map-assets','asset-preview',current_request_payload)
        yield gr.skip(),gr.skip(),f'{current_texture_key} · 저장 중…'
        execute_remote_management_command('map-assets','asset-save',{**current_request_payload,'token':current_preview_record['token']})
        yield gr.skip(),gr.skip(),f'{current_texture_key} · 저장 결과 조회 중…'
        current_catalog_record,current_table_values,_=load_asset_editor_catalog()
        current_feedback_text=f'{current_texture_key} 저장 완료. 해당 ID만 업데이트했습니다. 맵 경고 {len(current_preview_record.get("map_warnings",[]))}건.'
    else:
        current_feedback_text=current_texture_key+' · 변경된 값이 없습니다.'
    yield current_catalog_record,current_table_values,current_feedback_text


def save_selected_asset_properties(current_detail_record,*current_property_values):
    for current_save_result in iterate_selected_asset_save(current_detail_record,*current_property_values):
        pass
    return current_save_result


def stream_selected_asset_save(current_detail_record,*current_property_values):
    try:
        yield from iterate_selected_asset_save(current_detail_record,*current_property_values)
    except (ValueError,OSError,gr.Error) as current_save_error:
        yield gr.skip(),gr.skip(),'저장 실패 · 입력값은 유지됩니다. '+str(current_save_error)


def preview_asset_retirement(current_catalog_record,current_detail_record):
    if not current_detail_record:raise gr.Error('썸네일에서 폐기할 에셋을 선택하세요.')
    current_request_payload={'revision':current_catalog_record['revision'],'texture':current_detail_record['texture']}
    current_preview_result=execute_remote_management_command('map-assets','asset-retire-preview',current_request_payload)
    current_removed_count=sum(current_map_record['removed'] for current_map_record in current_preview_result['maps'])
    return {**current_request_payload,'token':current_preview_result['token']},gr.update(visible=True),f"**폐기 대상: {current_request_payload['texture']}**\n\n공용 목록과 맵 배치 {current_removed_count}개에서 제외합니다. 원본 이미지·생성 이력은 폐기 경로에 보존합니다. 미저장 편집은 폐기 완료 후 초기화됩니다.",current_preview_result


def confirm_asset_retirement(current_detail_record,current_pending_record):
    if not current_pending_record or not current_detail_record or current_detail_record['texture']!=current_pending_record['texture']:raise gr.Error('선택 대상이 변경되었습니다. 폐기 내용을 다시 확인하세요.')
    execute_remote_management_command('map-assets','asset-retire',current_pending_record)
    current_catalog_record,current_table_values,_=load_asset_editor_catalog()
    return current_catalog_record,current_table_values,'폐기 완료: '+current_pending_record['texture'],{},gr.update(visible=False),{},''


def calculate_editor_automatic_values(current_column_count,current_row_count):
    current_property_values=calculate_billboard_intersection_properties({'groundFootprintColumns':current_column_count,'groundFootprintRows':current_row_count})
    return current_property_values['billboardBlocksMovement']


def build_asset_editor_interface(current_review_port):
    with gr.Blocks(title='공용 빌보드 에셋 관리') as current_interface_blocks:
        gr.Markdown('## 공용 빌보드 에셋 관리\n썸네일을 선택해 속성을 편집하세요. **선택 에셋 변경 반영**을 누르면 해당 ID 하나만 검증하고 즉시 저장합니다. 앵커 X·Y는 하단 교차점 기준 수동 이동값입니다. 3×3 이상은 외곽을 제외한 내부 타일만 차단합니다.')
        current_catalog_state=gr.State({});current_visible_state=gr.State([])
        current_feedback_text=gr.Markdown()
        with gr.Row():
            current_search_text=gr.Textbox(label='에셋 검색',placeholder='ID · 이름 · 사용 맵',scale=3)
            current_asset_type=gr.Dropdown(label='에셋 타입',choices=[('전체','all'),('자연물','vegetation'),('큰 나무','large-trees'),('암석광물','rocks-minerals'),('소품','props')],value='all',scale=1)
            current_search_button=gr.Button('검색',scale=1)
            current_reload_button=gr.Button('목록 새로고침 · 편집 초기화',scale=1)
        current_search_feedback=gr.Markdown()
        current_gallery_page=gr.State(1)
        with gr.Row():
            current_previous_page=gr.Button('이전 페이지',interactive=False)
            current_next_page=gr.Button('다음 페이지',interactive=False)
        current_source_gallery=build_asset_source_gallery(EDITOR_GALLERY_COLUMN_COUNT, EDITOR_GALLERY_ROW_COUNT)
        current_editor_panel=build_selected_asset_panel('asset-editor-preview')
        current_asset_table=gr.State([])
        current_editor_panel.current_retire_button.click(preview_asset_retirement,inputs=[current_catalog_state,current_editor_panel.current_detail_record],outputs=[current_editor_panel.current_retire_pending,current_editor_panel.current_retire_group,current_editor_panel.current_retire_summary,current_editor_panel.current_retire_details])
        current_editor_panel.current_retire_cancel.click(lambda:({},gr.update(visible=False)),outputs=[current_editor_panel.current_retire_pending,current_editor_panel.current_retire_group])
        current_editor_panel.current_retire_confirm.click(confirm_asset_retirement,inputs=[current_editor_panel.current_detail_record,current_editor_panel.current_retire_pending],outputs=[current_catalog_state,current_asset_table,current_feedback_text,current_editor_panel.current_retire_pending,current_editor_panel.current_retire_group,current_editor_panel.current_detail_record,current_editor_panel.current_detail_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=[current_source_gallery,current_visible_state,current_search_feedback,current_gallery_page,current_previous_page,current_next_page])
        current_gallery_outputs=[current_source_gallery,current_visible_state,current_search_feedback,current_gallery_page,current_previous_page,current_next_page]
        current_previous_page.click(previous_asset_gallery_page,inputs=[current_catalog_state,current_search_text,current_asset_type,current_gallery_page],outputs=current_gallery_outputs)
        current_next_page.click(next_asset_gallery_page,inputs=[current_catalog_state,current_search_text,current_asset_type,current_gallery_page],outputs=current_gallery_outputs)
        current_reload_button.click(load_asset_editor_catalog,outputs=[current_catalog_state,current_asset_table,current_feedback_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_interface_blocks.load(load_asset_editor_catalog,outputs=[current_catalog_state,current_asset_table,current_feedback_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_search_button.click(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_asset_type.input(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_search_text.submit(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_selection_event=current_source_gallery.select(select_asset_editor_record,inputs=[current_visible_state,current_asset_table],outputs=[current_editor_panel.current_detail_record,*current_editor_panel.current_property_inputs,current_editor_panel.current_placement_choice,*current_editor_panel.current_shadow_inputs,current_editor_panel.current_blocking_choice,current_editor_panel.current_detail_text])
        for current_size_control in current_editor_panel.current_property_inputs[2:4]:
            current_size_control.change(calculate_editor_automatic_values,inputs=current_editor_panel.current_property_inputs[2:4],outputs=current_editor_panel.current_blocking_choice)
        current_editor_panel.current_update_button.click(stream_selected_asset_save,inputs=[current_editor_panel.current_detail_record,*current_editor_panel.current_property_inputs,current_editor_panel.current_placement_choice,*current_editor_panel.current_shadow_inputs,current_editor_panel.current_blocking_choice],outputs=[current_catalog_state,current_asset_table,current_editor_panel.current_save_progress],show_progress='full',concurrency_limit=1,trigger_mode='once')
        current_renderer_version=__import__('yaml').safe_load((WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map/vendor/field-renderer/manifest.yaml').read_text())['version']
        current_preview_script=build_asset_preview_script(current_review_port,current_renderer_version,'asset-editor-preview')
        current_editor_panel.current_detail_record.change(load_selected_resolution_controls,inputs=current_editor_panel.current_detail_record,outputs=[current_editor_panel.current_resolution_text,current_editor_panel.current_resolution_choice,current_editor_panel.current_resolution_button,current_editor_panel.current_resolution_feedback])
        current_editor_panel.current_resolution_choice.input(update_resolution_save_button,inputs=[current_editor_panel.current_detail_record,current_editor_panel.current_resolution_choice],outputs=current_editor_panel.current_resolution_button)
        current_resolution_event=current_editor_panel.current_resolution_button.click(resize_selected_asset_image,inputs=[current_editor_panel.current_detail_record,current_editor_panel.current_resolution_choice],outputs=[current_catalog_state,current_asset_table,current_editor_panel.current_detail_record,current_editor_panel.current_detail_text,current_editor_panel.current_resolution_feedback])
        current_resolution_event.then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type,current_gallery_page],outputs=current_gallery_outputs)
        current_crop_inputs=[current_catalog_state,current_editor_panel.current_detail_record,*current_editor_panel.current_property_inputs,current_editor_panel.current_placement_choice,*current_editor_panel.current_shadow_inputs,current_editor_panel.current_blocking_choice]
        current_editor_panel.current_crop_button.click(preview_selected_asset_crop,inputs=current_crop_inputs,outputs=[current_editor_panel.current_crop_pending,current_editor_panel.current_crop_group,current_editor_panel.current_crop_summary,current_editor_panel.current_crop_confirm,current_editor_panel.current_crop_feedback])
        current_editor_panel.current_crop_cancel.click(lambda:({},gr.update(visible=False),'크롭을 취소했습니다. 원본은 변경되지 않았습니다.'),outputs=[current_editor_panel.current_crop_pending,current_editor_panel.current_crop_group,current_editor_panel.current_crop_feedback])
        current_crop_event=current_editor_panel.current_crop_confirm.click(confirm_selected_asset_crop,inputs=[current_catalog_state,current_editor_panel.current_detail_record,current_editor_panel.current_crop_pending,*current_editor_panel.current_property_inputs,current_editor_panel.current_placement_choice,*current_editor_panel.current_shadow_inputs,current_editor_panel.current_blocking_choice],outputs=[current_catalog_state,current_asset_table,current_editor_panel.current_crop_pending,current_editor_panel.current_crop_group,current_editor_panel.current_crop_feedback,current_editor_panel.current_detail_record,*current_editor_panel.current_property_inputs,current_editor_panel.current_placement_choice,*current_editor_panel.current_shadow_inputs,current_editor_panel.current_blocking_choice,current_editor_panel.current_detail_text],concurrency_limit=1,trigger_mode='once')
        current_crop_event.then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type,current_gallery_page],outputs=current_gallery_outputs)
        current_preview_inputs=[current_editor_panel.current_detail_record,*current_editor_panel.current_property_inputs,current_editor_panel.current_placement_choice,*current_editor_panel.current_shadow_inputs,current_editor_panel.current_preview_kind,current_editor_panel.current_preview_zoom,current_editor_panel.current_blocking_choice,current_editor_panel.current_show_blocking]
        current_crop_event.then(fn=None,inputs=current_preview_inputs,outputs=[current_editor_panel.current_preview_feedback,current_editor_panel.current_placement_choice],js=current_preview_script,queue=False)
        current_resolution_event.then(fn=None,inputs=current_preview_inputs,outputs=[current_editor_panel.current_preview_feedback,current_editor_panel.current_placement_choice],js=current_preview_script,queue=False)
        current_selection_event.then(fn=None,inputs=current_preview_inputs,outputs=[current_editor_panel.current_preview_feedback,current_editor_panel.current_placement_choice],js=current_preview_script,queue=False)
        for current_input_control in current_preview_inputs[1:]:
            current_preview_event=current_input_control.change if current_input_control in current_editor_panel.current_shadow_inputs[2:] else current_input_control.input
            current_preview_event(fn=None,inputs=current_preview_inputs,outputs=[current_editor_panel.current_preview_feedback,current_editor_panel.current_placement_choice],js=current_preview_script,queue=False)
    return current_interface_blocks


if __name__=='__main__':
    from tools.review.ui.gradio.management_menu_app import compose_management_interface
    from tools.review.common.map_tile_assets import load_registered_tiles
    current_argument_parser=argparse.ArgumentParser()
    for current_argument_name in ('port','review-port','owner-pid'):current_argument_parser.add_argument('--'+current_argument_name,type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/asset-editor/')
    current_argument_values=current_argument_parser.parse_args()
    compose_management_interface(build_asset_editor_interface(current_argument_values.review_port),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[str(load_registered_tiles()[0]/'assets/billboards')])
