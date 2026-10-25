"""완성된 스냅샷 파일을 검증하고 DB 복구 입력으로 재구성한다."""
import hashlib
from pathlib import Path, PurePosixPath
import re
from tools.review.domains.map_assets.database_snapshot import encode_content_snapshot_payload
from tools.review.maintenance.sync_billboard_catalog import load_unique_yaml_document

CONTENT_SNAPSHOT_HASH_PATTERN = re.compile(r'[0-9a-f]{64}')


def read_verified_snapshot_payload(current_snapshot_root):
    current_snapshot_root=Path(current_snapshot_root).resolve(strict=True)
    current_manifest_path=current_snapshot_root/'current.yaml'
    if current_manifest_path.is_symlink():
        raise ValueError('스냅샷 manifest는 심볼릭 링크일 수 없습니다.')
    current_manifest_record=load_unique_yaml_document(current_manifest_path)
    if not isinstance(current_manifest_record,dict) or set(current_manifest_record)!={'schema_version','generation','payloadHash','files'}:
        raise ValueError('스냅샷 manifest 필드 오류')
    if type(current_manifest_record['schema_version']) is not int or current_manifest_record['schema_version']!=1:
        raise ValueError('지원하지 않는 스냅샷 버전')
    current_generation_number=current_manifest_record['generation']
    current_payload_hash=current_manifest_record['payloadHash']
    if type(current_generation_number) is not int or current_generation_number<1 or not isinstance(current_payload_hash,str) or not CONTENT_SNAPSHOT_HASH_PATTERN.fullmatch(current_payload_hash):
        raise ValueError('스냅샷 세대·해시 오류')
    current_generation_name=f'generation-{current_generation_number}-{current_payload_hash[:16]}'
    current_file_records=current_manifest_record['files']
    if not isinstance(current_file_records,list) or not current_file_records:
        raise ValueError('스냅샷 파일 목록 오류')
    current_loaded_documents={}
    for current_file_record in current_file_records:
        if not isinstance(current_file_record,dict) or set(current_file_record)!={'path','sha256'} or not isinstance(current_file_record['path'],str):
            raise ValueError('스냅샷 파일 항목 오류')
        current_relative_path=PurePosixPath(current_file_record['path'])
        if current_relative_path.is_absolute() or '..' in current_relative_path.parts or len(current_relative_path.parts)<2 or current_relative_path.parts[0]!=current_generation_name:
            raise ValueError('스냅샷 경로·세대 불일치')
        current_document_name='/'.join(current_relative_path.parts[1:])
        if current_document_name in current_loaded_documents:
            raise ValueError('중복 스냅샷 파일')
        current_file_path=current_snapshot_root.joinpath(*current_relative_path.parts)
        if any(current_parent_path.is_symlink() for current_parent_path in (current_file_path,*current_file_path.parents) if current_parent_path!=current_snapshot_root and current_parent_path.is_relative_to(current_snapshot_root)):
            raise ValueError('스냅샷 파일 경로에 심볼릭 링크가 있습니다.')
        if hashlib.sha256(current_file_path.read_bytes()).hexdigest()!=current_file_record['sha256']:
            raise ValueError('스냅샷 파일 해시 불일치: '+current_document_name)
        current_loaded_documents[current_document_name]=load_unique_yaml_document(current_file_path)
    if not {'types.yaml','building-properties.yaml','asset-order.yaml','map-revisions.yaml'}<=current_loaded_documents.keys():
        raise ValueError('스냅샷 필수 문서 누락')
    current_type_records=current_loaded_documents.pop('types.yaml')
    current_building_properties=current_loaded_documents.pop('building-properties.yaml')
    current_map_revisions=current_loaded_documents.pop('map-revisions.yaml')
    current_asset_order=current_loaded_documents.pop('asset-order.yaml')
    if not isinstance(current_type_records,dict) or not current_type_records:
        raise ValueError('스냅샷 에셋 분류 오류')
    current_asset_records=[]
    for current_type_identifier in current_type_records:
        if not isinstance(current_type_identifier,str) or not re.fullmatch('[a-z0-9-]+',current_type_identifier):
            raise ValueError('스냅샷 에셋 분류 ID 오류')
        current_partition_record=current_loaded_documents.pop('billboards/'+current_type_identifier+'.yaml',None)
        if not isinstance(current_partition_record,dict) or set(current_partition_record)!={'schema_version','category','assets'} or current_partition_record['schema_version']!=1 or current_partition_record['category']!=current_type_identifier or not isinstance(current_partition_record['assets'],list):
            raise ValueError('스냅샷 에셋 분류 문서 오류')
        if any(not isinstance(current_asset_record,dict) or current_asset_record.get('assetType')!=current_type_identifier for current_asset_record in current_partition_record['assets']):
            raise ValueError('스냅샷 에셋 분류 불일치')
        current_asset_records.extend(current_partition_record['assets'])
    current_asset_lookup={current_asset_record['assetId']:current_asset_record for current_asset_record in current_asset_records}
    if not isinstance(current_asset_order,list) or not all(isinstance(current_asset_identifier,str) for current_asset_identifier in current_asset_order) or len(current_asset_lookup)!=len(current_asset_records) or len(set(current_asset_order))!=len(current_asset_order) or set(current_asset_order)!=set(current_asset_lookup):
        raise ValueError('스냅샷 에셋 순서·ID 중복·누락 오류')
    current_map_documents={}
    for current_document_name,current_document_record in current_loaded_documents.items():
        if not current_document_name.startswith('maps/') or not current_document_name.endswith('.yaml'):
            raise ValueError('알 수 없는 스냅샷 문서: '+current_document_name)
        current_map_documents[current_document_name[5:]]=current_document_record
    current_payload_record={'schemaVersion':1,'generation':current_generation_number,'types':current_type_records,
        'assets':[current_asset_lookup[current_asset_identifier] for current_asset_identifier in current_asset_order],
        'mapDocuments':current_map_documents,'mapRevisions':current_map_revisions,'buildingProperties':current_building_properties}
    if hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()!=current_payload_hash:
        raise ValueError('스냅샷 전체 내용 해시 불일치')
    return current_payload_record
