"""폐기된 F2V 주소에 대체 생성기를 안내한다."""
import gradio as gr


def build_first_frame_interface(current_server_address):
    with gr.Blocks(title='F2V 생성기 폐기') as current_interface_blocks:
        gr.Markdown('## F2V 생성기는 폐기되었습니다.\n첫·끝 이미지를 사용하는 [FL2V 생성기](/management/frame/vace-fl2v-generator/?tool=vace-fl2v-generator&category=animation-tool) 또는 [V2V 생성기](/management/frame/vace-v2v-generator/?tool=vace-v2v-generator&category=animation-tool)를 사용하세요.')
    return current_interface_blocks
