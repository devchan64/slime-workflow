"""승인된 기본 걷기의 오픈포즈 PNG 24장과 외부 등록 정보를 검증한다."""
from pathlib import Path
import hashlib
from datetime import datetime
import traceback
import yaml
from resolve_default_rig import UniqueConfigLoader

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOOP_CONFIG = WORKFLOW_REPO_ROOT / 'generators/animation/config/default_walk_loop.yaml'


def resolve_default_loop():
    selected_asset_config=yaml.load(DEFAULT_LOOP_CONFIG.read_text(),Loader=UniqueConfigLoader)
    if not isinstance(selected_asset_config,dict) or set(selected_asset_config)!={'asset_id','version','artifact_sha256'}:
        raise ValueError('기본 루프 설정 필드 불일치')
    if selected_asset_config['asset_id']!='five-head-walk-6f' or type(selected_asset_config['version']) is not int or selected_asset_config['version']<1:
        raise ValueError('기본 루프 식별자·버전 오류')
    asset_manifest_hash=selected_asset_config['artifact_sha256']
    if not isinstance(asset_manifest_hash,str) or len(asset_manifest_hash)!=64 or any(hash_character_value not in '0123456789abcdef' for hash_character_value in asset_manifest_hash):
        raise ValueError('루프 manifest 해시 형식 오류')
    asset_directory_path=WORKFLOW_REPO_ROOT/'assets/animation-loops'/selected_asset_config['asset_id']/f"v{selected_asset_config['version']}"
    asset_manifest_path=WORKFLOW_REPO_ROOT/'generators/animation/config/default_walk_loop.artifact.yaml'
    if hashlib.sha256(asset_manifest_path.read_bytes()).hexdigest()!=asset_manifest_hash:
        raise ValueError('루프 manifest 해시 불일치')
    asset_manifest_record=yaml.load(asset_manifest_path.read_text(),Loader=UniqueConfigLoader)
    expected_manifest_fields={'asset_id','version','status','source_motion','source_rig','compatibility','files','regeneration'}
    if not isinstance(asset_manifest_record,dict) or set(asset_manifest_record)!=expected_manifest_fields:
        raise ValueError('포즈 등록 필드 불일치')
    expected_pose_paths={f'{current_direction_name}/openpose-{current_frame_number:04d}.png' for current_direction_name in ('down_left','down_right','up_left','up_right') for current_frame_number in range(1,7)}
    if not isinstance(asset_manifest_record['files'],dict) or set(asset_manifest_record['files'])!=expected_pose_paths:
        raise ValueError('4방향 × 6프레임 포즈 파일 계약 불일치')
    actual_pose_paths={str(current_file_path.relative_to(asset_directory_path)) for current_file_path in asset_directory_path.rglob('*') if current_file_path.is_file()}
    if actual_pose_paths!=expected_pose_paths:
        raise ValueError('오픈포즈맵 이외 파일 또는 누락 파일이 있습니다')
    if (asset_manifest_record['asset_id'],asset_manifest_record['version'],asset_manifest_record['status'])!=(selected_asset_config['asset_id'],selected_asset_config['version'],'user_accepted'):
        raise ValueError('루프 승인 상태 또는 등록 식별자 불일치')
    for asset_file_name,expected_file_hash in asset_manifest_record['files'].items():
        asset_file_path=(asset_directory_path/asset_file_name).resolve()
        if not asset_file_path.is_relative_to(asset_directory_path.resolve()): raise ValueError('등록 경로 범위 오류')
        if hashlib.sha256(asset_file_path.read_bytes()).hexdigest()!=expected_file_hash:
            raise ValueError(f'재사용 루프 파일 해시 불일치: {asset_file_name}')
    return asset_directory_path


if __name__=='__main__':
    validation_log_path=WORKFLOW_REPO_ROOT/'.result/workflow/logs/default-walk-loop.log'
    validation_log_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        selected_loop_directory=resolve_default_loop()
        validation_trace_line=f'{datetime.now().isoformat()}/walk-loop/verified {selected_loop_directory}\n'
    except Exception:
        validation_trace_line=f'{datetime.now().isoformat()}/walk-loop/failure {traceback.format_exc()}\n'
        with validation_log_path.open('a') as validation_log_handle: validation_log_handle.write(validation_trace_line)
        print(validation_trace_line,flush=True)
        raise
    with validation_log_path.open('a') as validation_log_handle: validation_log_handle.write(validation_trace_line)
    print(validation_trace_line,flush=True)
