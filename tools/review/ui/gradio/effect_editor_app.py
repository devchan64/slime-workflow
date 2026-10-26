"""빌보드 연결 발광의 공용 좌표를 검수하는 Gradio 클라이언트."""
import copy
from pathlib import Path
from uuid import uuid4
import gradio as gr
import yaml
from tools.review.common.management_client import execute_remote_management_command
from tools.review.ui.gradio.asset_editor_app import refresh_content_snapshot_status


def load_effect_editor_choices():
    current_records=execute_remote_management_command('map-assets','effect-list',{})['effects']
    return gr.update(choices=[(current_record['name'],current_record['id']) for current_record in current_records],value=None)


def load_effect_editor_detail(current_effect_identifier):
    current_detail_record=execute_remote_management_command('map-assets','effect-load',{'id':current_effect_identifier})
    current_alignment_record=current_detail_record['document']['alignment']
    return current_detail_record,*current_alignment_record['target'],current_alignment_record['alpha'],current_alignment_record['frames'],0,'DB 원본을 불러왔습니다. 이 설정은 같은 종류를 사용하는 모든 이펙트에 적용됩니다.',gr.update(visible=current_detail_record['hostImage'] is not None)


def save_effect_editor_detail(current_detail_record,current_left_value,current_top_value,current_right_value,current_bottom_value,current_alpha_value,current_frame_values):
    yield gr.update(interactive=False,value='저장 중…'),current_detail_record,'DB 저장 중…'
    try:
        if not current_detail_record:raise ValueError('이펙트를 먼저 불러오세요.')
        current_alignment_record={**current_detail_record['document']['alignment'],'target':[current_left_value,current_top_value,current_right_value,current_bottom_value],'alpha':current_alpha_value,'frames':current_frame_values}
        current_saved_record=execute_remote_management_command('map-assets','effect-save',{'id':current_detail_record['document']['id'],'expectedRevision':current_detail_record['revision'],'requestId':str(uuid4()),'alignment':current_alignment_record})
        current_next_detail=copy.deepcopy(current_detail_record)
        current_next_detail['revision']=current_saved_record['revision']
        current_next_detail['document']['alignment']=current_alignment_record
        yield gr.update(interactive=True,value='선택 이펙트 변경 반영'),current_next_detail,'DB 저장 완료 · 에셋 원장에 주기적으로 반영됩니다.'
    except (ValueError,RuntimeError,OSError) as current_save_error:
        yield gr.update(interactive=True,value='선택 이펙트 변경 반영'),current_detail_record,'저장 실패 · 입력값 유지 · '+str(current_save_error)


def build_effect_editor_interface(current_review_port):
    current_vendor_manifest=yaml.safe_load((Path(__file__).parents[1]/'map/vendor/field-renderer/manifest.yaml').read_text())
    current_preview_script=Path(__file__).with_name('effect_editor_preview.js').read_text().replace('__RENDERER_URL__',f'http://127.0.0.1:{current_review_port}/isloon-map-review/vendor/field-renderer/{current_vendor_manifest["version"]}/field-renderer.mjs')
    with gr.Blocks(title='발광 이펙트 좌표 검수') as current_interface_blocks:
        gr.Markdown('## 발광 이펙트 좌표 검수\n버섯 발광은 빌보드와 겹쳐 보고, 나방·반딧불은 독립 시트로 검수합니다. 이미지는 파일로 유지하고 좌표는 DB 저장 후 에셋 원장에 지연 반영합니다.')
        with gr.Row():
            current_effect_choice=gr.Dropdown(label='발광 이펙트',choices=[])
            current_reload_button=gr.Button('목록 새로고침')
            current_load_button=gr.Button('선택 이펙트 불러오기')
        current_detail_record=gr.JSON(value={},visible=False)
        with gr.Row():
            with gr.Column():
                gr.Markdown('### 이펙트 대상 영역')
                with gr.Row():
                    current_left_value=gr.Number(label='왼쪽',value=0,step=.01)
                    current_top_value=gr.Number(label='위쪽',value=0,step=.01)
                with gr.Row():
                    current_right_value=gr.Number(label='오른쪽',value=1,step=.01)
                    current_bottom_value=gr.Number(label='아래쪽',value=1,step=.01)
                current_alpha_value=gr.Slider(label='공용 밝기',minimum=0,maximum=1,value=.5,step=.01)
                current_frame_values=gr.Dataframe(label='시트 프레임별 발광 영역 · 1~8',headers=['왼쪽','위쪽','오른쪽','아래쪽'],datatype=['number']*4,type='array',row_count=(8,'fixed'),column_count=(4,'fixed'),interactive=True)
                with gr.Accordion('좌표·저장 안내',open=False):
                    gr.Markdown('좌표는 각 이미지의 왼쪽 위 0,0부터 오른쪽 아래 1,1까지입니다. 버섯의 대상 영역은 빌보드 원본 기준입니다. 나방·반딧불은 맵에 지정된 반경의 정사각형 영역 기준이며 중심은 0.5,0.5입니다. 프레임 영역은 시트 각 칸의 좌표입니다. 모든 프레임을 확인하세요. 맵 배치·빌보드 앵커는 변경하지 않습니다. 다른 편집에서 저장하면 다시 불러온 뒤 적용해야 합니다.')
                current_save_button=gr.Button('선택 이펙트 변경 반영')
                current_save_status=gr.Markdown('선택 이펙트를 불러오세요.')
            with gr.Column():
                gr.Markdown('### 공용 렌더러 좌표 미리보기')
                current_play_enabled=gr.Checkbox(label='시트 애니메이션 재생',value=True)
                current_frame_index=gr.Slider(label='정지 프레임',minimum=0,maximum=7,step=1,value=0)
                current_host_enabled=gr.Checkbox(label='빌보드 원본 보기',value=True)
                current_bounds_enabled=gr.Checkbox(label='영역 가이드 보기',value=True)
                gr.HTML('<canvas id="effect-alignment-preview" width="640" height="640" aria-label="빌보드 발광 정렬 미리보기" style="width:100%;aspect-ratio:1"></canvas>')
                current_preview_status=gr.Textbox(label='미리보기 상태',interactive=False)
        current_sync_status=gr.Markdown()
        current_preview_inputs=[current_detail_record,current_left_value,current_top_value,current_right_value,current_bottom_value,current_alpha_value,current_frame_values,current_play_enabled,current_frame_index,current_host_enabled,current_bounds_enabled]
        current_load_outputs=[current_detail_record,current_left_value,current_top_value,current_right_value,current_bottom_value,current_alpha_value,current_frame_values,current_frame_index,current_save_status,current_host_enabled]
        current_load_button.click(load_effect_editor_detail,current_effect_choice,current_load_outputs).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        for current_input_component in current_preview_inputs[1:]:
            current_input_component.input(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_save_button.click(save_effect_editor_detail,current_preview_inputs[:7],[current_save_button,current_detail_record,current_save_status],concurrency_limit=1,trigger_mode='once')
        current_reload_button.click(load_effect_editor_choices,outputs=current_effect_choice)
        current_interface_blocks.load(load_effect_editor_choices,outputs=current_effect_choice)
        gr.Timer(5).tick(lambda:refresh_content_snapshot_status({'storage':'database'}),outputs=current_sync_status,show_progress='hidden')
    return current_interface_blocks
