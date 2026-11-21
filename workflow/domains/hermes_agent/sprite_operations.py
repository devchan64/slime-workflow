"""등록 스프라이트 앵커 변경을 기존 시트 편집기에 위임한다."""
import base64
import hashlib
import json
import math
import re
from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record
from workflow.domains.hermes_agent.sprite_observer import validate_hermes_sprite_path, call_hermes_sprite_editor


def validate_hermes_sprite_anchor_draft(current_draft_record):
    if not isinstance(current_draft_record,dict) or set(current_draft_record)!={'path','snapshot','columns','anchors'}:
        raise ValueError('path·snapshot·columns·anchors가 필요합니다.')
    validate_hermes_sprite_path(current_draft_record['path'])
    if not isinstance(current_draft_record['snapshot'],str) or not re.fullmatch(r'[a-f0-9]{64}',current_draft_record['snapshot']):raise ValueError('스프라이트 기준 해시 오류')
    if type(current_draft_record['columns']) is not int or not 1<=current_draft_record['columns']<=128:raise ValueError('출력 열 수 오류')
    current_anchor_records=current_draft_record['anchors']
    if not isinstance(current_anchor_records,list) or not 1<=len(current_anchor_records)<=128:raise ValueError('변경할 앵커는 1~128개입니다.')
    current_seen_ids=set()
    for current_anchor_record in current_anchor_records:
        if not isinstance(current_anchor_record,dict) or set(current_anchor_record)!={'frame_id','x','y'}:raise ValueError('앵커 항목 오류')
        current_frame_identifier=current_anchor_record['frame_id']
        if not isinstance(current_frame_identifier,str) or not 1<=len(current_frame_identifier)<=200 or current_frame_identifier in current_seen_ids:raise ValueError('프레임 ID 오류 또는 중복')
        if any(type(current_anchor_record[current_axis_name]) not in (int,float) or not math.isfinite(current_anchor_record[current_axis_name]) for current_axis_name in ('x','y')):raise ValueError('앵커는 유한한 숫자여야 합니다.')
        current_seen_ids.add(current_frame_identifier)
    return hashlib.sha256(json.dumps(current_draft_record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def prepare_hermes_sprite_anchor_edit(current_draft_record):
    current_draft_hash=validate_hermes_sprite_anchor_draft(current_draft_record)
    current_source_record=call_hermes_sprite_editor('sheet-image',{'path':current_draft_record['path'],'source':'assets'})
    if not isinstance(current_source_record,dict) or current_source_record.get('path')!=current_draft_record['path'] or not isinstance(current_source_record.get('image'),str):raise ValueError('스프라이트 원본 응답 오류')
    try:current_source_bytes=base64.b64decode(current_source_record['image'],validate=True)
    except (TypeError,ValueError) as current_decode_error:raise ValueError('이미지 형식 오류') from current_decode_error
    current_image_hash=hashlib.sha256(current_source_bytes).hexdigest()
    current_metadata_hash=current_source_record.get('metadataSha256')
    if not isinstance(current_metadata_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_metadata_hash):raise ValueError('등록된 애니메이션 메타데이터가 정확히 하나 필요합니다.')
    current_snapshot_digest=hashlib.sha256((current_image_hash+':'+current_metadata_hash).encode('ascii')).hexdigest()
    if current_snapshot_digest!=current_draft_record['snapshot']:raise ValueError('스프라이트 원본이 변경됐습니다. 다시 조회하세요.')
    current_animation_record=current_source_record.get('animation')
    current_frame_records=current_animation_record.get('frames') if isinstance(current_animation_record,dict) else None
    if not isinstance(current_frame_records,list) or not 1<=len(current_frame_records)<=128:raise ValueError('등록 프레임이 1~128개 필요합니다.')
    current_anchor_by_id={current_anchor['frame_id']:current_anchor for current_anchor in current_draft_record['anchors']}
    current_frame_payloads=[];current_changes_list=[];current_frame_ids=set()
    for current_frame_record in current_frame_records:
        if not isinstance(current_frame_record,dict) or not isinstance(current_frame_record.get('frameId'),str) or current_frame_record['frameId'] in current_frame_ids:raise ValueError('원본 프레임 ID 오류')
        current_frame_identifier=current_frame_record['frameId'];current_frame_ids.add(current_frame_identifier)
        current_frame_rect=current_frame_record['rect'];current_original_anchor=current_frame_record['anchor']
        current_anchor_record=current_anchor_by_id.get(current_frame_identifier)
        current_selected_anchor={'x':current_anchor_record['x'],'y':current_anchor_record['y']} if current_anchor_record else current_original_anchor
        current_frame_payloads.append({**current_frame_rect,'anchorX':current_selected_anchor['x'],'anchorY':current_selected_anchor['y']})
        if current_anchor_record and current_selected_anchor!=current_original_anchor:
            current_changes_list.append({'frame_id':current_frame_identifier,'before':current_original_anchor,'after':current_selected_anchor})
    if set(current_anchor_by_id)-current_frame_ids:raise ValueError('선택 시트에 없는 프레임 ID입니다.')
    if not current_changes_list:raise ValueError('변경된 앵커가 없습니다.')
    current_export_payload={'image':current_source_record['image'],'frames':current_frame_payloads,'columns':current_draft_record['columns']}
    current_export_record=call_hermes_sprite_editor('sheet-export',current_export_payload)
    current_coordinate_record=current_export_record.get('coordinates') if isinstance(current_export_record,dict) else None
    if not isinstance(current_coordinate_record,dict) or current_coordinate_record.get('sourceSha256')!=current_image_hash or not isinstance(current_coordinate_record.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_coordinate_record['sha256']) or not isinstance(current_coordinate_record.get('sheet'),dict):raise ValueError('시트 출력 미리보기 오류')
    current_preview_image=current_export_record.get('image')
    if not isinstance(current_preview_image,str) or len(current_preview_image)>12_000_000:raise ValueError('미리보기 이미지 크기 오류')
    try:current_preview_bytes=base64.b64decode(current_preview_image,validate=True)
    except (TypeError,ValueError) as current_image_error:raise ValueError('미리보기 이미지 형식 오류') from current_image_error
    if not current_preview_bytes or hashlib.sha256(current_preview_bytes).hexdigest()!=current_coordinate_record['sha256']:
        raise ValueError('미리보기 이미지 해시 불일치')
    current_export_frames=current_coordinate_record.get('frames')
    if not isinstance(current_export_frames,list) or len(current_export_frames)!=len(current_frame_records):raise ValueError('출력 프레임 수 오류')
    current_frame_layout=[]
    for current_original_frame,current_export_frame in zip(current_frame_records,current_export_frames):
        if not isinstance(current_export_frame,dict) or not isinstance(current_export_frame.get('rect'),dict):raise ValueError('출력 프레임 좌표 오류')
        current_frame_layout.append({'frame_id':current_original_frame['frameId'],'before':current_original_frame['rect'],'after':current_export_frame['rect'],'anchor':current_export_frame['anchor']})
    current_clip_values=[]
    current_clip_records=current_animation_record.get('clips',[])
    if not isinstance(current_clip_records,list) or len(current_clip_records)>128:raise ValueError('재생 클립 목록 오류')
    for current_clip_record in current_clip_records:
        if not isinstance(current_clip_record,dict) or not isinstance(current_clip_record.get('clipId'),str) or not 1<=len(current_clip_record['clipId'])<=200 or not isinstance(current_clip_record.get('frames'),list) or not 1<=len(current_clip_record['frames'])<=128:
            raise ValueError('재생 클립 형식 오류')
        if type(current_clip_record.get('loop')) is not bool:raise ValueError('재생 클립 반복 설정 오류')
        current_clip_frames=[]
        for current_clip_frame in current_clip_record['frames']:
            if not isinstance(current_clip_frame,dict) or not isinstance(current_clip_frame.get('frameId'),str) or current_clip_frame['frameId'] not in current_frame_ids or type(current_clip_frame.get('durationMs')) is not int or not 10<=current_clip_frame['durationMs']<=60000:
                raise ValueError('선택 시트 재생 클립의 프레임 또는 시간 오류')
            current_clip_frames.append({'frame_id':current_clip_frame['frameId'],'duration_ms':current_clip_frame['durationMs']})
        if any(current_clip_value['id']==current_clip_record['clipId'] for current_clip_value in current_clip_values):raise ValueError('재생 클립 ID 중복')
        current_clip_values.append({'id':current_clip_record['clipId'],'loop':current_clip_record['loop'],'frames':current_clip_frames,'next_clip':current_clip_record.get('nextClipId')})
    current_review_record={'path':current_draft_record['path'],'source_sha256':current_image_hash,'metadata_sha256':current_metadata_hash,'output_sha256':current_coordinate_record['sha256'],'output_sheet':current_coordinate_record['sheet'],'frame_count':len(current_frame_records),'changed_anchors':current_changes_list,'frame_layout':current_frame_layout,'clips':current_clip_values,'columns':current_draft_record['columns']}
    current_review_hash=hashlib.sha256(json.dumps(current_review_record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    current_update_payload={'path':current_draft_record['path'],'metadataSha256':current_metadata_hash,'payload':current_export_payload,'confirm':True}
    return current_update_payload,{**current_review_record,'preview_image':current_preview_image,'token':current_draft_hash,'review_sha256':current_review_hash,'note':'시트 이미지를 다시 패킹하며 애니메이션·등록부·프런트 잠금을 갱신합니다. 모든 프레임과 외형을 검수하세요. 미리보기는 임시 시트 작업을 생성합니다.'}


def preview_hermes_sprite_anchor_edit(current_draft_record):
    return prepare_hermes_sprite_anchor_edit(current_draft_record)[1]



def render_hermes_sprite_anchor_playback(current_draft_record,current_preview_token,current_review_digest,current_fps_value):
    """검토한 초안의 모든 프레임을 균일 FPS로 정렬해 임시 GIF를 생성한다."""
    from workflow.domains.character_animation.sprite_sheet_editor import SPRITE_GIF_ALLOWED_FPS
    if type(current_fps_value) is not int or current_fps_value not in SPRITE_GIF_ALLOWED_FPS:
        raise ValueError('지원하지 않는 재생 FPS입니다.')
    if current_preview_token!=validate_hermes_sprite_anchor_draft(current_draft_record) or not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):
        raise ValueError('검토한 스프라이트 초안과 검수 해시가 필요합니다.')
    current_update_payload,current_preview_record=prepare_hermes_sprite_anchor_edit(current_draft_record)
    if current_preview_record['review_sha256']!=current_review_digest:
        raise ValueError('스프라이트 검수 결과가 변경됐습니다. 다시 검토하세요.')
    current_gif_record=call_hermes_sprite_editor('sheet-gif',{**current_update_payload['payload'],'fps':current_fps_value})
    if not isinstance(current_gif_record,dict) or not isinstance(current_gif_record.get('gif'),str) or len(current_gif_record['gif'])>12_000_000 or current_gif_record.get('frameCount')!=current_preview_record['frame_count'] or type(current_gif_record.get('durationMs')) is not int:
        raise ValueError('재생 검수 결과 오류')
    try:current_gif_bytes=base64.b64decode(current_gif_record['gif'],validate=True)
    except (TypeError,ValueError) as current_gif_error:raise ValueError('재생 GIF 형식 오류') from current_gif_error
    if not current_gif_bytes.startswith((b'GIF87a',b'GIF89a')) or len(current_gif_bytes)>9_000_000:
        raise ValueError('재생 GIF 크기 또는 형식 오류')
    return {'gif':current_gif_record['gif'],'sha256':hashlib.sha256(current_gif_bytes).hexdigest(),'frame_count':current_gif_record['frameCount'],'duration_ms':current_gif_record['durationMs'],'fps':current_fps_value,'review_sha256':current_review_digest,'note':'선택 시트의 모든 프레임을 나열 순서와 균일 FPS로 앵커 정렬하여 재생합니다. 실제 클립의 순서·타이밍이나 게임 렌더링을 대체하지 않으며 임시 파일을 생성합니다.'}



def quantize_hermes_sprite_clip_durations(current_clip_frames):
    """프레임 경계를 10ms 단위로 반올림해 전체 재생 시간의 오차 누적을 방지한다."""
    current_elapsed_milliseconds=0
    current_previous_boundary=0
    current_duration_values=[]
    for current_clip_frame in current_clip_frames:
        current_elapsed_milliseconds+=current_clip_frame['duration_ms']
        current_rounded_boundary=((current_elapsed_milliseconds+5)//10)*10
        current_duration_values.append(current_rounded_boundary-current_previous_boundary)
        current_previous_boundary=current_rounded_boundary
    return current_duration_values


def render_hermes_sprite_clip_playback(current_draft_record,current_preview_token,current_review_digest,current_clip_identifier):
    """등록 클립 순서·시간·반복을 보존한 앵커 정렬 GIF를 생성한다."""
    from io import BytesIO
    from PIL import Image
    from workflow.domains.character_animation.sprite_sheet_editor import SPRITE_GIF_PIXEL_BUDGET
    if current_preview_token!=validate_hermes_sprite_anchor_draft(current_draft_record) or not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):raise ValueError('검토한 초안과 검수 해시가 필요합니다.')
    if not isinstance(current_clip_identifier,str) or not 1<=len(current_clip_identifier)<=200:raise ValueError('클립 ID 오류')
    _,current_preview_record=prepare_hermes_sprite_anchor_edit(current_draft_record)
    if current_preview_record['review_sha256']!=current_review_digest:raise ValueError('스프라이트 검수 결과가 변경됐습니다. 다시 검토하세요.')
    current_clip_records=[current_clip_record for current_clip_record in current_preview_record['clips'] if current_clip_record['id']==current_clip_identifier]
    if len(current_clip_records)!=1:raise ValueError('선택 시트에 속하는 등록 클립을 선택하세요.')
    current_clip_record=current_clip_records[0]
    current_frames_by_id={current_frame_record['frame_id']:current_frame_record for current_frame_record in current_preview_record['frame_layout']}
    current_ordered_frames=[current_frames_by_id[current_clip_frame['frame_id']] for current_clip_frame in current_clip_record['frames']]
    current_left_value=math.ceil(max(current_frame_record['anchor']['x'] for current_frame_record in current_ordered_frames))
    current_top_value=math.ceil(max(current_frame_record['anchor']['y'] for current_frame_record in current_ordered_frames))
    current_width_value=current_left_value+math.ceil(max(current_frame_record['after']['width']-current_frame_record['anchor']['x'] for current_frame_record in current_ordered_frames))
    current_height_value=current_top_value+math.ceil(max(current_frame_record['after']['height']-current_frame_record['anchor']['y'] for current_frame_record in current_ordered_frames))
    if current_width_value<1 or current_height_value<1 or current_width_value*current_height_value*len(current_ordered_frames)>SPRITE_GIF_PIXEL_BUDGET:raise ValueError('GIF 전체 프레임 크기가 허용 범위를 초과합니다.')
    with Image.open(BytesIO(base64.b64decode(current_preview_record['preview_image'],validate=True))) as current_open_image:
        current_sheet_image=current_open_image.convert('RGBA')
    current_output_frames=[]
    for current_frame_record in current_ordered_frames:
        current_frame_rect=current_frame_record['after']
        current_frame_image=current_sheet_image.crop((current_frame_rect['x'],current_frame_rect['y'],current_frame_rect['x']+current_frame_rect['width'],current_frame_rect['y']+current_frame_rect['height']))
        current_canvas_image=Image.new('RGBA',(current_width_value,current_height_value),'white')
        current_canvas_image.alpha_composite(current_frame_image,(round(current_left_value-current_frame_record['anchor']['x']),round(current_top_value-current_frame_record['anchor']['y'])))
        current_output_frames.append(current_canvas_image.convert('RGB'))
    current_duration_values=quantize_hermes_sprite_clip_durations(current_clip_record['frames'])
    current_output_stream=BytesIO()
    current_save_options={'format':'GIF','save_all':True,'append_images':current_output_frames[1:],'duration':current_duration_values,'disposal':2}
    if current_clip_record['loop']:current_save_options['loop']=0
    current_output_frames[0].save(current_output_stream,**current_save_options)
    current_gif_bytes=current_output_stream.getvalue()
    if len(current_gif_bytes)>9_000_000:raise ValueError('재생 GIF 크기 초과')
    return {'gif':base64.b64encode(current_gif_bytes).decode(),'sha256':hashlib.sha256(current_gif_bytes).hexdigest(),'frame_count':len(current_ordered_frames),'durations_ms':current_duration_values,'clip':current_clip_identifier,'loop':current_clip_record['loop'],'next_clip':current_clip_record['next_clip'],'review_sha256':current_review_digest,'note':'등록 클립의 프레임 순서와 시간을 사용합니다. GIF는 프레임 경계를 10ms 단위로 반올림하며 다음 클립 전환과 게임 렌더링은 재현하지 않습니다.'}


def inspect_hermes_sprite_receipt(current_receipt_record,current_request_identifier):
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('version')!=9 or current_receipt_record.get('id')!=current_request_identifier or current_receipt_record.get('state') not in ('dispatching','completed'):raise ValueError('스프라이트 접수 기록 오류')
    current_target_path=current_receipt_record.get('path')
    if current_target_path is not None:validate_hermes_sprite_path(current_target_path)
    current_target_record={'path':current_target_path} if current_target_path is not None else {}
    if current_receipt_record['state']=='dispatching':return {'request_id':current_request_identifier,'state':'unknown','saved':None,**current_target_record}
    if current_receipt_record.get('saved') is not True:raise ValueError('스프라이트 저장 상태 오류')
    return {'request_id':current_request_identifier,'state':'completed','saved':True,'job_id':current_receipt_record['job_id'],**current_target_record}


def save_hermes_sprite_anchor_once(current_request_identifier,current_draft_record,current_preview_token,current_review_digest):
    if current_preview_token!=validate_hermes_sprite_anchor_draft(current_draft_record) or not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):raise ValueError('검토한 초안과 검수 해시가 필요합니다.')
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_record=read_bounded_delegation_record(current_receipt_path)
            current_result_record=inspect_hermes_sprite_receipt(current_receipt_record,current_request_identifier)
            if current_receipt_record.get('token')!=current_preview_token or current_receipt_record.get('review_sha256')!=current_review_digest:raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            return {**current_result_record,'duplicate':True}
        from workflow.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
        current_pending_record=inspect_hermes_sprite_pending_status()
        if not isinstance(current_pending_record,dict) or current_pending_record.get('state') not in ('clear','busy','pending','unavailable'):
            raise ValueError('스프라이트 저장 상태 응답 오류')
        if current_pending_record['state']!='clear':
            return {'request_id':current_request_identifier,'state':'blocked','saved':False,'reason':current_pending_record['state'],'path':current_draft_record['path'],'duplicate':False}
        current_update_payload,current_preview_record=prepare_hermes_sprite_anchor_edit(current_draft_record)
        if current_preview_record['review_sha256']!=current_review_digest:raise ValueError('스프라이트 검수 결과가 변경됐습니다. 다시 확인하세요.')
        current_receipt_record={'version':9,'id':current_request_identifier,'token':current_preview_token,'review_sha256':current_review_digest,'state':'dispatching','path':current_draft_record['path']}
        write_record_atomically(current_receipt_path,current_receipt_record)
        current_save_record=call_hermes_sprite_editor('sheet-update',current_update_payload)
        if not isinstance(current_save_record,dict) or current_save_record.get('path')!=current_draft_record['path'] or not isinstance(current_save_record.get('id'),str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_save_record['id']):raise ValueError('시트 저장 결과 확인 필요. 자동 재접수하지 않습니다.')
        if read_bounded_delegation_record(current_receipt_path)!=current_receipt_record:raise ValueError('저장 중 접수 기록이 변경됐습니다. 원본과 이력을 확인하고 자동 재저장하지 마세요.')
        current_receipt_record.update(state='completed',saved=True,job_id=current_save_record['id'])
        write_record_atomically(current_receipt_path,current_receipt_record)
        return {**inspect_hermes_sprite_receipt(current_receipt_record,current_request_identifier),'duplicate':False}


def read_hermes_sprite_anchor_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):return {'state':'not_found'}
        return inspect_hermes_sprite_receipt(read_bounded_delegation_record(current_receipt_path),current_request_identifier)
