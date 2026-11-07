"""스프라이트 프레임 크롭과 앵커 정렬 결과를 별도 작업으로 저장한다."""
import base64
import binascii
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from PIL import Image
from tools.review.common.generation_records import write_record_atomically

SPRITE_SHEET_JOB_ROOT = Path(__file__).resolve().parents[4] / '.tmp/test/sprite-sheet-editor'
SPRITE_SHEET_IMAGE_LIMIT = 8_000_000
SPRITE_SHEET_PIXEL_LIMIT = 16_777_216
SPRITE_SHEET_FRAME_LIMIT = 128
SPRITE_BASELINE_ROOT = Path(__file__).resolve().parents[4] / 'baseline/character-baselines'


def execute_sprite_sheet_export(command_payload_value):
    if not isinstance(command_payload_value, dict) or set(command_payload_value) not in ({'image','frames','columns'}, {'image','frames','columns','sourceFrames'}):
        raise ValueError('시트 내보내기 입력 필드가 올바르지 않습니다.')
    try:
        current_image_bytes = base64.b64decode(command_payload_value['image'], validate=True)
    except (ValueError, TypeError, binascii.Error) as current_decode_error:
        raise ValueError('PNG 이미지의 base64 형식이 올바르지 않습니다.') from current_decode_error
    if not current_image_bytes or len(current_image_bytes) > SPRITE_SHEET_IMAGE_LIMIT:
        raise ValueError('PNG 이미지는 8MB 이하여야 합니다.')
    with Image.open(BytesIO(current_image_bytes)) as current_source_image:
        if current_source_image.format != 'PNG' or current_source_image.width * current_source_image.height > SPRITE_SHEET_PIXEL_LIMIT or getattr(current_source_image, 'n_frames', 1) != 1:
            raise ValueError('단일 프레임 PNG와 1600만 픽셀 이하 이미지만 지원합니다.')
        current_source_image.load()
        current_source_image = current_source_image.convert('RGBA')
    current_frame_records = command_payload_value['frames']
    if not isinstance(current_frame_records, list) or not 1 <= len(current_frame_records) <= SPRITE_SHEET_FRAME_LIMIT:
        raise ValueError('프레임은 1~128개여야 합니다.')
    current_column_count=command_payload_value['columns']
    if type(current_column_count) is not int or not 1<=current_column_count<=SPRITE_SHEET_FRAME_LIMIT:raise ValueError('출력 열 수 범위 오류')
    current_source_bounds = command_payload_value.get('sourceFrames')
    if current_source_bounds is not None:
        if not isinstance(current_source_bounds,list) or len(current_source_bounds)!=len(current_frame_records):
            raise ValueError('원본 셀 경계 수가 프레임 수와 다릅니다.')
        for current_source_bound in current_source_bounds:
            if not isinstance(current_source_bound,list) or len(current_source_bound)!=4 or any(type(current_bound_value) is not int for current_bound_value in current_source_bound):
                raise ValueError('원본 셀 경계는 정수 4개여야 합니다.')
            current_bound_left,current_bound_top,current_bound_width,current_bound_height=current_source_bound
            if not (current_bound_left>=0 and current_bound_top>=0 and current_bound_width>0 and current_bound_height>0 and current_bound_left+current_bound_width<=current_source_image.width and current_bound_top+current_bound_height<=current_source_image.height):
                raise ValueError('원본 셀 경계가 이미지 범위를 벗어났습니다.')
    current_output_frames = []
    for current_frame_index, current_frame_record in enumerate(current_frame_records):
        if not isinstance(current_frame_record,dict) or set(current_frame_record) != {'x','y','width','height','anchorX','anchorY'} or any(type(current_frame_record[current_field_name]) is not int for current_field_name in current_frame_record):
            raise ValueError(f'{current_frame_index+1}번 프레임 좌표는 정수여야 합니다.')
        current_left, current_top = current_frame_record['x'], current_frame_record['y']
        current_width, current_height = current_frame_record['width'], current_frame_record['height']
        current_frame_anchor_x, current_frame_anchor_y = current_frame_record['anchorX'], current_frame_record['anchorY']
        if not (current_width > 0 and current_height > 0 and abs(current_left)<=SPRITE_SHEET_PIXEL_LIMIT and abs(current_top)<=SPRITE_SHEET_PIXEL_LIMIT and 0 <= current_frame_anchor_x < current_width and 0 <= current_frame_anchor_y < current_height):
            raise ValueError(f'{current_frame_index+1}번 프레임 크롭 또는 앵커가 원본 범위를 벗어났습니다.')
        current_output_frames.append({'frameId':f'frame.{current_frame_index}','rect':{'x':0,'y':0,'width':current_width,'height':current_height},'anchor':{'x':current_frame_anchor_x,'y':current_frame_anchor_y},'source':current_frame_record})
    current_sheet_width=0
    current_sheet_height=0
    for current_row_start in range(0,len(current_output_frames),current_column_count):
        current_row_frames=current_output_frames[current_row_start:current_row_start+current_column_count]
        current_row_width=0
        for current_frame_record in current_row_frames:
            current_frame_record['rect']['x']=current_row_width
            current_frame_record['rect']['y']=current_sheet_height
            current_row_width+=current_frame_record['rect']['width']
        current_sheet_width=max(current_sheet_width,current_row_width)
        current_sheet_height+=max(current_frame_record['rect']['height'] for current_frame_record in current_row_frames)
    if current_sheet_width*current_sheet_height>SPRITE_SHEET_PIXEL_LIMIT:raise ValueError('출력 시트는 1600만 픽셀 이하여야 합니다.')
    current_output_image=Image.new('RGBA',(current_sheet_width,current_sheet_height))
    for current_frame_index,current_frame_record in enumerate(current_output_frames):
        current_source_rect=current_frame_record['source']
        current_bound_left,current_bound_top,current_bound_width,current_bound_height=current_source_bounds[current_frame_index] if current_source_bounds is not None else (0,0,current_source_image.width,current_source_image.height)
        current_clip_left=max(current_source_rect['x'],current_bound_left)
        current_clip_top=max(current_source_rect['y'],current_bound_top)
        current_clip_right=min(current_source_rect['x']+current_source_rect['width'],current_bound_left+current_bound_width)
        current_clip_bottom=min(current_source_rect['y']+current_source_rect['height'],current_bound_top+current_bound_height)
        if current_clip_right>current_clip_left and current_clip_bottom>current_clip_top:
            current_output_image.paste(current_source_image.crop((current_clip_left,current_clip_top,current_clip_right,current_clip_bottom)),(current_frame_record['rect']['x']+current_clip_left-current_source_rect['x'],current_frame_record['rect']['y']+current_clip_top-current_source_rect['y']))
    current_output_stream = BytesIO()
    current_output_image.save(current_output_stream,format='PNG')
    current_output_bytes = current_output_stream.getvalue()
    current_identifier = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid4().hex[:8]
    current_job_directory = SPRITE_SHEET_JOB_ROOT / current_identifier[:19] / current_identifier
    current_job_directory.mkdir(parents=True,exist_ok=False)
    current_coordinate_map = {'schemaVersion':1,'image':'sprite-sheet.png','sheet':{'width':current_output_image.width,'height':current_output_image.height},'sourceSha256':sha256(current_image_bytes).hexdigest(),'sha256':sha256(current_output_bytes).hexdigest(),'frames':current_output_frames}
    (current_job_directory/'source.png').write_bytes(current_image_bytes)
    (current_job_directory/'sprite-sheet.png').write_bytes(current_output_bytes)
    write_record_atomically(current_job_directory/'coordinates.json',current_coordinate_map)
    write_record_atomically(current_job_directory/'request.json',{**command_payload_value,'image':None,'sourceSha256':current_coordinate_map['sourceSha256']})
    return {'id':current_identifier,'image':base64.b64encode(current_output_bytes).decode(),'coordinates':current_coordinate_map}


