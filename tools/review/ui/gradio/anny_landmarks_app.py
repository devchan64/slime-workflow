"""ANNY 기준점 후보 검수 GUI. 모든 자료·기록은 HTTP 게이트웨이로 읽고 쓴다."""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import threading
import time

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from tools.review.common.management_client import execute_remote_management_command
from tools.review.domains.anny.landmarks import LANDMARK_IDENTIFIER_LABELS

LANDMARK_CANVAS_MARKUP = '<div style="position:relative;width:100%;height:560px"><canvas id="anny-landmark-mesh" aria-label="ANNY 기준점 선택 메시" style="width:100%;height:100%;touch-action:none"></canvas><canvas id="anny-landmark-overlay" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></canvas></div>'


def execute_landmark_request(current_command_name, current_payload_record):
    return execute_remote_management_command('anny-landmarks', 'landmark-' + current_command_name, current_payload_record)


def format_candidate_response(current_result_record):
    current_draft_record = current_result_record['draft']
    current_summary_text = '\n'.join(current_result_record['review']['warnings'])
    current_table_values = [[current_point_name, *current_point_record['position'], current_point_record['method'], current_point_record['evidence']] for current_point_name, current_point_record in current_draft_record['points'].items()]
    return current_draft_record, json.dumps(current_result_record, ensure_ascii=False), current_table_values, current_summary_text


def load_candidate_source():
    current_source_record = execute_landmark_request('source', {})
    return {'source': current_source_record['source'], 'points': {}}, json.dumps(current_source_record), json.dumps(current_source_record['source'], ensure_ascii=False, indent=2)


def update_candidate_point(current_draft_record, current_point_name, current_x_value, current_y_value, current_z_value, current_method_name, current_evidence_text):
    if current_draft_record is None:
        raise gr.Error('원본을 불러온 뒤 지정하세요.')
    current_updated_draft = copy.deepcopy(current_draft_record)
    current_updated_draft['points'][current_point_name] = {'position': [current_x_value, current_y_value, current_z_value], 'method': current_method_name, 'evidence': current_evidence_text}
    return format_candidate_response(execute_landmark_request('preview', current_updated_draft))


def remove_candidate_point(current_draft_record, current_point_name):
    if current_draft_record is None or current_point_name not in current_draft_record['points']:
        raise gr.Error('삭제할 후보 기준점이 없습니다.')
    current_updated_draft = copy.deepcopy(current_draft_record)
    del current_updated_draft['points'][current_point_name]
    return format_candidate_response(execute_landmark_request('preview', current_updated_draft))


def read_candidate_point(current_draft_record, current_point_name):
    if current_draft_record is None or current_point_name not in current_draft_record['points']:
        raise gr.Error('아직 지정하지 않은 기준점입니다. 표면 선택 또는 수동 좌표로 입력하세요.')
    current_point_record = current_draft_record['points'][current_point_name]
    return (*current_point_record['position'], current_point_record['method'], current_point_record['evidence'])


def save_candidate_record(current_draft_record):
    current_result_record = execute_landmark_request('save', current_draft_record)
    return '후보 저장 완료 · 리타기팅 미적용 · ' + current_result_record['id']


def load_candidate_record(current_record_identifier, current_replace_confirmed):
    if not current_replace_confirmed:
        raise gr.Error('현재 미저장 입력을 교체할지 확인하세요.')
    return (*format_candidate_response(execute_landmark_request('load', {'id': current_record_identifier})), False)


