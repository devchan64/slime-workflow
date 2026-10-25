"""맵 검수와 공용 에셋 관리가 함께 사용하는 표준 Gradio 편집 컨트롤."""
from dataclasses import dataclass
import json
import gradio as gr

ASSET_RESOLUTION_CHOICES = (128,256,384,512)


def build_asset_source_gallery(current_column_count=4, current_row_count=None):
    return gr.Gallery(value=[],interactive=False,label='원본 목록 · 썸네일을 선택하여 편집',columns=current_column_count,rows=current_row_count,height='max-content',object_fit='contain',allow_preview=False,fit_columns=False)


def build_asset_property_inputs(current_automatic_anchor=False):
    with gr.Row():
        current_anchor_horizontal=gr.Number(label='하단 교차점 X · 자동' if current_automatic_anchor else '앵커 X',interactive=not current_automatic_anchor,value=0,minimum=-16,maximum=16,step=.01,precision=2)
        current_anchor_vertical=gr.Number(label='하단 교차점 Y · 자동' if current_automatic_anchor else '앵커 Y',interactive=not current_automatic_anchor,value=0,minimum=-16,maximum=16,step=.01,precision=2)
    with gr.Row():
        current_ground_columns=gr.Number(label='점유 열',value=1,minimum=1,maximum=8,step=1,precision=0)
        current_ground_rows=gr.Number(label='점유 행',value=1,minimum=1,maximum=8,step=1,precision=0)
    current_display_height=gr.Number(label='표시 높이',value=128,minimum=1,maximum=1024,step=1,precision=2)
    return [current_anchor_horizontal,current_anchor_vertical,current_ground_columns,current_ground_rows,current_display_height]


def build_asset_preview_canvas(current_canvas_identifier='map-source-size-preview',current_background_color='transparent'):
    return gr.HTML('<canvas id="'+current_canvas_identifier+'" width="768" height="480" aria-label="에셋 표시 크기와 점유 타일 미리보기" style="max-width:100%;height:auto;background-color:'+current_background_color+'"></canvas>')


def fit_selected_asset_shadow(current_detail_record,current_display_height,current_column_count,current_row_count):
    import base64
    import io
    from tools.review.common.billboard_shadow_fit import calculate_image_shadow_size
    if not current_detail_record:raise gr.Error('썸네일에서 에셋을 선택하세요.')
    if current_detail_record.get('metadata'):raise gr.Error('애니메이션 시트는 자동 맞춤 대상이 아닙니다.')
    current_image_uri=current_detail_record['image']
    if not current_image_uri.startswith('data:image/png;base64,'):raise gr.Error('PNG 미리보기를 다시 불러오세요.')
    current_image_bytes=base64.b64decode(current_image_uri.split(',',1)[1],validate=True)
    current_shadow_column,current_shadow_row=calculate_image_shadow_size(io.BytesIO(current_image_bytes),current_display_height,current_column_count,current_row_count)
    return current_shadow_column,current_shadow_row,'자동 맞춤 완료 · 미리보기 확인 후 저장하세요.'


def build_asset_shadow_inputs():
    with gr.Row():
        current_shadow_column=gr.Number(label='열 이동',value=0,minimum=-4,maximum=4,step=.1,precision=2)
        current_shadow_row=gr.Number(label='행 이동',value=0,minimum=-4,maximum=4,step=.1,precision=2)
    with gr.Row():
        current_shadow_width=gr.Number(label='열 배율',value=1,minimum=.01,maximum=4,step=.1,precision=2)
        current_shadow_height=gr.Number(label='행 배율',value=1,minimum=.01,maximum=4,step=.1,precision=2)
    return [current_shadow_column,current_shadow_row,current_shadow_width,current_shadow_height]


