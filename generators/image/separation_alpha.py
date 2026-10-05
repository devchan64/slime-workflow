"""Qwen이 생성한 알파를 수정하지 않고 보존한다."""

def preserve_generated_alpha(current_source_image):
    if current_source_image.mode != 'RGBA':
        raise ValueError('Qwen 분리 결과에 네이티브 RGBA 출력이 필요합니다. 배경 제거로 대체하지 않습니다.')
    return current_source_image.copy()
