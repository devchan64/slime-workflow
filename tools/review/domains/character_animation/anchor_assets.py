"""등록 애니메이션의 앵커와 소비 해시를 함께 갱신한다."""
from pathlib import Path
from hashlib import sha256
import json
import os
import yaml
from tools.review.common.map_tile_assets import load_registered_tiles, UniqueAssetYamlLoader
from tools.review.domains.character_animation.sprite_sheet_editor import SPRITE_SHEET_UPDATE_LOCK


def apply_registered_anchor_document(current_document_record, current_history_directory):
    """원본 일치 검사 후 좌표를 반영하며 실패하면 파일을 복원한다."""
    with SPRITE_SHEET_UPDATE_LOCK:
        current_asset_root,current_asset_records=load_registered_tiles()
        current_lock_path=current_asset_root.parent/'slime-frontend/sprite-assets.lock.yaml'
        current_lock_document=yaml.load(current_lock_path.read_text(),Loader=UniqueAssetYamlLoader)
        current_source_record=current_document_record['source']
        current_matching_records=[]
        for current_lock_record in current_lock_document['files']:
            current_relative_path=current_lock_record['source_path']
            if not current_relative_path.endswith('.animation.json'):continue
            current_metadata_path=(current_asset_root/current_relative_path).resolve()
            if not current_metadata_path.is_relative_to(current_asset_root):raise ValueError('등록 애니메이션 경로 이탈')
            current_metadata_bytes=current_metadata_path.read_bytes()
            current_metadata_record=json.loads(current_metadata_bytes)
            if current_metadata_record.get('animationId')!=current_source_record['animationId']:continue
            if sha256(current_metadata_bytes).hexdigest()!=current_lock_record['sha256'] or current_asset_records[current_relative_path]['sha256']!=current_lock_record['sha256']:raise ValueError('등록 애니메이션 해시 불일치')
            current_matching_records.append((current_metadata_path,current_metadata_record,current_relative_path))
        if len(current_matching_records)!=1:raise ValueError('등록 애니메이션 원본이 정확히 하나여야 합니다.')
        current_metadata_path,current_metadata_record,current_relative_path=current_matching_records[0]
        if current_metadata_record['version']!=current_source_record['animationVersion']:raise ValueError('에셋 버전이 변경되었습니다. 검수 화면을 새로고침하세요.')
        if current_document_record['coordinateMode']!='anchor':raise ValueError('등록 에셋에는 최종 앵커 모드만 저장할 수 있습니다.')
        for current_sheet_record in current_source_record['sheets']:
            current_sheet_path=(current_metadata_path.parent/current_sheet_record['image']).resolve()
            if current_sheet_path.parent!=current_metadata_path.parent:raise ValueError('시트 경로 이탈')
            current_sheet_relative=current_sheet_path.relative_to(current_asset_root).as_posix()
            if current_sheet_relative not in current_asset_records or sha256(current_sheet_path.read_bytes()).hexdigest()!=current_sheet_record['sha256'] or current_asset_records[current_sheet_relative]['sha256']!=current_sheet_record['sha256']:raise ValueError('원본 시트가 변경되었습니다. 다시 불러오세요.')
        current_frame_lookup={current_frame_record['frameId']:current_frame_record for current_frame_record in current_document_record['frames']}
        if set(current_frame_lookup)!={current_frame_record['frameId'] for current_frame_record in current_metadata_record['frames']}:raise ValueError('원본 프레임 구성이 다릅니다.')
        for current_frame_record in current_metadata_record['frames']:
            current_saved_frame=current_frame_lookup[current_frame_record['frameId']]
            if current_frame_record['rect']!=current_saved_frame['rect']:raise ValueError('원본 프레임 영역이 다릅니다.')
            current_frame_record['anchor']=current_saved_frame['anchor'].copy()
        current_next_version='anchor-'+current_history_directory.name
        current_metadata_record['version']=current_next_version
        current_metadata_bytes=(json.dumps(current_metadata_record,ensure_ascii=False,indent=2)+'\n').encode()
        current_registry_path=current_asset_root/'asset-registry.yaml'
        current_registry_document=yaml.load(current_registry_path.read_text(),Loader=UniqueAssetYamlLoader)
        current_metadata_digest=sha256(current_metadata_bytes).hexdigest()
        for current_registry_record in current_registry_document['assets']:
            if current_registry_record['path']==current_relative_path:
                current_registry_record['version']=current_next_version
                current_registry_record['sha256']=current_metadata_digest
        for current_lock_record in current_lock_document['files']:
            if current_lock_record['source_path']==current_relative_path:current_lock_record['sha256']=current_metadata_digest
        current_pending_files={current_metadata_path:current_metadata_bytes,current_registry_path:yaml.safe_dump(current_registry_document,allow_unicode=True,sort_keys=False).encode(),current_lock_path:yaml.safe_dump(current_lock_document,allow_unicode=True,sort_keys=False).encode()}
        current_previous_files={current_file_path:current_file_path.read_bytes() for current_file_path in current_pending_files}
        current_backup_directory=current_history_directory/'before'
        current_backup_directory.mkdir()
        (current_backup_directory/'paths.json').write_text(json.dumps([str(current_file_path) for current_file_path in current_previous_files]))
        for current_file_index,current_file_bytes in enumerate(current_previous_files.values()):(current_backup_directory/str(current_file_index)).write_bytes(current_file_bytes)
        try:
            for current_file_path,current_file_bytes in current_pending_files.items():
                current_temporary_path=current_file_path.with_name(current_file_path.name+'.anchor-update')
                current_temporary_path.write_bytes(current_file_bytes)
                os.replace(current_temporary_path,current_file_path)
        except Exception:
            for current_file_path,current_file_bytes in current_previous_files.items():current_file_path.write_bytes(current_file_bytes)
            raise
        return {'version':current_next_version,'path':current_relative_path,'sha256':current_metadata_digest}


def publish_registered_anchor_review():
    """현재 채택 UI 번들을 유지하며 등록 애니메이션 검수를 재게시한다."""
    from tools.review.build_frontend_review import build_frontend_review
    current_workflow_root=Path(__file__).resolve().parents[4]
    current_bundle_record=json.loads((current_workflow_root/'.tmp/ui-review/latest.json').read_text())
    current_asset_root,_=load_registered_tiles()
    build_frontend_review(current_asset_root.parent/'slime-frontend',Path(current_bundle_record['snapshotBundle']))
