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

EDITOR_GALLERY_PAGE_SIZE = 12

EDITOR_PROPERTY_FIELDS = ['anchorX','anchorY','groundFootprintColumns','groundFootprintRows','displayHeight','billboardPlacementAnchor','shadowOffsetColumn','shadowOffsetRow','shadowScaleX','shadowScaleY']
EDITOR_TABLE_HEADERS = ['에셋 ID','이름','앵커 X','앵커 Y','점유 열','점유 행','표시 높이','배치 top/bottom','그림자 열 이동','그림자 행 이동','그림자 가로 배율','그림자 세로 배율','통행 차단','사용 맵 수']


def load_asset_editor_catalog():
    current_catalog_record = execute_remote_management_command('map-assets','asset-list',{})
    current_table_values = [[current_asset_record['texture'],current_asset_record['name'],*[(('top' if current_asset_record['properties']['anchorY']<.5 else 'bottom') if current_field_name=='billboardPlacementAnchor' and current_asset_record['properties'].get('billboardAnchorMode')=='tile-bottom-center' else current_asset_record['properties'].get(current_field_name,0 if current_field_name.startswith('shadowOffset') else 1)) for current_field_name in EDITOR_PROPERTY_FIELDS],current_asset_record['properties'].get('billboardBlocksMovement',False),len(current_asset_record['maps'])] for current_asset_record in current_catalog_record['assets']]
    return current_catalog_record,current_table_values,f"{len(current_table_values)}종을 불러왔습니다. 표의 수정값은 검증 후 저장해야 반영됩니다."


