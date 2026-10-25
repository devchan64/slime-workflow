"""새 이미지 파일을 보존한 후 DB 이미지 참조와 공용 속성을 저장한다."""
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
from PIL import Image
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.domains.map_assets.editor import EDITOR_STORAGE_DIRECTORY
from tools.review.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
from tools.review.common.sprite_display_properties import normalize_sprite_property_precision
from tools.review.domains.map_assets.crop import CROP_ALPHA_THRESHOLD,CROP_REFERENCE_TILE_WIDTH,CROP_REFERENCE_TILE_HEIGHT


def read_database_image_source(current_request_payload):
    current_asset_identifier=current_request_payload['texture']
    current_asset_revisions=json.loads(current_request_payload['revision'])
    current_asset_record=execute_content_api_request('GET','/internal/v1/content/billboards/'+quote(current_asset_identifier,safe=''))
    if current_asset_record['retired'] or current_asset_revisions.get(current_asset_identifier)!=current_asset_record['revision']:
        raise ValueError('선택 이후 에셋이 변경되었습니다. 다시 선택하세요.')
    current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY)).resolve()
    current_image_path=current_asset_root/current_asset_record['image']['path']
    if not current_image_path.resolve().is_relative_to(current_asset_root) or current_image_path.is_symlink() or current_image_path.suffix!='.png':
        raise ValueError('등록된 정적 PNG 경로 오류')
    if current_asset_record['metadata'].get('metadataReferences') or current_image_path.with_suffix('.animation.json').exists():
        raise ValueError('프레임 시트는 지원하지 않습니다.')
    current_image_bytes=current_image_path.read_bytes()
    if hashlib.sha256(current_image_bytes).hexdigest()!=current_asset_record['image']['sha256']:
        raise ValueError('DB 이미지 해시와 원본이 일치하지 않습니다.')
    with Image.open(io.BytesIO(current_image_bytes)) as current_source_image:
        if list(current_source_image.size)!=[current_asset_record['image']['width'],current_asset_record['image']['height']]:
            raise ValueError('DB 이미지 크기와 원본이 일치하지 않습니다.')
    return current_asset_root,current_asset_record,current_image_bytes


