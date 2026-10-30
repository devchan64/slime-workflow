"""업로드 순서를 보존하는 공용 PNG 입력 미리보기."""
import gradio as gr

INPUT_PREVIEW_COLUMN_COUNT = 3
INPUT_PREVIEW_ROW_COUNT = 2


def describe_input_preview(current_file_paths):
    return [(str(current_file_path),f'{current_frame_index}번') for current_frame_index,current_file_path in enumerate(current_file_paths or [],1)]


def build_input_preview(current_file_control,current_label_text):
    current_preview_gallery = gr.Gallery(value=[],label=current_label_text,columns=INPUT_PREVIEW_COLUMN_COUNT,rows=INPUT_PREVIEW_ROW_COUNT,object_fit='contain',interactive=False,allow_preview=True)
    current_file_control.change(describe_input_preview,inputs=current_file_control,outputs=current_preview_gallery,queue=False)
    return current_preview_gallery
