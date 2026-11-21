"""공통 이력 복원 오류를 기존 Gradio 화면에 표시한다."""
import gradio as gr

from tools.management.common import reference_restore


def validate_history_input_settings(current_history_record):
    try:
        return reference_restore.validate_history_input_settings(current_history_record)
    except reference_restore.HistoryInputError as exc:
        raise gr.Error(str(exc)) from exc


def restore_reference_inputs(current_history_record, reference_storage_root=None, reference_slot_limit=3):
    try:
        return reference_restore.restore_reference_inputs(
            current_history_record, reference_storage_root, reference_slot_limit
        )
    except reference_restore.HistoryInputError as exc:
        raise gr.Error(str(exc)) from exc
