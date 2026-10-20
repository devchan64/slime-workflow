"""공용 빌보드 일괄 조회·편집 GUI. 저장은 공용 게이트웨이를 사용한다."""
import argparse
import base64
from pathlib import Path
import sys
import gradio as gr

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_asset_editor import build_asset_source_gallery, build_asset_property_inputs, build_asset_preview_canvas, build_asset_shadow_inputs
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.sprite_display_properties import calculate_billboard_blocking_state, validate_sprite_display_properties

EDITOR_PROPERTY_FIELDS = ['anchorX','anchorY','groundFootprintColumns','groundFootprintRows','displayHeight','billboardPlacementAnchor','shadowOffsetColumn','shadowOffsetRow','shadowScaleX','shadowScaleY']
EDITOR_TABLE_HEADERS = ['에셋 ID','이름','앵커 X','앵커 Y','점유 열','점유 행','표시 높이','배치 top/bottom','그림자 열 이동','그림자 행 이동','그림자 가로 배율','그림자 세로 배율','현재 차단','사용 맵 수']


def load_asset_editor_catalog():
    current_catalog_record = execute_remote_management_command('map-assets','asset-list',{})
    current_table_values = [[current_asset_record['texture'],current_asset_record['name'],*[current_asset_record['properties'].get(current_field_name,0 if current_field_name.startswith('shadowOffset') else 1) for current_field_name in EDITOR_PROPERTY_FIELDS],current_asset_record['properties']['billboardBlocksMovement'],len(current_asset_record['maps'])] for current_asset_record in current_catalog_record['assets']]
    return current_catalog_record,current_table_values,f"{len(current_table_values)}종을 불러왔습니다. 표의 수정값은 검증 후 저장해야 반영됩니다."


def filter_asset_editor_gallery(current_catalog_record,current_search_text):
    current_search_terms = current_search_text.lower().split()
    current_matching_assets = [current_asset_record for current_asset_record in current_catalog_record.get('assets',[]) if all(current_search_term in (current_asset_record['texture']+' '+current_asset_record['name']+' '+str(current_asset_record['maps'])).lower() for current_search_term in current_search_terms)]
    current_visible_assets = current_matching_assets[:60]
    return [(current_asset_record['image'],current_asset_record['texture']) for current_asset_record in current_visible_assets],current_visible_assets,f'검색 결과 {len(current_matching_assets)}종 · 썸네일은 최대 60종. 전체 값은 아래 표에서 검색·편집하세요.'


def select_asset_editor_record(current_visible_assets,current_table_values,current_select_event:gr.SelectData):
    current_asset_record = current_visible_assets[current_select_event.index]
    current_selected_row = next(current_table_row for current_table_row in current_table_values if current_table_row[0]==current_asset_record['texture'])
    current_image_uri = 'data:image/png;base64,'+base64.b64encode(Path(current_asset_record['image']).read_bytes()).decode()
    current_detail_record = {**current_asset_record,'image':current_image_uri}
    current_modeling_values = current_asset_record['modeling']
    current_detail_text = '**'+current_asset_record['texture']+'** · '+str(current_asset_record['size'])+' px\n\n'+current_modeling_values.get('purpose','')+'\n\n'+current_modeling_values.get('composition','')+'\n\n사용 맵: '+(', '.join(Path(current_map_record['path']).stem for current_map_record in current_asset_record['maps']) or '없음')
    if current_asset_record['metadata']:
        current_detail_text += '\n\n별도 프레임 메타데이터가 있는 에셋입니다. 아래 원본 시트 표시는 단일 프레임 접지 판정용이 아닙니다.'
    return current_detail_record,*current_selected_row[2:12],current_detail_text


