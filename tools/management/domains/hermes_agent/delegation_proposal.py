"""Hermes 답변의 미신뢰 Kimodo 제안을 검토 가능한 입력으로 제한한다."""
import re

HERMES_PROPOSAL_START = 'HERMES_KIMODO_PROPOSAL'
HERMES_PROPOSAL_END = 'END_HERMES_KIMODO_PROPOSAL'


def parse_hermes_kimodo_proposal(current_answer_text):
    """지정된 단일 블록만 파싱하며 동작 실행이나 접수는 수행하지 않는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    if not isinstance(current_answer_text, str) or len(current_answer_text) > 8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_PROPOSAL_START) != 2 or current_answer_text.count(HERMES_PROPOSAL_END) != 1:
        raise ValueError('Kimodo 제안 블록이 하나 필요합니다.')
    current_block_match = re.search(r'(?m)^HERMES_KIMODO_PROPOSAL\s*\n([\s\S]*?)\nEND_HERMES_KIMODO_PROPOSAL\s*$', current_answer_text)
    if current_block_match is None or len(current_block_match.group(1)) > 4000:
        raise ValueError('Kimodo 제안 형식 또는 크기 오류')
    current_proposal_record = parse_management_request_json(current_block_match.group(1))
    validate_kimodo_proposal_inputs(current_proposal_record)
    return current_proposal_record


def validate_kimodo_proposal_inputs(current_proposal_record):
    from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
    if not isinstance(current_proposal_record, dict) or set(current_proposal_record) != {'prompt', 'frames', 'steps', 'seed'}:
        raise ValueError('Kimodo 제안에는 prompt, frames, steps, seed만 허용합니다.')
    current_generation_record = {current_key_name: current_value for current_key_name, current_value in KIMODO_DEFAULT_SETTINGS.items() if current_key_name != 'schema_version'}
    current_generation_record.update(current_proposal_record, action='generate')
    validate_kimodo_request(current_generation_record)
    return current_generation_record


HERMES_FLUX_PROPOSAL_START = 'HERMES_FLUX_PROPOSAL'
HERMES_FLUX_PROPOSAL_END = 'END_HERMES_FLUX_PROPOSAL'


def parse_hermes_flux_proposal(current_answer_text):
    """미신뢰 답변의 텍스트 이미지 제안만 기존 FLUX 검증기로 확인한다."""
    from tools.management.domains.image.flux_image_generation import FluxImageGenerationManager
    from tools.management.common.management_gateway import parse_management_request_json
    if not isinstance(current_answer_text, str) or len(current_answer_text) > 8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_FLUX_PROPOSAL_START) != 2 or current_answer_text.count(HERMES_FLUX_PROPOSAL_END) != 1:
        raise ValueError('FLUX 제안 블록이 하나 필요합니다.')
    current_block_match = re.search(r'(?m)^HERMES_FLUX_PROPOSAL\s*\n([\s\S]*?)\nEND_HERMES_FLUX_PROPOSAL\s*$', current_answer_text)
    if current_block_match is None or len(current_block_match.group(1)) > 4000:
        raise ValueError('FLUX 제안 형식 또는 크기 오류')
    current_proposal_record = parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_record, dict) or set(current_proposal_record) not in ({'prompt','width','height','seed'},{'service','prompt','width','height','seed'}):
        raise ValueError('FLUX 제안에는 service, prompt, width, height, seed만 허용합니다.')
    current_service_name=current_proposal_record.get('service','flux-image')
    from tools.management.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    if not isinstance(current_service_name,str) or current_service_name not in (*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression'):
        raise ValueError('지원하는 FLUX 이미지 프로필이 아닙니다.')
    current_generation_record = {key:value for key,value in current_proposal_record.items() if key!='service'}
    current_placeholder_images=[]
    if current_service_name=='flux-expression' or FLUX_IMAGE_PROFILE_RECORDS[current_service_name][4]:
        import base64
        import io
        from PIL import Image
        current_placeholder_buffer=io.BytesIO()
        Image.new('RGB',(16,16)).save(current_placeholder_buffer,format='PNG')
        current_placeholder_images=[base64.b64encode(current_placeholder_buffer.getvalue()).decode('ascii')]
    current_generation_record.update(action='generate',images=current_placeholder_images,steps=16)
    if current_service_name=='flux-expression':
        from tools.management.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        current_generation_record['tag']=''
        FluxExpressionGenerationManager().validate_generation_request(current_generation_record)
    else:
        FluxImageGenerationManager(current_service_name).validate_generation_request(current_generation_record)
    return current_proposal_record


HERMES_FIELD_PROPOSAL_START = 'HERMES_FIELD_PROPOSAL'
HERMES_FIELD_PROPOSAL_END = 'END_HERMES_FIELD_PROPOSAL'

HERMES_CITY_PROPOSAL_START = 'HERMES_CITY_PROPOSAL'
HERMES_CITY_PROPOSAL_END = 'END_HERMES_CITY_PROPOSAL'

HERMES_BUILDING_PROPOSAL_START = 'HERMES_BUILDING_PROPOSAL'
HERMES_BUILDING_PROPOSAL_END = 'END_HERMES_BUILDING_PROPOSAL'


def parse_hermes_building_proposal(current_answer_text):
    """완료 답변에서 기존 건물 앵커 변경 초안만 읽는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.building_operations import inspect_hermes_building_draft
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count(HERMES_BUILDING_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_BUILDING_PROPOSAL_END)!=1:
        raise ValueError('건물 제안 블록이 하나 필요합니다.')
    current_match_value=re.search(r'(?m)^HERMES_BUILDING_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_BUILDING_PROPOSAL[ \t]*$',current_answer_text)
    if current_match_value is None or len(current_match_value.group(1))>4000:raise ValueError('건물 제안 형식 오류')
    current_draft_record=parse_management_request_json(current_match_value.group(1))
    inspect_hermes_building_draft(current_draft_record)
    return current_draft_record


