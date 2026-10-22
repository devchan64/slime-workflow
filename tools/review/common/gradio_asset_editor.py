"""맵 검수와 공용 에셋 관리가 함께 사용하는 표준 Gradio 편집 컨트롤."""
from dataclasses import dataclass
import json
import gradio as gr

ASSET_RESOLUTION_CHOICES = (128,256,384,512)


def build_asset_source_gallery(current_column_count=4, current_row_count=None):
    return gr.Gallery(value=[],interactive=False,label='원본 목록 · 썸네일을 선택하여 편집',columns=current_column_count,rows=current_row_count,height='max-content',object_fit='contain',allow_preview=False)


def build_asset_property_inputs(current_automatic_anchor=False):
    with gr.Row():
        current_anchor_horizontal=gr.Number(label='하단 교차점 X · 자동' if current_automatic_anchor else '아랫변 중심 X · 교차점 기준',interactive=not current_automatic_anchor,value=.5,minimum=-16,maximum=16,step=.01)
        current_anchor_vertical=gr.Number(label='하단 교차점 Y · 자동' if current_automatic_anchor else '아랫변 중심 Y · 교차점 기준',interactive=not current_automatic_anchor,value=1,minimum=-16,maximum=16,step=.01)
    with gr.Row():
        current_ground_columns=gr.Number(label='점유 타일 열 · 칸',value=1,minimum=1,maximum=8,step=1,precision=0)
        current_ground_rows=gr.Number(label='점유 타일 행 · 칸',value=1,minimum=1,maximum=8,step=1,precision=0)
    current_display_height=gr.Number(label='공용 표시 높이 · px',value=128,minimum=1,maximum=1024)
    return [current_anchor_horizontal,current_anchor_vertical,current_ground_columns,current_ground_rows,current_display_height]


def build_asset_preview_canvas(current_canvas_identifier='map-source-size-preview',current_background_color='transparent'):
    return gr.HTML('<canvas id="'+current_canvas_identifier+'" width="768" height="480" aria-label="에셋 표시 크기와 점유 타일 미리보기" style="max-width:100%;height:auto;background-color:'+current_background_color+'"></canvas>')


def build_asset_shadow_inputs():
    with gr.Row():
        current_shadow_column=gr.Number(label='그림자 열 방향 이동 · 타일',value=0,minimum=-4,maximum=4,step=.05)
        current_shadow_row=gr.Number(label='그림자 행 방향 이동 · 타일',value=0,minimum=-4,maximum=4,step=.05)
    with gr.Row():
        current_shadow_width=gr.Number(label='그림자 가로/열 배율',value=1,minimum=.1,maximum=4,step=.05)
        current_shadow_height=gr.Number(label='그림자 세로/행 배율',value=1,minimum=.05,maximum=4,step=.05)
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
    current_resolution_text: object
    current_resolution_choice: object
    current_resolution_button: object
    current_resolution_feedback: object
    current_update_button: object
    current_save_progress: object
    current_preview_kind: object
    current_preview_zoom: object
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
                gr.Markdown('### 배치와 크기')
                current_property_inputs=build_asset_property_inputs(current_automatic_anchor=False)
                current_blocking_choice=gr.Checkbox(label='내부 타일 자동 차단',value=False,interactive=False)
            current_placement_choice=gr.Dropdown(['top','bottom'],value='bottom',label='타일 상하 판정 · 앵커 Y 기준',interactive=False,visible=False)
            with gr.Group():
                gr.Markdown('### 그림자 위치와 크기')
                current_shadow_inputs=build_asset_shadow_inputs()
                gr.Markdown('이동 0·0은 하단 기준 교차점입니다. 가로 1·세로 1가 기본 크기입니다.')
            current_update_button=gr.Button('선택 에셋 변경 반영')
            current_save_progress=gr.Markdown('선택한 ID만 검증하고 즉시 저장합니다.')
            with gr.Accordion('원본 이미지 해상도',open=False):
                current_resolution_text=gr.Markdown('현재 원본: 에셋을 선택하세요.')
                current_resolution_choice=gr.Radio(list(ASSET_RESOLUTION_CHOICES),value=128,label='원본 해상도 · 긴 변 px',info='현재 긴 변과 가장 가까운 값을 자동 선택합니다. 다른 축소 크기를 선택하면 저장할 수 있습니다. 동일 선택값·확대는 저장하지 않습니다.')
                current_resolution_button=gr.Button('선택 해상도로 원본 저장',interactive=False)
                current_resolution_feedback=gr.Markdown()
        with gr.Column():
            gr.Markdown('### 미리보기')
            current_preview_kind=gr.Radio(['야외 80×40 · 0.5배','마을·전투 160×80 · 1배'],value='야외 80×40 · 0.5배',label='미리보기 타일 규격')
            current_preview_zoom=gr.Slider(minimum=.5,maximum=4,value=1,step=.5,label='미리보기 확대 배율',info='0.5배 단위로 확대·축소합니다. 에셋 저장 값은 바뀌지 않습니다.')
            current_show_blocking=gr.Checkbox(label='이동금지 영역 보기',value=True,info='차단 타일과 이동할 수 없는 경계를 표시합니다. 저장 값은 바뀌지 않습니다.')
            current_background_choice=gr.Radio(['검은색','흰색'],value='검은색',label='미리보기 배경')
            build_asset_preview_canvas(current_canvas_identifier,'#000000')
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
        current_resolution_text=current_resolution_text,
        current_resolution_choice=current_resolution_choice,
        current_resolution_button=current_resolution_button,
        current_resolution_feedback=current_resolution_feedback,
        current_update_button=current_update_button,
        current_save_progress=current_save_progress,
        current_preview_kind=current_preview_kind,
        current_preview_zoom=current_preview_zoom,
        current_show_blocking=current_show_blocking,
        current_preview_feedback=current_preview_feedback,
    )


