"""Gradio 표준 결과 갤러리와 공용 이미지 주소 구성."""
import gradio as gr


def build_generation_gallery(current_label_text='생성 결과'):
    """결과 이미지는 기본 갤러리의 확대·다운로드 기능으로 검수한다."""
    return gr.Gallery(value=[], label=current_label_text, columns=2,
                      object_fit='contain', interactive=False, visible=False)


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
