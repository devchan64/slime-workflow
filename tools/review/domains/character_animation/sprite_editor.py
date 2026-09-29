"""생성 프레임의 비파괴 정렬 프로젝트를 버전별로 보관한다."""
import hashlib
import json
import math
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from tools.review.common.generation_records import write_record_atomically
from .sprite_sheet import render_sprite_saved_sheet

SPRITE_PROJECT_DIRECTORY = Path(__file__).resolve().parents[4]/'.local/sprite-editor'
SPRITE_HISTORY_COMMAND_LOCK=threading.RLock()
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
    with SPRITE_HISTORY_COMMAND_LOCK:
        return execute_sprite_locked_command(operation_command_name,command_payload_value)

def execute_sprite_locked_command(operation_command_name, command_payload_value):
    if operation_command_name not in {'sprite-source','sprite-load','sprite-save','sprite-history','sprite-history-reset','sprite-history-delete'}:raise ValueError('지원하지 않는 스프라이트 명령입니다.')
    if set(command_payload_value) != ({'id','document'} if operation_command_name=='sprite-save' else {'id','revision'} if operation_command_name=='sprite-history-delete' else {'id'}):raise ValueError('스프라이트 명령 필드 오류')
    source_asset_record=load_sprite_editor_source(command_payload_value['id'])
    if operation_command_name=='sprite-source':return source_asset_record
    project_output_directory=SPRITE_PROJECT_DIRECTORY/hashlib.sha256(command_payload_value['id'].encode()).hexdigest()[:24]
    hidden_history_path=project_output_directory/'hidden-history.json'
    hidden_revision_values=set(json.loads(hidden_history_path.read_text())['revisions']) if hidden_history_path.exists() else set()
    revision_file_paths=[current_revision_path for current_revision_path in project_output_directory.glob('*.json') if re.fullmatch(r'\d{8}T\d{6}-[0-9a-f]{8}',current_revision_path.stem)]
    if operation_command_name in ('sprite-history-reset','sprite-history-delete'):
        if operation_command_name=='sprite-history-delete':
            selected_revision_value=command_payload_value['revision']
            if not isinstance(selected_revision_value,str) or selected_revision_value not in {current_revision_path.stem for current_revision_path in revision_file_paths}:raise ValueError('존재하지 않는 저장 이력입니다.')
            removed_revision_values={selected_revision_value}
        else:removed_revision_values={current_revision_path.stem for current_revision_path in revision_file_paths}
        removed_revision_count=len(removed_revision_values-hidden_revision_values)
        project_output_directory.mkdir(parents=True,exist_ok=True)
        write_record_atomically(hidden_history_path,{'revisions':sorted(hidden_revision_values|removed_revision_values)})
        return {'removed':removed_revision_count,'files_preserved':True}
    if operation_command_name=='sprite-history':
        current_source_digest=hashlib.sha256(json.dumps(source_asset_record,sort_keys=True).encode()).hexdigest()
        history_record_items=[]
        for current_revision_path in sorted(revision_file_paths,reverse=True):
            if current_revision_path.stem in hidden_revision_values:continue
            current_saved_record=json.loads(current_revision_path.read_text())
            history_record_items.append({'id':current_saved_record['revision'],'created_at':current_saved_record['saved_at'],'frames':len(current_saved_record['document']['frames']),'label':'스프라이트 저장','compatible':current_saved_record['source_digest']==current_source_digest,'document':current_saved_record['document'],'sheet':current_saved_record.get('sheet')})
        return {'items':history_record_items}
    if operation_command_name=='sprite-load':
        latest_project_path=project_output_directory/'latest.json'
        if not latest_project_path.exists():return {'document':None}
        saved_project_record=json.loads(latest_project_path.read_text())
        if saved_project_record['revision'] in hidden_revision_values:return {'document':None}
        if saved_project_record['source_digest']!=hashlib.sha256(json.dumps(source_asset_record,sort_keys=True).encode()).hexdigest():
            return {'document':None,'warning':'원본 버전이 변경되어 새 편집으로 열었습니다. 이전 저장 파일은 보존됩니다.'}
        return saved_project_record
    current_project_document=command_payload_value['document']
    if not isinstance(current_project_document,dict):raise ValueError('스프라이트 문서 형식 오류')
    current_document_version=current_project_document.get('version')
    expected_document_fields={'version','source','frames','output'} if current_document_version in (2,3) else {'version','source','frames'}
    if current_document_version in (2,3) and 'guides' in current_project_document:expected_document_fields.add('guides')
    if type(current_document_version) is not int or current_document_version not in (1,2,3) or set(current_project_document)!=expected_document_fields or current_project_document['source']!=command_payload_value['id']:raise ValueError('스프라이트 문서 형식 오류')
    if current_document_version in (2,3):
        current_output_settings=current_project_document['output']
        if not isinstance(current_output_settings,dict) or set(current_output_settings)!={'cellSize','targetHeight'}:raise ValueError('출력 설정 필드 오류')
        output_cell_pixels=current_output_settings['cellSize']
        target_body_height=current_output_settings['targetHeight']
        if type(output_cell_pixels) is not int or not 1<=output_cell_pixels<=4096:raise ValueError('출력 셀은 1~4096px 정수여야 합니다.')
        if type(target_body_height) not in (int,float) or not math.isfinite(target_body_height) or not 0<target_body_height<=output_cell_pixels:raise ValueError('목표 몸체 높이는 출력 셀 안의 양수여야 합니다.')
    current_guide_records=current_project_document.get('guides',[])
    if not isinstance(current_guide_records,list) or len(current_guide_records)>32:raise ValueError('추가 가이드는 최대 32개 목록이어야 합니다.')
    for current_guide_record in current_guide_records:
        if not isinstance(current_guide_record,dict) or set(current_guide_record)!={'axis','position'}:raise ValueError('추가 가이드 필드 오류')
        if current_guide_record['axis'] not in ('horizontal','vertical'):raise ValueError('가이드 방향은 가로 또는 세로여야 합니다.')
        current_guide_position=current_guide_record['position']
        if type(current_guide_position) not in (int,float) or not math.isfinite(current_guide_position) or not 0<=current_guide_position<=1:raise ValueError('가이드 상대 위치는 0~1이어야 합니다.')
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
    saved_project_record['sheet']=render_sprite_saved_sheet(source_asset_record,current_project_document,project_output_directory/(revision_identifier+'.png'))
    saved_project_record['sheet']['url']='/character-animation/sprite-sheet/'+project_output_directory.name+'/'+revision_identifier+'.png'
    write_record_atomically(project_output_directory/(revision_identifier+'.json'),saved_project_record)
    write_record_atomically(project_output_directory/'latest.json',saved_project_record)
    return {**saved_project_record,'path':str(project_output_directory/(revision_identifier+'.json'))}
