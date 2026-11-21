"""중단된 야외 맵 저장의 백업 상태를 읽기 전용으로 확인한다."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re


def require_map_observer_presence(current_path_value):
    """실제 부재와 확인 오류를 구분한다."""
    try:
        current_path_value.lstat()
    except FileNotFoundError:
        return False
    return True


def read_bounded_map_pending_bytes(current_file_path):
    """표식과 목록은 열기 이후 크기가 바뀌어도 상한까지만 읽는다."""
    current_descriptor_value=os.open(current_file_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(current_descriptor_value,'rb') as current_file_handle:
        current_file_bytes=current_file_handle.read(131073)
    if len(current_file_bytes)>131072:
        raise ValueError('맵 저장 표식 크기 초과')
    return current_file_bytes


def inspect_hermes_map_pending_status():
    from tools.management.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
    from tools.management.domains.hermes_agent.sprite_pending_observer import read_sprite_pending_file_hash
    from tools.management.domains.map_assets.map_editor import MAP_EDITOR_STORAGE_ROOT
    current_root_path=MAP_EDITOR_STORAGE_ROOT
    current_marker_path=current_root_path/'map-save-pending.json'
    current_lock_path=current_root_path/'save.lock'
    current_note_text='백업과 현재 파일의 조회 시점 해시 비교이며 복구 또는 전원 장애 후 내구성을 보장하지 않습니다.'
    try:
        if current_root_path.is_symlink() or current_marker_path.is_symlink() or current_lock_path.is_symlink():raise ValueError('경로 오류')
        if not require_map_observer_presence(current_root_path):return {'state':'clear','note':current_note_text}
        if not current_root_path.is_dir():raise ValueError('경로 오류')
        if not require_map_observer_presence(current_lock_path):
            if require_map_observer_presence(current_marker_path):raise ValueError('잠금 파일 없음')
            return {'state':'clear','note':current_note_text}
        current_lock_descriptor=os.open(current_lock_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            try:fcntl.flock(current_lock_descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return {'state':'busy','note':'야외 맵 저장 잠금이 사용 중입니다.'}
            if not require_map_observer_presence(current_marker_path):return {'state':'clear','note':current_note_text}
            current_marker_hash=read_sprite_pending_file_hash(current_marker_path)
            current_marker_bytes=read_bounded_map_pending_bytes(current_marker_path)
            if len(current_marker_bytes)>131072 or hashlib.sha256(current_marker_bytes).hexdigest()!=current_marker_hash:raise ValueError('표시 오류')
            current_marker_record=json.loads(current_marker_bytes)
            if not isinstance(current_marker_record,dict) or type(current_marker_record.get('version')) is not int or current_marker_record['version'] not in (1,2) or set(current_marker_record)!=({'version','map','backup','before_sha256'} if current_marker_record['version']==1 else {'version','map','backup','before_sha256','after_sha256'}) or not isinstance(current_marker_record['map'],str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_marker_record['map']) or not isinstance(current_marker_record['backup'],str) or not re.fullmatch(r'[a-f0-9]{64}-backup',current_marker_record['backup']) or not isinstance(current_marker_record['before_sha256'],list) or not 1<=len(current_marker_record['before_sha256'])<=128 or any(not isinstance(current_hash_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_hash_value) for current_hash_value in current_marker_record['before_sha256']):raise ValueError('표시 형식 오류')
            current_after_hashes=current_marker_record.get('after_sha256',[None]*len(current_marker_record['before_sha256']))
            if not isinstance(current_after_hashes,list) or len(current_after_hashes)!=len(current_marker_record['before_sha256']) or any(current_hash_value is not None and (not isinstance(current_hash_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_hash_value)) for current_hash_value in current_after_hashes):raise ValueError('저장 결과 해시 오류')
            current_backup_path=current_root_path/current_marker_record['backup']
            if current_backup_path.is_symlink() or not current_backup_path.is_dir():raise ValueError('백업 경로 오류')
            current_manifest_path=current_backup_path/'paths.json'
            current_manifest_hash=read_sprite_pending_file_hash(current_manifest_path)
            current_manifest_bytes=read_bounded_map_pending_bytes(current_manifest_path)
            if len(current_manifest_bytes)>131072 or hashlib.sha256(current_manifest_bytes).hexdigest()!=current_manifest_hash:raise ValueError('백업 목록 오류')
            current_manifest_records=json.loads(current_manifest_bytes)
            if not isinstance(current_manifest_records,list) or len(current_manifest_records)!=len(current_marker_record['before_sha256']) or any(not isinstance(current_path_text,str) for current_path_text in current_manifest_records):raise ValueError('백업 목록 형식 오류')
            current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',str(DEFAULT_ASSET_REPOSITORY))).resolve()
            current_backend_lock=current_asset_root.parent/'slime-backend/map-data.lock.yaml'
            current_seen_paths=set()
            current_valid_backups=0
            current_invalid_backups=0
            current_unknown_backups=0
            current_changed_files=0
            current_unknown_files=0
            current_file_results=[]
            for current_index_value,(current_path_text,current_hash_value) in enumerate(zip(current_manifest_records,current_marker_record['before_sha256'])):
                current_target_path=Path(current_path_text)
                if not current_target_path.is_absolute() or current_target_path.is_symlink():raise ValueError('대상 경로 오류')
                current_resolved_path=current_target_path.resolve()
                if current_resolved_path in current_seen_paths or not (current_resolved_path==current_backend_lock or current_resolved_path==current_asset_root/'asset-registry.yaml' or current_resolved_path.is_relative_to(current_asset_root/'assets/maps') or current_resolved_path.is_relative_to(current_asset_root/'assets/billboards')):raise ValueError('대상 범위 오류')
                current_seen_paths.add(current_resolved_path)
                current_display_path='backend/map-data.lock.yaml' if current_resolved_path==current_backend_lock else current_resolved_path.relative_to(current_asset_root).as_posix()
                try:
                    if read_sprite_pending_file_hash(current_backup_path/str(current_index_value))==current_hash_value:
                        current_backup_status='valid'
                        current_valid_backups+=1
                    else:
                        current_backup_status='invalid'
                        current_invalid_backups+=1
                except (OSError,ValueError):
                    current_backup_status='unavailable'
                    current_unknown_backups+=1
                try:
                    current_actual_hash=read_sprite_pending_file_hash(current_target_path)
                    if current_actual_hash!=current_hash_value:
                        current_file_status='after' if current_after_hashes[current_index_value] is not None and current_actual_hash==current_after_hashes[current_index_value] else 'changed'
                        current_changed_files+=1
                    else:current_file_status='before'
                except (OSError,ValueError):
                    current_file_status='unavailable'
                    current_unknown_files+=1
                current_file_results.append({'path':current_display_path,'current':current_file_status,'backup':current_backup_status})
            if read_sprite_pending_file_hash(current_marker_path)!=current_marker_hash or read_sprite_pending_file_hash(current_manifest_path)!=current_manifest_hash:raise ValueError('조회 중 변경')
            return {'state':'pending','map':current_marker_record['map'],'files':len(current_manifest_records),'backup_valid':current_valid_backups,'backup_invalid':current_invalid_backups,'backup_unavailable':current_unknown_backups,'changed_since_backup':current_changed_files,'current_unavailable':current_unknown_files,'file_details':current_file_results,'note':current_note_text}
        finally:os.close(current_lock_descriptor)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        return {'state':'unavailable','note':'중단된 야외 맵 저장 상태를 확인할 수 없습니다. 기록을 보존하고 원본과 백업을 확인하세요.'}