def parse_hermes_city_proposal(current_answer_text):
    """도시 문서의 기존 값에 대한 제한된 변경 제안을 읽는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.field_map_operations import HERMES_FIELD_MAP_PATTERN
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count(HERMES_CITY_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_CITY_PROPOSAL_END)!=1:
        raise ValueError('도시 맵 제안 블록이 하나 필요합니다.')
    current_match_value=re.search(r'(?m)^HERMES_CITY_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_CITY_PROPOSAL[ \t]*$',current_answer_text)
    if current_match_value is None or len(current_match_value.group(1))>6000:raise ValueError('도시 맵 제안 형식 오류')
    current_proposal_record=parse_management_request_json(current_match_value.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'map','generation','revision','changes'}:
        raise ValueError('도시 맵 제안 필드 오류')
    if not isinstance(current_proposal_record['map'],str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_proposal_record['map']):raise ValueError('도시 맵 ID 오류')
    if any(type(current_proposal_record[current_name]) is not int or current_proposal_record[current_name]<0 for current_name in ('generation','revision')):raise ValueError('도시 세대·리비전 오류')
    current_changes_value=current_proposal_record['changes']
    if not isinstance(current_changes_value,list) or not 1<=len(current_changes_value)<=30:raise ValueError('도시 변경은 1~30건이 필요합니다.')
    current_seen_paths=set()
    for current_change_record in current_changes_value:
        if not isinstance(current_change_record,dict) or set(current_change_record)!={'path','before','after'}:raise ValueError('도시 변경 필드 오류')
        current_path_value=current_change_record['path']
        if (not isinstance(current_path_value,list) or not 2<=len(current_path_value)<=12 or current_path_value[0]!='data'
                or any(not ((isinstance(current_item,str) and 1<=len(current_item)<=100 and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',current_item)) or (type(current_item) is int and 0<=current_item<=10000)) for current_item in current_path_value)):
            raise ValueError('도시 변경 경로 오류')
        current_path_key=tuple(current_path_value)
        if any(current_path_key[:len(current_existing)]==current_existing or current_existing[:len(current_path_key)]==current_path_key for current_existing in current_seen_paths):raise ValueError('도시 변경 경로 중복 또는 중첩')
        current_seen_paths.add(current_path_key)
    return current_proposal_record


def parse_hermes_field_proposal(current_answer_text):
    """미신뢰 답변에서 야외 셀 변경 제안만 추출한다. 원본 검증은 별도다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.field_map_operations import HERMES_FIELD_MAP_PATTERN
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_FIELD_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_FIELD_PROPOSAL_END)!=1:
        raise ValueError('야외 맵 제안 블록이 하나 필요합니다.')
    current_block_match = re.search(r'(?m)^HERMES_FIELD_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_FIELD_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>6000:
        raise ValueError('야외 맵 제안 형식 또는 크기 오류')
    current_proposal_record = parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'map','revision','cells'}:
        raise ValueError('야외 맵 제안에는 map·revision·cells만 허용합니다.')
    if not isinstance(current_proposal_record['map'],str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_proposal_record['map']):
        raise ValueError('맵 ID 형식 오류')
    if not isinstance(current_proposal_record['revision'],str) or not 0<len(current_proposal_record['revision'])<=4096:
        raise ValueError('맵 리비전 형식 오류')
    current_cells_value = current_proposal_record['cells']
    if not isinstance(current_cells_value,list) or not 1<=len(current_cells_value)<=30:
        raise ValueError('셀 변경은 1~30개가 필요합니다.')
    current_seen_positions = set()
    for current_cell_value in current_cells_value:
        if not isinstance(current_cell_value,dict) or set(current_cell_value)!={'column','row','tile','height','blocked'}:
            raise ValueError('셀 변경 필드 오류')
        if any(type(current_cell_value[key]) is not int or not 0<=current_cell_value[key]<=10000 for key in ('column','row')):
            raise ValueError('셀 좌표 형식 오류')
        if type(current_cell_value['height']) is not int or not 0<=current_cell_value['height']<=20 or type(current_cell_value['blocked']) is not bool:
            raise ValueError('셀 고도 또는 차단 값 오류')
        if not isinstance(current_cell_value['tile'],str) or len(current_cell_value['tile'])!=1:
            raise ValueError('셀 타일 코드 형식 오류')
        current_cell_position = (current_cell_value['column'],current_cell_value['row'])
        if current_cell_position in current_seen_positions:
            raise ValueError('중복 셀 변경')
        current_seen_positions.add(current_cell_position)
    return current_proposal_record


