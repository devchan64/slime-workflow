"""프론트엔드 에셋 계약을 읽어 독립적인 애니메이션 검수 스냅샷을 만든다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.common.game_render_metrics import load_game_render_metrics
from tools.review.common.map_asset_sources import MAP_CITY_REVIEW_IDENTIFIERS
from tools.review.common.sprite_asset_sources import load_locked_sprite_sources
from tools.review.ui_assets import resolve_review_ui_asset, read_review_shared_styles, read_animation_anchor_template
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import math
import shutil
import threading
import traceback
import yaml
try:
    from .link_review_file import link_or_copy_review_file
except ImportError:
    from link_review_file import link_or_copy_review_file

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIRECTION_NAMES = ('down_left', 'down_right', 'up_left', 'up_right')
REVIEW_IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp'}
REVIEW_HEARTBEAT_SECONDS = 5
DEFAULT_MANAGEMENT_TOOL_PAGE_RECORDS = (
    {'id':'floor-tile-generator','label':'맵 타일 생성기','path':'/floor-tile-generator/','category':'image-generation','uiMode':'gradio','description':'512×512 · 4스텝 · 단일 이미지 생성'},
    {'id':'writer-agent','label':'작가 AI 에이전트','path':'/writer-agent/','anchorEditor':False,'category':'writer-agent','uiMode':'gradio','description':'Gradio · 문서 학습 · 아이디어 작성 · 실행 기록'},
    {'id':'expression-generator','label':'표정 생성기','path':'/expression-generator/','category':'image-generation','uiMode':'gradio','description':'Qwen 2511 · AU 표정 39종 · 참조 1~3장'},
    {'id':'three-reference-generator','label':'Qwen 2511 3참조 생성','path':'/image-generation-2511/','anchorEditor':False,'category':'image-generation','uiMode':'gradio','description':'Gradio · 참조 이미지 3장 · 프롬프트 · 결과 비교'},
    {'id':'image-generator','label':'Qwen 2512 이미지 생성','path':'/image-generation/','anchorEditor':False,'category':'image-generation','uiMode':'gradio','description':'Gradio · 프롬프트 · 실행 상태 · 생성 이력 · 결과 다운로드'},
)


def reject_duplicate_fields(object_field_pairs):
    parsed_object_record = {}
    for current_field_name, current_field_value in object_field_pairs:
        if current_field_name in parsed_object_record:
            raise ValueError(f'중복 필드: {current_field_name}')
        parsed_object_record[current_field_name] = current_field_value
    return parsed_object_record


def reject_nonfinite_number(invalid_number_text):
    raise ValueError(f'유한 숫자가 필요합니다: {invalid_number_text}')


def read_source_metadata(source_metadata_path):
    if source_metadata_path.suffix == '.yaml':
        class UniqueSourceMetadataLoader(yaml.SafeLoader):
            pass
        def construct_source_mapping(current_yaml_loader, current_mapping_node):
            current_yaml_loader.flatten_mapping(current_mapping_node)
            return reject_duplicate_fields(current_yaml_loader.construct_pairs(current_mapping_node, deep=True))
        UniqueSourceMetadataLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_source_mapping)
        return yaml.load(source_metadata_path.read_text(), Loader=UniqueSourceMetadataLoader)
    return json.loads(source_metadata_path.read_text(), object_pairs_hook=reject_duplicate_fields,
                      parse_constant=reject_nonfinite_number)


def require_record_fields(source_record_value, expected_field_names, source_context_text):
    if not isinstance(source_record_value, dict) or set(source_record_value) != set(expected_field_names):
        raise ValueError(f'{source_context_text}: 필수 필드 누락 또는 알 수 없는 필드')


def resolve_frontend_file(frontend_asset_root, requested_file_path):
    resolved_file_path = requested_file_path.resolve()
    if not resolved_file_path.is_relative_to(frontend_asset_root) or not resolved_file_path.is_file():
        raise ValueError(f'에셋 파일 누락 또는 에셋 루트 밖 경로: {requested_file_path}')
    return resolved_file_path


def load_animation_labels(frontend_asset_root):
    label_catalog_path = resolve_frontend_file(frontend_asset_root, frontend_asset_root/'animation-labels.yaml')
    class UniqueLabelLoader(yaml.SafeLoader):
        pass
    def construct_label_mapping(current_yaml_loader, current_mapping_node):
        current_yaml_loader.flatten_mapping(current_mapping_node)
        return reject_duplicate_fields(current_yaml_loader.construct_pairs(current_mapping_node, deep=True))
    UniqueLabelLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_label_mapping)
    label_catalog_data = yaml.load(label_catalog_path.read_text(), Loader=UniqueLabelLoader)
    require_record_fields(label_catalog_data, ('schemaVersion', 'animations'), '한국어 라벨 목록')
    if type(label_catalog_data['schemaVersion']) is not int or label_catalog_data['schemaVersion'] != 1 or not isinstance(label_catalog_data['animations'], list) or not label_catalog_data['animations']:
        raise ValueError('라벨 schemaVersion 1과 비어 있지 않은 animations 목록이 필요합니다.')
    animation_label_lookup = {}
    for animation_label_record in label_catalog_data['animations']:
        require_record_fields(animation_label_record, ('animationId', 'displayNameKo'), '애니메이션 라벨')
        animation_identifier_text = animation_label_record['animationId']
        display_label_text = animation_label_record['displayNameKo']
        if not isinstance(animation_identifier_text, str) or not animation_identifier_text.strip() or animation_identifier_text.strip() != animation_identifier_text:
            raise ValueError('라벨 animationId는 공백 없는 식별자 문자열이어야 합니다.')
        if animation_identifier_text in animation_label_lookup:
            raise ValueError(f'중복 라벨 ID: {animation_identifier_text}')
        if not isinstance(display_label_text, str) or not display_label_text.strip() or display_label_text != display_label_text.strip() or not any('가' <= current_character_value <= '힣' for current_character_value in display_label_text) or any(ord(current_character_value) < 32 for current_character_value in display_label_text):
            raise ValueError(f'한글이 포함된 한 줄 displayNameKo가 필요합니다: {animation_identifier_text}')
        animation_label_lookup[animation_identifier_text] = display_label_text
    return animation_label_lookup


def load_animation_review(frontend_asset_root, animation_metadata_path):
    # 이미지 크기는 파일 헤더로 검증하며 원본 에셋은 수정하지 않는다.
    from PIL import Image
    animation_metadata_path = resolve_frontend_file(frontend_asset_root, animation_metadata_path)
    animation_source_data = read_source_metadata(animation_metadata_path)
    declared_reference_body_height = animation_source_data.get('referenceBodyHeight')
    declared_game_body_height = animation_source_data.get('gameBodyHeight')
    packed_sheet_manifest_data = None
    if 'sheets' in animation_source_data:
        require_record_fields(animation_source_data, ('animationId', 'version', 'referenceBodyHeight', 'gameBodyHeight', 'sheets', 'frames', 'clips', 'poseReviewStatus'), str(animation_metadata_path))
        if not isinstance(animation_source_data['sheets'], list) or not animation_source_data['sheets']:
            raise ValueError(f'{animation_metadata_path}: sheets 목록이 필요합니다.')
        packed_direction_records = []
        packed_direction_images = {}
        packed_sheet_size = None
        for packed_sheet_record in animation_source_data['sheets']:
            require_record_fields(packed_sheet_record, ('image', 'width', 'height', 'sha256', 'directions', 'managementId'), '패킹 시트')
            if not isinstance(packed_sheet_record['image'], str) or Path(packed_sheet_record['image']).name != packed_sheet_record['image'] or not isinstance(packed_sheet_record['sha256'], str) or len(packed_sheet_record['sha256']) != 64 or not isinstance(packed_sheet_record['directions'], list):
                raise ValueError('패킹 시트 이미지·해시·방향 형식이 잘못되었습니다.')
            current_sheet_size = (packed_sheet_record['width'], packed_sheet_record['height'])
            if any(type(current_dimension_value) is not int or current_dimension_value < 1 for current_dimension_value in current_sheet_size):
                raise ValueError('패킹 시트 크기는 양의 정수여야 합니다.')
            if packed_sheet_size is None:
                packed_sheet_size = current_sheet_size
            elif packed_sheet_size != current_sheet_size:
                raise ValueError('현재 검수기는 같은 크기의 패킹 시트만 지원합니다.')
            for current_direction_name in packed_sheet_record['directions']:
                if current_direction_name not in REVIEW_DIRECTION_NAMES or current_direction_name in packed_direction_images:
                    raise ValueError('패킹 시트 방향이 잘못되었거나 중복되었습니다.')
                packed_direction_images[current_direction_name] = packed_sheet_record['image']
                packed_direction_records.append({'direction': current_direction_name, 'image': packed_sheet_record['image'], 'sha256': packed_sheet_record['sha256']})
        if set(packed_direction_images) != set(REVIEW_DIRECTION_NAMES):
            raise ValueError('패킹 시트는 네 방향을 모두 포함해야 합니다.')
        normalized_frame_records = []
        for packed_frame_record in animation_source_data['frames']:
            required_packed_frame_fields = {'frameId', 'anchor', 'anchorStatus', 'sha256', 'regenerated', 'texture', 'rect', 'poseReviewStatus'}
            allowed_packed_frame_fields = required_packed_frame_fields | {'managementId'}
            if not isinstance(packed_frame_record, dict) or not required_packed_frame_fields.issubset(packed_frame_record) or set(packed_frame_record) - allowed_packed_frame_fields:
                raise ValueError('패킹 프레임: 필수 필드 누락 또는 알 수 없는 필드')
            packed_direction_name = packed_frame_record['frameId'].rsplit('.', 1)[0] if isinstance(packed_frame_record['frameId'], str) else ''
            if packed_direction_name not in packed_direction_images or packed_frame_record['texture'] != packed_direction_images[packed_direction_name]:
                raise ValueError('패킹 프레임 texture와 방향 시트가 일치하지 않습니다.')
            normalized_frame_records.append({current_field_name: packed_frame_record[current_field_name] for current_field_name in ('frameId', 'rect', 'anchor')})
        animation_source_data = {'animationId': animation_source_data['animationId'], 'version': animation_source_data['version'], 'sheet': {'width': packed_sheet_size[0], 'height': packed_sheet_size[1]}, 'frames': normalized_frame_records, 'clips': animation_source_data['clips']}
        packed_sheet_manifest_data = {'sheets': packed_direction_records}
    require_record_fields(animation_source_data, ('animationId', 'version', 'sheet', 'frames', 'clips'), str(animation_metadata_path))
    for identity_field_name in ('animationId', 'version'):
        if not isinstance(animation_source_data[identity_field_name], str) or not animation_source_data[identity_field_name].strip():
            raise ValueError(f'{animation_metadata_path}: {identity_field_name} 문자열이 필요합니다.')
    require_record_fields(animation_source_data['sheet'], ('width', 'height'), '시트 크기')
    if any(type(dimension_pixel_value) is not int or dimension_pixel_value < 1 for dimension_pixel_value in animation_source_data['sheet'].values()):
        raise ValueError('시트 크기는 양의 정수여야 합니다.')
    source_manifest_candidates = [animation_metadata_path.with_name(current_source_filename) for current_source_filename in ('source.yaml', 'source.json')]
    existing_manifest_paths = [current_manifest_path for current_manifest_path in source_manifest_candidates if current_manifest_path.exists()]
    if len(existing_manifest_paths) > 1:
        raise ValueError(f'{animation_metadata_path.parent}: source.yaml과 source.json 원본이 중복되었습니다.')
    source_manifest_path = existing_manifest_paths[0] if existing_manifest_paths else source_manifest_candidates[0]
    source_manifest_data = packed_sheet_manifest_data if packed_sheet_manifest_data is not None else (read_source_metadata(resolve_frontend_file(frontend_asset_root, source_manifest_path)) if source_manifest_path.exists() else {})
    if not isinstance(source_manifest_data, dict):
        raise ValueError(f'{source_manifest_path}: 객체가 필요합니다.')
    source_reference_body_height = source_manifest_data.get('referenceBodyHeight', declared_reference_body_height)
    source_game_body_height = source_manifest_data.get('gameBodyHeight', declared_game_body_height)
    selected_clip_directions = {current_clip_record['direction'] for current_clip_record in animation_source_data['clips']}
    if selected_clip_directions not in ({'down_left'}, set(REVIEW_DIRECTION_NAMES)):
        raise ValueError('정면왼쪽 단일 방향 또는 네 방향 클립이 필요합니다.')
    direction_sheet_paths = {}
    expected_sheet_hashes = {}
    if 'sheets' in source_manifest_data:
        if not isinstance(source_manifest_data['sheets'], list) or len(source_manifest_data['sheets']) != 4:
            raise ValueError('출처 메타데이터의 sheets는 네 방향 목록이어야 합니다.')
        for source_sheet_record in source_manifest_data['sheets']:
            require_record_fields(source_sheet_record, ('direction', 'image', 'sha256'), '방향별 시트')
            current_direction_name = source_sheet_record['direction']
            source_image_name = source_sheet_record['image']
            if current_direction_name not in REVIEW_DIRECTION_NAMES or current_direction_name in direction_sheet_paths:
                raise ValueError('시트 방향이 잘못되었거나 중복되었습니다.')
            if not isinstance(source_image_name, str) or Path(source_image_name).name != source_image_name:
                raise ValueError('시트 경로는 같은 폴더의 파일명이어야 합니다.')
            direction_sheet_paths[current_direction_name] = resolve_frontend_file(frontend_asset_root, animation_metadata_path.with_name(source_image_name))
            expected_sheet_hashes[current_direction_name] = source_sheet_record['sha256']
    else:
        # 단일 시트는 <이름>.animation.json ↔ <이름>.png 명명 계약을 사용한다.
        single_sheet_path = resolve_frontend_file(frontend_asset_root, animation_metadata_path.with_name(animation_metadata_path.name.removesuffix('.animation.json')+'.png'))
        direction_sheet_paths = {current_direction_name: single_sheet_path for current_direction_name in selected_clip_directions}
        if 'sha256' in source_manifest_data:
            expected_sheet_hashes = {current_direction_name: source_manifest_data['sha256'] for current_direction_name in selected_clip_directions}
    source_sheet_records = []
    for current_direction_name, current_sheet_path in direction_sheet_paths.items():
        if current_sheet_path.suffix.lower() not in REVIEW_IMAGE_SUFFIXES:
            raise ValueError(f'지원하지 않는 이미지 형식: {current_sheet_path}')
        with Image.open(current_sheet_path) as current_sheet_image:
            if current_sheet_image.size != (animation_source_data['sheet']['width'], animation_source_data['sheet']['height']):
                raise ValueError(f'시트 크기 불일치: {current_sheet_path}')
        actual_sheet_hash = hashlib.sha256(current_sheet_path.read_bytes()).hexdigest()
        if current_direction_name in expected_sheet_hashes and expected_sheet_hashes[current_direction_name] != actual_sheet_hash:
            raise ValueError(f'시트 해시 불일치: {current_sheet_path}')
        source_sheet_records.append({'direction': current_direction_name, 'image': current_sheet_path.name, 'sha256': actual_sheet_hash})
    animation_frame_records = animation_source_data['frames']
    animation_clip_records = animation_source_data['clips']
    if not isinstance(animation_frame_records, list) or not animation_frame_records or not isinstance(animation_clip_records, list) or not animation_clip_records:
        raise ValueError('프레임 목록과 방향별 클립이 필요합니다.')
    source_frame_lookup = {}
    for current_frame_record in animation_frame_records:
        require_record_fields(current_frame_record, ('frameId', 'rect', 'anchor'), '프레임')
        current_frame_identifier = current_frame_record['frameId']
        if not isinstance(current_frame_identifier, str) or current_frame_identifier in source_frame_lookup:
            raise ValueError('잘못되었거나 중복된 프레임 ID')
        require_record_fields(current_frame_record['rect'], ('x', 'y', 'width', 'height'), '셀 영역')
        current_frame_bounds = current_frame_record['rect']
        if any(type(current_pixel_value) is not int or current_pixel_value < (1 if current_field_name in ('width', 'height') else 0) for current_field_name, current_pixel_value in current_frame_bounds.items()):
            raise ValueError('셀 영역은 유효한 정수여야 합니다.')
        if any(current_frame_bounds[current_axis_name]+current_frame_bounds[current_size_name] > animation_source_data['sheet'][current_size_name] for current_axis_name, current_size_name in (('x', 'width'), ('y', 'height'))):
            raise ValueError('셀이 시트 경계를 벗어납니다.')
        require_record_fields(current_frame_record['anchor'], ('x', 'y'), '앵커')
        if any(type(current_coordinate_value) not in (int, float) or not math.isfinite(current_coordinate_value) or not 0 <= current_coordinate_value < current_frame_bounds['width' if current_axis_name == 'x' else 'height'] for current_axis_name, current_coordinate_value in current_frame_record['anchor'].items()):
            raise ValueError('앵커는 셀 내부의 유한 숫자여야 합니다.')
        source_frame_lookup[current_frame_identifier] = current_frame_record
    review_frame_records = []
    seen_direction_actions = set()
    seen_clip_identifiers = set()
    seen_frame_identifiers = set()
    frame_duration_values = set()
    for current_clip_record in animation_clip_records:
        require_record_fields(current_clip_record, ('clipId', 'action', 'direction', 'frames', 'loop', 'nextClipId'), '클립')
        current_direction_name = current_clip_record['direction']
        if current_direction_name not in REVIEW_DIRECTION_NAMES or (current_direction_name, current_clip_record['action']) in seen_direction_actions:
            raise ValueError('클립 방향이 잘못되었거나 중복되었습니다.')
        if any(not isinstance(current_clip_record[current_field_name], str) or not current_clip_record[current_field_name] for current_field_name in ('clipId', 'action')) or type(current_clip_record['loop']) is not bool or current_clip_record['nextClipId'] is not None:
            raise ValueError('현재 검수기는 독립적인 반복 또는 종료 고정 클립만 지원합니다.')
        if not isinstance(current_clip_record['frames'], list) or not current_clip_record['frames']:
            raise ValueError('클립 프레임 목록이 필요합니다.')
        if current_clip_record['clipId'] in seen_clip_identifiers:
            raise ValueError('중복 클립 ID입니다.')
        seen_clip_identifiers.add(current_clip_record['clipId'])
        seen_direction_actions.add((current_direction_name, current_clip_record['action']))
        for clip_frame_record in current_clip_record['frames']:
            require_record_fields(clip_frame_record, ('frameId', 'durationMs'), '클립 프레임')
            current_frame_identifier = clip_frame_record['frameId']
            if not current_frame_identifier.startswith(current_direction_name+'.') or current_frame_identifier not in source_frame_lookup:
                raise ValueError('방향별 순차 프레임 참조가 잘못되었습니다.')
            if type(clip_frame_record['durationMs']) is not int or clip_frame_record['durationMs'] < 1:
                raise ValueError('프레임 시간은 양의 정수여야 합니다.')
            frame_duration_values.add(clip_frame_record['durationMs'])
            if current_frame_identifier in seen_frame_identifiers:
                continue
            seen_frame_identifiers.add(current_frame_identifier)
            current_frame_record = source_frame_lookup[current_frame_identifier]
            review_frame_records.append({**current_frame_record, 'direction': current_direction_name, 'image': direction_sheet_paths[current_direction_name].name, 'contacts': [dict(current_frame_record['anchor']), dict(current_frame_record['anchor'])], 'endpoints': []})
    if len(frame_duration_values) != 1 or seen_frame_identifiers != set(source_frame_lookup):
        raise ValueError('동일한 프레임 시간 및 전체 프레임 참조가 필요합니다.')
    animation_identifier_text = animation_source_data['animationId']
    if source_game_body_height is not None and (type(source_game_body_height) not in (int, float) or not math.isfinite(source_game_body_height) or source_game_body_height <= 0):
        raise ValueError(f'{animation_metadata_path}: gameBodyHeight는 양의 유한 숫자이어야 합니다.')
    if animation_identifier_text == 'character.default.white-shirt.rest':
        if type(source_reference_body_height) not in (int, float) or not math.isfinite(source_reference_body_height) or source_reference_body_height <= 0:
            raise ValueError('휴식 에셋의 referenceBodyHeight가 필요합니다.')
        runtime_scale_metadata = {'actorKind': 'human-rest', 'baseHeight': source_game_body_height or 80, 'sourceHeight': source_reference_body_height, 'defaultSizeClass': 'medium'}
    elif animation_identifier_text.startswith('monster.'):
        default_size_class = {'monster.slime.idle': 'small', 'monster.giant.idle': 'large'}.get(animation_identifier_text, 'medium')
        runtime_scale_metadata = {'actorKind': 'monster', 'baseHeight': 60, 'sourceHeightMultiplier': 0.75, 'defaultSizeClass': default_size_class}
    else:
        if type(source_reference_body_height) not in (int, float) or not math.isfinite(source_reference_body_height) or source_reference_body_height <= 0:
            raise ValueError(f'{animation_metadata_path}: 게임 출력 비율에 필요한 referenceBodyHeight가 없습니다.')
        runtime_scale_metadata = {'actorKind': 'human', 'baseHeight': source_game_body_height or 60, 'sourceHeight': source_reference_body_height, 'defaultSizeClass': 'medium'}
    review_source_metadata = {'coordinateMode': 'anchor', 'registeredSource': True, 'animationId': animation_identifier_text, 'animationVersion': animation_source_data['version'], 'artifactType': 'character-animation-anchor-review', 'exportFilename': animation_metadata_path.name.removesuffix('.animation.json')+'-anchor-review.json', 'clips': animation_clip_records, 'frameDurationMs': next(iter(frame_duration_values)), 'sheets': source_sheet_records, 'runtimeScale': runtime_scale_metadata, 'description': '프론트엔드 등록 메타데이터의 앵커 검수. 원본 소수 좌표를 유지하며 클릭 지정은 정수 픽셀을 사용합니다. 저장 파일은 별도 검수 산출물입니다.'}
    return review_frame_records, review_source_metadata, set(direction_sheet_paths.values())


def clear_generated_review_files(output_review_directory):
    """재생성 가능한 화면만 지우고 사용자의 이미지 생성 이력은 보존한다."""
    preserved_history_names = {'qwen-2511', 'qwen-2512', 'expression', 'floor-tile', 'tile-map'}
    output_review_directory.mkdir(parents=True, exist_ok=True)
    for current_review_path in output_review_directory.iterdir():
        if current_review_path.name in preserved_history_names:
            continue
        if current_review_path.is_dir() and not current_review_path.is_symlink():
            shutil.rmtree(current_review_path)
        else:
            current_review_path.unlink()


def build_frontend_review(frontend_repository_path, ui_bundle_directory=None):
    frontend_repository_path = frontend_repository_path.resolve()
    frontend_asset_root = frontend_repository_path.parent/'slime-assets/assets/ui'
    if not (frontend_repository_path/'package.json').is_file() or not frontend_asset_root.is_dir():
        raise ValueError('package.json과 인접 slime-assets/assets/ui가 있는 프론트엔드 저장소를 지정하세요.')
    registered_sprite_root, locked_sprite_sources = load_locked_sprite_sources(frontend_repository_path)
    animation_metadata_paths = [frontend_repository_path/current_relative_path for current_relative_path in sorted(locked_sprite_sources) if current_relative_path.endswith('.animation.json')]
    if not animation_metadata_paths:
        raise ValueError(f'애니메이션 메타데이터가 없습니다: {frontend_asset_root}')
    output_review_directory = WORKFLOW_REPO_ROOT/'.tmp'/'manager-current'
    clear_generated_review_files(output_review_directory)
    execution_log_path = output_review_directory/'frontend-review.log'
    trace_write_lock = threading.Lock()
    heartbeat_stop_event = threading.Event()
    completed_asset_count = [0]
    def emit_review_trace(trace_stage_name, trace_message_text):
        trace_output_line = f'{datetime.now().isoformat()}/frontend-review/{trace_stage_name} {trace_message_text}'
        with trace_write_lock:
            print(trace_output_line, flush=True)
            with execution_log_path.open('a') as execution_log_stream:
                execution_log_stream.write(trace_output_line+'\n')
    def emit_review_heartbeat():
        while not heartbeat_stop_event.wait(REVIEW_HEARTBEAT_SECONDS):
            emit_review_trace('heartbeat', f'assets={completed_asset_count[0]}/{len(animation_metadata_paths)} log_bytes={execution_log_path.stat().st_size}')
    emit_review_trace('start', str(frontend_repository_path))
    heartbeat_worker_thread = threading.Thread(target=emit_review_heartbeat, daemon=True)
    heartbeat_worker_thread.start()
    try:
        animation_label_lookup = load_animation_labels(frontend_asset_root)
        shared_review_styles = read_review_shared_styles()
        anchor_template_text = read_animation_anchor_template().replace('</style>', '</style><style>'+shared_review_styles+'</style>', 1)
        game_render_metrics = load_game_render_metrics(frontend_repository_path)
        manager_page_records = []
        discovered_source_records = []
        sprite_asset_records = []
        for animation_sequence_index, animation_metadata_path in enumerate(animation_metadata_paths):
            relative_metadata_path = animation_metadata_path.relative_to(frontend_repository_path).as_posix()
            registered_metadata_path, metadata_provenance_record = locked_sprite_sources[relative_metadata_path]
            review_frame_records, review_source_metadata, source_image_paths = load_animation_review(registered_sprite_root, registered_metadata_path)
            related_source_records = {current_source_path: current_provenance_record for current_source_path, current_provenance_record in locked_sprite_sources.values()}
            if any(current_source_path not in related_source_records for current_source_path in source_image_paths):
                raise ValueError('검수 시트가 스프라이트 잠금 목록에 없습니다.')
            review_source_metadata['provenance'] = {
                'animation': metadata_provenance_record,
                'files': [current_provenance_record for current_source_path, current_provenance_record in locked_sprite_sources.values() if current_source_path.parent == registered_metadata_path.parent],
            }
            review_source_metadata['gameRenderMetrics'] = game_render_metrics
            runtime_scale_metadata = review_source_metadata['runtimeScale']
            runtime_scale_metadata['baseHeight'] = game_render_metrics['characterHeight'] * (game_render_metrics['restHeightRatio'] if runtime_scale_metadata['actorKind'] == 'human-rest' else 1)
            animation_identifier_text = review_source_metadata['animationId']
            if animation_identifier_text not in animation_label_lookup:
                raise ValueError(f'한국어 라벨 누락: {animation_identifier_text} / slime-assets/assets/ui/animation-labels.yaml')
            review_source_metadata['displayNameKo'] = animation_label_lookup[animation_identifier_text]
            page_identifier_text = f'animation-{animation_sequence_index+1}'
            destination_asset_directory = output_review_directory/page_identifier_text
            destination_asset_directory.mkdir()
            for source_image_path in source_image_paths:
                link_or_copy_review_file(source_image_path, destination_asset_directory/source_image_path.name)
            rendered_page_text = anchor_template_text.replace('__FRAME_RECORDS__', json.dumps(review_frame_records, ensure_ascii=False).replace('<', '\\u003c')).replace('__SOURCE_METADATA__', json.dumps(review_source_metadata, ensure_ascii=False).replace('<', '\\u003c'))
            (destination_asset_directory/'anchors.html').write_text(rendered_page_text)
            sprite_asset_records.append({'id':'asset:'+animation_identifier_text,'label':review_source_metadata['displayNameKo']+' v'+review_source_metadata['animationVersion'],'fps':1000/review_source_metadata['frameDurationMs'],'frames':[{**frame_record_value,'url':'/'+page_identifier_text+'/'+frame_record_value['image']} for frame_record_value in review_frame_records],'source':review_source_metadata})
            relative_metadata_path = animation_metadata_path.relative_to(frontend_repository_path).as_posix()
            manager_page_records.append({'id': page_identifier_text, 'label': review_source_metadata['displayNameKo']+' · v'+review_source_metadata['animationVersion'], 'path': page_identifier_text+'/anchors.html', 'anchorEditor': True, 'category': 'animation', 'uiMode':'gradio-static', 'description':'Gradio · '+animation_identifier_text+' · '+relative_metadata_path})
            discovered_source_records.append({'metadata': relative_metadata_path, 'displayNameKo': review_source_metadata['displayNameKo'], 'sha256': metadata_provenance_record['sha256'], 'sheets': review_source_metadata['sheets'], 'provenance': review_source_metadata['provenance']})
            completed_asset_count[0] += 1
            emit_review_trace('asset', relative_metadata_path)
        # 기본 캐릭터 동작은 하나의 검수 화면에서 선택하며 저장 출처는 각각 유지한다.
        character_action_records = [current_asset_record for current_asset_record in sprite_asset_records if current_asset_record['source']['animationId'].startswith('character.default.')]
        if character_action_records:
            character_page_identifiers = [current_asset_record['frames'][0]['url'].split('/')[1] for current_asset_record in character_action_records]
            for current_action_record in character_action_records:
                current_page_identifier = current_action_record['frames'][0]['url'].split('/')[1]
                current_source_metadata = {**current_action_record['source'], 'actionReviews': character_action_records, 'defaultActionId': current_action_record['id']}
                current_rendered_page = anchor_template_text.replace('__FRAME_RECORDS__', json.dumps(current_action_record['frames'], ensure_ascii=False).replace('<', '\\u003c')).replace('__SOURCE_METADATA__', json.dumps(current_source_metadata, ensure_ascii=False).replace('<', '\\u003c'))
                (output_review_directory/current_page_identifier/'anchors.html').write_text(current_rendered_page)
            manager_page_records = [current_page_record for current_page_record in manager_page_records if current_page_record['id'] not in character_page_identifiers[1:]]
            next(current_page_record for current_page_record in manager_page_records if current_page_record['id']==character_page_identifiers[0]).update(label='기본 캐릭터 · 애니메이션 통합 검수', description='Gradio · 대기·휴식·걷기 · 방향 선택 · 동작별 좌표 저장·이력')
        (output_review_directory/'sprite-assets.json').write_text(json.dumps({'assets':sprite_asset_records},ensure_ascii=False))
        if __package__:
            from .build_map_review import build_map_review
        else:
            from build_map_review import build_map_review
        isloon_review_directory = build_map_review(output_root=output_review_directory/'isloon-map-review')
        map_review_relative_path=isloon_review_directory.relative_to(output_review_directory).as_posix()+'/map-review.html'
        map_index_record=json.loads((isloon_review_directory/'block-map-index.json').read_text(encoding='utf-8'))
        for current_map_record in map_index_record:
            current_map_identifier=current_map_record['id']
            current_review_category = 'town-map-review' if current_map_identifier in MAP_CITY_REVIEW_IDENTIFIERS else 'field-map-review'
            current_review_label = '마을맵 검수' if current_map_identifier in MAP_CITY_REVIEW_IDENTIFIERS else '필드맵 검수'
            manager_page_records.append({'id': f'map-review-{current_map_identifier}', 'label': current_map_record['name']+' · '+current_review_label, 'path': map_review_relative_path+f'?map={current_map_identifier}&townPage=1', 'anchorEditor': False, 'category': current_review_category, 'uiMode':'gradio', 'frameIdentifier':'map-review', 'frameQuery':f'map={current_map_identifier}&townPage=1', 'description': 'Gradio · '+current_map_record['name']+' 전용 검수 · 타일 연결 · 건물 충돌 검수'})
        emit_review_trace('tile-map-review', str(isloon_review_directory.relative_to(WORKFLOW_REPO_ROOT)))
        if __package__:
            from .build_animation_tools import build_animation_tools
        else:
            from build_animation_tools import build_animation_tools
        manager_page_records.extend(build_animation_tools(output_review_directory))
        if __package__:
            from .collect_tile_reviews import collect_tile_reviews
        else:
            from collect_tile_reviews import collect_tile_reviews
        manager_page_records.extend(collect_tile_reviews(WORKFLOW_REPO_ROOT, output_review_directory, emit_review_trace))
        if ui_bundle_directory is not None:
            if __package__:
                from .import_ui_bundle import import_ui_bundle
            else:
                from import_ui_bundle import import_ui_bundle
            manager_page_records.extend(import_ui_bundle(ui_bundle_directory, output_review_directory, emit_review_trace))
        existing_page_identifier_values={current_page_record['id'] for current_page_record in manager_page_records}
        manager_page_records.extend(current_page_record for current_page_record in DEFAULT_MANAGEMENT_TOOL_PAGE_RECORDS if current_page_record['id'] not in existing_page_identifier_values)
        manager_template_text = resolve_review_ui_asset('frame-manager.html').read_text().replace('</style>', '</style><style>'+shared_review_styles+'</style>', 1)
        (output_review_directory/'preview.html').write_text(manager_template_text.replace('__MANAGER_PAGES__', json.dumps(manager_page_records, ensure_ascii=False).replace('<', '\\u003c')))
        (output_review_directory/'manager-source.json').write_text(json.dumps({'frontendRepository': str(frontend_repository_path), 'labelCatalog': {'path': 'slime-assets/assets/ui/animation-labels.yaml', 'sha256': hashlib.sha256((frontend_asset_root/'animation-labels.yaml').read_bytes()).hexdigest()}, 'assets': discovered_source_records, 'pages': manager_page_records}, ensure_ascii=False, indent=2))
        emit_review_trace('complete', str(output_review_directory/'preview.html'))
        return output_review_directory
    except Exception:
        emit_review_trace('failure', traceback.format_exc())
        print('\n'.join(execution_log_path.read_text().splitlines()[-20:]), flush=True)
        raise
    finally:
        heartbeat_stop_event.set()
        heartbeat_worker_thread.join(timeout=1)
