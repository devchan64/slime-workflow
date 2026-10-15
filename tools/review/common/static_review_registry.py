"""정적 검수 GUI와 직접 문서 라우팅이 공유하는 등록 경로 검증."""
import json
from pathlib import Path
from urllib.parse import urlsplit


def load_static_review_paths(source_file_path):
    source_record_values=json.loads(Path(source_file_path).read_text())
    if not isinstance(source_record_values, dict):
        raise ValueError('정적 검수 원본은 객체여야 합니다.')
    current_page_records=source_record_values.get('pages',[])
    if not isinstance(current_page_records, list):
        raise ValueError('정적 검수 페이지 목록은 배열이어야 합니다.')
    static_review_paths={}
    for current_page_record in current_page_records:
        if not isinstance(current_page_record, dict):
            raise ValueError('정적 검수 페이지 항목은 객체여야 합니다.')
        if current_page_record.get('uiMode')!='gradio-static':continue
        current_identifier_value=current_page_record.get('id')
        current_path_value=current_page_record.get('path')
        if not isinstance(current_identifier_value,str) or not current_identifier_value or not isinstance(current_path_value,str) or not current_path_value:
            raise ValueError('정적 검수 페이지 항목 형식 오류')
        if not urlsplit(current_path_value).path.endswith('.html'):
            raise ValueError('정적 검수 페이지는 HTML 경로여야 합니다.')
        if current_identifier_value in static_review_paths:
            raise ValueError('정적 검수 페이지 ID 중복: '+current_identifier_value)
        static_review_paths[current_identifier_value]=current_path_value
    return static_review_paths