HERMES_TRANSLATION_PROPOSAL_START = 'HERMES_TRANSLATION_PROPOSAL'
HERMES_TRANSLATION_PROPOSAL_END = 'END_HERMES_TRANSLATION_PROPOSAL'


def parse_hermes_translation_proposal(current_answer_text):
    """단일 미신뢰 번역 제안을 기존 입력·용어 정책으로 검증한다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.translation.service import validate_translation_submission
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_TRANSLATION_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_TRANSLATION_PROPOSAL_END)!=1:
        raise ValueError('번역 제안 블록이 하나 필요합니다.')
    current_block_match = re.search(r'(?m)^HERMES_TRANSLATION_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_TRANSLATION_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>7000:
        raise ValueError('번역 제안 형식 또는 크기 오류')
    current_proposal_value = parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_value,dict) or set(current_proposal_value)!={'text','target_language','glossary'}:
        raise ValueError('번역 제안에는 text·target_language·glossary만 허용합니다.')
    validate_translation_submission(current_proposal_value)
    return current_proposal_value


HERMES_AUDIO_PROPOSAL_START = 'HERMES_AUDIO_PROPOSAL'
HERMES_AUDIO_PROPOSAL_END = 'END_HERMES_AUDIO_PROPOSAL'


def parse_hermes_audio_proposal(current_answer_text):
    """단일 오디오 제안을 화면에서 보존 가능한 필드와 기존 계약으로 검증한다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.audio_operations import validate_hermes_audio_request
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_AUDIO_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_AUDIO_PROPOSAL_END)!=1:
        raise ValueError('오디오 제안 블록이 하나 필요합니다.')
    current_block_match=re.search(r'(?m)^HERMES_AUDIO_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_AUDIO_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>7000:
        raise ValueError('오디오 제안 형식 또는 크기 오류')
    current_proposal_value=parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_value,dict) or set(current_proposal_value)!={'service','request'} or not isinstance(current_proposal_value['request'],dict):
        raise ValueError('오디오 제안에는 service와 request만 허용합니다.')
    current_service_name=current_proposal_value['service']
    current_request_value=current_proposal_value['request']
    current_expected_fields={'action','prompt','seed','loop_request'}
    if current_service_name=='music-heartmula':
        current_expected_fields|={'lyrics','duration_seconds'}
    elif current_service_name!='sfx-dasheng-audiogen':
        raise ValueError('지원하는 오디오 생성 서비스가 아닙니다.')
    if set(current_request_value)!=current_expected_fields:
        raise ValueError('오디오 서비스에 맞는 제안 입력이 필요합니다.')
    validate_hermes_audio_request(current_service_name,current_request_value)
    return current_proposal_value


