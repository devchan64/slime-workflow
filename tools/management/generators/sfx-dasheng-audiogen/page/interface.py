"""생성기 전용 화면 설정."""
from tools.management.ui.shared.audio_generator_page import build_music_interface

def build_generator_page(current_server_address, current_review_port):
    return build_music_interface('sfx-dasheng-audiogen', current_server_address)
