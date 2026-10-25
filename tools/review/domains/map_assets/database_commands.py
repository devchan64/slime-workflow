"""콘텐츠 DB 시드·스냅샷의 공용 게이트웨이 명령."""
import os
from pathlib import Path
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.domains.map_assets.database_seed import build_billboard_database_seed, build_map_database_seed
from tools.review.domains.map_assets.database_snapshot import execute_content_snapshot_cycle
from tools.review.domains.map_assets.database_restore import read_verified_snapshot_payload
from tools.review.domains.map_assets.database_snapshot import encode_content_snapshot_payload
import hashlib


def execute_content_database_command(current_command_name,current_request_payload):
    if current_command_name=='database-restore':
        if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'snapshotRoot'} or not isinstance(current_request_payload['snapshotRoot'],str) or not Path(current_request_payload['snapshotRoot']).is_absolute():
            raise ValueError('snapshotRoot 절대 경로가 필요합니다.')
        current_snapshot_payload=read_verified_snapshot_payload(current_request_payload['snapshotRoot'])
        return execute_content_api_request('POST','/internal/v1/content/snapshots/restore',{'payload':current_snapshot_payload,
            'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_snapshot_payload)).hexdigest()})
    if current_command_name=='database-seed':
        if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'assetRoot','publicAssetPrefix'}:
            raise ValueError('assetRoot·publicAssetPrefix가 필요합니다.')
        current_seed_bundle=build_billboard_database_seed(current_request_payload['assetRoot'],current_request_payload['publicAssetPrefix'])
        current_map_bundle=build_map_database_seed(current_request_payload['assetRoot'])
        return execute_content_api_request('POST','/internal/v1/content/seed/bundle',
            {'billboards':current_seed_bundle,'maps':current_map_bundle})
    if current_request_payload!={}:
        raise ValueError('이 명령은 빈 payload를 사용합니다.')
    if current_command_name=='database-status':
        return execute_content_api_request('GET','/internal/v1/content/status')
    if current_command_name=='database-snapshot':
        current_snapshot_root=os.environ.get('SLIME_CONTENT_SNAPSHOT_ROOT')
        if not current_snapshot_root or not Path(current_snapshot_root).is_absolute():
            raise ValueError('SLIME_CONTENT_SNAPSHOT_ROOT에 절대 경로를 지정하세요.')
        return execute_content_snapshot_cycle(current_snapshot_root)
    raise ValueError('지원하지 않는 콘텐츠 DB 명령')