def build_asset_preview_script(current_review_port,current_renderer_version,current_canvas_identifier):
    """인스턴스별 캔버스에 공용 미리보기 동작을 연결한다."""
    import json
    return '''async(currentAssetRecord,currentAnchorX,currentAnchorY,currentColumns,currentRows,currentHeight,currentPlacement,currentShadowColumn,currentShadowRow,currentShadowWidth,currentShadowHeight,currentKind,currentPreviewZoom,currentBlockingValue,currentShowBlocking)=>{
if(!currentAssetRecord?.image)return ['썸네일을 선택하세요.',{__type__:'update'}];
const currentPreviewCanvas=document.getElementById(__CANVAS_IDENTIFIER__);
const currentPreviewVersion=String(Number(currentPreviewCanvas.dataset.version??0)+1);currentPreviewCanvas.dataset.version=currentPreviewVersion;
const currentPreviewModule=await import('http://127.0.0.1:__PORT__/isloon-map-review/source-size-preview.js');
const currentRendererManifest={version:__RENDERER_VERSION__};
const currentShadowRenderer=await import(`http://127.0.0.1:__PORT__/isloon-map-review/vendor/field-renderer/${currentRendererManifest.version}/field-renderer.mjs`);
const currentSourceImage=new Image();currentSourceImage.src=currentAssetRecord.image;await currentSourceImage.decode();
if(currentPreviewCanvas.dataset.version!==currentPreviewVersion)return [{__type__:'update'},{__type__:'update'}];
const currentOutdoorMode=currentKind.startsWith('야외');
currentBlockingValue=currentColumns>=3&&currentRows>=3;
const currentPreviewResult=currentPreviewModule.drawAssetGroundPreview(currentPreviewCanvas,currentSourceImage,{anchorX:currentAnchorX,anchorY:currentAnchorY,groundFootprintColumns:currentColumns,groundFootprintRows:currentRows,displayHeight:currentHeight,billboardAnchorMode:currentAssetRecord.properties.billboardAnchorMode,billboardPlacementAnchor:currentPlacement,shadowOffsetColumn:currentShadowColumn,shadowOffsetRow:currentShadowRow,shadowScaleX:currentShadowWidth,shadowScaleY:currentShadowHeight},{tileWidth:currentOutdoorMode?80:160,tileHeight:currentOutdoorMode?40:80,billboardScale:currentOutdoorMode?.5:1,previewZoom:currentPreviewZoom,showBlockedAreas:currentShowBlocking,drawShadow:currentShadowRenderer.drawBillboardContactShadow});
return [`미리보기 ${currentPreviewZoom.toFixed(1)}배 · 선언 ${currentColumns}×${currentRows} · 실제 점유 ${currentPreviewResult.occupiedCells}칸 · ${currentBlockingValue?'내부 '+((currentColumns-2)*(currentRows-2))+'칸 차단':currentColumns===3&&currentRows===2?'가운데 이동 경계 차단':'통행 가능'} · 표시 ${currentPreviewResult.width.toFixed(1)}×${currentPreviewResult.height.toFixed(1)}px. 노랑: 타일 · 파랑: 이미지 · 빨강: 앵커. ${currentColumns<=2&&currentRows<=2?'보조 포함 2×2 격자 · 회색 점선은 점유 제외.':'보조 타일 없음.'} ${currentAssetRecord.metadata.length?'프레임 시트 원본 표시이므로 접지 판정에는 개별 프레임 검수가 필요합니다.':''}`,currentAnchorY<.5?'top':'bottom'];
}'''.replace('__PORT__',str(current_review_port)).replace('__RENDERER_VERSION__',json.dumps(current_renderer_version)).replace('__CANVAS_IDENTIFIER__',json.dumps(current_canvas_identifier))