@dataclass
class AssetEditorPanelControls:
    """선택 에셋 편집 패널의 입력·행동·상태 컴포넌트."""
    current_detail_record: object
    current_detail_text: object
    current_copy_button: object
    current_retire_button: object
    current_copy_feedback: object
    current_retire_pending: object
    current_retire_group: object
    current_retire_summary: object
    current_retire_details: object
    current_retire_confirm: object
    current_retire_cancel: object
    current_property_inputs: list
    current_blocking_choice: object
    current_placement_choice: object
    current_shadow_inputs: list
    current_crop_button: object
    current_crop_pending: object
    current_crop_group: object
    current_crop_summary: object
    current_crop_confirm: object
    current_crop_cancel: object
    current_crop_feedback: object
    current_resolution_text: object
    current_resolution_choice: object
    current_resolution_button: object
    current_resolution_feedback: object
    current_update_button: object
    current_save_progress: object
    current_preview_kind: object
    current_preview_zoom: object
    current_show_character: object
    current_show_guidelines: object
    current_show_blocking: object
    current_preview_feedback: object


def build_selected_asset_panel(current_canvas_identifier):
    """정보·속성·그림자·저장·해상도·미리보기를 공용 패널로 구성한다."""
    current_detail_record=gr.JSON(visible=False)
    with gr.Group():
        with gr.Row():
            with gr.Column(scale=3):
                current_detail_text=gr.Markdown()
            with gr.Column(scale=1):
                current_copy_button=gr.Button('에셋 ID 복사')
                current_retire_button=gr.Button('선택 빌보드 폐기')
                current_copy_feedback=gr.Markdown()
    current_retire_pending=gr.State({})
    with gr.Group(visible=False) as current_retire_group:
        current_retire_summary=gr.Markdown()
        current_retire_details=gr.JSON(label='폐기 영향 맵')
        with gr.Row():
            current_retire_confirm=gr.Button('확인 · 폐기 실행',variant='stop')
            current_retire_cancel=gr.Button('취소 · 유지')
    current_copy_button.click(fn=None,inputs=current_detail_record,outputs=current_copy_feedback,queue=False,js="async currentAssetRecord=>{if(!currentAssetRecord?.texture)return '썸네일에서 에셋을 먼저 선택하세요.';try{await navigator.clipboard.writeText(currentAssetRecord.texture);return '에셋 ID를 복사했습니다: '+currentAssetRecord.texture;}catch(currentClipboardError){return '복사 실패: 브라우저 클립보드 권한을 확인하세요.';}}")
    with gr.Row():
        with gr.Column():
            with gr.Group():
                gr.Markdown('### 배치·크기·그림자')
                current_property_inputs=build_asset_property_inputs(current_automatic_anchor=False)
                with gr.Row():
                    current_reset_anchor=gr.Button('배치 초기화',size='sm',scale=0,interactive=False)
                    current_reset_size=gr.Button('크기 초기화',size='sm',scale=0,interactive=False)
                current_reset_anchor.click(fn=None,outputs=current_property_inputs[:2],queue=False,js="()=>[0,0]")
                current_reset_size.click(fn=None,outputs=current_property_inputs[2:],queue=False,js="()=>[1,1,128]")
                current_blocking_choice=gr.Checkbox(label='내부 타일 자동 차단',value=False,interactive=False)
                current_placement_choice=gr.Dropdown(['top','bottom'],value='bottom',label='타일 상하 판정 · 앵커 Y 기준',interactive=False,visible=False)
                gr.Markdown('**그림자**')
                current_shadow_inputs=build_asset_shadow_inputs()
                with gr.Row():
                    current_reset_shadow_position=gr.Button('그림자 위치 초기화',size='sm',scale=0,interactive=False)
                    current_reset_shadow_size=gr.Button('그림자 크기 초기화',size='sm',scale=0,interactive=False)
                current_reset_shadow_position.click(fn=None,outputs=current_shadow_inputs[:2],queue=False,js="()=>[0,0]")
                current_reset_shadow_size.click(fn=None,outputs=current_shadow_inputs[2:],queue=False,js="()=>[1,1]")
                for current_reset_button in (current_reset_anchor,current_reset_size,current_reset_shadow_position,current_reset_shadow_size):
                    current_detail_record.change(lambda current_asset_record:gr.update(interactive=bool(current_asset_record)),inputs=current_detail_record,outputs=current_reset_button)
                current_shadow_fit_button=gr.Button('그림자 크기 자동 맞춤',interactive=False)
                current_shadow_fit_feedback=gr.Markdown('에셋을 선택하면 자동 맞춤을 사용할 수 있습니다.')
                with gr.Accordion('배치·크기·그림자 설명',open=False):
                    gr.Markdown('앵커 X·Y는 이미지 아랫변 중심을 하단 교차점에서 이동하는 값입니다. 점유 열·행은 타일 수, 표시 높이는 px 단위입니다.\n\n배치 초기화는 앵커 0·0, 크기 초기화는 점유 1×1과 표시 높이 128px로 되돌립니다. 3×3 이상은 외곽 한 줄을 제외한 내부 타일만 자동 차단합니다. 초기화는 입력과 미리보기만 바꾸며, 선택 에셋 변경 반영으로 저장합니다.')
                    gr.Markdown('열·행 이동은 타일 단위이며, 0·0은 점유 영역 전체의 중심입니다. 열·행 배율은 점유 크기를 기준으로 합니다. 점유 2×3에 배율 1·1이면 2×3칸을 채웁니다.\n\n위치 초기화는 이동 0·0, 크기 초기화는 배율 1·1로 되돌립니다. 자동 맞춤은 투명 여백을 제외한 가로축 픽셀 분포를 분석해 이미지 폭의 95~120%에 그림자 외곽 폭을 맞추며 점유 열·행 비율을 유지합니다. 접지 형태에 따라 수동 보정하세요.\n\n초기화와 자동 맞춤은 입력과 미리보기만 변경합니다. 선택 에셋 변경 반영으로 저장합니다.')
                current_detail_record.change(lambda current_asset_record:gr.update(interactive=bool(current_asset_record) and not current_asset_record.get('metadata')),inputs=current_detail_record,outputs=current_shadow_fit_button)
                current_shadow_fit_button.click(fit_selected_asset_shadow,inputs=[current_detail_record,current_property_inputs[4],current_property_inputs[2],current_property_inputs[3]],outputs=[*current_shadow_inputs[2:],current_shadow_fit_feedback])
            current_update_button=gr.Button('선택 에셋 변경 반영')
            current_save_progress=gr.Markdown('선택한 ID만 검증하고 즉시 저장합니다.')
            with gr.Accordion('투명 여백 크롭',open=False):
                gr.Markdown('알파값 5 이하(0~255 기준)를 여백으로 판단하여 외곽을 크롭합니다. 크롭 영역 안의 픽셀은 그대로 보존합니다. 표시 크기·접지 위치·그림자는 유지하며, 저장 전 원본은 이력에 보관합니다. 편집 중인 속성은 먼저 변경 반영으로 저장하세요.')
                current_crop_button=gr.Button('크롭 범위 확인')
                current_crop_pending=gr.State({})
                with gr.Group(visible=False) as current_crop_group:
                    current_crop_summary=gr.Markdown()
                    with gr.Row():
                        current_crop_confirm=gr.Button('확인 · 크롭 저장')
                        current_crop_cancel=gr.Button('취소')
                current_crop_feedback=gr.Markdown('썸네일에서 빌보드를 선택한 뒤 크롭 범위를 확인하세요. 투명 여백이 없으면 저장하지 않습니다.')
            with gr.Accordion('원본 이미지 해상도' ,open=False):
                current_resolution_text=gr.Markdown('현재 원본: 에셋을 선택하세요.')
                current_resolution_choice=gr.Radio(list(ASSET_RESOLUTION_CHOICES),value=128,label='원본 해상도 · 긴 변 px',info='현재 긴 변과 가장 가까운 값을 자동 선택합니다. 원본 긴 변보다 작으면 바로 축소 저장할 수 있습니다. 버튼이 비활성화되면 더 작은 값을 선택하세요. 동일 해상도·확대는 저장하지 않습니다.')
                current_resolution_button=gr.Button('선택 해상도로 원본 저장',interactive=False)
                current_resolution_feedback=gr.Markdown()
        with gr.Column():
            gr.Markdown('### 미리보기')
            current_preview_kind=gr.Radio(['야외 80×40 · 0.5배','마을·전투 160×80 · 1배'],value='마을·전투 160×80 · 1배',label='미리보기 타일 규격')
            current_preview_zoom=gr.Slider(minimum=.5,maximum=4,value=2,step=.5,label='미리보기 확대 배율',info='0.5배 단위로 확대·축소합니다. 에셋 저장 값은 바뀌지 않습니다.')
            current_show_character=gr.Checkbox(label='캐릭터 보기 · 마을',value=True,info='마을·전투 규격에서 기본 캐릭터를 실제 표시 크기로 함께 보여줍니다.')
            current_show_guidelines=gr.Checkbox(label='높이 가이드라인 보기',value=True,info='접지 기준에서 위쪽으로 40px마다 표시합니다. 확대 배율을 함께 적용합니다.')
            current_show_blocking=gr.Checkbox(label='이동금지 영역 보기',value=True,info='차단 타일과 이동할 수 없는 경계를 표시합니다. 저장 값은 바뀌지 않습니다.')
            current_background_choice=gr.Radio(['검은색','흰색'],value='흰색',label='미리보기 배경')
            build_asset_preview_canvas(current_canvas_identifier,'#ffffff')
            current_background_choice.change(fn=None,inputs=current_background_choice,outputs=None,queue=False,js='''currentBackgroundChoice=>{
const currentPreviewRoot=document.querySelector('gradio-app')?.shadowRoot||document;
const currentPreviewCanvas=currentPreviewRoot.getElementById(__CANVAS_IDENTIFIER__);
if(currentPreviewCanvas)currentPreviewCanvas.style.backgroundColor=currentBackgroundChoice==='흰색'?'#ffffff':'#000000';
}'''.replace('__CANVAS_IDENTIFIER__',json.dumps(current_canvas_identifier)))
            current_preview_feedback=gr.Markdown('노랑: 점유 타일 · 파랑: 이미지 경계 · 빨강: 앵커. 이미지의 뿌리·밑동이 타일을 넘는지 확인하세요.')
    return AssetEditorPanelControls(
        current_detail_record=current_detail_record,
        current_detail_text=current_detail_text,
        current_copy_button=current_copy_button,
        current_retire_button=current_retire_button,
        current_copy_feedback=current_copy_feedback,
        current_retire_pending=current_retire_pending,
        current_retire_group=current_retire_group,
        current_retire_summary=current_retire_summary,
        current_retire_details=current_retire_details,
        current_retire_confirm=current_retire_confirm,
        current_retire_cancel=current_retire_cancel,
        current_property_inputs=current_property_inputs,
        current_blocking_choice=current_blocking_choice,
        current_placement_choice=current_placement_choice,
        current_shadow_inputs=current_shadow_inputs,
        current_crop_button=current_crop_button,
        current_crop_pending=current_crop_pending,
        current_crop_group=current_crop_group,
        current_crop_summary=current_crop_summary,
        current_crop_confirm=current_crop_confirm,
        current_crop_cancel=current_crop_cancel,
        current_crop_feedback=current_crop_feedback,
        current_resolution_text=current_resolution_text,
        current_resolution_choice=current_resolution_choice,
        current_resolution_button=current_resolution_button,
        current_resolution_feedback=current_resolution_feedback,
        current_update_button=current_update_button,
        current_save_progress=current_save_progress,
        current_preview_kind=current_preview_kind,
        current_preview_zoom=current_preview_zoom,
        current_show_character=current_show_character,
        current_show_guidelines=current_show_guidelines,
        current_show_blocking=current_show_blocking,
        current_preview_feedback=current_preview_feedback,
    )


