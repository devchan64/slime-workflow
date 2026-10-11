"""앵커 검수의 실행 코드와 독립된 버전 있는 데이터 계약."""
from html.parser import HTMLParser
import json

ANCHOR_REVIEW_PAYLOAD_IDENTIFIER = 'anchor-review-data'
ANCHOR_REVIEW_PAYLOAD_VERSION = 1


def reject_review_duplicate_fields(current_field_pairs):
    current_payload_record = {}
    for current_field_name, current_field_value in current_field_pairs:
        if current_field_name in current_payload_record:
            raise ValueError(f'앵커 검수 데이터 중복 필드: {current_field_name}')
        current_payload_record[current_field_name] = current_field_value
    return current_payload_record


class AnimationReviewPayloadParser(HTMLParser):
    """지정한 JSON 데이터 블록만 읽으며 실행 스크립트는 해석하지 않는다."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.current_payload_count = 0
        self.current_payload_active = False
        self.current_payload_chunks = []

    def handle_starttag(self, current_tag_name, current_attribute_pairs):
        current_attribute_record = dict(current_attribute_pairs)
        if current_attribute_record.get('id') != ANCHOR_REVIEW_PAYLOAD_IDENTIFIER:
            return
        if current_tag_name != 'script' or current_attribute_record.get('type') != 'application/json':
            raise ValueError('앵커 검수 데이터 블록은 application/json script여야 합니다.')
        if len(current_attribute_record) != len(current_attribute_pairs):
            raise ValueError('앵커 검수 데이터 블록 중복 속성')
        self.current_payload_count += 1
        if self.current_payload_count != 1:
            raise ValueError('앵커 검수 데이터 블록이 중복되었습니다.')
        self.current_payload_active = True

    def handle_data(self, current_data_text):
        if self.current_payload_active:
            self.current_payload_chunks.append(current_data_text)

    def handle_endtag(self, current_tag_name):
        if current_tag_name == 'script':
            self.current_payload_active = False


def read_animation_review_payload(current_page_source):
    """외부 실행 코드 평가나 복구 파싱 없이 JSON 계약을 검증한다."""
    current_payload_parser = AnimationReviewPayloadParser()
    current_payload_parser.feed(current_page_source)
    current_payload_parser.close()
    if current_payload_parser.current_payload_count != 1 or current_payload_parser.current_payload_active:
        raise ValueError('앵커 검수 JSON 데이터 블록이 없거나 닫히지 않았습니다. 검수 페이지를 다시 게시하세요.')
    current_payload_record = json.loads(''.join(current_payload_parser.current_payload_chunks), object_pairs_hook=reject_review_duplicate_fields)
    if not isinstance(current_payload_record, dict) or set(current_payload_record) != {'schemaVersion', 'sourceMetadata', 'frames'}:
        raise ValueError('앵커 검수 데이터 필드 형식 오류')
    if type(current_payload_record['schemaVersion']) is not int or current_payload_record['schemaVersion'] != ANCHOR_REVIEW_PAYLOAD_VERSION:
        raise ValueError('지원하지 않는 앵커 검수 데이터 버전')
    if not isinstance(current_payload_record['sourceMetadata'], dict) or not isinstance(current_payload_record['frames'], list) or not current_payload_record['frames'] or not all(isinstance(current_frame_record, dict) for current_frame_record in current_payload_record['frames']):
        raise ValueError('앵커 검수 원본·프레임 데이터 형식 오류')
    return current_payload_record