def execute_baseline_sheet_command(current_command_name,current_payload_record):
    """제작 기준 시트를 에셋 등록부와 분리하여 읽는다."""
    import json
    import yaml
    from tools.review.common.strict_yaml import UniqueConfigLoader
    current_root_path=SPRITE_BASELINE_ROOT.resolve()
    current_sheet_records={}
    for current_image_path in sorted(current_root_path.rglob('*.png')):
        if not current_image_path.resolve().is_relative_to(current_root_path):
            continue
        current_sidecar_path=current_image_path.with_suffix('.yaml')
        if not current_sidecar_path.is_file() or not current_sidecar_path.resolve().is_relative_to(current_root_path):
            continue
        current_sidecar_record=yaml.load(current_sidecar_path.read_text(),Loader=UniqueConfigLoader)
        if not isinstance(current_sidecar_record,dict) or not isinstance(current_sidecar_record.get('layout'),dict):
            continue
        current_relative_path=current_image_path.relative_to(current_root_path).as_posix()
        current_sheet_records[current_relative_path]=(current_image_path,current_sidecar_record)
    if current_command_name=='sheet-search':
        current_search_tokens=current_payload_record['query'].casefold().split()
        return {'items':[{'path':current_relative_path,'label':str(current_sidecar_record.get('description',current_image_path.stem)),'sha256':sha256(current_image_path.read_bytes()).hexdigest()} for current_relative_path,(current_image_path,current_sidecar_record) in current_sheet_records.items() if all(current_search_token in (current_relative_path+' '+str(current_sidecar_record.get('description',''))).casefold() for current_search_token in current_search_tokens)]}
    if current_payload_record['path'] not in current_sheet_records:
        raise ValueError('목록에 있는 베이스라인 시트를 선택하세요.')
    current_image_path,current_sidecar_record=current_sheet_records[current_payload_record['path']]
    if current_image_path.stat().st_size>SPRITE_SHEET_IMAGE_LIMIT:
        raise ValueError('편집기는 8MB 이하 PNG만 지원합니다.')
    current_image_bytes=current_image_path.read_bytes()
    current_layout_record=current_sidecar_record['layout']
    if any(type(current_layout_record.get(current_field_name)) is not int or current_layout_record[current_field_name]<1 for current_field_name in ('columns','rows')):
        raise ValueError('베이스라인 행·열은 양의 정수여야 합니다.')
    current_coordinate_record=None
    current_coordinate_name=current_sidecar_record.get('coordinates')
    if current_coordinate_name:
        current_coordinate_path=(current_image_path.parent/current_coordinate_name).resolve()
        if not current_coordinate_path.is_relative_to(current_root_path):
            raise ValueError('베이스라인 좌표맵 경로 이탈')
        current_coordinate_record=json.loads(current_coordinate_path.read_text())
        if current_coordinate_record.get('sha256')!=sha256(current_image_bytes).hexdigest():
            raise ValueError('베이스라인 이미지와 좌표맵 해시 불일치')
    return {'path':current_payload_record['path'],'image':base64.b64encode(current_image_bytes).decode(),'animation':current_coordinate_record,'layout':current_layout_record,'metadataSha256':None}