def prepare_database_image_request(current_input_record,current_asset_record,current_output_bytes,current_property_values,current_preview_record):
    current_output_hash=hashlib.sha256(current_output_bytes).hexdigest()
    current_original_image=current_asset_record['image']
    if not current_original_image['publishedPath'].endswith('/'+current_original_image['path']):
        raise ValueError('이미지 게시 경로가 등록 경로와 일치하지 않습니다.')
    current_relative_path='assets/billboards/versions/'+current_output_hash+'.png'
    current_image_record={**current_original_image,'version':'sha256-'+current_output_hash,'path':current_relative_path,
        'sha256':current_output_hash,'width':current_preview_record['after'][0],'height':current_preview_record['after'][1],
        'publishedPath':current_original_image['publishedPath'][:-len(current_original_image['path'])]+current_relative_path}
    current_backend_request={'requestId':'image-'+uuid4().hex,'expectedRevision':current_asset_record['revision'],
        'properties':current_property_values,'image':current_image_record}
    current_prepared_record={'input':current_input_record,'assetId':current_asset_record['assetId'],'request':current_backend_request,'preview':current_preview_record}
    current_prepared_bytes=json.dumps(current_prepared_record,sort_keys=True).encode()
    current_preview_token=hashlib.sha256(current_prepared_bytes).hexdigest()
    EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    (EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-image.png')).write_bytes(current_output_bytes)
    (EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-image.json')).write_bytes(current_prepared_bytes)
    return {**current_preview_record,'token':current_preview_token}


def preview_database_image_crop(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture'}:raise ValueError('revision·texture가 필요합니다.')
    current_asset_root,current_asset_record,current_image_bytes=read_database_image_source(current_request_payload)
    current_original_values=current_asset_record['properties']
    if current_original_values.get('billboardAnchorMode')!='tile-intersection':raise ValueError('하단 교차점 방식만 크롭할 수 있습니다.')
    with Image.open(io.BytesIO(current_image_bytes)) as current_source_image:
        current_source_image=current_source_image.convert('RGBA')
        current_crop_bounds=current_source_image.getchannel('A').point(lambda current_alpha_value:255 if current_alpha_value>CROP_ALPHA_THRESHOLD else 0).getbbox()
        if current_crop_bounds is None:raise ValueError('크롭할 불투명 픽셀이 없습니다.')
        current_source_width,current_source_height=current_source_image.size
        current_output_image=current_source_image.crop(current_crop_bounds)
        current_output_stream=io.BytesIO()
        current_output_image.save(current_output_stream,format='PNG')
    current_crop_left,current_crop_top,current_crop_right,current_crop_bottom=current_crop_bounds
    current_pixel_scale=current_original_values['displayHeight']/current_source_height
    current_updated_values=normalize_sprite_property_precision({**current_original_values,
        'displayHeight':current_output_image.height*current_pixel_scale,
        'anchorX':current_original_values['anchorX']+((current_crop_left+current_crop_right-current_source_width)/2)*current_pixel_scale/CROP_REFERENCE_TILE_WIDTH,
        'anchorY':current_original_values['anchorY']+(current_crop_bottom-current_source_height)*current_pixel_scale/CROP_REFERENCE_TILE_HEIGHT})
    current_preview_record={'texture':current_asset_record['assetId'],'changed':current_crop_bounds!=(0,0,current_source_width,current_source_height),
        'before':[current_source_width,current_source_height],'after':list(current_output_image.size),'bounds':list(current_crop_bounds),'properties':current_updated_values}
    return prepare_database_image_request(current_request_payload,current_asset_record,current_output_stream.getvalue(),current_updated_values,current_preview_record)


def save_database_image_change(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture','token'}:raise ValueError('검수한 revision·texture·token이 필요합니다.')
    current_preview_token=current_request_payload['token']
    if not isinstance(current_preview_token,str) or len(current_preview_token)!=64 or any(current_character not in '0123456789abcdef' for current_character in current_preview_token):raise ValueError('이미지 확인 토큰 오류')
    current_prepared_bytes=(EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-image.json')).read_bytes()
    if hashlib.sha256(current_prepared_bytes).hexdigest()!=current_preview_token:raise ValueError('이미지 확인 기록 변경')
    current_prepared_record=json.loads(current_prepared_bytes)
    if current_prepared_record['input']!={current_field_name:current_request_payload[current_field_name] for current_field_name in ('revision','texture')}:
        raise ValueError('이미지 확인 대상이 변경되었습니다.')
    if not current_prepared_record['preview']['changed']:return {**current_prepared_record['preview'],'saved':False}
    current_image_record=current_prepared_record['request']['image']
    current_output_bytes=(EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-image.png')).read_bytes()
    if hashlib.sha256(current_output_bytes).hexdigest()!=current_image_record['sha256']:raise ValueError('검수 이미지 해시 불일치')
    current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY)).resolve()
    current_target_path=current_asset_root/current_image_record['path']
    current_target_path.parent.mkdir(parents=True,exist_ok=True)
    if not current_target_path.resolve().is_relative_to(current_asset_root) or current_target_path.is_symlink():raise ValueError('이미지 저장 경로 이탈')
    # 불변 파일 게시가 먼저 완료된다. DB 실패 시 원본 참조는 유지하고 새 파일은 재시도에 재사용한다.
    current_temporary_path=current_target_path.with_name('.'+uuid4().hex+'.pending')
    try:
        with current_temporary_path.open('xb') as current_image_stream:
            current_image_stream.write(current_output_bytes)
            current_image_stream.flush()
            os.fsync(current_image_stream.fileno())
        try:os.link(current_temporary_path,current_target_path)
        except FileExistsError:
            if current_target_path.read_bytes()!=current_output_bytes:raise ValueError('불변 이미지 경로의 내용이 다릅니다.')
        current_directory_descriptor=os.open(current_target_path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(current_directory_descriptor)
        finally:os.close(current_directory_descriptor)
    finally:
        current_temporary_path.unlink(missing_ok=True)
    current_saved_record=execute_content_api_request('POST','/internal/v1/content/billboards/'+quote(current_prepared_record['assetId'],safe='')+'/image',current_prepared_record['request'])
    return {**current_prepared_record['preview'],**current_saved_record}


def resize_database_asset_image(current_request_payload):
    from tools.review.domains.map_assets.resize import RESIZE_ALLOWED_SIZES
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture','size'}:
        raise ValueError('revision·texture·size가 필요합니다.')
    current_target_size=current_request_payload['size']
    if type(current_target_size) is not int or current_target_size not in RESIZE_ALLOWED_SIZES:raise ValueError('지원하지 않는 축소 크기')
    current_input_record={current_field_name:current_request_payload[current_field_name] for current_field_name in ('revision','texture')}
    current_resize_key=hashlib.sha256(json.dumps(current_request_payload,sort_keys=True).encode()).hexdigest()
    current_resize_receipt=EDITOR_STORAGE_DIRECTORY/(current_resize_key+'-resize.json')
    if current_resize_receipt.exists():
        current_previous_request=json.loads(current_resize_receipt.read_text())
        return save_database_image_change(current_previous_request)
    current_asset_root,current_asset_record,current_image_bytes=read_database_image_source(current_input_record)
    with Image.open(io.BytesIO(current_image_bytes)) as current_source_image:
        if current_target_size>max(current_source_image.size):raise ValueError('원본보다 확대할 수 없습니다.')
        current_scale_ratio=current_target_size/max(current_source_image.size)
        current_output_size=tuple(max(1,round(current_dimension_value*current_scale_ratio)) for current_dimension_value in current_source_image.size)
        current_output_stream=io.BytesIO()
        current_source_image.convert('RGBA').resize(current_output_size,Image.Resampling.LANCZOS).save(current_output_stream,format='PNG')
        current_preview_record={'texture':current_asset_record['assetId'],'changed':current_source_image.size!=current_output_size,
            'before':list(current_source_image.size),'after':list(current_output_size),'properties':current_asset_record['properties']}
    current_prepared_record=prepare_database_image_request(current_input_record,current_asset_record,current_output_stream.getvalue(),current_asset_record['properties'],current_preview_record)
    current_confirm_record={**current_input_record,'token':current_prepared_record['token']}
    current_resize_receipt.write_text(json.dumps(current_confirm_record,sort_keys=True))
    return save_database_image_change(current_confirm_record)


def read_database_published_image(current_image_digest):
    """DB에 등록된 불변 이미지 버전만 원본 저장소에서 제공한다."""
    import re
    if re.fullmatch(r'[0-9a-f]{64}',current_image_digest) is None:
        raise ValueError('이미지 SHA-256 형식 오류')
    current_image_record=execute_content_api_request('GET','/internal/v1/content/images/'+current_image_digest)
    current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY)).resolve()
    current_image_path=(current_asset_root/current_image_record['path']).resolve()
    if not current_image_path.is_relative_to(current_asset_root) or current_image_path.suffix!='.png':
        raise ValueError('등록된 이미지 경로 이탈 또는 형식 오류')
    current_image_bytes=current_image_path.read_bytes()
    if hashlib.sha256(current_image_bytes).hexdigest()!=current_image_digest:
        raise ValueError('등록된 이미지 해시와 원본이 일치하지 않습니다.')
    return current_image_bytes,'image/png'
