"""맵 검수와 공용 에셋 관리가 함께 사용하는 표준 Gradio 편집 컨트롤."""
import gradio as gr


def build_asset_source_gallery():
    return gr.Gallery(value=[],interactive=False,label='원본 목록 · 썸네일을 선택하여 편집',columns=4,height=360,object_fit='contain',allow_preview=False)


def build_asset_property_inputs():
    with gr.Row():
        current_anchor_horizontal=gr.Number(label='앵커 X · 0~1',value=.5,minimum=0,maximum=1,step=.01)
        current_anchor_vertical=gr.Number(label='앵커 Y · 0~1',value=1,minimum=0,maximum=1,step=.01)
    with gr.Row():
        current_ground_columns=gr.Number(label='점유 타일 열 · 칸',value=1,minimum=1,maximum=8,step=1,precision=0)
        current_ground_rows=gr.Number(label='점유 타일 행 · 칸',value=1,minimum=1,maximum=8,step=1,precision=0)
    current_display_height=gr.Number(label='공용 표시 높이 · px',value=128,minimum=1,maximum=1024)
    return [current_anchor_horizontal,current_anchor_vertical,current_ground_columns,current_ground_rows,current_display_height]


def build_asset_preview_canvas(current_canvas_identifier='map-source-size-preview'):
    return gr.HTML('<canvas id="'+current_canvas_identifier+'" width="768" height="320" aria-label="에셋 표시 크기와 점유 타일 미리보기" style="max-width:100%;height:auto"></canvas>')