def execute_sprite_asset_command(current_command_name,current_payload_record):
    from tools.review.common.map_tile_assets import load_registered_tiles
    current_expected_fields={'query'} if current_command_name=='sheet-search' else {'path'}
    if not isinstance(current_payload_record,dict) or set(current_payload_record) not in (current_expected_fields,current_expected_fields|{'source'}) or any(not isinstance(current_field_value,str) for current_field_value in current_payload_record.values()):
        raise ValueError('스프라이트 검색 입력 형식 오류')
    current_source_kind=current_payload_record.get('source','assets')
    if current_source_kind not in ('assets','baseline'):raise ValueError('지원하지 않는 스프라이트 원본입니다.')
    if current_source_kind=='baseline':return execute_baseline_sheet_command(current_command_name,current_payload_record)
    current_repository_path,current_registry_records=load_registered_tiles()
    current_sprite_records={current_asset_path:current_asset_record for current_asset_path,current_asset_record in current_registry_records.items() if current_asset_path.endswith('.png') and (current_asset_path.startswith('assets/sprites/') or (current_asset_path.startswith('assets/characters/') and '/animations/' in current_asset_path)) and not current_asset_record['source'].get('retirement_reason')}
    if current_command_name=='sheet-search':
        current_search_tokens=current_payload_record['query'].casefold().split()
        return {'items':[{'path':current_asset_path,'label':current_asset_record.get('name',current_asset_record['managementId'])+' · '+current_asset_record['version'],'sha256':current_asset_record['sha256']} for current_asset_path,current_asset_record in current_sprite_records.items() if all(current_search_token in (current_asset_path+' '+str(current_asset_record.get('name',''))+' '+current_asset_record['managementId']).casefold() for current_search_token in current_search_tokens)]}
    current_asset_path=current_payload_record['path']
    if current_asset_path not in current_sprite_records:raise ValueError('등록된 스프라이트 PNG를 선택하세요.')
    current_image_path=(current_repository_path/current_asset_path).resolve()
    if not current_image_path.is_relative_to(current_repository_path):raise ValueError('에셋 경로가 저장소 밖을 가리킵니다.')
    if current_image_path.stat().st_size>SPRITE_SHEET_IMAGE_LIMIT:raise ValueError('편집기는 8MB 이하 PNG만 지원합니다.')
    current_image_bytes=current_image_path.read_bytes()
    if sha256(current_image_bytes).hexdigest()!=current_sprite_records[current_asset_path]['sha256']:raise ValueError('등록부와 스프라이트 해시가 다릅니다.')
    current_metadata_matches=[current_record for current_path,current_record in current_registry_records.items() if Path(current_path).parent==Path(current_asset_path).parent and current_path.endswith('.animation.json')]
    current_animation_record=None
    if len(current_metadata_matches)==1:
        import json
        current_metadata_file=(current_repository_path/current_metadata_matches[0]['path']).resolve()
        if not current_metadata_file.is_relative_to(current_repository_path):raise ValueError('좌표맵 경로 이탈')
        current_metadata_bytes=current_metadata_file.read_bytes()
        if sha256(current_metadata_bytes).hexdigest()!=current_metadata_matches[0]['sha256']:raise ValueError('좌표맵 해시 불일치')
        current_animation_record=json.loads(current_metadata_bytes)
    return {'image':base64.b64encode(current_image_bytes).decode(),'path':current_asset_path,'metadataSha256':current_metadata_matches[0]['sha256'] if len(current_metadata_matches)==1 else None,'animation':current_animation_record}