def update_asset_editor_row(current_detail_record,current_table_values,*current_property_values):
    if not current_detail_record:raise gr.Error('썸네일에서 에셋을 선택하세요.')
    current_updated_table = [list(current_table_row) for current_table_row in current_table_values]
    for current_table_row in current_updated_table:
        if current_table_row[0]==current_detail_record['texture']:
            current_table_row[2:12]=current_property_values
    return current_updated_table,'선택한 에셋의 값을 편집 표에 반영했습니다. 검증 후 저장하세요.'


def build_asset_editor_payload(current_catalog_record,current_table_values):
    current_baseline_records = {current_asset_record['texture']:current_asset_record['properties'] for current_asset_record in current_catalog_record['assets']}
    if len(current_table_values)!=len(current_baseline_records):raise ValueError('표 행 수가 변경되었습니다. 새로고침하세요.')
    current_change_records=[];current_seen_textures=set()
    for current_table_row in current_table_values:
        current_texture_key=current_table_row[0]
        if current_texture_key not in current_baseline_records or current_texture_key in current_seen_textures:raise ValueError('표의 에셋 ID 오류')
        current_seen_textures.add(current_texture_key)
        current_property_values=dict(zip(EDITOR_PROPERTY_FIELDS,current_table_row[2:12]))
        for current_field_name in ('groundFootprintColumns','groundFootprintRows'):
            current_number_value=current_property_values[current_field_name]
            if isinstance(current_number_value,bool) or not isinstance(current_number_value,(int,float)) or current_number_value!=int(current_number_value):raise ValueError('점유 타일 크기는 정수여야 합니다.')
            current_property_values[current_field_name]=int(current_number_value)
        current_property_values['billboardBlocksMovement']=calculate_billboard_blocking_state(current_property_values)
        validate_sprite_display_properties({current_texture_key:current_property_values})
        current_changed_values={current_field_name:current_property_values[current_field_name] for current_field_name in EDITOR_PROPERTY_FIELDS if current_property_values[current_field_name]!=current_baseline_records[current_texture_key].get(current_field_name,0 if current_field_name.startswith('shadowOffset') else 1)}
        if current_changed_values:current_change_records.append({'texture':current_texture_key,'values':current_changed_values})
    return {'revision':current_catalog_record['revision'],'changes':current_change_records}


def preview_asset_editor_changes(current_catalog_record,current_table_values):
    current_request_payload=build_asset_editor_payload(current_catalog_record,current_table_values)
    current_preview_record=execute_remote_management_command('map-assets','asset-preview',current_request_payload)
    return {**current_request_payload,'token':current_preview_record['token']},current_preview_record,gr.update(visible=True)


def save_asset_editor_changes(current_catalog_record,current_table_values,current_pending_record):
    current_request_payload=build_asset_editor_payload(current_catalog_record,current_table_values)
    if not current_pending_record or any(current_pending_record[current_field_name]!=current_request_payload[current_field_name] for current_field_name in ('revision','changes')):raise gr.Error('검증 이후 값이 변경되었습니다. 다시 검증하세요.')
    current_saved_record=execute_remote_management_command('map-assets','asset-save',current_pending_record)
    return f"{current_saved_record['count']}종 저장 완료. 공용 속성·카탈로그·해시 잠금을 갱신했습니다. 목록 새로고침으로 저장값을 확인하세요.",{},gr.update(visible=False)


