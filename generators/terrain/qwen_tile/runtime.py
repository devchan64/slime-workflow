#!/usr/bin/env python3
"""Qwen-Image-Edit-2511로 바닥·벽 타일 후보와 높이 미리보기를 만든다."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import threading
import time
from pathlib import Path

import yaml

from .map_preview import read_map_preview_snapshot

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXED_MODEL_IDENTIFIER = 'Qwen/Qwen-Image-Edit-2511'
FIXED_MODEL_REVISION = '6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9'
FIXED_MODEL_DIRECTORY = WORKFLOW_REPOSITORY_ROOT / '.model/qwen-image-edit-2511' / FIXED_MODEL_REVISION
FIXED_INFERENCE_STEPS = 10
FIXED_GENERATOR_SEED = 21409
FIXED_TRUE_CFG_SCALE = 4.0
FIXED_GUIDANCE_SCALE = 1.0
ALLOWED_TILE_ROLES = frozenset({'ground', 'wall-front', 'wall-side'})
ALLOWED_TILEABILITY = frozenset({'repeat-x', 'repeat-y', 'repeat-both', 'none'})
ASSET_IDENTIFIER_PATTERN = re.compile(r'^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$')
PIPELINE_EXECUTION_LOCK = threading.Lock()


def read_tile_set_ticket(ticket_file_path: Path) -> dict:
    """YAML 타일 세트 티켓을 중복 키 없이 읽는다."""
    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_unique_mapping(loader_instance, node_value, deep=False):
        mapping_values = {}
        for key_node, value_node in node_value.value:
            key_value = loader_instance.construct_object(key_node, deep=deep)
            if key_value in mapping_values:
                raise ValueError(f'중복 티켓 키: {key_value}')
            mapping_values[key_value] = loader_instance.construct_object(value_node, deep=deep)
        return mapping_values

    UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)
    ticket_values = yaml.load(ticket_file_path.read_text(encoding='utf-8'), Loader=UniqueKeyLoader)
    if not isinstance(ticket_values, dict):
        raise ValueError('타일 티켓 최상위 값은 객체여야 합니다.')
    return ticket_values


def validate_tile_set_ticket(ticket_values: dict) -> dict:
    """모델 선택을 포함하지 않는 엄격한 타일 세트 티켓을 검증한다."""
    required_ticket_keys = {'asset_id', 'tile_size', 'generation_size', 'tileability', 'tile_variants', 'style_reference_id', 'style_reference_sha256', 'prompt', 'height_steps', 'acceptance'}
    optional_ticket_keys = {'shape_reference_id', 'shape_reference_sha256', 'apply_shape_alpha', 'material_reference_id', 'material_reference_sha256'}
    unknown_ticket_keys = set(ticket_values) - required_ticket_keys - optional_ticket_keys
    missing_ticket_keys = required_ticket_keys - set(ticket_values)
    if unknown_ticket_keys or missing_ticket_keys:
        raise ValueError(f'티켓 필드 불일치: unknown={sorted(unknown_ticket_keys)} missing={sorted(missing_ticket_keys)}')
    if not isinstance(ticket_values['asset_id'], str) or not ASSET_IDENTIFIER_PATTERN.fullmatch(ticket_values['asset_id']):
        raise ValueError('asset_id 형식이 올바르지 않습니다.')
    for dimension_key in ('tile_size', 'generation_size'):
        dimension_values = ticket_values[dimension_key]
        if not isinstance(dimension_values, list) or len(dimension_values) != 2 or any(type(value) is not int for value in dimension_values):
            raise ValueError(f'{dimension_key}는 정수 2개 배열이어야 합니다.')
        minimum_value, maximum_value = (16, 512) if dimension_key == 'tile_size' else (256, 1024)
        if any(value < minimum_value or value > maximum_value or value % 16 for value in dimension_values):
            raise ValueError(f'{dimension_key}는 {minimum_value}~{maximum_value} 범위의 16 배수여야 합니다.')
    if ticket_values['tileability'] not in ALLOWED_TILEABILITY:
        raise ValueError('tileability 값이 올바르지 않습니다.')
    if not isinstance(ticket_values['tile_variants'], list) or not ticket_values['tile_variants']:
        raise ValueError('tile_variants는 비어 있지 않은 배열이어야 합니다.')
    if len(set(ticket_values['tile_variants'])) != len(ticket_values['tile_variants']) or not set(ticket_values['tile_variants']) <= ALLOWED_TILE_ROLES:
        raise ValueError('tile_variants는 허용된 중복 없는 역할이어야 합니다.')
    if not isinstance(ticket_values['style_reference_id'], str) or not ASSET_IDENTIFIER_PATTERN.fullmatch(ticket_values['style_reference_id']):
        raise ValueError('style_reference_id 형식이 올바르지 않습니다.')
    if not isinstance(ticket_values['style_reference_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', ticket_values['style_reference_sha256']):
        raise ValueError('style_reference_sha256은 소문자 SHA-256이어야 합니다.')
    if not isinstance(ticket_values['prompt'], str) or not ticket_values['prompt'].strip() or len(ticket_values['prompt']) > 600:
        raise ValueError('prompt는 1~600자의 문자열이어야 합니다.')
    if type(ticket_values['height_steps']) is not int or not 1 <= ticket_values['height_steps'] <= 8:
        raise ValueError('height_steps는 1~8 정수여야 합니다.')
    if not isinstance(ticket_values['acceptance'], dict) or set(ticket_values['acceptance']) != {'seam_check', 'transparent_background'}:
        raise ValueError('acceptance는 seam_check와 transparent_background만 가져야 합니다.')
    if any(type(ticket_values['acceptance'][key]) is not bool for key in ticket_values['acceptance']):
        raise ValueError('acceptance 값은 bool이어야 합니다.')
    if ticket_values['acceptance']['transparent_background']:
        raise ValueError('현재 타일 생성기는 투명 배경 후보를 지원하지 않습니다.')
    defined_shape_keys = {'shape_reference_id', 'shape_reference_sha256', 'apply_shape_alpha'} & set(ticket_values)
    if defined_shape_keys and defined_shape_keys != {'shape_reference_id', 'shape_reference_sha256', 'apply_shape_alpha'}:
        raise ValueError('형태 참조는 ID·SHA-256·알파 적용 여부를 함께 지정해야 합니다.')
    if defined_shape_keys:
        if not isinstance(ticket_values['shape_reference_id'], str) or not ASSET_IDENTIFIER_PATTERN.fullmatch(ticket_values['shape_reference_id']):
            raise ValueError('shape_reference_id 형식이 올바르지 않습니다.')
        if not isinstance(ticket_values['shape_reference_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', ticket_values['shape_reference_sha256']):
            raise ValueError('shape_reference_sha256은 소문자 SHA-256이어야 합니다.')
        if type(ticket_values['apply_shape_alpha']) is not bool:
            raise ValueError('apply_shape_alpha는 bool이어야 합니다.')
    defined_material_keys = {'material_reference_id', 'material_reference_sha256'} & set(ticket_values)
    if defined_material_keys and defined_material_keys != {'material_reference_id', 'material_reference_sha256'}:
        raise ValueError('재질 참조는 ID와 SHA-256을 함께 지정해야 합니다.')
    if defined_material_keys:
        if not isinstance(ticket_values['material_reference_id'], str) or not ASSET_IDENTIFIER_PATTERN.fullmatch(ticket_values['material_reference_id']):
            raise ValueError('material_reference_id 형식이 올바르지 않습니다.')
        if not isinstance(ticket_values['material_reference_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', ticket_values['material_reference_sha256']):
            raise ValueError('material_reference_sha256은 소문자 SHA-256이어야 합니다.')
    return ticket_values


def validate_style_reference(style_reference_path: Path, expected_sha256: str, generation_size: list[int]):
    """스타일 참조의 해시·형식·투명도를 검증해 생성 크기로 준비한다."""
    from PIL import Image
    resolved_reference_path = style_reference_path.resolve()
    actual_sha256 = hashlib.sha256(resolved_reference_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError('스타일 참조 SHA-256이 티켓과 다릅니다.')
    with Image.open(resolved_reference_path) as source_image:
        if source_image.format not in ('PNG', 'WEBP') or source_image.mode not in ('RGB', 'RGBA'):
            raise ValueError('스타일 참조는 RGB/RGBA PNG 또는 WEBP여야 합니다.')
        if source_image.mode == 'RGBA' and source_image.getextrema()[3] != (255, 255):
            raise ValueError('스타일 참조 투명도는 완전 불투명이어야 합니다.')
        return source_image.convert('RGB').resize(tuple(generation_size), Image.LANCZOS), actual_sha256


def validate_material_reference(material_reference_path: Path, expected_sha256: str, generation_size: list[int]):
    """벽 재질용 불투명 참조의 해시와 형식을 검증한다."""
    return validate_style_reference(material_reference_path, expected_sha256, generation_size)


def validate_shape_reference(shape_reference_path: Path, expected_sha256: str, generation_size: list[int], tile_size: list[int]):
    """투명 벽 형태 참조를 편집 입력과 최종 알파 마스크로 준비한다."""
    from PIL import Image
    resolved_reference_path = shape_reference_path.resolve()
    actual_sha256 = hashlib.sha256(resolved_reference_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError('형태 참조 SHA-256이 티켓과 다릅니다.')
    with Image.open(resolved_reference_path) as source_image:
        if source_image.mode != 'RGBA' or source_image.getextrema()[3] == (255, 255):
            raise ValueError('형태 참조는 투명 영역이 있는 RGBA 이미지여야 합니다.')
        shape_canvas = Image.new('RGBA', source_image.size, (240, 240, 240, 255))
        shape_canvas.alpha_composite(source_image.convert('RGBA'))
        generation_reference = shape_canvas.convert('RGB').resize(tuple(generation_size), Image.LANCZOS)
        final_alpha_mask = source_image.getchannel('A').resize(tuple(tile_size), Image.LANCZOS)
        return generation_reference, final_alpha_mask, actual_sha256


def build_variant_prompt(ticket_values: dict, tile_role: str) -> str:
    """역할별 표면 제약을 짧은 Qwen 편집 프롬프트로 만든다."""
    role_description = {
        'ground': 'top-down ground tile, flat walkable top surface',
        'wall-front': 'front-facing vertical wall tile for a height change',
        'wall-side': 'side-facing vertical wall tile for a height change',
    }[tile_role]
    material_instruction = ' Use the single reference only as a repeating rock or soil surface-pattern guide.' if 'material_reference_id' in ticket_values else ''
    shape_instruction = ' Preserve the first reference silhouette and visible material layout.' if 'shape_reference_id' in ticket_values else ''
    return f"Create one square flat orthographic 2D {role_description} surface pattern.{material_instruction}{shape_instruction} {ticket_values['prompt'].strip()} Repeat seamlessly in both axes. Surface pattern only: no individual object, extruded wall, perspective, character, person, text, UI, watermark, scene, border, or tile grid."


def build_height_preview(tile_images: dict, tile_size: list[int], height_steps: int, preview_path: Path):
    """바닥과 전면·측면 벽의 연결을 확인할 수 있는 결정적 미리보기를 만든다."""
    from PIL import Image, ImageDraw
    tile_width, tile_height = tile_size
    preview_width = tile_width * 5
    preview_height = tile_height * (height_steps + 4)
    preview_image = Image.new('RGBA', (preview_width, preview_height), (31, 38, 52, 255))
    ground_image = tile_images.get('ground')
    wall_front_image = tile_images.get('wall-front')
    wall_side_image = tile_images.get('wall-side')
    if ground_image:
        for grid_y in range(2):
            for grid_x in range(3):
                preview_image.alpha_composite(ground_image, (tile_width + grid_x * tile_width, tile_height + grid_y * tile_height))
    for level_index in range(height_steps):
        vertical_offset = tile_height * (3 + level_index)
        if wall_front_image:
            for grid_x in range(3):
                preview_image.alpha_composite(wall_front_image, (tile_width + grid_x * tile_width, vertical_offset))
        if wall_side_image:
            preview_image.alpha_composite(wall_side_image, (0, vertical_offset))
    preview_draw = ImageDraw.Draw(preview_image)
    preview_draw.rectangle((0, 0, preview_width - 1, preview_height - 1), outline=(245, 186, 61, 255), width=2)
    preview_draw.text((8, 8), f"{height_steps} step height preview", fill=(255, 255, 255, 255))
    preview_image.save(preview_path)


def write_tile_review_record(trial_output_root: Path, result_values: dict, ticket_file_path: Path, map_preview_record: dict | None = None):
    """관리도구가 실행 폴더만으로 후보를 찾도록 검수 기록을 남긴다."""
    variant_records = []
    for current_variant_record in result_values['variants']:
        current_tile_path = trial_output_root / current_variant_record['tile']
        variant_records.append({'role': current_variant_record['role'], 'file': current_tile_path.name,
                                'sha256': hashlib.sha256(current_tile_path.read_bytes()).hexdigest()})
    preview_file_name = result_values['preview']
    review_record_values = {'schemaVersion': 1, 'kind': 'qwen-terrain-tile-review',
                            'assetId': result_values['asset_id'], 'status': result_values['status'],
                            'modelId': result_values['model_id'], 'modelRevision': result_values['revision'],
                            'tileSize': result_values['tile_size'], 'tileability': result_values['tileability'],
                            'heightSteps': result_values['height_steps'], 'ticket': {'file': 'ticket.yaml', 'sha256': hashlib.sha256(ticket_file_path.read_bytes()).hexdigest()},
                            'variants': variant_records,
                            'preview': None if preview_file_name is None else {'file': preview_file_name, 'sha256': hashlib.sha256((trial_output_root / preview_file_name).read_bytes()).hexdigest()},
                            'mapPreview': map_preview_record,
                            'qualityWarnings': result_values['quality_warnings']}
    (trial_output_root / 'tile-review.json').write_text(json.dumps(review_record_values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return review_record_values


def execute_tile_set_generation(*, ticket_file_path, style_reference_path, trial_output_root, shape_reference_path=None, material_reference_path=None, map_preview_path=None):
    """고정 Qwen 모델로 타일 역할별 후보와 이음새·높이 미리보기를 생성한다."""
    from PIL import Image
    ticket_file_path = Path(ticket_file_path).resolve()
    trial_output_root = Path(trial_output_root).resolve()
    if not trial_output_root.is_relative_to((WORKFLOW_REPOSITORY_ROOT / '.tmp').resolve()):
        raise ValueError('후보 출력은 워크플로우 .tmp 하위만 허용합니다.')
    if trial_output_root.exists() and any(trial_output_root.iterdir()):
        raise FileExistsError('기존 실행을 덮어쓸 수 없습니다. 새 실행 경로를 사용하세요.')
    ticket_values = validate_tile_set_ticket(read_tile_set_ticket(ticket_file_path))
    reference_image, reference_sha256 = validate_style_reference(Path(style_reference_path), ticket_values['style_reference_sha256'], ticket_values['generation_size'])
    shape_reference_image = None
    final_alpha_mask = None
    shape_reference_sha256 = None
    if 'shape_reference_id' in ticket_values:
        if shape_reference_path is None:
            raise ValueError('형태 참조가 티켓에 있으므로 --shape-reference가 필요합니다.')
        shape_reference_image, final_alpha_mask, shape_reference_sha256 = validate_shape_reference(Path(shape_reference_path), ticket_values['shape_reference_sha256'], ticket_values['generation_size'], ticket_values['tile_size'])
    elif shape_reference_path is not None:
        raise ValueError('형태 참조 입력에는 티켓의 형태 참조 기록이 필요합니다.')
    material_reference_image = None
    material_reference_sha256 = None
    if 'material_reference_id' in ticket_values:
        if material_reference_path is None:
            raise ValueError('재질 참조가 티켓에 있으므로 --material-reference가 필요합니다.')
        material_reference_image, material_reference_sha256 = validate_material_reference(Path(material_reference_path), ticket_values['material_reference_sha256'], ticket_values['generation_size'])
    elif material_reference_path is not None:
        raise ValueError('재질 참조 입력에는 티켓의 재질 참조 기록이 필요합니다.')
    map_preview_snapshot = None
    map_preview_sha256 = None
    if map_preview_path is not None:
        map_preview_snapshot, map_preview_sha256 = read_map_preview_snapshot(Path(map_preview_path))
    if not PIPELINE_EXECUTION_LOCK.acquire(blocking=False):
        raise RuntimeError('동시 Qwen 타일 추론은 허용하지 않습니다.')
    trial_output_root.mkdir(parents=True, exist_ok=False)
    logger_name_value = f"qwen-tile.{trial_output_root.name}"
    execution_logger = logging.getLogger(logger_name_value)
    execution_logger.setLevel(logging.INFO)
    execution_logger.propagate = False
    for log_handler in (logging.FileHandler(trial_output_root / 'execution.log'), logging.StreamHandler()):
        log_handler.setFormatter(logging.Formatter('%(asctime)s/qwen-tile/%(message)s'))
        execution_logger.addHandler(log_handler)
    run_started_time = time.monotonic()
    progress_state = {'stage': 'imports', 'role': '-', 'step': 0}
    heartbeat_stop_event = threading.Event()

    def emit_progress_heartbeat():
        while not heartbeat_stop_event.wait(5):
            try:
                gpu_result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu', '--format=csv,noheader'], check=True, capture_output=True, text=True, timeout=3)
                execution_logger.info('heartbeat stage=%s role=%s step=%s/%s elapsed=%.0fs gpu=%s', progress_state['stage'], progress_state['role'], progress_state['step'], FIXED_INFERENCE_STEPS, time.monotonic() - run_started_time, gpu_result.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                execution_logger.exception('heartbeat GPU 상태 조회 실패')

    heartbeat_thread = threading.Thread(target=emit_progress_heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        import diffusers
        import torch
        from diffusers import QwenImageEditPlusPipeline
        from diffusers.pipelines.qwenimage import pipeline_qwenimage_edit_plus as qwen_pipeline_module
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA를 사용할 수 없어 중단합니다. CPU 추론은 지원하지 않습니다.')
        if diffusers.__version__ != '0.37.0':
            raise RuntimeError('검증한 diffusers 0.37.0 환경에서만 실행합니다.')
        if not (FIXED_MODEL_DIRECTORY / 'model_index.json').is_file():
            raise FileNotFoundError(f'모델 준비 필요: model_id={FIXED_MODEL_IDENTIFIER} model_path={FIXED_MODEL_DIRECTORY}')
        generation_width, generation_height = ticket_values['generation_size']
        original_vae_area = qwen_pipeline_module.VAE_IMAGE_SIZE
        qwen_pipeline_module.VAE_IMAGE_SIZE = generation_width * generation_height
        execution_logger.info('load model_id=%s revision=%s path=%s', FIXED_MODEL_IDENTIFIER, FIXED_MODEL_REVISION, FIXED_MODEL_DIRECTORY)
        image_edit_pipeline = QwenImageEditPlusPipeline.from_pretrained(str(FIXED_MODEL_DIRECTORY), torch_dtype=torch.bfloat16, local_files_only=True, low_cpu_mem_usage=True)
        image_edit_pipeline.enable_sequential_cpu_offload()
        image_edit_pipeline.vae.enable_slicing()
        image_edit_pipeline.vae.enable_tiling()
        generated_tile_images = {}
        generated_records = []
        for role_index, tile_role in enumerate(ticket_values['tile_variants']):
            prompt_text = build_variant_prompt(ticket_values, tile_role)
            progress_state.update({'stage': 'inference', 'role': tile_role, 'step': 0})
            execution_logger.info('inference role=%s size=%sx%s steps=%s', tile_role, generation_width, generation_height, FIXED_INFERENCE_STEPS)
            def record_denoise_progress(pipeline_instance, step_index, timestep_value, callback_values):
                progress_state['step'] = step_index + 1
                execution_logger.info('denoise role=%s step=%s/%s', tile_role, step_index + 1, FIXED_INFERENCE_STEPS)
                return callback_values
            with torch.inference_mode():
                input_reference_images = ([material_reference_image] if material_reference_image else ([shape_reference_image, reference_image] if shape_reference_image else [reference_image]))
                output_image = image_edit_pipeline(image=input_reference_images, prompt=prompt_text, negative_prompt='text, watermark, character, person, interface, grid', width=generation_width, height=generation_height, num_inference_steps=FIXED_INFERENCE_STEPS, true_cfg_scale=FIXED_TRUE_CFG_SCALE, guidance_scale=FIXED_GUIDANCE_SCALE, generator=torch.Generator(device='cuda').manual_seed(FIXED_GENERATOR_SEED + role_index), callback_on_step_end=record_denoise_progress).images[0]
            candidate_path = trial_output_root / f'{tile_role}-candidate.png'
            final_path = trial_output_root / f'{tile_role}.png'
            output_image.convert('RGBA').save(candidate_path)
            final_image = output_image.convert('RGBA').resize(tuple(ticket_values['tile_size']), Image.LANCZOS)
            if final_alpha_mask is not None and ticket_values['apply_shape_alpha']:
                final_image.putalpha(final_alpha_mask)
            final_image.save(final_path)
            generated_tile_images[tile_role] = final_image
            generated_records.append({'role': tile_role, 'prompt_sha256': hashlib.sha256(prompt_text.encode()).hexdigest(), 'candidate': candidate_path.name, 'tile': final_path.name, 'seed': FIXED_GENERATOR_SEED + role_index})
            (trial_output_root / f'{tile_role}-prompt.txt').write_text(prompt_text + '\n', encoding='utf-8')
        if ticket_values['acceptance']['seam_check']:
            preview_tile_images = dict(generated_tile_images)
            if 'ground' not in preview_tile_images:
                preview_tile_images['ground'] = reference_image.convert('RGBA').resize(tuple(ticket_values['tile_size']), Image.LANCZOS)
            build_height_preview(preview_tile_images, ticket_values['tile_size'], ticket_values['height_steps'], trial_output_root / 'height-preview.png')
        (trial_output_root / 'ticket.yaml').write_text(ticket_file_path.read_text(encoding='utf-8'), encoding='utf-8')
        result_values = {'status': 'candidate-needs-user-review', 'asset_id': ticket_values['asset_id'], 'model_id': FIXED_MODEL_IDENTIFIER, 'revision': FIXED_MODEL_REVISION, 'generation_size': ticket_values['generation_size'], 'tile_size': ticket_values['tile_size'], 'tileability': ticket_values['tileability'], 'height_steps': ticket_values['height_steps'], 'style_reference_id': ticket_values['style_reference_id'], 'style_reference_path': str(Path(style_reference_path).resolve()), 'style_reference_sha256': reference_sha256, 'material_reference_id': ticket_values.get('material_reference_id'), 'material_reference_path': str(Path(material_reference_path).resolve()) if material_reference_path else None, 'material_reference_sha256': material_reference_sha256, 'shape_reference_id': ticket_values.get('shape_reference_id'), 'shape_reference_path': str(Path(shape_reference_path).resolve()) if shape_reference_path else None, 'shape_reference_sha256': shape_reference_sha256, 'shape_alpha_applied': final_alpha_mask is not None and ticket_values.get('apply_shape_alpha', False), 'steps': FIXED_INFERENCE_STEPS, 'true_cfg_scale': FIXED_TRUE_CFG_SCALE, 'guidance_scale': FIXED_GUIDANCE_SCALE, 'seed': FIXED_GENERATOR_SEED, 'execution_device': 'cuda', 'elapsed_seconds': round(time.monotonic() - run_started_time, 2), 'variants': generated_records, 'preview_ground': 'generated-ground' if 'ground' in generated_tile_images else 'style-reference-resize', 'preview': 'height-preview.png' if ticket_values['acceptance']['seam_check'] else None, 'quality_warnings': ['이음새와 높이 변화 미리보기를 검수한 뒤에만 정식 에셋으로 채택합니다.']}
        (trial_output_root / 'result.json').write_text(json.dumps(result_values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        map_preview_record = None
        if map_preview_snapshot is not None:
            (trial_output_root / 'map-preview.yaml').write_text(Path(map_preview_path).read_text(encoding='utf-8'), encoding='utf-8')
            map_preview_record = {'file': 'map-preview.yaml', 'sha256': map_preview_sha256, 'mapId': map_preview_snapshot['mapId'], 'targetCells': map_preview_snapshot['targetCells']}
        write_tile_review_record(trial_output_root, result_values, ticket_file_path, map_preview_record)
        execution_logger.info('complete preview=%s', result_values['preview'])
        return result_values
    except Exception:
        execution_logger.exception('failed stage=%s role=%s', progress_state['stage'], progress_state['role'])
        raise
    finally:
        if 'qwen_pipeline_module' in locals() and 'original_vae_area' in locals():
            qwen_pipeline_module.VAE_IMAGE_SIZE = original_vae_area
        heartbeat_stop_event.set()
        heartbeat_thread.join(timeout=4)
        for log_handler in list(execution_logger.handlers):
            log_handler.close()
            execution_logger.removeHandler(log_handler)
        PIPELINE_EXECUTION_LOCK.release()
