"""생성 프레임의 비파괴 정렬 프로젝트를 버전별로 보관한다."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from tools.review.common.generation_records import write_record_atomically

SPRITE_PROJECT_DIRECTORY = Path(__file__).resolve().parents[4]/'.local/sprite-editor'
SPRITE_FRAME_FIELDS = {'center','floor','head','anchorX','anchorY','x','y','scale'}

def load_sprite_editor_source(source_identifier_value):
    if isinstance(source_identifier_value,str) and source_identifier_value.startswith('asset:'):
        catalog_source_path=Path(__file__).resolve().parents[4]/'.tmp/manager-current/sprite-assets.json'
        for current_asset_record in json.loads(catalog_source_path.read_text())['assets']:
            if current_asset_record['id']==source_identifier_value:return current_asset_record
        raise ValueError('등록되지 않은 프론트 에셋입니다.')
    from .character_animation_jobs import read_generation_status
    generation_status_record=read_generation_status(source_identifier_value)
    if generation_status_record['status']!='completed':raise ValueError('완료된 생성 결과만 편집할 수 있습니다.')
    from PIL import Image
    frame_output_records=[]
    for direction_name_value,source_frame_paths in generation_status_record['result']['frames'].items():
        for frame_index_value,source_frame_path in enumerate(source_frame_paths):
            image_source_path=(Path(generation_status_record['path'])/source_frame_path).resolve()
            if not image_source_path.is_relative_to(Path(generation_status_record['path']).resolve()):raise ValueError('프레임 경로 오류')
            with Image.open(image_source_path) as source_image_value: image_width_value,image_height_value=source_image_value.size
            frame_output_records.append({'direction':direction_name_value,'frameId':f'{direction_name_value}.{frame_index_value}','rect':{'x':0,'y':0,'width':image_width_value,'height':image_height_value},'anchor':{'x':image_width_value/2,'y':image_height_value*.9},'url':'/character-animation/files/'+source_identifier_value+'/'+source_frame_path})
    return {'id':source_identifier_value,'label':source_identifier_value,'fps':generation_status_record['result']['fps'],'frames':frame_output_records}

def execute_sprite_editor_command(operation_command_name, command_payload_value):
    if set(command_payload_value) != ({'id','document'} if operation_command_name=='sprite-save' else {'id'}):raise ValueError('스프라이트 명령 필드 오류')
    source_asset_record=load_sprite_editor_source(command_payload_value['id'])
    if operation_command_name=='sprite-source':return source_asset_record
    project_output_directory=SPRITE_PROJECT_DIRECTORY/hashlib.sha256(command_payload_value['id'].encode()).hexdigest()[:24]
    if operation_command_name=='sprite-load':
        latest_project_path=project_output_directory/'latest.json'
        if not latest_project_path.exists():return {'document':None}
        saved_project_record=json.loads(latest_project_path.read_text())
        if saved_project_record['source_digest']!=hashlib.sha256(json.dumps(source_asset_record,sort_keys=True).encode()).hexdigest():
            return {'document':None,'warning':'원본 버전이 변경되어 새 편집으로 열었습니다. 이전 저장 파일은 보존됩니다.'}
        return saved_project_record
    current_project_document=command_payload_value['document']
    if not isinstance(current_project_document,dict) or set(current_project_document)!={'version','source','frames'} or current_project_document['version']!=1 or current_project_document['source']!=command_payload_value['id']:raise ValueError('스프라이트 문서 형식 오류')
    expected_frame_keys={frame_record_value['frameId'] for frame_record_value in source_asset_record['frames']}
    current_frame_values=current_project_document['frames']
    if not isinstance(current_frame_values,dict) or set(current_frame_values)!=expected_frame_keys or len(expected_frame_keys)>4000:raise ValueError('원본과 편집 프레임 목록이 일치하지 않습니다.')
    for current_frame_settings in current_frame_values.values():
        if not isinstance(current_frame_settings,dict) or set(current_frame_settings)!=SPRITE_FRAME_FIELDS:raise ValueError('프레임 설정 필드 오류')
        if any(type(value) not in (int,float) or not math.isfinite(value) or abs(value)>8192 for value in current_frame_settings.values()):raise ValueError('프레임 설정은 유한한 좌표여야 합니다.')
        if not 0.01<=current_frame_settings['scale']<=8 or current_frame_settings['floor']<=current_frame_settings['head']:raise ValueError('배율은 0.01~8, 머리는 바닥보다 위여야 합니다.')
    project_output_directory.mkdir(parents=True,exist_ok=True)
    revision_identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:8]
    saved_project_record={'revision':revision_identifier,'document':current_project_document,'source_digest':hashlib.sha256(json.dumps(source_asset_record,sort_keys=True).encode()).hexdigest(),'saved_at':datetime.now(timezone.utc).isoformat()}
    write_record_atomically(project_output_directory/(revision_identifier+'.json'),saved_project_record)
    write_record_atomically(project_output_directory/'latest.json',saved_project_record)
    return {**saved_project_record,'path':str(project_output_directory/(revision_identifier+'.json'))}
