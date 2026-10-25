"""빌보드 폐기 계획·확인 실행. 원본은 보관하고 실패 시 변경을 복원한다."""
from tools.review.maintenance.sync_billboard_catalog import load_billboard_catalog, list_billboard_catalog_paths, write_billboard_catalog, prepare_billboard_catalog_files
import hashlib
import json
from pathlib import Path
import yaml
from tools.review.domains.map_assets.editor import read_editor_snapshot, EDITOR_STORAGE_DIRECTORY
from tools.review.maintenance.sync_billboard_catalog import build_catalog_reference, load_unique_yaml_document


def prepare_billboard_retirement(current_request_payload, current_asset_root=None):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture'}:
        raise ValueError('revision·texture가 필요합니다.')
    current_snapshot_values=read_editor_snapshot(current_asset_root)
    current_asset_root,current_source_paths,current_source_bytes,current_revision_hash,current_property_document,current_catalog_document=current_snapshot_values
    if current_request_payload['revision']!=current_revision_hash:raise ValueError('원본이 변경되었습니다. 목록을 새로고침하세요.')
    current_texture_name=current_request_payload['texture']
    current_asset_record=next((current_record for current_record in current_catalog_document['billboards'] if current_record['texture_key']==current_texture_name),None)
    if current_asset_record is None:raise ValueError('활성 빌보드가 아닙니다.')
    if current_asset_record.get('metadata_references'):raise ValueError('프레임 메타데이터가 있는 에셋은 별도 폐기 검수가 필요합니다.')
    current_image_path=current_asset_root/current_asset_record['source_file']['path']
    if current_image_path.parent!=current_asset_root/'assets/billboards' or current_image_path.is_symlink():raise ValueError('빌보드 원본 경로 오류')
    current_retired_path=current_asset_root/'assets/retired/billboards'/current_image_path.name
    if current_retired_path.exists():raise ValueError('폐기 보관 경로가 이미 존재합니다.')
    current_source_bytes=dict(current_source_bytes)
    current_source_bytes[current_image_path]=current_image_path.read_bytes()
    current_updated_documents={}
    current_map_impacts=[]
    for current_map_path in sorted((current_asset_root/'assets/maps').rglob('*.yaml')):
        current_map_document=load_unique_yaml_document(current_map_path)
        if not isinstance(current_map_document,dict) or not isinstance(current_map_document.get('data'),dict):continue
        current_object_records=current_map_document['data'].get('objects',[])
        current_filtered_records=[current_record for current_record in current_object_records if current_record.get('textureKey')!=current_texture_name]
        if len(current_filtered_records)==len(current_object_records):continue
        current_source_bytes[current_map_path]=current_map_path.read_bytes()
        current_map_document['data']['objects']=current_filtered_records
        current_updated_documents[current_map_path]=current_map_document
        current_map_impacts.append({'map':current_map_path.stem,'removed':len(current_object_records)-len(current_filtered_records)})
    current_property_document['data'].pop(current_texture_name)
    current_updated_documents[current_source_paths[0]]=current_property_document
    current_registry_document=load_unique_yaml_document(current_source_paths[1])
    current_registry_record=next(current_record for current_record in current_registry_document['assets'] if current_record['path']==str(current_image_path.relative_to(current_asset_root)))
    if hashlib.sha256(current_source_bytes[current_image_path]).hexdigest()!=current_registry_record['sha256']:raise ValueError('원본 이미지 해시 불일치')
    current_registry_record.setdefault('source',{}).update(lifecycle_status='retired',retirement_reason='관리 UI에서 사용자 확인 후 폐기',original_path=current_registry_record['path'])
    current_registry_record['path']=str(current_retired_path.relative_to(current_asset_root))
    current_catalog_document['billboards']=[current_record for current_record in current_catalog_document['billboards'] if current_record['texture_key']!=current_texture_name]
    current_catalog_document['families'].pop(current_texture_name,None)
    current_catalog_pending=prepare_billboard_catalog_files(current_asset_root,current_catalog_document)
    current_frontend_root=current_asset_root.parent/'slime-frontend'
    current_list_path=current_frontend_root/'src/game/terrain/scenery.asset-list.yaml'
    current_lock_path=current_frontend_root/'sprite-assets.lock.yaml'
    for current_file_path in (current_list_path,current_lock_path):current_source_bytes[current_file_path]=current_file_path.read_bytes()
    current_list_document=load_unique_yaml_document(current_list_path)
    current_updated_documents[current_list_path]={current_key:current_value for current_key,current_value in current_list_document.items() if current_value!=str(current_image_path.relative_to(current_asset_root))}
    current_lock_document=load_unique_yaml_document(current_lock_path)
    current_lock_document['files']=[current_record for current_record in current_lock_document['files'] if Path(current_record.get('source_path',current_record['path'])).stem!=current_texture_name]
    current_updated_documents[current_lock_path]=current_lock_document
    current_pending_files={current_path:yaml.safe_dump(current_document,allow_unicode=True,sort_keys=False).encode() for current_path,current_document in current_updated_documents.items()}
    current_registry_text=yaml.safe_dump(current_registry_document,allow_unicode=True,sort_keys=False)
    current_backend_text=current_source_bytes[current_source_paths[3]].decode()
    for current_file_path in current_updated_documents:
        if current_file_path.is_relative_to(current_asset_root/'assets/maps'):
            current_old_hash=hashlib.sha256(current_source_bytes[current_file_path]).hexdigest()
            current_new_hash=hashlib.sha256(current_pending_files[current_file_path]).hexdigest()
            if current_registry_text.count(current_old_hash)!=1 or current_backend_text.count(current_old_hash)!=1:raise ValueError('등록부·맵 소비자 잠금 불일치')
            current_registry_text=current_registry_text.replace(current_old_hash,current_new_hash)
            current_backend_text=current_backend_text.replace(current_old_hash,current_new_hash)
    current_pending_files.update(current_catalog_pending)
    current_pending_files[current_source_paths[1]]=current_registry_text.encode()
    current_pending_files[current_source_paths[3]]=current_backend_text.encode()
    current_plan_token=hashlib.sha256(json.dumps(current_request_payload,sort_keys=True).encode()+b''.join(hashlib.sha256(current_content).digest() for current_content in current_source_bytes.values())).hexdigest()
    return current_asset_root,current_source_bytes,current_pending_files,current_image_path,current_retired_path,{'texture':current_texture_name,'maps':current_map_impacts,'token':current_plan_token,'original_preserved':True}


