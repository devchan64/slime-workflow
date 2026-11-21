"""중단된 등록 스프라이트 저장을 변경 없이 확인한다."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import yaml


def read_sprite_pending_file_hash(current_file_path):
    """크기가 제한된 일반 파일의 해시만 읽는다."""
    current_descriptor_value=os.open(current_file_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(current_descriptor_value,'rb') as current_file_handle:
        current_stat_value=os.fstat(current_file_handle.fileno())
        if not stat.S_ISREG(current_stat_value.st_mode) or current_stat_value.st_size>64_000_000:
            raise ValueError('검사 파일 형식 또는 크기 오류')
        current_digest_value=hashlib.sha256()
        current_total_bytes=0
        for current_data_chunk in iter(lambda:current_file_handle.read(1024*1024),b''):
            current_total_bytes+=len(current_data_chunk)
            if current_total_bytes>64_000_000:raise ValueError('검사 파일 크기 초과')
            current_digest_value.update(current_data_chunk)
        current_final_stat=os.fstat(current_file_handle.fileno())
        current_path_stat=os.stat(current_file_path,follow_symlinks=False)
        current_stat_fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
        if any(getattr(current_stat_value,current_field_name)!=getattr(current_final_stat,current_field_name) or getattr(current_final_stat,current_field_name)!=getattr(current_path_stat,current_field_name) for current_field_name in current_stat_fields) or current_total_bytes!=current_final_stat.st_size:
            raise ValueError('검사 중 파일이 변경되었습니다.')
        return current_digest_value.hexdigest()


def load_sprite_pending_alignment(current_asset_root,current_frontend_lock):
    """등록부와 소비자 잠금의 안정적인 읽기를 검증한다."""
    import yaml
    from workflow.common.map_tile_assets import load_registered_tiles, UniqueAssetYamlLoader
    current_registry_path=current_asset_root/'asset-registry.yaml'
    current_registry_hash=read_sprite_pending_file_hash(current_registry_path)
    current_lock_hash=read_sprite_pending_file_hash(current_frontend_lock)
    _,current_registry_records=load_registered_tiles(current_asset_root)
    current_lock_document=yaml.load(current_frontend_lock.read_text(encoding='utf-8'),Loader=UniqueAssetYamlLoader)
    if not isinstance(current_lock_document,dict) or set(current_lock_document)!={'schema_version','repository','files'} or type(current_lock_document['schema_version']) is not int or current_lock_document['schema_version']!=1 or current_lock_document['repository']!='slime-assets' or not isinstance(current_lock_document['files'],list):
        raise ValueError('소비자 잠금 형식 오류')
    current_lock_records={}
    current_target_paths=set()
    for current_lock_record in current_lock_document['files']:
        if not isinstance(current_lock_record,dict) or set(current_lock_record)!={'path','source_path','sha256'} or any(not isinstance(current_lock_record[current_key_name],str) or not current_lock_record[current_key_name] for current_key_name in ('path','source_path')) or not isinstance(current_lock_record['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',current_lock_record['sha256']):raise ValueError('소비자 잠금 항목 오류')
        for current_path_name in ('path','source_path'):
            current_path_text=current_lock_record[current_path_name]
            if not current_path_text.startswith('assets/') or '\\' in current_path_text or '..' in current_path_text.split('/') or '\x00' in current_path_text or any(not current_path_part for current_path_part in current_path_text.split('/')):raise ValueError('소비자 잠금 경로 오류')
        if current_lock_record['source_path'] in current_lock_records or current_lock_record['path'] in current_target_paths:raise ValueError('소비자 잠금 중복')
        current_lock_records[current_lock_record['source_path']]=current_lock_record['sha256']
        current_target_paths.add(current_lock_record['path'])
    if read_sprite_pending_file_hash(current_registry_path)!=current_registry_hash or read_sprite_pending_file_hash(current_frontend_lock)!=current_lock_hash:
        raise ValueError('등록부 또는 잠금이 조회 중 변경되었습니다.')
    return current_registry_records,current_lock_records,current_registry_hash,current_lock_hash


def inspect_hermes_sprite_pending_status():
    """실행 잠금을 확인하고 기록된 파일 및 백업 해시를 비교한다."""
    from workflow.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
    from workflow.domains.character_animation import sprite_sheet_editor, anchor_history
    current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',str(DEFAULT_ASSET_REPOSITORY))).resolve()
    current_local_root=current_asset_root/'.local'
    current_ledger_root=current_local_root/'content-ledger'
    current_lock_path=current_ledger_root/'sprite-asset-update.lock'
    current_marker_path=current_ledger_root/'sprite-update-pending.json'
    current_note_text='조회 시점의 파일과 백업 해시 비교입니다. 복구 가능성이나 전원 장애 후 내구성을 보장하지 않습니다.'
    try:
        if not current_asset_root.is_dir() or current_local_root.is_symlink() or current_ledger_root.is_symlink() or (sprite_sheet_editor.check_sprite_transaction_presence(current_local_root) and not current_local_root.is_dir()) or (sprite_sheet_editor.check_sprite_transaction_presence(current_ledger_root) and not current_ledger_root.is_dir()):raise ValueError('경로 오류')
        if not sprite_sheet_editor.check_sprite_transaction_presence(current_ledger_root):return {'state':'clear','files':[],'note':current_note_text}
        if current_lock_path.is_symlink() or current_marker_path.is_symlink():raise ValueError('잠금 경로 오류')
        if not sprite_sheet_editor.check_sprite_transaction_presence(current_lock_path):
            if sprite_sheet_editor.check_sprite_transaction_presence(current_marker_path):raise ValueError('잠금 파일 없음')
            return {'state':'clear','files':[],'note':current_note_text}
        if not current_lock_path.is_file():raise ValueError('잠금 파일 오류')
        current_descriptor_value=os.open(current_lock_path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            try:fcntl.flock(current_descriptor_value,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return {'state':'busy','files':[],'note':'스프라이트 저장이 진행 중이거나 잠금이 사용 중입니다. 완료 후 다시 확인하세요.'}
            if not sprite_sheet_editor.check_sprite_transaction_presence(current_marker_path):return {'state':'clear','files':[],'note':current_note_text}
            if current_marker_path.stat().st_size>131072:raise ValueError('표시 크기 오류')
            current_marker_value=json.loads(current_marker_path.read_text(encoding='utf-8'))
            if not isinstance(current_marker_value,dict) or set(current_marker_value)!={'version','backup_root','files'} or type(current_marker_value['version']) is not int or current_marker_value['version']!=1 or not isinstance(current_marker_value['backup_root'],str) or not isinstance(current_marker_value['files'],list) or not 1<=len(current_marker_value['files'])<=32:raise ValueError('표시 형식 오류')
            current_backup_root=Path(current_marker_value['backup_root'])
            current_backup_allowed=(sprite_sheet_editor.SPRITE_SHEET_JOB_ROOT.resolve(),(anchor_history.ANCHOR_HISTORY_ROOT.parent/'animation-anchor-transactions').resolve())
            if not current_backup_root.is_absolute() or not any(current_backup_root.resolve().is_relative_to(current_allowed_root) for current_allowed_root in current_backup_allowed) or current_backup_root.name!='before':raise ValueError('백업 경로 오류')
            current_manifest_state='unavailable'
            try:
                current_manifest_path=current_backup_root/'paths.json'
                if os.stat(current_manifest_path,follow_symlinks=False).st_size>131072:raise ValueError('백업 경로 목록 크기 오류')
                current_manifest_before=read_sprite_pending_file_hash(current_manifest_path)
                current_manifest_descriptor=os.open(current_manifest_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                with os.fdopen(current_manifest_descriptor,'rb') as current_manifest_handle:
                    current_manifest_bytes=current_manifest_handle.read(131073)
                if len(current_manifest_bytes)>131072 or hashlib.sha256(current_manifest_bytes).hexdigest()!=current_manifest_before or read_sprite_pending_file_hash(current_manifest_path)!=current_manifest_before:raise ValueError('백업 경로 목록 변경')
                current_manifest_value=json.loads(current_manifest_bytes)
                current_expected_paths=[current_entry_value.get('path') if isinstance(current_entry_value,dict) else None for current_entry_value in current_marker_value['files']]
                current_manifest_state='valid' if isinstance(current_manifest_value,list) and current_manifest_value==current_expected_paths else 'invalid'
            except (OSError,ValueError,TypeError,json.JSONDecodeError):pass
            current_frontend_lock=(current_asset_root.parent/'slime-frontend').resolve()/'sprite-assets.lock.yaml'
            if current_frontend_lock.is_symlink():raise ValueError('프런트 잠금 경로 오류')
            try:current_alignment_records=load_sprite_pending_alignment(current_asset_root,current_frontend_lock)
            except (OSError,ValueError,TypeError,KeyError,yaml.YAMLError):current_alignment_records=None
            current_seen_paths=set()
            current_file_results=[]
            for current_index_value,current_entry_value in enumerate(current_marker_value['files']):
                if not isinstance(current_entry_value,dict) or set(current_entry_value)!={'path','before_sha256','after_sha256','backup_index'} or type(current_entry_value['backup_index']) is not int or current_entry_value['backup_index']!=current_index_value:raise ValueError('파일 항목 오류')
                if any(not isinstance(current_entry_value[current_key_name],str) or not re.fullmatch(r'[a-f0-9]{64}',current_entry_value[current_key_name]) for current_key_name in ('before_sha256','after_sha256')):raise ValueError('해시 오류')
                current_target_path=Path(current_entry_value['path'])
                if not current_target_path.is_absolute() or current_target_path.is_symlink():raise ValueError('대상 경로 오류')
                current_resolved_path=current_target_path.resolve()
                if current_resolved_path in current_seen_paths:raise ValueError('중복 경로')
                current_seen_paths.add(current_resolved_path)
                if current_resolved_path==current_frontend_lock:current_display_path='frontend/sprite-assets.lock.yaml'
                elif current_resolved_path.is_relative_to(current_asset_root) and (current_resolved_path==current_asset_root/'asset-registry.yaml' or current_resolved_path.is_relative_to(current_asset_root/'assets')):current_display_path=current_resolved_path.relative_to(current_asset_root).as_posix()
                else:raise ValueError('대상 경로 이탈')
                current_actual_hash=None
                try:
                    current_actual_hash=read_sprite_pending_file_hash(current_target_path)
                    current_file_state='unchanged' if current_actual_hash==current_entry_value['before_sha256']==current_entry_value['after_sha256'] else 'before' if current_actual_hash==current_entry_value['before_sha256'] else 'after' if current_actual_hash==current_entry_value['after_sha256'] else 'different'
                except (OSError,ValueError):current_file_state='unavailable'
                current_alignment_state='not_applicable'
                if current_display_path.startswith('assets/'):
                    current_alignment_state='unavailable'
                    if current_alignment_records is not None and current_actual_hash is not None:
                        current_registry_record=current_alignment_records[0].get(current_display_path)
                        current_lock_hash=current_alignment_records[1].get(current_display_path)
                        current_alignment_state='matched' if isinstance(current_registry_record,dict) and current_registry_record.get('sha256')==current_actual_hash==current_lock_hash else 'mismatch'
                current_backup_state='unavailable'
                if current_manifest_state=='valid':
                    try:current_backup_state='valid' if read_sprite_pending_file_hash(current_backup_root/str(current_index_value))==current_entry_value['before_sha256'] else 'invalid'
                    except (OSError,ValueError):pass
                current_file_results.append({'path':current_display_path,'current':current_file_state,'backup':current_backup_state,'registry_lock':current_alignment_state})
            if current_alignment_records is not None:
                try:
                    if read_sprite_pending_file_hash(current_asset_root/'asset-registry.yaml')!=current_alignment_records[2] or read_sprite_pending_file_hash(current_frontend_lock)!=current_alignment_records[3]:raise ValueError('조회 중 변경')
                except (OSError,ValueError):
                    for current_file_result in current_file_results:
                        if current_file_result['registry_lock']!='not_applicable':current_file_result['registry_lock']='unavailable'
            return {'state':'pending','backup_manifest':current_manifest_state,'files':current_file_results,'note':current_note_text}
        finally:os.close(current_descriptor_value)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        return {'state':'unavailable','files':[],'note':'중단된 스프라이트 저장 상태를 확인할 수 없습니다. 기록을 보존하고 원본·잠금·백업을 확인하세요.'}