HERMES_VIDEO_PROPOSAL_START = 'HERMES_VIDEO_PROPOSAL'
HERMES_VIDEO_PROPOSAL_END = 'END_HERMES_VIDEO_PROPOSAL'
HERMES_VIDEO_PROPOSAL_MODES = {
    'dwpose':('image',),
    'wan22-animate2':('motion',),
    'wan22-fun-control':('frames','pose_video','driving_video'),
    'wan22-vace':('text','reference','first_frame','video_edit','video_condition','pose'),
}


def parse_hermes_video_proposal(current_answer_text):
    """동작·영상의 서비스·모드·지시만 읽으며 첨부와 경로는 허용하지 않는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_VIDEO_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_VIDEO_PROPOSAL_END)!=1:
        raise ValueError('동작·영상 제안 블록이 하나 필요합니다.')
    current_block_match=re.search(r'(?m)^HERMES_VIDEO_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_VIDEO_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>7000:
        raise ValueError('동작·영상 제안 형식 또는 크기 오류')
    current_proposal_value=parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_value,dict) or set(current_proposal_value)!={'service','mode','prompt'}:
        raise ValueError('동작·영상 제안에는 service·mode·prompt만 허용합니다.')
    current_service_name=current_proposal_value['service']
    current_mode_value=current_proposal_value['mode']
    current_prompt_text=current_proposal_value['prompt']
    if not isinstance(current_service_name,str) or current_service_name not in HERMES_VIDEO_PROPOSAL_MODES:
        raise ValueError('지원하는 동작·영상 서비스가 아닙니다.')
    if not isinstance(current_mode_value,str) or current_mode_value not in HERMES_VIDEO_PROPOSAL_MODES[current_service_name]:
        raise ValueError('서비스에 맞는 입력 모드가 아닙니다.')
    if not isinstance(current_prompt_text,str) or len(current_prompt_text)>6000 or '\x00' in current_prompt_text:
        raise ValueError('동작·영상 지시 형식 오류')
    if current_service_name=='dwpose' and current_prompt_text:
        raise ValueError('DWPose 이미지 추출에는 지시를 지정하지 않습니다.')
    if current_service_name!='dwpose' and not current_prompt_text.strip():
        raise ValueError('영상 장면·동작 지시가 필요합니다.')
    return current_proposal_value


HERMES_BILLBOARD_PROPOSAL_START = 'HERMES_BILLBOARD_PROPOSAL'
HERMES_BILLBOARD_PROPOSAL_END = 'END_HERMES_BILLBOARD_PROPOSAL'


def parse_hermes_billboard_proposal(current_answer_text):
    """카탈로그에서 읽을 수 있는 속성의 현재값과 변경 제안만 파싱한다."""
    import math
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.billboard_operations import BILLBOARD_IDENTIFIER_PATTERN
    from tools.management.domains.hermes_agent.asset_observer import BILLBOARD_DISPLAY_FIELDS
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_BILLBOARD_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_BILLBOARD_PROPOSAL_END)!=1:
        raise ValueError('빌보드 제안 블록이 하나 필요합니다.')
    current_block_match=re.search(r'(?m)^HERMES_BILLBOARD_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_BILLBOARD_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>4000:
        raise ValueError('빌보드 제안 형식 또는 크기 오류')
    current_proposal_record=parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'texture','expected','values'}:
        raise ValueError('빌보드 제안에는 texture·expected·values만 허용합니다.')
    if not isinstance(current_proposal_record['texture'],str) or not BILLBOARD_IDENTIFIER_PATTERN.fullmatch(current_proposal_record['texture']):
        raise ValueError('빌보드 ID 오류')
    current_expected_values=current_proposal_record['expected']
    current_proposed_values=current_proposal_record['values']
    current_allowed_fields=set(BILLBOARD_DISPLAY_FIELDS)-{'billboardAnchorMode'}
    if not isinstance(current_expected_values,dict) or not isinstance(current_proposed_values,dict) or not current_proposed_values or set(current_expected_values)!=set(current_proposed_values) or set(current_proposed_values)-current_allowed_fields:
        raise ValueError('카탈로그에서 확인한 변경 대상 속성의 현재값과 제안값이 필요합니다.')
    for current_field_name in current_proposed_values:
        for current_field_value in (current_expected_values[current_field_name],current_proposed_values[current_field_name]):
            if current_field_name=='billboardBlocksMovement':
                if type(current_field_value) is not bool:
                    raise ValueError('통행 차단 값은 불리언이어야 합니다.')
            elif type(current_field_value) not in (int,float) or not math.isfinite(current_field_value):
                raise ValueError('속성 값은 유한한 숫자여야 합니다.')
    return current_proposal_record


HERMES_EFFECT_PROPOSAL_START = 'HERMES_EFFECT_PROPOSAL'
HERMES_EFFECT_PROPOSAL_END = 'END_HERMES_EFFECT_PROPOSAL'


def parse_hermes_effect_proposal(current_answer_text):
    """완료 답변의 좌표 초안만 읽으며 원본 조회와 저장은 수행하지 않는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.effect_operations import validate_hermes_effect_edit
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_EFFECT_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_EFFECT_PROPOSAL_END)!=1:
        raise ValueError('이펙트 제안 블록이 하나 필요합니다.')
    current_block_match=re.search(r'(?m)^HERMES_EFFECT_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_EFFECT_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>6000:
        raise ValueError('이펙트 제안 형식 또는 크기 오류')
    current_proposal_record=parse_management_request_json(current_block_match.group(1))
    validate_hermes_effect_edit(current_proposal_record)
    return current_proposal_record


HERMES_SPRITE_PROPOSAL_START = 'HERMES_SPRITE_PROPOSAL'
HERMES_SPRITE_PROPOSAL_END = 'END_HERMES_SPRITE_PROPOSAL'


def parse_hermes_sprite_proposal(current_answer_text):
    """미신뢰 답변에서 단일 앵커 변경 제안만 추출한다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.sprite_operations import validate_hermes_sprite_anchor_draft
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_SPRITE_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_SPRITE_PROPOSAL_END)!=1:
        raise ValueError('스프라이트 제안 블록이 하나 필요합니다.')
    current_block_match=re.search(r'(?m)^HERMES_SPRITE_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_SPRITE_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>6000:
        raise ValueError('스프라이트 제안 형식 또는 크기 오류')
    current_proposal_record=parse_management_request_json(current_block_match.group(1))
    validate_hermes_sprite_anchor_draft(current_proposal_record)
    return current_proposal_record


HERMES_WRITER_PROPOSAL_START = 'HERMES_WRITER_PROPOSAL'
HERMES_WRITER_PROPOSAL_END = 'END_HERMES_WRITER_PROPOSAL'


def parse_hermes_writer_proposal(current_answer_text):
    """완료 답변의 단일 작가 요청을 검증하며 생성·적용은 수행하지 않는다."""
    from generators.writer_agent.jobs import validate_job_request
    from tools.management.common.management_gateway import parse_management_request_json
    if not isinstance(current_answer_text, str) or len(current_answer_text) > 8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_WRITER_PROPOSAL_START) != 2 or current_answer_text.count(HERMES_WRITER_PROPOSAL_END) != 1:
        raise ValueError('작가 제안 블록이 하나 필요합니다.')
    current_block_match = re.search(r'(?m)^HERMES_WRITER_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_WRITER_PROPOSAL[ \t]*$', current_answer_text)
    if current_block_match is None or len(current_block_match.group(1)) > 7000:
        raise ValueError('작가 제안 형식 또는 크기 오류')
    current_proposal_record = parse_management_request_json(current_block_match.group(1))
    return validate_job_request(current_proposal_record)


HERMES_CAPTURE_PROPOSAL_START = 'HERMES_CAPTURE_PROPOSAL'
HERMES_CAPTURE_PROPOSAL_END = 'END_HERMES_CAPTURE_PROPOSAL'


def parse_hermes_capture_proposal(current_answer_text):
    """단일 미신뢰 캡처 제안을 기존 검증기로 정규화하며 실행하지 않는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.capture_delegation import normalize_capture_delegation_request
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count(HERMES_CAPTURE_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_CAPTURE_PROPOSAL_END)!=1:
        raise ValueError('캡처 제안 블록이 하나 필요합니다.')
    current_block_match=re.search(r'(?m)^HERMES_CAPTURE_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_CAPTURE_PROPOSAL[ \t]*$',current_answer_text)
    if current_block_match is None or len(current_block_match.group(1))>7000:
        raise ValueError('캡처 제안 형식 또는 크기 오류')
    current_proposal_value=parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_value,dict) or set(current_proposal_value)!={'service','settings'}:
        raise ValueError('캡처 제안에는 service와 settings만 허용합니다.')
    current_service_name=current_proposal_value['service']
    current_capture_settings=normalize_capture_delegation_request(current_service_name,current_proposal_value['settings'])
    return {'service':current_service_name,'settings':current_capture_settings}


