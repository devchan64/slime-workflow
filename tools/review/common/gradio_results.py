"""Gradio 표준 결과 갤러리와 공용 이미지 주소 구성."""
import gradio as gr
from io import BytesIO
from urllib.parse import urlsplit
from urllib.request import urlopen
from PIL import Image


def load_gallery_image_values(current_gallery_items, server_base_address, timeout_seconds=10):
    """내부 서버 주소 대신 Gradio가 현재 접속 주소로 제공할 이미지를 반환한다."""
    current_server_parts = urlsplit(server_base_address)
    current_loaded_items = []
    for current_image_address, current_image_label in current_gallery_items:
        current_image_parts = urlsplit(current_image_address)
        if (current_image_parts.scheme, current_image_parts.netloc) != (current_server_parts.scheme, current_server_parts.netloc):
            raise ValueError('결과 이미지가 관리 서버 주소와 일치하지 않습니다.')
        with urlopen(current_image_address, timeout=timeout_seconds) as current_image_response:
            with Image.open(BytesIO(current_image_response.read())) as current_image_value:
                current_loaded_items.append((current_image_value.copy(), current_image_label))
    return current_loaded_items


def build_generation_gallery(current_label_text='생성 결과'):
    """결과 이미지는 별도 미리보기 없이 기본 갤러리에서 검수한다."""
    return gr.Gallery(value=[], label=current_label_text, columns=2, height='max-content',
                      object_fit='contain', allow_preview=False, interactive=False, visible=False)


def collect_generation_gallery(current_image_address, include_repeat_preview=False, server_base_address=''):
    if not current_image_address:
        return []
    if not current_image_address.startswith(('http://','https://')):
        if not server_base_address:
            raise ValueError('결과 갤러리의 상대 이미지 주소에는 관리 서버 주소가 필요합니다.')
        current_image_address=server_base_address.rstrip('/')+'/'+current_image_address.lstrip('/')
    current_gallery_items=[(current_image_address,'생성 원본')]
    if include_repeat_preview:
        current_gallery_items.append((current_image_address.replace('/result.png','/tiled-preview.png'),'3×3 반복 검수'))
    return current_gallery_items