def build_asset_preview_script(current_review_port,current_renderer_version,current_canvas_identifier):
    """인스턴스별 캔버스에 공용 미리보기 동작을 연결한다."""
    import json
    return '''async(currentAssetRecord,currentAnchorX,currentAnchorY,currentColumns,currentRows,currentHeight,currentPlacement,currentShadowColumn,currentShadowRow,currentShadowWidth,currentShadowHeight,currentKind,currentPreviewZoom,currentBlockingValue,currentShowBlocking,currentShowCharacter,currentShowGuidelines)=>{
if(!currentAssetRecord?.image)return ['썸네일을 선택하세요.',{__type__:'update'}];
const currentPreviewCanvas=document.getElementById(__CANVAS_IDENTIFIER__);
const currentPreviewVersion=String(Number(currentPreviewCanvas.dataset.version??0)+1);currentPreviewCanvas.dataset.version=currentPreviewVersion;
const currentPreviewModule=await import('http://127.0.0.1:__PORT__/isloon-map-review/source-size-preview.js');
const currentRendererManifest={version:__RENDERER_VERSION__};
const currentShadowRenderer=await import(`http://127.0.0.1:__PORT__/isloon-map-review/vendor/field-renderer/${currentRendererManifest.version}/field-renderer.mjs`);
const currentSourceImage=new Image();currentSourceImage.src=currentAssetRecord.image;await currentSourceImage.decode();
if(currentPreviewCanvas.dataset.version!==currentPreviewVersion)return [{__type__:'update'},{__type__:'update'}];
const currentOutdoorMode=currentKind.startsWith('야외');
let currentCharacterPreview=null;
if(!currentOutdoorMode&&currentShowCharacter){
 const currentCharacterResponse=await fetch('http://127.0.0.1:__PORT__/isloon-map-review/review-character.json');
 if(!currentCharacterResponse.ok)throw Error('미리보기 캐릭터 정보를 불러오지 못했습니다.');
 const currentCharacterRecord=await currentCharacterResponse.json();
 const currentCharacterImage=new Image();currentCharacterImage.src=new URL(currentCharacterRecord.image,currentCharacterResponse.url).href;await currentCharacterImage.decode();
 currentCharacterPreview={record:currentCharacterRecord,image:currentCharacterImage};
}
if(currentPreviewCanvas.dataset.version!==currentPreviewVersion)return [{__type__:'update'},{__type__:'update'}];
currentBlockingValue=currentColumns>=3&&currentRows>=3;
const currentPreviewResult=currentPreviewModule.drawAssetGroundPreview(currentPreviewCanvas,currentSourceImage,{anchorX:currentAnchorX,anchorY:currentAnchorY,groundFootprintColumns:currentColumns,groundFootprintRows:currentRows,displayHeight:currentHeight,billboardAnchorMode:currentAssetRecord.properties.billboardAnchorMode,shadowCoordinateVersion:currentAssetRecord.properties.shadowCoordinateVersion??1,shadowSizeVersion:currentAssetRecord.properties.shadowSizeVersion??1,billboardPlacementAnchor:currentPlacement,shadowOffsetColumn:currentShadowColumn,shadowOffsetRow:currentShadowRow,shadowScaleX:currentShadowWidth,shadowScaleY:currentShadowHeight},{tileWidth:currentOutdoorMode?80:160,tileHeight:currentOutdoorMode?40:80,billboardScale:currentOutdoorMode?.5:1,previewZoom:currentPreviewZoom,characterPreview:currentCharacterPreview,showHeightGuidelines:currentShowGuidelines,showBlockedAreas:currentShowBlocking,drawShadow:currentShadowRenderer.drawBillboardContactShadow});
return [`미리보기 ${currentPreviewZoom.toFixed(1)}배 · 선언 ${currentColumns}×${currentRows} · 실제 점유 ${currentPreviewResult.occupiedCells}칸 · ${currentBlockingValue?'내부 '+((currentColumns-2)*(currentRows-2))+'칸 차단':currentColumns===3&&currentRows===2?'가운데 이동 경계 차단':'통행 가능'} · 표시 ${currentPreviewResult.width.toFixed(1)}×${currentPreviewResult.height.toFixed(1)}px. 노랑: 타일 · 파랑: 이미지 · 빨강: 앵커. ${currentColumns<=2&&currentRows<=2?'보조 포함 2×2 격자 · 회색 점선은 점유 제외.':'보조 타일 없음.'} ${currentAssetRecord.metadata.length?'프레임 시트 원본 표시이므로 접지 판정에는 개별 프레임 검수가 필요합니다.':''}`,currentAnchorY<.5?'top':'bottom'];
}'''.replace('__PORT__',str(current_review_port)).replace('__RENDERER_VERSION__',json.dumps(current_renderer_version)).replace('__CANVAS_IDENTIFIER__',json.dumps(current_canvas_identifier))
