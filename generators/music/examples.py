"""버전 관리되는 음악 예제 목록을 엄격하게 검증한다."""
from pathlib import Path
import yaml
from generators.music.contracts import MusicDefaultsLoader, validate_music_request

MUSIC_EXAMPLE_CATALOG = Path(__file__).with_name('examples.yaml')
MUSIC_EXAMPLE_FIELDS = {'id','label','description','source_generation_id','request'}
MUSIC_EXAMPLE_REQUEST_FIELDS = {'prompt','lyrics','duration_seconds','seed','loop_request','min_duration_seconds'}


def load_music_examples():
    current_catalog_record = yaml.load(MUSIC_EXAMPLE_CATALOG.read_text(encoding='utf-8'),Loader=MusicDefaultsLoader)
    if not isinstance(current_catalog_record,dict) or set(current_catalog_record) != {'version','examples'} or type(current_catalog_record['version']) is not int or current_catalog_record['version'] != 1:
        raise ValueError('음악 예제 목록 스키마 오류')
    current_example_records = current_catalog_record['examples']
    if not isinstance(current_example_records,list) or not current_example_records:
        raise ValueError('음악 예제 목록은 비어 있지 않은 배열이어야 합니다.')
    current_seen_identifiers = set()
    for current_example_record in current_example_records:
        if not isinstance(current_example_record,dict) or set(current_example_record) != MUSIC_EXAMPLE_FIELDS:
            raise ValueError('음악 예제 필드 오류')
        for current_field_name in MUSIC_EXAMPLE_FIELDS - {'request'}:
            if not isinstance(current_example_record[current_field_name],str) or not current_example_record[current_field_name].strip():
                raise ValueError('음악 예제 메타데이터 오류: '+current_field_name)
        if current_example_record['id'] in current_seen_identifiers:
            raise ValueError('중복 음악 예제 ID')
        current_seen_identifiers.add(current_example_record['id'])
        current_request_record = current_example_record['request']
        if not isinstance(current_request_record,dict) or set(current_request_record) != MUSIC_EXAMPLE_REQUEST_FIELDS:
            raise ValueError('음악 예제 입력 필드 오류')
        validate_music_request('music-minimax',current_request_record)
    return current_example_records


def resolve_music_example(current_example_identifier):
    for current_example_record in load_music_examples():
        if current_example_record['id'] == current_example_identifier:
            return current_example_record
    raise ValueError('예제를 목록에서 선택하세요.')
