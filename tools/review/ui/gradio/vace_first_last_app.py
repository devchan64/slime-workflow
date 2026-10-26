"""첫·끝 프레임을 지정하는 FL2V 관리 페이지."""
import gradio as gr
from generators.vace.first_last import VACE_FIRST_LAST_ROOT
from tools.review.common.management_client import execute_remote_management_command
from tools.review.ui.gradio.vace_timeline_app import build_timeline_payload, restore_timeline_inputs
from tools.review.ui.gradio.vace_endpoint_app import build_endpoint_frame_interface


def execute_first_last_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan21-vace-fl2v', current_command_name, current_payload_record)


def build_first_last_payload(current_first_path, current_last_path, current_prompt_text, current_negative_text,
        current_frame_count, current_seed_value, current_steps_value, current_shift_value,
        current_guidance_value, current_conditioning_value, current_padding_color):
    if not current_first_path or not current_last_path:
        raise ValueError('첫 프레임과 마지막 프레임 이미지를 모두 첨부하세요.')
    if current_frame_count < 5:
        raise ValueError('FL2V는 5프레임 이상이어야 합니다.')
    current_payload_record = build_timeline_payload(
        [current_first_path, current_last_path], [[1, False], [current_frame_count, False]],
        current_prompt_text, current_negative_text, current_frame_count, current_seed_value,
        '832×480', current_steps_value, current_shift_value, current_guidance_value,
        current_conditioning_value, None, current_padding_color)
    current_payload_record['tag'] = 'FL2V · 첫·끝 프레임 보존'
    return current_payload_record


def restore_first_last_inputs(current_history_record):
    current_saved_inputs = restore_timeline_inputs(current_history_record, VACE_FIRST_LAST_ROOT)
    if current_saved_inputs[1] != [[1, False], [current_saved_inputs[4], False]] or len(current_saved_inputs[0]) != 2 or current_saved_inputs[11]:
        raise gr.Error('첫·끝 프레임 2장 보존 방식의 이력만 불러올 수 있습니다.')
    return (*current_saved_inputs[0], *current_saved_inputs[2:6],
            *current_saved_inputs[7:11], current_saved_inputs[12], current_saved_inputs[-1])


def build_first_last_interface(current_server_address):
    return build_endpoint_frame_interface(current_server_address, current_endpoint_mode=True,
        current_command_callback=execute_first_last_command, current_payload_callback=build_first_last_payload,
        current_restore_callback=restore_first_last_inputs)
