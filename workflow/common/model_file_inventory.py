"""모델별 고정 저장 위치의 파일 존재 여부를 읽기 전용으로 조회한다."""
import os
from pathlib import Path

MODEL_INVENTORY_ROOT = Path(__file__).resolve().parents[2]
MODEL_INVENTORY_LIMIT = 500


def resolve_model_inventory_paths():
    """생성기 계약에 등록된 모델만 조회하며 실행 환경·시험 파일은 제외한다."""
    from generators.image.qwen_21_runtime import QWEN_MODEL_DIRECTORY
    from workflow.domains.image.flux_expression_generation import FLUX_MODEL_ROOT_DIRECTORY
    from workflow.domains.image.expression_generation import EXPRESSION_ADAPTER_PATH
    from generators.kimodo.contracts import KIMODO_MODEL_ROOT
    from generators.kimodo.dwpose_runtime import FUN_POSE_MODEL_DIRECTORY
    from generators.music.contracts import resolve_music_paths
    from generators.music.heartmula.runtime import resolve_heart_component, resolve_heart_bundle
    from generators.music.heartmula.separation import resolve_demucs_directory
    from generators.sound_effects.runtime import resolve_effects_component
    from generators.wan_animate2.contracts import ANIMATE_MODEL_DIRECTORY
    from generators.wan_animate2.lightx2v_assets import PATH as ANIMATE_LIGHTX2V_PATH
    from generators.wan_fun.contracts import FUN_MODEL_FILES, FUN_WORKSPACE_ROOT
    from generators.wan_fun.wan13_model_assets import WAN13_MODEL_DIRECTORY
    from generators.wan_vace.contracts import VACE_MODEL_FILES, VACE_WORKSPACE_ROOT
    from generators.wan_vace.q8_assets import DIRECTORY as Q8_DIRECTORY, FILES as Q8_FILES
    from generators.wan_vace.fighting_lora import PATH as FIGHTING_LORA_PATH
    from generators.wan_vace.lightning_lora import DIRECTORY as LIGHTNING_DIRECTORY, FILES as LIGHTNING_FILES
    from generators.wan_i2v.assets import DIRECTORY as I2V_DIRECTORY, FILES as I2V_FILES
    from generators.wan21_t2v.assets import DIRECTORY as T2V21_DIRECTORY, FILES as T2V21_FILES
    from generators.wan21_i2v.assets import DIRECTORY as I2V21_DIRECTORY, FILES as I2V21_FILES
    from generators.wan21_i2v.attack_lora import FILES as I2V21_ATTACK_FILES
    from generators.writer_agent.prepare import embedding_model_directory
    from workflow.domains.translation.service import current_translation_model_root
    from workflow.common.hermes_model_download import current_hermes_model_directory
    from workflow.common.animationgpt_model_download import ANIMATIONGPT_MODEL_DIRECTORY, AUTHOR_T5_DIRECTORY
    from workflow.generators.minimax_h3_ref2va.assets import REF as REF2VA_MODEL_ROOT, FILES as MINIMAX_SHARED_FILES
    from generators.minimax_h3.assets import ASSETS as MINIMAX_I2V_CONFIG
    from generators.minimax_h3_image.contracts import BASE as MINIMAX_IMAGE_CONFIG, FILES as MINIMAX_IMAGE_FILES
    return {
        'animationgpt': [ANIMATIONGPT_MODEL_DIRECTORY, AUTHOR_T5_DIRECTORY, MODEL_INVENTORY_ROOT / '.model/animationgpt-author'],
        'flux-image': [FLUX_MODEL_ROOT_DIRECTORY],
        'prop-generator': [QWEN_MODEL_DIRECTORY],
        'expression-lora': [EXPRESSION_ADAPTER_PATH],
        'kimodo': [KIMODO_MODEL_ROOT, FUN_POSE_MODEL_DIRECTORY],
        'dwpose': [FUN_POSE_MODEL_DIRECTORY],
        'wan22-animate2': [ANIMATE_MODEL_DIRECTORY],
        'wan22-animate2-lightx2v': [ANIMATE_LIGHTX2V_PATH],
        'wan22-fun-control': [*(FUN_WORKSPACE_ROOT / current_file_record[0] for current_file_record in FUN_MODEL_FILES.values()), FUN_POSE_MODEL_DIRECTORY],
        'wan21-fun-1.3b': [WAN13_MODEL_DIRECTORY],
        'wan22-vace': [VACE_WORKSPACE_ROOT / current_file_record[0] for current_file_record in VACE_MODEL_FILES.values()],
        'wan22-vace-q8': [Q8_DIRECTORY / entry[0] for entry in Q8_FILES.values()],
        'wan22-fighting-lora': [FIGHTING_LORA_PATH],
        'wan22-vace-lightning': [LIGHTNING_DIRECTORY / entry[0] for entry in LIGHTNING_FILES.values()],
        'wan22-i2v-assets': [I2V_DIRECTORY / entry[0] for entry in I2V_FILES],
        'wan21-t2v-assets': [T2V21_DIRECTORY / entry[0] for entry in T2V21_FILES],
        'wan21-i2v-assets': [I2V21_DIRECTORY / entry[0] for entry in I2V21_FILES],
        'wan21-i2v-attack-lora': [I2V21_DIRECTORY / entry[0] for entry in I2V21_ATTACK_FILES],
        'music-heartmula': [resolve_heart_component(resolve_music_paths('music-heartmula')[1], name) for name in ('HeartMuLa-oss-3B','HeartCodec-oss')] + [resolve_heart_bundle(resolve_music_paths('music-heartmula')[1]), resolve_demucs_directory(resolve_music_paths('music-heartmula')[1])],
        'sfx-dasheng-audiogen': [resolve_effects_component(resolve_music_paths('sfx-dasheng-audiogen')[1], name) for name in ('model','text-encoder','audio-tokenizer')],
        'writer-agent': [embedding_model_directory(), current_hermes_model_directory()],
        'prompt-translation': [current_translation_model_root()],
        'hermes-model': [current_hermes_model_directory()],
        'minimax-h3-ref2va': [REF2VA_MODEL_ROOT, *(entry[0] for entry in MINIMAX_SHARED_FILES[1:6])],
        'minimax-h3-i2v': [MINIMAX_I2V_CONFIG, *(entry[0] for entry in MINIMAX_SHARED_FILES)],
        'minimax-h3-image': [MINIMAX_IMAGE_CONFIG, *(entry[0] for entry in MINIMAX_IMAGE_FILES)],
    }