def build_landmark_interface():
    with gr.Blocks(title='ANNY 해부학 기준점 검수') as current_interface_blocks:
        gr.Markdown('# ANNY 해부학 기준점 검수\nneutral_v4 고정 원본 · 지정값은 **미검증 후보**입니다. 저장은 승인이나 리타기팅 적용이 아닙니다.')
        current_draft_state = gr.State(None)
        current_source_text = gr.Textbox(visible=False)
        current_review_text = gr.Textbox(visible=False)
        with gr.Row():
            with gr.Column():
                current_point_input = gr.Dropdown(choices=[(current_point_label, current_point_name) for current_point_name, current_point_label in LANDMARK_IDENTIFIER_LABELS.items()], value='left_shoulder_center', label='기준점')
                gr.Markdown('메시 클릭 → 선택 좌표 읽기 → 근거 입력 → 후보에 반영. 드래그는 회전, 휠은 확대입니다. 어깨 중심 등 내부 위치는 수동 XYZ를 사용하세요.')
                with gr.Row():
                    current_x_input = gr.Number(label='X · m', value=0)
                    current_y_input = gr.Number(label='Y · m', value=0)
                    current_z_input = gr.Number(label='Z · m', value=0)
                current_method_input = gr.Dropdown(['manual_xyz', 'surface_pick'], value='manual_xyz', label='지정 방식 · 좌표를 편집하면 manual_xyz 선택')
                current_pick_button = gr.Button('선택 좌표 읽기')
                current_read_button = gr.Button('현재 후보 좌표·근거 읽기')
                current_evidence_input = gr.Textbox(label='지정 근거 · 해부학 자료/관찰 방법/불확실성', lines=3)
                current_apply_button = gr.Button('후보에 반영 · 선택 기준점 갱신')
                current_remove_button = gr.Button('선택 기준점 후보 삭제')
                current_save_button = gr.Button('새 후보 기록 저장')
                current_save_feedback = gr.Textbox(label='저장·조작 결과', interactive=False)
            with gr.Column():
                gr.HTML(LANDMARK_CANVAS_MARKUP)
                current_camera_input = gr.Radio([('정면', 0), ('왼쪽', 90), ('후면', 180), ('오른쪽', 270)], value=0, label='검수 방향')
                gr.Markdown('마커는 가림 없이 표시됩니다. 빨강: 길이축, 초록: 직교화된 가로축, 파랑: 외적. 좌우의 해부학적 부호·관절축을 확정한 표시가 아닙니다.')
                current_status_output = gr.Textbox(label='검수 상태 · 미지정/퇴화 축은 생성하지 않음', value='기준점 미지정 · 후보를 반영하면 축 완전성과 퇴화 여부를 검사합니다.', lines=5, interactive=False)
        current_points_table = gr.Dataframe(headers=['기준점', 'X', 'Y', 'Z', '방식', '근거'], interactive=False, label='현재 후보 · 미저장 변경 포함')
        with gr.Accordion('고정 원본·좌표 변환·해시', open=False):
            current_provenance_text = gr.Textbox(interactive=False, lines=8)
        with gr.Group():
            gr.Markdown('## 누적 후보 이력\n각 저장은 새 기록입니다. 기존 기록은 덮어쓰지 않습니다. 재연결 후 저장된 기록을 다시 선택하세요.')
            current_history_input = gr.Dropdown(choices=[], label='저장 기록')
            current_history_button = gr.Button('이력 새로 고침')
            current_replace_input = gr.Checkbox(label='현재 미저장 후보를 선택 이력으로 교체', value=False)
            current_load_button = gr.Button('선택 후보 불러오기')
        current_review_outputs = [current_draft_state, current_review_text, current_points_table, current_status_output]
        current_apply_button.click(update_candidate_point, [current_draft_state, current_point_input, current_x_input, current_y_input, current_z_input, current_method_input, current_evidence_input], current_review_outputs)
        current_read_button.click(read_candidate_point, [current_draft_state, current_point_input], [current_x_input, current_y_input, current_z_input, current_method_input, current_evidence_input])
        current_remove_button.click(remove_candidate_point, [current_draft_state, current_point_input], current_review_outputs)
        current_save_button.click(save_candidate_record, current_draft_state, current_save_feedback)
        current_history_button.click(lambda: gr.update(choices=execute_landmark_request('history', {})['records']), outputs=current_history_input)
        current_load_button.click(load_candidate_record, [current_history_input, current_replace_input], [*current_review_outputs, current_replace_input])
        current_review_text.change(fn=None, inputs=current_review_text, js='(currentReviewText)=>window.updateLandmarkViewer(currentReviewText)')
        current_pick_button.click(fn=None, inputs=[current_x_input, current_y_input, current_z_input, current_method_input], outputs=[current_x_input, current_y_input, current_z_input, current_method_input, current_save_feedback], js='(...currentInputValues)=>{const currentPickedPoint=window.currentAnnyLandmarkViewer?.currentPickedPoint;return currentPickedPoint?[...currentPickedPoint,"surface_pick","좌표를 읽었습니다. 근거 입력 후 후보에 반영하세요."]:[...currentInputValues,"먼저 메시 표면을 클릭하세요."]}', queue=False)
        current_camera_input.change(fn=None, inputs=current_camera_input, js='(currentAngleValue)=>window.currentAnnyLandmarkViewer?.setPreviewRotation(currentAngleValue)', queue=False)
        current_interface_blocks.load(load_candidate_source, outputs=[current_draft_state, current_source_text, current_provenance_text]).then(fn=None, inputs=current_source_text, js='(currentSourceText)=>window.initializeLandmarkViewer(currentSourceText)')
    return current_interface_blocks


def create_landmark_loader():
    current_viewer_directory = WORKFLOW_ROOT_DIRECTORY / 'tools/review/ui/anny'
    return '()=>{' + (current_viewer_directory / 'anny-mesh-viewer.js').read_text() + '\n' + (current_viewer_directory / 'anny-landmarks.js').read_text() + '\n}'


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--port', type=int, required=True)
    current_argument_parser.add_argument('--review-port', type=int, required=True)
    current_argument_parser.add_argument('--owner-pid', type=int, required=True)
    current_argument_parser.add_argument('--root-path', default='/management/frame/anny-landmarks/')
    current_argument_values = current_argument_parser.parse_args()

    def monitor_landmark_owner():
        while os.getppid() == current_argument_values.owner_pid:
            time.sleep(1)
        os._exit(0)

    threading.Thread(target=monitor_landmark_owner, daemon=True).start()
    build_landmark_interface().queue().launch(server_name='127.0.0.1', server_port=current_argument_values.port, root_path=current_argument_values.root_path, js=create_landmark_loader(), allowed_paths=[])
