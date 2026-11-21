"""생성기 전용 페이지."""
from tools.management.ui.shared.flux_image_page import build_flux_image_page


def build_generator_page(current_server_address, current_review_port):
    return build_flux_image_page('flux-building', current_server_address, current_review_port)