def update_registered_sprite_sheet(current_request_record):
    """등록 시트와 기존 애니메이션 좌표를 보존 계약에 따라 함께 갱신한다."""
    import json
    import threading
    import yaml
    from tools.review.common.strict_yaml import UniqueConfigLoader
    from tools.review.common.map_tile_assets import load_registered_tiles, UniqueAssetYamlLoader
    if not isinstance(current_request_record,dict) or set(current_request_record)!={'path','metadataSha256','payload','confirm'} or current_request_record['confirm'] is not True:
        raise ValueError('대상·좌표맵 해시·편집 입력·확인이 필요합니다.')
    with SPRITE_SHEET_UPDATE_LOCK:
        current_asset_root,current_asset_records=load_registered_tiles()
        current_asset_path=current_request_record['path']
        current_verified_image=execute_sprite_asset_command('sheet-image',{'path':current_asset_path})
        if current_verified_image['image']!=current_request_record['payload']['image']:raise ValueError('원본이 변경되었거나 선택한 에셋과 편집 이미지가 다릅니다. 다시 불러오세요.')
        current_metadata_paths=[current_path for current_path in current_asset_records if Path(current_path).parent==Path(current_asset_path).parent and current_path.endswith('.animation.json')]
        if len(current_metadata_paths)!=1:raise ValueError('같은 폴더에 등록된 애니메이션 좌표맵이 정확히 하나여야 합니다.')
        current_metadata_path=current_asset_root/current_metadata_paths[0]
        if not current_metadata_path.resolve().is_relative_to(current_asset_root):raise ValueError('좌표맵 경로 이탈')
        current_metadata_bytes=current_metadata_path.read_bytes()
        if sha256(current_metadata_bytes).hexdigest()!=current_request_record['metadataSha256'] or current_request_record['metadataSha256']!=current_asset_records[current_metadata_paths[0]]['sha256']:raise ValueError('좌표맵이 변경되었습니다. 다시 확인하세요.')
        current_metadata_record=json.loads(current_metadata_bytes)
        if len(current_metadata_record['frames'])!=len(current_request_record['payload']['frames']):raise ValueError('기존 프레임 수를 유지해야 합니다.')
        current_export_record=execute_sprite_sheet_export(current_request_record['payload'])
        current_metadata_record['sheet']=current_export_record['coordinates']['sheet']
        for current_original_frame,current_new_frame in zip(current_metadata_record['frames'],current_export_record['coordinates']['frames']):
            current_original_frame['rect']=current_new_frame['rect'];current_original_frame['anchor']=current_new_frame['anchor']
        current_metadata_record['version']=current_metadata_record['version']+'.edit-'+current_export_record['id']
        current_pending_files={current_asset_root/current_asset_path:base64.b64decode(current_export_record['image']),current_metadata_path:(json.dumps(current_metadata_record,ensure_ascii=False,indent=2)+'\n').encode()}
        current_source_path=current_asset_root/Path(current_asset_path).parent/'source.json'
        current_source_relative=current_source_path.relative_to(current_asset_root).as_posix()
        if current_source_relative in current_asset_records:
            if not current_source_path.resolve().is_relative_to(current_asset_root):raise ValueError('출처 파일 경로 이탈')
            current_source_bytes=current_source_path.read_bytes()
            if sha256(current_source_bytes).hexdigest()!=current_asset_records[current_source_relative]['sha256']:raise ValueError('출처 메타데이터 해시 불일치')
            current_source_document=json.loads(current_source_bytes)
            if current_source_document.get('image')==Path(current_asset_path).name and 'sha256' in current_source_document:
                current_source_document['sha256']=current_export_record['coordinates']['sha256']
                current_pending_files[current_source_path]=(json.dumps(current_source_document,ensure_ascii=False,indent=2)+'\n').encode()
        current_registry_path=current_asset_root/'asset-registry.yaml'
        current_registry_document=yaml.load(current_registry_path.read_text(),Loader=UniqueAssetYamlLoader)
        current_lock_path=current_asset_root.parent/'slime-frontend/sprite-assets.lock.yaml'
        current_lock_document=yaml.load(current_lock_path.read_text(),Loader=UniqueAssetYamlLoader)
        for current_file_path,current_file_bytes in current_pending_files.items():
            current_relative_path=current_file_path.relative_to(current_asset_root).as_posix()
            current_new_hash=sha256(current_file_bytes).hexdigest()
            for current_registry_entry in current_registry_document['assets']:
                if current_registry_entry['path']==current_relative_path:
                    current_registry_entry['sha256']=current_new_hash
                    current_registry_entry['version']+='-edit-'+current_export_record['id']
                    if 'width' in current_registry_entry:current_registry_entry['width']=current_metadata_record['sheet']['width']
                    if 'height' in current_registry_entry:current_registry_entry['height']=current_metadata_record['sheet']['height']
            for current_lock_entry in current_lock_document['files']:
                if current_lock_entry['source_path']==current_relative_path:
                    if current_lock_entry['sha256']!=current_asset_records[current_relative_path]['sha256']:raise ValueError('소비자 잠금 해시가 등록부와 다릅니다.')
                    current_lock_entry['sha256']=current_new_hash
        current_pending_files[current_registry_path]=yaml.safe_dump(current_registry_document,allow_unicode=True,sort_keys=False).encode()
        current_pending_files[current_lock_path]=yaml.safe_dump(current_lock_document,allow_unicode=True,sort_keys=False).encode()
        current_previous_files={current_file_path:current_file_path.read_bytes() for current_file_path in current_pending_files}
        current_backup_root=SPRITE_SHEET_JOB_ROOT/current_export_record['id'][:19]/current_export_record['id']/'before'
        current_backup_root.mkdir()
        for current_file_index,(current_file_path,current_file_bytes) in enumerate(current_previous_files.items()):(current_backup_root/str(current_file_index)).write_bytes(current_file_bytes)
        write_record_atomically(current_backup_root/'paths.json',[str(current_file_path) for current_file_path in current_previous_files])
        try:
            for current_file_path,current_file_bytes in current_pending_files.items():current_file_path.write_bytes(current_file_bytes)
        except Exception:
            for current_file_path,current_file_bytes in current_previous_files.items():current_file_path.write_bytes(current_file_bytes)
            raise
        return {'id':current_export_record['id'],'path':current_asset_path,'metadata':current_metadata_paths[0]}


import threading
SPRITE_SHEET_UPDATE_LOCK = threading.RLock()
