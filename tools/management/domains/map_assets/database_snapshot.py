"""완성된 DB 스냅샷 세대만 파일 시드로 공개한다."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import UUID
import yaml
from tools.management.domains.map_assets.database_client import execute_content_api_request


def encode_content_snapshot_payload(current_payload_record):
    return json.dumps(current_payload_record,ensure_ascii=False,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()


def validate_content_export_response(current_export_record):
    """동기화 요청의 응답 식별자와 세대를 파일 반영 전에 검증한다."""
    if not isinstance(current_export_record,dict) or type(current_export_record.get('needed')) is not bool:
        raise ValueError('DB 원장 출력 응답 형식 오류')
    if not current_export_record['needed']:
        if type(current_export_record.get('generation')) is not int or current_export_record['generation']<0:
            raise ValueError('DB 원장 출력 세대 오류')
        return
    current_run_identifier=current_export_record.get('runId')
    current_payload_hash=current_export_record.get('payloadHash')
    current_payload_record=current_export_record.get('payload')
    try:
        if not isinstance(current_run_identifier,str) or str(UUID(current_run_identifier))!=current_run_identifier:raise ValueError('실행 ID 오류')
    except (ValueError,AttributeError) as current_run_error:
        raise ValueError('DB 원장 실행 ID 오류') from current_run_error
    if (not isinstance(current_payload_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_payload_hash)
            or not isinstance(current_payload_record,dict) or type(current_payload_record.get('generation')) is not int
            or current_payload_record['generation']<0):
        raise ValueError('DB 원장 전달 해시 또는 세대 오류')


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
    """구 명령 이름은 호환 유지하되 새 세대 보관 없이 원장을 지연 동기화한다."""
    from tools.management.domains.map_assets.database_ledger import publish_content_asset_ledger
    current_asset_root=Path(os.environ['SLIME_ASSETS_ROOT'])
    current_state_directory=current_asset_root/'.local/content-ledger'
    current_state_directory.mkdir(parents=True,exist_ok=True)
    with (current_state_directory/'sync.lock').open('a') as current_lock_stream:
        fcntl.flock(current_lock_stream,fcntl.LOCK_EX)
        current_export_record=execute_content_api_request('POST','/internal/v1/content/snapshots/export',{})
        validate_content_export_response(current_export_record)
        current_receipt_path=current_state_directory/'synced.yaml'
        if not current_export_record['needed']:
            if current_receipt_path.exists() and yaml.safe_load(current_receipt_path.read_text())['generation']==current_export_record['generation']:
                from tools.management.domains.map_assets.source_consistency import inspect_hermes_map_sources
                current_map_status=inspect_hermes_map_sources(current_asset_root,current_asset_root.parent/'slime-backend/map-data.lock.yaml')
                if current_map_status.get('status')!='matched':
                    raise ValueError('맵 원본·등록부·백엔드 잠금 일치를 확인할 수 없습니다.')
                return {**current_export_record,'ledgerSynced':True}
            # 로컬 영수증 유실 시 현재 DB 세대를 명시적으로 재출력한다.
            current_export_record=execute_content_api_request('POST','/internal/v1/content/snapshots/export?replay=true',{})
            validate_content_export_response(current_export_record)
            if not current_export_record.get('needed'):
                raise ValueError('연결된 콘텐츠 API가 원장 재출력을 지원하지 않습니다.')
        current_run_identifier=current_export_record['runId']
        try:
            if hashlib.sha256(encode_content_snapshot_payload(current_export_record['payload'])).hexdigest()!=current_export_record['payloadHash']:
                raise ValueError('DB 원장 전달 해시 불일치')
            current_sync_result=publish_content_asset_ledger(current_asset_root,current_export_record['payload'])
            if (not isinstance(current_sync_result,dict) or type(current_sync_result.get('generation')) is not int
                    or current_sync_result['generation']!=current_export_record['payload']['generation']):
                raise ValueError('원장 반영 세대를 확인할 수 없습니다.')
        except Exception as current_sync_error:
            try:
                execute_content_api_request('POST',f'/internal/v1/content/snapshots/{current_run_identifier}/fail',{'message':str(current_sync_error)[:2000]})
            except (OSError,RuntimeError,ValueError,TypeError) as current_failure_error:
                raise RuntimeError('원장 반영 실패와 DB 실패 기록을 확인하세요. 실패 기록 전송도 확인하지 못했습니다: '+str(current_sync_error)) from current_failure_error
            raise
        try:
            current_completion_record=execute_content_api_request('POST',f'/internal/v1/content/snapshots/{current_run_identifier}/complete',
                {'payloadHash':current_export_record['payloadHash'],'manifestHash':current_export_record['payloadHash']})
        except (OSError,RuntimeError,ValueError,TypeError) as current_completion_error:
            raise RuntimeError('파일 원장은 반영됐으나 DB 완료 응답을 확인하지 못했습니다. DB 상태와 원장을 확인한 뒤 동기화를 다시 확인하세요.') from current_completion_error
        current_payload_generation=current_export_record['payload'].get('generation')
        if (not isinstance(current_completion_record,dict) or current_completion_record.get('completed') is not True
                or type(current_payload_generation) is not int or current_payload_generation<0
                or type(current_completion_record.get('generation')) is not int or current_completion_record['generation']!=current_payload_generation):
            raise ValueError('DB 원장 완료 응답 또는 반영 세대를 확인할 수 없습니다. 재출력 상태를 확인하세요.')
        with tempfile.TemporaryDirectory(prefix='.receipt-',dir=current_state_directory) as current_temporary_name:
            current_pending_path=Path(current_temporary_name)/'synced.yaml'
            write_content_snapshot_file(current_pending_path,yaml.safe_dump(current_sync_result).encode())
            os.replace(current_pending_path,current_receipt_path)
            sync_content_snapshot_directory(current_state_directory)
        return {**current_completion_record,'ledgerSynced':True,**current_sync_result}