def build_asset_editor_interface(current_review_port):
    with gr.Blocks(title='공용 빌보드 에셋 관리') as current_interface_blocks:
        gr.Markdown('## 공용 빌보드 에셋 관리\n표에서 여러 에셋을 편집하거나 썸네일을 선택해 접지를 확인하세요. **새로고침은 미저장 편집을 버립니다.** 통행 차단은 배치·점유 크기·공용 높이로 자동 계산합니다.')
        current_catalog_state=gr.State({});current_visible_state=gr.State([]);current_pending_state=gr.State({})
        current_feedback_text=gr.Markdown()
        current_reload_button=gr.Button('목록 새로고침 · 미저장 편집 버리기')
        current_search_text=gr.Textbox(label='썸네일 검색 · ID / 이름 / 사용 맵')
        current_search_button=gr.Button('썸네일 검색')
        current_search_feedback=gr.Markdown()
        current_source_gallery=build_asset_source_gallery()
        current_detail_record=gr.JSON(visible=False)
        current_detail_text=gr.Markdown()
        with gr.Row():
            with gr.Column():
                current_property_inputs=build_asset_property_inputs()
                current_placement_choice=gr.Dropdown(['top','bottom'],value='bottom',label='타일 배치 · top 상단 / bottom 하단')
                current_shadow_inputs=build_asset_shadow_inputs()
                gr.Markdown('이동 0·0은 타일 중앙입니다. 타원은 화면 가로·세로, 긴 직사각형은 지면 열·행 크기를 조절합니다.')
            with gr.Column():
                current_preview_kind=gr.Radio(['야외 80×40 · 0.5배','마을·전투 160×80 · 1배'],value='야외 80×40 · 0.5배',label='미리보기 타일 규격')
                build_asset_preview_canvas('asset-editor-preview')
                current_preview_feedback=gr.Markdown('노랑: 점유 타일 · 파랑: 이미지 경계 · 빨강: 앵커. 이미지의 뿌리·밑동이 타일을 넘는지 확인하세요.')
        current_update_button=gr.Button('선택 에셋 값을 편집 표에 반영')
        current_asset_table=gr.Dataframe(headers=EDITOR_TABLE_HEADERS,datatype=['str','str','number','number','number','number','number','str','number','number','number','number','bool','number'],type='array',interactive=True,static_columns=[0,1,12,13],show_search='filter',column_count=(14,'fixed'),label='전체 에셋 편집 표 · 현재 차단 열은 저장 전 원본 값')
        current_preview_button=gr.Button('변경 검증 · 저장 내용 확인',variant='primary')
        with gr.Group(visible=False) as current_confirmation_group:
            gr.Markdown('검증한 변경만 공용 원본에 저장합니다. 아래 before / after 및 사용 맵을 확인하세요. 인라인 확인 영역이며 취소하면 저장하지 않습니다.')
            current_preview_result=gr.JSON(label='변경 전후 · 영향 맵')
            with gr.Row():
                current_save_button=gr.Button('검증한 변경 저장',variant='primary');current_cancel_button=gr.Button('취소 · 편집 유지')
        current_reload_button.click(load_asset_editor_catalog,outputs=[current_catalog_state,current_asset_table,current_feedback_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text],outputs=[current_source_gallery,current_visible_state,current_search_feedback])
        current_interface_blocks.load(load_asset_editor_catalog,outputs=[current_catalog_state,current_asset_table,current_feedback_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text],outputs=[current_source_gallery,current_visible_state,current_search_feedback])
        current_search_button.click(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text],outputs=[current_source_gallery,current_visible_state,current_search_feedback])
        current_selection_event=current_source_gallery.select(select_asset_editor_record,inputs=[current_visible_state,current_asset_table],outputs=[current_detail_record,*current_property_inputs,current_placement_choice,*current_shadow_inputs,current_detail_text])
        current_update_button.click(update_asset_editor_row,inputs=[current_detail_record,current_asset_table,*current_property_inputs,current_placement_choice,*current_shadow_inputs],outputs=[current_asset_table,current_feedback_text])
        current_preview_button.click(preview_asset_editor_changes,inputs=[current_catalog_state,current_asset_table],outputs=[current_pending_state,current_preview_result,current_confirmation_group])
        current_save_button.click(save_asset_editor_changes,inputs=[current_catalog_state,current_asset_table,current_pending_state],outputs=[current_feedback_text,current_pending_state,current_confirmation_group])
        current_cancel_button.click(lambda:({},gr.update(visible=False)),outputs=[current_pending_state,current_confirmation_group])
        current_preview_script='''async(currentAssetRecord,currentAnchorX,currentAnchorY,currentColumns,currentRows,currentHeight,currentPlacement,currentShadowColumn,currentShadowRow,currentShadowWidth,currentShadowHeight,currentKind)=>{
if(!currentAssetRecord?.image)return '썸네일을 선택하세요.';
const currentPreviewCanvas=document.getElementById('asset-editor-preview');
const currentPreviewVersion=String(Number(currentPreviewCanvas.dataset.version??0)+1);currentPreviewCanvas.dataset.version=currentPreviewVersion;
const currentPreviewModule=await import('http://127.0.0.1:__PORT__/isloon-map-review/source-size-preview.js');
const currentRendererManifest={version:__RENDERER_VERSION__};
const currentShadowRenderer=await import(`http://127.0.0.1:__PORT__/isloon-map-review/vendor/field-renderer/${currentRendererManifest.version}/field-renderer.mjs`);
const currentSourceImage=new Image();currentSourceImage.src=currentAssetRecord.image;await currentSourceImage.decode();
if(currentPreviewCanvas.dataset.version!==currentPreviewVersion)return {__type__:'update'};
const currentOutdoorMode=currentKind.startsWith('야외');
const currentPreviewResult=currentPreviewModule.drawAssetGroundPreview(currentPreviewCanvas,currentSourceImage,{anchorX:currentAnchorX,anchorY:currentAnchorY,groundFootprintColumns:currentColumns,groundFootprintRows:currentRows,displayHeight:currentHeight,billboardPlacementAnchor:currentPlacement,shadowOffsetColumn:currentShadowColumn,shadowOffsetRow:currentShadowRow,shadowScaleX:currentShadowWidth,shadowScaleY:currentShadowHeight},{tileWidth:currentOutdoorMode?80:160,tileHeight:currentOutdoorMode?40:80,billboardScale:currentOutdoorMode?.5:1,drawShadow:currentShadowRenderer.drawBillboardContactShadow});
return `선언 ${currentColumns}×${currentRows} · 실제 점유 ${currentPreviewResult.occupiedCells}칸 · ${currentPlacement==='bottom'&&(currentColumns>1||currentRows>1||currentHeight>80)?'통행 차단':'통행 가능'} · 표시 ${currentPreviewResult.width.toFixed(1)}×${currentPreviewResult.height.toFixed(1)}px. 노랑: 타일 · 파랑: 이미지 · 빨강: 앵커. ${currentAssetRecord.metadata.length?'프레임 시트 원본 표시이므로 접지 판정에는 개별 프레임 검수가 필요합니다.':''}`;
}'''.replace('__PORT__',str(current_review_port)).replace('__RENDERER_VERSION__',repr(__import__('yaml').safe_load((WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map/vendor/field-renderer/manifest.yaml').read_text())['version']))
        current_preview_inputs=[current_detail_record,*current_property_inputs,current_placement_choice,*current_shadow_inputs,current_preview_kind]
        current_selection_event.then(fn=None,inputs=current_preview_inputs,outputs=current_preview_feedback,js=current_preview_script,queue=False)
        for current_input_control in current_preview_inputs[1:]:
            current_input_control.input(fn=None,inputs=current_preview_inputs,outputs=current_preview_feedback,js=current_preview_script,queue=False)
    return current_interface_blocks


if __name__=='__main__':
    from tools.review.ui.gradio.management_menu_app import compose_management_interface
    from tools.review.common.map_tile_assets import load_registered_tiles
    current_argument_parser=argparse.ArgumentParser()
    for current_argument_name in ('port','review-port','owner-pid'):current_argument_parser.add_argument('--'+current_argument_name,type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/asset-editor/')
    current_argument_values=current_argument_parser.parse_args()
    compose_management_interface(build_asset_editor_interface(current_argument_values.review_port),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[str(load_registered_tiles()[0]/'assets/billboards')])
