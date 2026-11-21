"""맵 원본·등록부·백엔드 잠금의 일치 여부를 읽기 전용으로 확인한다."""
import hashlib
import json
from pathlib import Path
import re
import yaml

from workflow.common.map_tile_assets import UniqueAssetYamlLoader, load_registered_tiles


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


def read_registered_city_source(current_asset_root,current_backend_lock,current_city_identifier):
    """등록 원본·백엔드 잠금이 일치할 때 도시 문서를 읽는다."""
    if not isinstance(current_city_identifier,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_city_identifier):
        raise ValueError('도시 맵 ID 형식 오류')
    current_asset_root=Path(current_asset_root).resolve()
    current_source_path=current_asset_root/'assets/maps/city_layouts'/(current_city_identifier+'.yaml')
    if current_source_path.is_symlink() or not current_source_path.is_file() or not current_source_path.resolve().is_relative_to((current_asset_root/'assets/maps').resolve()):
        raise ValueError('도시 맵 원본을 확인할 수 없습니다.')
    if inspect_hermes_map_sources(current_asset_root,current_backend_lock).get('status')!='matched':
        raise ValueError('맵 원본·등록부·백엔드 잠금을 확인할 수 없습니다.')
    current_source_bytes=current_source_path.read_bytes()
    if len(current_source_bytes)>1_000_000:raise ValueError('도시 맵 원본 크기 초과')
    current_document_value=yaml.load(current_source_bytes,Loader=UniqueAssetYamlLoader)
    if not isinstance(current_document_value,dict) or set(current_document_value)!={'managementId','data'} or current_document_value.get('managementId')!='config.city-layouts.'+current_city_identifier or not isinstance(current_document_value.get('data'),dict) or current_document_value['data'].get('cityId')!=current_city_identifier:
        raise ValueError('도시 맵 원본 식별자 오류')
    validate_city_json_structure(current_document_value)
    json.dumps(current_document_value,ensure_ascii=False,allow_nan=False)
    if current_source_path.is_symlink() or current_source_path.read_bytes()!=current_source_bytes or inspect_hermes_map_sources(current_asset_root,current_backend_lock).get('status')!='matched':
        raise ValueError('도시 맵 원본이 조회 중 변경되었습니다.')
    return {'map':current_city_identifier,'document':current_document_value,'source_sha256':hashlib.sha256(current_source_bytes).hexdigest(),'note':'에셋 원본의 조회 시점 자료입니다. DB 세대·리비전과 실행 중인 백엔드 반영은 확인하지 않으며 저장할 수 없습니다.'}


def validate_city_json_structure(current_document_value):
    """JSON 객체의 키가 문자열이고 모든 값이 JSON 자료형인지 확인한다."""
    current_pending_values=[current_document_value]
    current_seen_objects=set()
    while current_pending_values:
        current_value_object=current_pending_values.pop()
        if isinstance(current_value_object,(dict,list)):
            if id(current_value_object) in current_seen_objects:raise ValueError('JSON 구조 반복 또는 순환 오류')
            current_seen_objects.add(id(current_value_object))
        if isinstance(current_value_object,dict):
            if any(not isinstance(current_key_value,str) for current_key_value in current_value_object):raise ValueError('JSON 객체 키 오류')
            current_pending_values.extend(current_value_object.values())
        elif isinstance(current_value_object,list):
            current_pending_values.extend(current_value_object)
        elif current_value_object is not None and type(current_value_object) not in (str,int,float,bool):
            raise ValueError('JSON 값 오류')