HERMES_MODEL_PREPARATION_PROPOSAL_START = 'HERMES_MODEL_PREPARATION_PROPOSAL'
HERMES_MODEL_PREPARATION_PROPOSAL_END = 'END_HERMES_MODEL_PREPARATION_PROPOSAL'


def parse_hermes_model_preparation_proposal(current_answer_text):
    """미신뢰 답변에서 모델 서비스 한 개만 추출하며 준비를 실행하지 않는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.common.model_management_catalog import MODEL_PREPARATION_SERVICES
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count(HERMES_MODEL_PREPARATION_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_MODEL_PREPARATION_PROPOSAL_END)!=1:
        raise ValueError('모델 준비 제안 블록이 하나 필요합니다.')
    current_match_value=re.search(r'(?m)^HERMES_MODEL_PREPARATION_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_MODEL_PREPARATION_PROPOSAL[ \t]*$',current_answer_text)
    if current_match_value is None or len(current_match_value.group(1))>500:
        raise ValueError('모델 준비 제안 형식 오류')
    current_proposal_record=parse_management_request_json(current_match_value.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'service'} or not isinstance(current_proposal_record['service'],str) or current_proposal_record['service'] not in {current_service_name for _,current_service_name in MODEL_PREPARATION_SERVICES}:
        raise ValueError('모델 준비 서비스 오류')
    return current_proposal_record


HERMES_KIMODO_RESUME_PROPOSAL_START = 'HERMES_KIMODO_RESUME_PROPOSAL'
HERMES_KIMODO_RESUME_PROPOSAL_END = 'END_HERMES_KIMODO_RESUME_PROPOSAL'


def parse_hermes_kimodo_resume_proposal(current_answer_text):
    """미신뢰 답변에서 확인한 Kimodo 작업과 검토값만 읽는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count(HERMES_KIMODO_RESUME_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_KIMODO_RESUME_PROPOSAL_END)!=1:
        raise ValueError('Kimodo 재개 제안 블록이 하나 필요합니다.')
    current_match_value=re.search(r'(?m)^HERMES_KIMODO_RESUME_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_KIMODO_RESUME_PROPOSAL[ \t]*$',current_answer_text)
    if current_match_value is None or len(current_match_value.group(1))>500:raise ValueError('Kimodo 재개 제안 형식 오류')
    current_proposal_record=parse_management_request_json(current_match_value.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'job_id','expected_resume_fingerprint'} or not validate_service_job_identifier('kimodo',current_proposal_record['job_id']) or not isinstance(current_proposal_record['expected_resume_fingerprint'],str) or not re.fullmatch(r'[a-f0-9]{64}',current_proposal_record['expected_resume_fingerprint']):raise ValueError('Kimodo 재개 제안 대상 오류')
    return current_proposal_record


