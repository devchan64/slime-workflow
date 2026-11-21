"""생성기 전용 화면 설정."""
from tools.management.ui.shared.qwen_generator_page import build_qwen_2511_interface

GENERATOR_PAGE_OPTIONS = {'qwen21_mode_enabled': True, 'prop_mode_enabled': True}

def build_generator_page(current_server_address, current_review_port):
    return build_qwen_2511_interface(current_server_address, **GENERATOR_PAGE_OPTIONS)
