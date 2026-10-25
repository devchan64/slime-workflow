"""완성된 DB 스냅샷 세대만 파일 시드로 공개한다."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import yaml
from tools.review.domains.map_assets.database_client import execute_content_api_request


def encode_content_snapshot_payload(current_payload_record):
    return json.dumps(current_payload_record,ensure_ascii=False,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()


def write_content_snapshot_file(current_target_path,current_file_bytes):
    current_target_path.parent.mkdir(parents=True,exist_ok=True)
    with current_target_path.open('xb') as current_file_stream:
        current_file_stream.write(current_file_bytes)
        current_file_stream.flush()
        os.fsync(current_file_stream.fileno())


def sync_content_snapshot_directory(current_directory_path):
    current_directory_descriptor=os.open(current_directory_path,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(current_directory_descriptor)
    finally:
        os.close(current_directory_descriptor)


def verify_content_snapshot_manifest(current_snapshot_root,current_manifest_record):
    for current_file_record in current_manifest_record['files']:
        current_file_path=current_snapshot_root/current_file_record['path']
        if not current_file_path.resolve().is_relative_to(current_snapshot_root.resolve()) or current_file_path.is_symlink():
            raise ValueError('스냅샷 경로 이탈')
        if hashlib.sha256(current_file_path.read_bytes()).hexdigest()!=current_file_record['sha256']:
            raise ValueError('스냅샷 파일이 외부에서 변경되었습니다: '+current_file_record['path'])


def publish_content_snapshot_bundle(current_snapshot_root,current_export_record):
    current_snapshot_root=Path(current_snapshot_root)
    current_snapshot_root.mkdir(parents=True,exist_ok=True)
    current_payload_record=current_export_record['payload']
    current_payload_hash=hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()
    if current_payload_hash!=current_export_record['payloadHash']:
        raise ValueError('DB 스냅샷 전달 해시 불일치')
    with (current_snapshot_root/'.snapshot.lock').open('a') as current_lock_stream:
        fcntl.flock(current_lock_stream,fcntl.LOCK_EX)
        current_pointer_path=current_snapshot_root/'current.yaml'
        if current_pointer_path.exists():
            current_previous_manifest=yaml.safe_load(current_pointer_path.read_text())
            verify_content_snapshot_manifest(current_snapshot_root,current_previous_manifest)
            if current_previous_manifest['generation']>current_payload_record['generation']:
                raise ValueError('이전 세대로 스냅샷을 되돌릴 수 없습니다.')
            if current_previous_manifest['generation']==current_payload_record['generation']:
                if current_previous_manifest['payloadHash']!=current_payload_hash:
                    raise ValueError('동일 세대의 스냅샷 내용이 다릅니다.')
                return hashlib.sha256(current_pointer_path.read_bytes()).hexdigest()
        current_generation_name=f"generation-{current_payload_record['generation']}-{current_payload_hash[:16]}"
        current_generation_directory=current_snapshot_root/current_generation_name
        current_file_contents={}
        for current_asset_type in current_payload_record['types']:
            if not current_asset_type or any(current_character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for current_character in current_asset_type):
                raise ValueError('스냅샷 에셋 타입 오류')
            current_type_assets=[current_asset_record for current_asset_record in current_payload_record['assets'] if current_asset_record['assetType']==current_asset_type]
            current_file_contents[f'billboards/{current_asset_type}.yaml']=yaml.safe_dump(
                {'schema_version':1,'category':current_asset_type,'assets':current_type_assets},allow_unicode=True,sort_keys=False).encode()
        for current_document_name,current_map_document in current_payload_record.get('mapDocuments',{}).items():
            current_relative_document=Path(current_document_name)
            if current_relative_document.is_absolute() or '..' in current_relative_document.parts or current_relative_document.suffix!='.yaml':
                raise ValueError('맵 스냅샷 상대 경로 오류')
            current_file_contents['maps/'+current_document_name]=yaml.safe_dump(current_map_document,allow_unicode=True,sort_keys=False).encode()
        current_file_contents['building-properties.yaml']=yaml.safe_dump(current_payload_record.get('buildingProperties',{}),allow_unicode=True,sort_keys=False).encode()
        current_file_contents['map-revisions.yaml']=yaml.safe_dump(current_payload_record.get('mapRevisions',{}),allow_unicode=True,sort_keys=False).encode()
        current_file_contents['types.yaml']=yaml.safe_dump(current_payload_record['types'],allow_unicode=True,sort_keys=False).encode()
        current_file_contents['asset-order.yaml']=yaml.safe_dump([current_asset_record['assetId'] for current_asset_record in current_payload_record['assets']],allow_unicode=True,sort_keys=False).encode()
        current_manifest_record={'schema_version':1,'generation':current_payload_record['generation'],'payloadHash':current_payload_hash,
            'files':[{'path':current_generation_name+'/'+current_file_name,'sha256':hashlib.sha256(current_file_bytes).hexdigest()}
                for current_file_name,current_file_bytes in current_file_contents.items()]}
        if not current_generation_directory.exists():
            with tempfile.TemporaryDirectory(prefix='.snapshot-',dir=current_snapshot_root) as current_temporary_name:
                current_temporary_root=Path(current_temporary_name)
                current_bundle_directory=current_temporary_root/'bundle'
                for current_file_name,current_file_bytes in current_file_contents.items():
                    write_content_snapshot_file(current_bundle_directory/current_file_name,current_file_bytes)
                for current_nested_directory in sorted((current_path for current_path in current_bundle_directory.rglob('*') if current_path.is_dir()),reverse=True):
                    sync_content_snapshot_directory(current_nested_directory)
                sync_content_snapshot_directory(current_bundle_directory)
                os.rename(current_bundle_directory,current_generation_directory)
                sync_content_snapshot_directory(current_snapshot_root)
        verify_content_snapshot_manifest(current_snapshot_root,current_manifest_record)
        current_manifest_bytes=yaml.safe_dump(current_manifest_record,allow_unicode=True,sort_keys=False).encode()
        with tempfile.TemporaryDirectory(prefix='.publish-',dir=current_snapshot_root) as current_temporary_name:
            current_pending_path=Path(current_temporary_name)/'current.yaml'
            write_content_snapshot_file(current_pending_path,current_manifest_bytes)
            os.replace(current_pending_path,current_pointer_path)
            sync_content_snapshot_directory(current_snapshot_root)
        return hashlib.sha256(current_manifest_bytes).hexdigest()


def execute_content_snapshot_cycle(current_snapshot_root):
    current_export_record=execute_content_api_request('POST','/internal/v1/content/snapshots/export',{})
    if not current_export_record['needed']:
        return current_export_record
    current_run_identifier=current_export_record['runId']
    try:
        current_manifest_hash=publish_content_snapshot_bundle(current_snapshot_root,current_export_record)
    except Exception as current_snapshot_error:
        execute_content_api_request('POST',f'/internal/v1/content/snapshots/{current_run_identifier}/fail',{'message':str(current_snapshot_error)[:2000]})
        raise
    return execute_content_api_request('POST',f'/internal/v1/content/snapshots/{current_run_identifier}/complete',
        {'payloadHash':current_export_record['payloadHash'],'manifestHash':current_manifest_hash})