def list_model_inventory_files(current_model_paths=None, current_workspace_root=MODEL_INVENTORY_ROOT):
    """파일명·크기만 반환한다. 존재 여부는 다운로드 완료나 해시 검증을 뜻하지 않는다."""
    current_model_paths = current_model_paths if current_model_paths is not None else resolve_model_inventory_paths()
    current_model_root = (current_workspace_root / '.model').resolve()
    current_inventory_records = {}
    for current_service_name, current_root_paths in current_model_paths.items():
        current_file_records = {}
        current_scan_errors = []
        for current_root_path in current_root_paths:
            current_root_path = Path(current_root_path)
            try:
                if current_root_path.is_symlink() or not current_root_path.resolve().is_relative_to(current_model_root):
                    continue
                if current_root_path.is_file():
                    current_walk_entries = [(current_root_path.parent, (), (current_root_path.name,))]
                elif current_root_path.is_dir():
                    current_walk_entries = os.walk(current_root_path, followlinks=False, onerror=current_scan_errors.append)
                else:
                    continue
                for current_directory_name, current_directory_names, current_file_names in current_walk_entries:
                    current_directory_path = Path(current_directory_name)
                    if isinstance(current_directory_names, list):
                        current_directory_names[:] = [current_name for current_name in current_directory_names
                                                      if not current_name.startswith('.') and not (current_directory_path/current_name).is_symlink()]
                    for current_file_name in current_file_names:
                        if (current_file_name.startswith('.') or current_file_name.endswith(('.partial', '.verified', '.incomplete', '.lock', '.tmp', '.checkpoint.bin', '.checkpoint.json'))
                                or current_file_name in ('prepared.json', 'ready.sha256', 'PINNED_REVISION')):
                            continue
                        current_file_path = current_directory_path / current_file_name
                        try:
                            if current_file_path.is_symlink() or not current_file_path.is_file():
                                continue
                            current_relative_name = current_file_path.relative_to(current_model_root).as_posix()
                            current_file_records[current_relative_name] = current_file_path.stat().st_size
                        except OSError as current_scan_error:
                            current_scan_errors.append(current_scan_error)
                            continue
                        except ValueError:
                            continue
            except OSError as current_scan_error:
                current_scan_errors.append(current_scan_error)
                continue
        current_sorted_files = sorted(current_file_records.items(), key=lambda current_item: current_item[0].casefold())
        current_inventory_records[current_service_name] = {
            'count': len(current_sorted_files),
            'total_bytes': sum(current_file_bytes for _, current_file_bytes in current_sorted_files),
            'files': [{'path': current_path_name, 'bytes': current_file_bytes}
                      for current_path_name, current_file_bytes in current_sorted_files[:MODEL_INVENTORY_LIMIT]],
            'truncated': len(current_sorted_files) > MODEL_INVENTORY_LIMIT,
            'incomplete': bool(current_scan_errors),
        }
    return current_inventory_records