HERMES_FLUX_RESUME_PROPOSAL_START = 'HERMES_FLUX_RESUME_PROPOSAL'
HERMES_FLUX_RESUME_PROPOSAL_END = 'END_HERMES_FLUX_RESUME_PROPOSAL'


def parse_hermes_flux_resume_proposal(current_answer_text):
    """대화 답변에서 FLUX 작업과 예비 검토값만 읽는다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.flux_resume_operations import validate_flux_resume_target
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count(HERMES_FLUX_RESUME_PROPOSAL_START)!=2 or current_answer_text.count(HERMES_FLUX_RESUME_PROPOSAL_END)!=1:
        raise ValueError('FLUX 재개 제안 블록이 하나 필요합니다.')
    current_match_value=re.search(r'(?m)^HERMES_FLUX_RESUME_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_FLUX_RESUME_PROPOSAL[ \t]*$',current_answer_text)
    if current_match_value is None or len(current_match_value.group(1))>500:raise ValueError('FLUX 재개 제안 형식 오류')
    current_proposal_record=parse_management_request_json(current_match_value.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'service','job_id','expected_resume_fingerprint'}:raise ValueError('FLUX 재개 제안 대상 오류')
    validate_flux_resume_target(current_proposal_record['service'],current_proposal_record['job_id'],current_proposal_record['expected_resume_fingerprint'])
    if not isinstance(current_proposal_record['expected_resume_fingerprint'],str):raise ValueError('FLUX 재개 제안 확인값 오류')
    return current_proposal_record


def parse_hermes_video_resume_proposal(current_answer_text):
    """완료된 대화에서 영상 재개 대상과 검토 지문만 추출한다."""
    from tools.management.common.management_gateway import parse_management_request_json
    from tools.management.domains.hermes_agent.video_resume_operations import validate_video_resume_target
    if not isinstance(current_answer_text,str) or len(current_answer_text)>8000 or current_answer_text.count('HERMES_VIDEO_RESUME_PROPOSAL')!=2 or current_answer_text.count('END_HERMES_VIDEO_RESUME_PROPOSAL')!=1:
        raise ValueError('영상 재개 제안 블록이 하나 필요합니다.')
    current_match_value=re.search(r'(?m)^HERMES_VIDEO_RESUME_PROPOSAL[ \t]*\n([\s\S]*?)\nEND_HERMES_VIDEO_RESUME_PROPOSAL[ \t]*$',current_answer_text)
    if current_match_value is None or len(current_match_value.group(1))>500:raise ValueError('영상 재개 제안 형식 오류')
    current_proposal_record=parse_management_request_json(current_match_value.group(1))
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'service','job_id','expected_resume_fingerprint'}:raise ValueError('영상 재개 제안 대상 오류')
    validate_video_resume_target(current_proposal_record['service'],current_proposal_record['job_id'],current_proposal_record['expected_resume_fingerprint'])
    if not isinstance(current_proposal_record['expected_resume_fingerprint'],str):raise ValueError('영상 재개 제안 확인값 오류')
    return current_proposal_record
