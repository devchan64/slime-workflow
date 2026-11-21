"""Hermes 페이지를 공용 관리 화면에 합성한다."""
from tools.management.ui.gradio.hermes_agent_app import build_hermes_agent_interface


def build_generator_page(management_server_address, management_review_port, current_source_path=None):
    return build_hermes_agent_interface(include_advanced_controls=False, current_source_path=current_source_path)