def filter_asset_editor_gallery(current_catalog_record,current_search_text,current_asset_type='all',current_page_number=1):
    current_search_terms = current_search_text.lower().split()
    current_matching_assets = [current_asset_record for current_asset_record in current_catalog_record.get('assets',[]) if (current_asset_type=='all' or current_asset_record['category']==current_asset_type) and all(current_search_term in (current_asset_record['texture']+' '+current_asset_record['name']+' '+str(current_asset_record['maps'])).lower() for current_search_term in current_search_terms)]
    current_page_count=max(1,(len(current_matching_assets)+EDITOR_GALLERY_PAGE_SIZE-1)//EDITOR_GALLERY_PAGE_SIZE)
    current_page_number=max(1,min(int(current_page_number),current_page_count))
    current_start_index=(current_page_number-1)*EDITOR_GALLERY_PAGE_SIZE
    current_visible_assets = current_matching_assets[current_start_index:current_start_index+EDITOR_GALLERY_PAGE_SIZE]
    return [(current_asset_record['image'],current_asset_record['texture']) for current_asset_record in current_visible_assets],current_visible_assets,f'검색 결과 {len(current_matching_assets)}종 · {current_page_number}/{current_page_count}페이지 · 페이지당 12개. 첫·마지막 페이지에서는 해당 방향으로 이동할 수 없습니다.',current_page_number,gr.update(interactive=current_page_number>1),gr.update(interactive=current_page_number<current_page_count)


def previous_asset_gallery_page(current_catalog_record,current_search_text,current_asset_type,current_page_number):
    return filter_asset_editor_gallery(current_catalog_record,current_search_text,current_asset_type,current_page_number-1)


def next_asset_gallery_page(current_catalog_record,current_search_text,current_asset_type,current_page_number):
    return filter_asset_editor_gallery(current_catalog_record,current_search_text,current_asset_type,current_page_number+1)


def select_asset_editor_record(current_visible_assets,current_table_values,current_select_event:gr.SelectData):
    current_asset_record = current_visible_assets[current_select_event.index]
    current_selected_row = next(current_table_row for current_table_row in current_table_values if current_table_row[0]==current_asset_record['texture'])
    current_image_uri = 'data:image/png;base64,'+base64.b64encode(Path(current_asset_record['image']).read_bytes()).decode()
    current_detail_record = {**current_asset_record,'image':current_image_uri}
    current_modeling_values = current_asset_record['modeling']
    current_detail_text = '**'+current_asset_record['texture']+'** · '+str(current_asset_record['size'])+' px\n\n'+current_modeling_values.get('purpose','')+'\n\n'+current_modeling_values.get('composition','')+'\n\n사용 맵: '+(', '.join(Path(current_map_record['path']).stem for current_map_record in current_asset_record['maps']) or '없음')
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
        current_property_values=dict(zip(EDITOR_PROPERTY_FIELDS,current_table_row[2:12]))
        for current_field_name in ('groundFootprintColumns','groundFootprintRows'):
            current_number_value=current_property_values[current_field_name]
            if isinstance(current_number_value,bool) or not isinstance(current_number_value,(int,float)) or current_number_value!=int(current_number_value):raise ValueError('점유 타일 크기는 정수여야 합니다.')
            current_property_values[current_field_name]=int(current_number_value)
        if current_baseline_records[current_texture_key].get('billboardAnchorMode')=='tile-bottom-center':
            current_property_values.pop('billboardPlacementAnchor')
            current_property_values['billboardAnchorMode']='tile-bottom-center'
        current_property_values['billboardBlocksMovement']=current_table_row[12]
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
        current_preview_record=execute_remote_management_command('map-assets','asset-preview',current_request_payload)
    except ValueError as current_validation_error:
        return {},{},gr.update(visible=False),'변경 검증 실패 · 편집값은 유지됩니다.\n\n'+str(current_validation_error).replace('\n','  \n')
    return {**current_request_payload,'token':current_preview_record['token']},current_preview_record,gr.update(visible=True),f"변경 검증 완료. 맵 경고 {len(current_preview_record.get('map_warnings',[]))}건은 저장을 차단하지 않습니다. 아래 변경 전후를 확인하고 저장하세요."


def save_asset_editor_changes(current_catalog_record,current_table_values,current_pending_record):
    current_request_payload=build_asset_editor_payload(current_catalog_record,current_table_values)
    if not current_pending_record or any(current_pending_record[current_field_name]!=current_request_payload[current_field_name] for current_field_name in ('revision','changes')):raise gr.Error('검증 이후 값이 변경되었습니다. 다시 검증하세요.')
    current_saved_record=execute_remote_management_command('map-assets','asset-save',current_pending_record)
    current_saved_catalog,current_saved_table,_=load_asset_editor_catalog()
    return f"{current_saved_record['count']}종 저장 완료. 저장 기준을 갱신했습니다. 계속 편집하고 다시 검증할 수 있습니다.",{},gr.update(visible=False),current_saved_catalog,current_saved_table


def build_asset_editor_interface(current_review_port):
    with gr.Blocks(title='공용 빌보드 에셋 관리') as current_interface_blocks:
        gr.Markdown('## 공용 빌보드 에셋 관리\n표에서 여러 에셋을 편집하거나 썸네일을 선택해 접지를 확인하세요. **새로고침은 미저장 편집을 버립니다.** 통행 차단은 에셋별로 직접 설정합니다. 기본값은 꺼짐입니다.')
        current_catalog_state=gr.State({});current_visible_state=gr.State([]);current_pending_state=gr.State({})
        current_feedback_text=gr.Markdown()
        with gr.Row():
            current_search_text=gr.Textbox(label='에셋 검색',placeholder='ID · 이름 · 사용 맵',scale=3)
            current_asset_type=gr.Dropdown(label='에셋 타입',choices=[('전체','all'),('자연물','vegetation'),('소품','props')],value='all',scale=1)
            current_search_button=gr.Button('검색',scale=1)
            current_reload_button=gr.Button('목록 새로고침 · 편집 초기화',scale=1)
        current_search_feedback=gr.Markdown()
        current_gallery_page=gr.State(1)
        with gr.Row():
            current_previous_page=gr.Button('이전 페이지',interactive=False)
            current_next_page=gr.Button('다음 페이지',interactive=False)
        current_source_gallery=build_asset_source_gallery()
        current_detail_record=gr.JSON(visible=False)
        current_detail_text=gr.Markdown()
        with gr.Row():
            with gr.Column():
                with gr.Group():
                    gr.Markdown('### 배치와 크기')
                    current_property_inputs=build_asset_property_inputs()
                    current_blocking_choice=gr.Checkbox(label='통행 차단',value=False)
                current_placement_choice=gr.Dropdown(['top','bottom'],value='bottom',label='타일 상하 판정 · 앵커 Y 기준',interactive=False,visible=False)
                with gr.Group():
                    gr.Markdown('### 그림자 위치와 크기')
                    current_shadow_inputs=build_asset_shadow_inputs()
                    gr.Markdown('이동 0·0은 전체 점유 영역의 중앙입니다. 가로 1·세로 1가 기본 크기입니다.')
                current_update_button=gr.Button('선택 에셋 변경 반영')
                gr.Markdown('반영 후 아래 **변경 검증**을 눌러 저장하세요.')
            with gr.Column():
                gr.Markdown('### 미리보기')
                current_preview_kind=gr.Radio(['야외 80×40 · 0.5배','마을·전투 160×80 · 1배'],value='야외 80×40 · 0.5배',label='미리보기 타일 규격')
                current_preview_zoom=gr.Slider(minimum=.5,maximum=4,value=1,step=.5,label='미리보기 확대 배율',info='0.5배 단위로 확대·축소합니다. 에셋 저장 값은 바뀌지 않습니다.')
                build_asset_preview_canvas('asset-editor-preview')
                current_preview_feedback=gr.Markdown('노랑: 점유 타일 · 파랑: 이미지 경계 · 빨강: 앵커. 이미지의 뿌리·밑동이 타일을 넘는지 확인하세요.')
        with gr.Accordion('전체 에셋 일괄 편집',open=False):
            current_asset_table=gr.Dataframe(headers=EDITOR_TABLE_HEADERS,datatype=['str','str','number','number','number','number','number','str','number','number','number','number','bool','number'],type='array',interactive=True,static_columns=[0,1,7,13],show_search='filter',column_count=(14,'fixed'),label='전체 에셋 편집 표 · 통행 차단은 직접 켜고 끌 수 있습니다')
        current_preview_button=gr.Button('변경 검증 · 저장 내용 확인',variant='primary')
        current_validation_feedback=gr.Markdown()
        with gr.Group(visible=False) as current_confirmation_group:
            gr.Markdown('검증한 변경만 공용 원본에 저장합니다. 아래 before / after 및 사용 맵을 확인하세요. 인라인 확인 영역이며 취소하면 저장하지 않습니다.')
            current_preview_result=gr.JSON(label='변경 전후 · 영향 맵')
            with gr.Row():
                current_save_button=gr.Button('검증한 변경 저장',variant='primary');current_cancel_button=gr.Button('취소 · 편집 유지')
        current_gallery_outputs=[current_source_gallery,current_visible_state,current_search_feedback,current_gallery_page,current_previous_page,current_next_page]
        current_previous_page.click(previous_asset_gallery_page,inputs=[current_catalog_state,current_search_text,current_asset_type,current_gallery_page],outputs=current_gallery_outputs)
        current_next_page.click(next_asset_gallery_page,inputs=[current_catalog_state,current_search_text,current_asset_type,current_gallery_page],outputs=current_gallery_outputs)
        current_reload_button.click(load_asset_editor_catalog,outputs=[current_catalog_state,current_asset_table,current_feedback_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_interface_blocks.load(load_asset_editor_catalog,outputs=[current_catalog_state,current_asset_table,current_feedback_text]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_search_button.click(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_asset_type.input(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_search_text.submit(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_selection_event=current_source_gallery.select(select_asset_editor_record,inputs=[current_visible_state,current_asset_table],outputs=[current_detail_record,*current_property_inputs,current_placement_choice,*current_shadow_inputs,current_blocking_choice,current_detail_text])
        current_update_button.click(update_asset_editor_row,inputs=[current_detail_record,current_asset_table,*current_property_inputs,current_placement_choice,*current_shadow_inputs,current_blocking_choice],outputs=[current_asset_table,current_feedback_text])
        current_preview_button.click(preview_asset_editor_changes,inputs=[current_catalog_state,current_asset_table],outputs=[current_pending_state,current_preview_result,current_confirmation_group,current_validation_feedback])
        current_save_button.click(save_asset_editor_changes,inputs=[current_catalog_state,current_asset_table,current_pending_state],outputs=[current_feedback_text,current_pending_state,current_confirmation_group,current_catalog_state,current_asset_table]).then(filter_asset_editor_gallery,inputs=[current_catalog_state,current_search_text,current_asset_type],outputs=current_gallery_outputs)
        current_cancel_button.click(lambda:({},gr.update(visible=False)),outputs=[current_pending_state,current_confirmation_group])
        current_preview_script='''async(currentAssetRecord,currentAnchorX,currentAnchorY,currentColumns,currentRows,currentHeight,currentPlacement,currentShadowColumn,currentShadowRow,currentShadowWidth,currentShadowHeight,currentKind,currentPreviewZoom,currentBlockingValue)=>{
if(!currentAssetRecord?.image)return ['썸네일을 선택하세요.',{__type__:'update'}];
const currentPreviewCanvas=document.getElementById('asset-editor-preview');
const currentPreviewVersion=String(Number(currentPreviewCanvas.dataset.version??0)+1);currentPreviewCanvas.dataset.version=currentPreviewVersion;
const currentPreviewModule=await import('http://127.0.0.1:__PORT__/isloon-map-review/source-size-preview.js');
const currentRendererManifest={version:__RENDERER_VERSION__};
const currentShadowRenderer=await import(`http://127.0.0.1:__PORT__/isloon-map-review/vendor/field-renderer/${currentRendererManifest.version}/field-renderer.mjs`);
const currentSourceImage=new Image();currentSourceImage.src=currentAssetRecord.image;await currentSourceImage.decode();
if(currentPreviewCanvas.dataset.version!==currentPreviewVersion)return [{__type__:'update'},{__type__:'update'}];
const currentOutdoorMode=currentKind.startsWith('야외');
const currentPreviewResult=currentPreviewModule.drawAssetGroundPreview(currentPreviewCanvas,currentSourceImage,{anchorX:currentAnchorX,anchorY:currentAnchorY,groundFootprintColumns:currentColumns,groundFootprintRows:currentRows,displayHeight:currentHeight,billboardAnchorMode:currentAssetRecord.properties.billboardAnchorMode,billboardPlacementAnchor:currentPlacement,shadowOffsetColumn:currentShadowColumn,shadowOffsetRow:currentShadowRow,shadowScaleX:currentShadowWidth,shadowScaleY:currentShadowHeight},{tileWidth:currentOutdoorMode?80:160,tileHeight:currentOutdoorMode?40:80,billboardScale:currentOutdoorMode?.5:1,previewZoom:currentPreviewZoom,drawShadow:currentShadowRenderer.drawBillboardContactShadow});
return [`미리보기 ${currentPreviewZoom.toFixed(1)}배 · 선언 ${currentColumns}×${currentRows} · 실제 점유 ${currentPreviewResult.occupiedCells}칸 · ${currentBlockingValue?'통행 차단':'통행 가능'} · 표시 ${currentPreviewResult.width.toFixed(1)}×${currentPreviewResult.height.toFixed(1)}px. 노랑: 타일 · 파랑: 이미지 · 빨강: 앵커. ${currentAssetRecord.metadata.length?'프레임 시트 원본 표시이므로 접지 판정에는 개별 프레임 검수가 필요합니다.':''}`,currentAnchorY<.5?'top':'bottom'];
}'''.replace('__PORT__',str(current_review_port)).replace('__RENDERER_VERSION__',repr(__import__('yaml').safe_load((WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map/vendor/field-renderer/manifest.yaml').read_text())['version']))
        current_preview_inputs=[current_detail_record,*current_property_inputs,current_placement_choice,*current_shadow_inputs,current_preview_kind,current_preview_zoom,current_blocking_choice]
        current_selection_event.then(fn=None,inputs=current_preview_inputs,outputs=[current_preview_feedback,current_placement_choice],js=current_preview_script,queue=False)
        for current_input_control in current_preview_inputs[1:]:
            current_input_control.input(fn=None,inputs=current_preview_inputs,outputs=[current_preview_feedback,current_placement_choice],js=current_preview_script,queue=False)
    return current_interface_blocks


if __name__=='__main__':
    from tools.review.ui.gradio.management_menu_app import compose_management_interface
    from tools.review.common.map_tile_assets import load_registered_tiles
    current_argument_parser=argparse.ArgumentParser()
    for current_argument_name in ('port','review-port','owner-pid'):current_argument_parser.add_argument('--'+current_argument_name,type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/asset-editor/')
    current_argument_values=current_argument_parser.parse_args()
    compose_management_interface(build_asset_editor_interface(current_argument_values.review_port),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[str(load_registered_tiles()[0]/'assets/billboards')])
