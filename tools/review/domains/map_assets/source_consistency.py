"""맵 원본·등록부·백엔드 잠금의 일치 여부를 읽기 전용으로 확인한다."""
import hashlib
from pathlib import Path
import re
import yaml

from tools.review.common.map_tile_assets import UniqueAssetYamlLoader, load_registered_tiles


def inspect_hermes_map_sources(current_asset_root, current_backend_lock):
    """파일 집합과 해시를 확인하며 DB 상태나 실행 중인 서비스는 판단하지 않는다."""
    try:
        current_asset_root = Path(current_asset_root).resolve()
        current_registry_path = current_asset_root/'asset-registry.yaml'
        if current_registry_path.is_symlink():raise ValueError('등록부 경로 오류')
        current_registry_bytes = current_registry_path.read_bytes()
        current_asset_root, current_registry_records = load_registered_tiles(current_asset_root)
        if current_registry_path.read_bytes()!=current_registry_bytes:raise ValueError('등록부가 조회 중 변경됐습니다.')
        current_backend_lock = Path(current_backend_lock)
        if current_backend_lock.is_symlink():
            raise ValueError('잠금 경로 오류')
        current_lock_bytes = current_backend_lock.read_bytes()
        current_lock_record = yaml.load(current_lock_bytes, Loader=UniqueAssetYamlLoader)
        if (not isinstance(current_lock_record, dict) or set(current_lock_record) != {'schema_version','repository','files'}
                or type(current_lock_record['schema_version']) is not int or current_lock_record['schema_version'] != 1
                or current_lock_record['repository'] != 'slime-assets' or not isinstance(current_lock_record['files'], list)
                or not current_lock_record['files']):
            raise ValueError('잠금 형식 오류')
        current_lock_entries = {}
        for current_entry_record in current_lock_record['files']:
            if not isinstance(current_entry_record, dict) or set(current_entry_record) != {'path','sha256'}:
                raise ValueError('잠금 항목 오류')
            current_relative_name = current_entry_record['path']
            current_hash_value = current_entry_record['sha256']
            if (not isinstance(current_relative_name, str) or not current_relative_name.startswith('assets/maps/')
                    or Path(current_relative_name).as_posix() != current_relative_name
                    or '..' in Path(current_relative_name).parts or Path(current_relative_name).suffix != '.yaml'
                    or current_relative_name in current_lock_entries or not isinstance(current_hash_value, str)
                    or not re.fullmatch(r'[a-f0-9]{64}', current_hash_value)):
                raise ValueError('잠금 경로 또는 해시 오류')
            current_lock_entries[current_relative_name] = current_hash_value
        current_map_root = current_asset_root / 'assets/maps'
        if not current_map_root.is_dir() or current_map_root.is_symlink():
            raise ValueError('맵 원본 경로 오류')
        current_source_names = set()
        for current_source_path in current_map_root.rglob('*.yaml'):
            if current_source_path.is_symlink() or not current_source_path.is_file() or not current_source_path.resolve().is_relative_to(current_map_root.resolve()):
                raise ValueError('맵 원본 경로 오류')
            current_source_names.add(current_source_path.relative_to(current_asset_root).as_posix())
        current_registry_names = {current_name for current_name in current_registry_records if current_name.startswith('assets/maps/') and current_name.endswith('.yaml')}
        if any(Path(current_name).as_posix()!=current_name or '..' in Path(current_name).parts
               or not re.fullmatch(r'[a-f0-9]{64}',current_registry_records[current_name]['sha256']) for current_name in current_registry_names):
            raise ValueError('맵 등록 경로 또는 해시 오류')
        current_all_names = current_source_names | set(current_lock_entries) | current_registry_names
        current_mismatch_names = []
        current_observed_hashes = {}
        for current_relative_name in sorted(current_all_names):
            if current_relative_name not in current_source_names or current_relative_name not in current_lock_entries or current_relative_name not in current_registry_names:
                current_mismatch_names.append(current_relative_name)
                continue
            current_source_digest = hashlib.sha256((current_asset_root / current_relative_name).read_bytes()).hexdigest()
            current_observed_hashes[current_relative_name] = current_source_digest
            if current_source_digest != current_lock_entries[current_relative_name] or current_source_digest != current_registry_records[current_relative_name]['sha256']:
                current_mismatch_names.append(current_relative_name)
        if current_registry_path.is_symlink() or current_backend_lock.is_symlink() or current_registry_path.read_bytes()!=current_registry_bytes or current_backend_lock.read_bytes()!=current_lock_bytes:
            raise ValueError('등록부 또는 잠금이 조회 중 변경됐습니다.')
        current_verified_names=set()
        for current_source_path in current_map_root.rglob('*.yaml'):
            if current_source_path.is_symlink() or not current_source_path.is_file() or not current_source_path.resolve().is_relative_to(current_map_root.resolve()):raise ValueError('맵 원본 경로 오류')
            current_verified_names.add(current_source_path.relative_to(current_asset_root).as_posix())
        if current_verified_names!=current_source_names:raise ValueError('맵 원본 목록이 조회 중 변경됐습니다.')
        for current_relative_name,current_source_digest in current_observed_hashes.items():
            if hashlib.sha256((current_asset_root/current_relative_name).read_bytes()).hexdigest()!=current_source_digest:raise ValueError('맵 원본이 조회 중 변경됐습니다.')
        return {'status':'matched' if not current_mismatch_names else 'mismatch', 'checked_files':len(current_all_names), 'mismatched_files':len(current_mismatch_names),
                'mismatched_paths':current_mismatch_names[:30], 'paths_truncated':len(current_mismatch_names)>30,
                'note':'로컬 에셋 저장소와 인접 백엔드 잠금의 조회 시점 비교이며 DB 일치나 실행 중인 백엔드 적용을 확인하지 않습니다.'}
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError):
        return {'status':'unavailable', 'note':'맵 원본·등록부 또는 잠금 목록을 확인할 수 없습니다.'}