def preview_billboard_retirement(current_request_payload,current_asset_root=None):
    current_plan_values=prepare_billboard_retirement(current_request_payload,current_asset_root)
    current_plan_result=current_plan_values[-1]
    EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    (EDITOR_STORAGE_DIRECTORY/(current_plan_result['token']+'-retire.json')).write_text(json.dumps(current_request_payload))
    return current_plan_result


def execute_billboard_retirement(current_request_payload,current_asset_root=None):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture','token'}:raise ValueError('검수한 revision·texture·token이 필요합니다.')
    current_validation_payload={current_key:current_request_payload[current_key] for current_key in ('revision','texture')}
    if not isinstance(current_request_payload['token'],str) or len(current_request_payload['token'])!=64 or any(current_character not in '0123456789abcdef' for current_character in current_request_payload['token']):raise ValueError('폐기 확인 토큰 오류')
    current_preview_path=EDITOR_STORAGE_DIRECTORY/(current_request_payload['token']+'-retire.json')
    if not current_preview_path.is_file() or json.loads(current_preview_path.read_text())!=current_validation_payload:raise ValueError('폐기 내용을 먼저 확인하세요.')
    current_asset_root,current_source_bytes,current_pending_files,current_image_path,current_retired_path,current_plan_result=prepare_billboard_retirement(current_validation_payload,current_asset_root)
    if current_plan_result['token']!=current_request_payload['token']:raise ValueError('확인 후 원본이 변경되었습니다. 다시 확인하세요.')
    for current_file_path,current_file_bytes in current_source_bytes.items():
        if current_file_path.read_bytes()!=current_file_bytes:raise ValueError('폐기 직전에 원본이 변경되었습니다.')
    try:
        current_retired_path.parent.mkdir(parents=True,exist_ok=True)
        current_image_path.rename(current_retired_path)
        for current_file_path,current_file_bytes in current_pending_files.items():current_file_path.write_bytes(current_file_bytes)
        current_catalog_path=current_asset_root/'assets/billboards/catalog.yaml'
        write_billboard_catalog(current_asset_root,build_catalog_reference(current_asset_root))
        build_catalog_reference(current_asset_root)
        return {**current_plan_result,'retired':True}
    except Exception:
        if current_retired_path.exists():current_retired_path.rename(current_image_path)
        for current_file_path,current_file_bytes in current_source_bytes.items():current_file_path.write_bytes(current_file_bytes)
        raise
