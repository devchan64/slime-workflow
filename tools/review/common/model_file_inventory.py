"""모델별 고정 저장 위치의 파일 존재 여부를 읽기 전용으로 조회한다."""
import os
from pathlib import Path

MODEL_INVENTORY_ROOT = Path(__file__).resolve().parents[3]
MODEL_INVENTORY_LIMIT = 500


def resolve_model_inventory_paths():
    """생성기 계약에 등록된 모델만 조회하며 실행 환경·시험 파일은 제외한다."""
    from generators.image.qwen_21_runtime import QWEN_MODEL_DIRECTORY
    from generators.kimodo.contracts import KIMODO_MODEL_ROOT
    from generators.kimodo.dwpose_runtime import FUN_POSE_MODEL_DIRECTORY
    from generators.music.contracts import resolve_music_paths
    from generators.wan_animate2.contracts import ANIMATE_MODEL_DIRECTORY
    from generators.wan_fun.contracts import FUN_MODEL_FILES, FUN_WORKSPACE_ROOT
    from generators.wan_vace.contracts import VACE_MODEL_FILES, VACE_WORKSPACE_ROOT
    from generators.writer_agent.prepare import MODEL_DOWNLOAD_ROOT
    return {
        'prop-generator': [QWEN_MODEL_DIRECTORY],
        'kimodo': [KIMODO_MODEL_ROOT, FUN_POSE_MODEL_DIRECTORY],
        'wan22-animate2': [ANIMATE_MODEL_DIRECTORY],
        'wan22-fun-control': [*(FUN_WORKSPACE_ROOT / current_file_record[0] for current_file_record in FUN_MODEL_FILES.values()), FUN_POSE_MODEL_DIRECTORY],
        'wan22-vace': [VACE_WORKSPACE_ROOT / current_file_record[0] for current_file_record in VACE_MODEL_FILES.values()],
        'music-heartmula': [resolve_music_paths('music-heartmula')[1]],
        'sfx-dasheng-audiogen': [resolve_music_paths('sfx-dasheng-audiogen')[1]],
        'writer-agent': [MODEL_DOWNLOAD_ROOT],
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
            'files': [{'path': current_path_name, 'bytes': current_file_bytes}
                      for current_path_name, current_file_bytes in current_sorted_files[:MODEL_INVENTORY_LIMIT]],
            'truncated': len(current_sorted_files) > MODEL_INVENTORY_LIMIT,
            'incomplete': bool(current_scan_errors),
        }
    return current_inventory_records