def inspect_city_source_alignment(current_asset_root,current_backend_lock,current_city_identifier,current_database_document):
    """도시 DB 문서와 등록된 원본이 같은지 읽기 전용으로 확인한다."""
    try:
        if not isinstance(current_city_identifier,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_city_identifier) or not isinstance(current_database_document,dict):
            raise ValueError('도시 식별자 또는 DB 문서 오류')
        current_asset_root=Path(current_asset_root).resolve()
        current_source_path=current_asset_root/'assets/maps/city_layouts'/(current_city_identifier+'.yaml')
        if current_source_path.is_symlink() or not current_source_path.is_file() or not current_source_path.resolve().is_relative_to((current_asset_root/'assets/maps').resolve()):
            raise ValueError('도시 원본 경로 오류')
        current_source_bytes=current_source_path.read_bytes()
        current_source_document=yaml.load(current_source_bytes,Loader=UniqueAssetYamlLoader)
        if not isinstance(current_source_document,dict) or current_source_document.get('managementId')!='config.city-layouts.'+current_city_identifier or not isinstance(current_source_document.get('data'),dict) or current_source_document['data'].get('cityId')!=current_city_identifier:
            raise ValueError('도시 원본 식별자 오류')
        current_source_status=inspect_hermes_map_sources(current_asset_root,current_backend_lock)
        if current_source_status.get('status')!='matched' or current_source_path.is_symlink() or current_source_path.read_bytes()!=current_source_bytes:
            return {'status':'unavailable','note':'에셋 원본·등록부·잠금의 일치를 확인할 수 없습니다.'}
        validate_city_json_structure(current_source_document)
        validate_city_json_structure(current_database_document)
        current_source_json=json.dumps(current_source_document,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        current_database_json=json.dumps(current_database_document,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        return {'status':'matched' if current_source_json==current_database_json else 'mismatch','note':'조회 시점의 도시 DB 문서와 등록 원본 내용 비교이며 실행 중인 서비스 반영은 확인하지 않습니다.'}
    except (OSError,ValueError,TypeError,KeyError,yaml.YAMLError):
        return {'status':'unavailable','note':'도시 원본 또는 DB 문서를 확인할 수 없습니다.'}


def inspect_field_source_alignment(current_asset_root,current_backend_lock,current_map_identifier,current_database_tiles,current_database_terrain):
    """야외 맵의 DB 타일·지형 데이터와 등록 원본을 비교한다."""
    try:
        if not isinstance(current_map_identifier,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_map_identifier):
            raise ValueError('야외 맵 ID 오류')
        current_asset_root=Path(current_asset_root).resolve()
        current_map_root=current_asset_root/'assets/maps'
        current_source_paths=[current_map_root/'field_tiles'/(current_map_identifier+'.yaml'),current_map_root/'terrain/maps'/(current_map_identifier+'.yaml')]
        current_source_bytes=[]
        current_source_data=[]
        for current_source_path in current_source_paths:
            if current_source_path.is_symlink() or not current_source_path.is_file() or not current_source_path.resolve().is_relative_to(current_map_root.resolve()):
                raise ValueError('야외 맵 원본 경로 오류')
            current_document_bytes=current_source_path.read_bytes()
            current_document_value=yaml.load(current_document_bytes,Loader=UniqueAssetYamlLoader)
            if not isinstance(current_document_value,dict) or 'data' not in current_document_value:raise ValueError('야외 맵 문서 오류')
            current_source_bytes.append(current_document_bytes)
            current_source_data.append(current_document_value['data'])
        if inspect_hermes_map_sources(current_asset_root,current_backend_lock).get('status')!='matched':
            return {'status':'unavailable','note':'에셋 원본·등록부·잠금의 일치를 확인할 수 없습니다.'}
        if any(current_source_path.is_symlink() or current_source_path.read_bytes()!=current_previous_bytes for current_source_path,current_previous_bytes in zip(current_source_paths,current_source_bytes)):
            raise ValueError('야외 맵 원본이 비교 중 변경되었습니다.')
        current_database_data=[current_database_tiles,current_database_terrain]
        for current_document_value in (*current_source_data,*current_database_data):validate_city_json_structure(current_document_value)
        current_source_json=json.dumps(current_source_data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        current_database_json=json.dumps(current_database_data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        return {'status':'matched' if current_source_json==current_database_json else 'mismatch','note':'조회 시점의 야외 맵 DB 타일·지형과 등록 원본 비교이며 실행 중인 서비스 반영은 확인하지 않습니다.'}
    except (OSError,ValueError,TypeError,KeyError,yaml.YAMLError):
        return {'status':'unavailable','note':'야외 맵 원본 또는 DB 문서를 확인할 수 없습니다.'}
