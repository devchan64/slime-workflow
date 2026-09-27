"""앵커 좌표 저장 결과를 변경 불가능한 실행별 이력으로 보관한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import math
import re
import uuid
from tools.review.common.generation_records import write_record_atomically

ANCHOR_HISTORY_ROOT = Path(__file__).resolve().parents[4]/'.tmp/test/animation-anchor-edits'

def validate_anchor_document(document_record_value):
    if not isinstance(document_record_value,dict) or set(document_record_value)!={'schemaVersion','artifactType','description','coordinateMode','source','frames'}:
        raise ValueError('좌표 문서 필드 오류')
    if document_record_value['schemaVersion']!=1 or document_record_value['coordinateMode'] not in ('anchor','foot-centers','endpoints'):
        raise ValueError('좌표 문서 버전 또는 모드 오류')
    if document_record_value['artifactType'] not in ('character-animation-anchor-review','character-standing-anchor-review') or not isinstance(document_record_value['description'],str):
        raise ValueError('좌표 산출물 형식 오류')
    source_record_value=document_record_value['source']
    if not isinstance(source_record_value,dict) or set(source_record_value)!={'animationId','animationVersion','sheets'}:raise ValueError('좌표 출처 필드 오류')
    for field_name_value in ('animationId','animationVersion'):
        if not isinstance(source_record_value[field_name_value],str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,160}',source_record_value[field_name_value]):raise ValueError('애니메이션 식별자 오류')
    sheets_record_values=source_record_value['sheets']
    if not isinstance(sheets_record_values,list) or not sheets_record_values:raise ValueError('시트 출처 필요')
    for sheet_record_value in sheets_record_values:
        if not isinstance(sheet_record_value,dict) or not isinstance(sheet_record_value.get('image'),str) or not re.fullmatch(r'[a-f0-9]{64}',sheet_record_value.get('sha256','')):raise ValueError('시트 해시 오류')
    frames_record_values=document_record_value['frames']
    if not isinstance(frames_record_values,list) or not 1<=len(frames_record_values)<=10000:raise ValueError('프레임 개수 오류')
    seen_frame_identifiers=set()
    for frame_record_value in frames_record_values:
        if not isinstance(frame_record_value,dict) or set(frame_record_value)!={'frameId','direction','image','rect','points','anchor'}:raise ValueError('프레임 필드 오류')
        frame_identifier_value=frame_record_value['frameId']
        if not isinstance(frame_identifier_value,str) or frame_identifier_value in seen_frame_identifiers:raise ValueError('프레임 ID 오류')
        seen_frame_identifiers.add(frame_identifier_value)
        if frame_record_value['direction'] not in ('down_left','down_right','up_left','up_right') or frame_record_value['image'] not in [s['image'] for s in sheets_record_values]:raise ValueError('프레임 출처 오류')
        rect_record_value=frame_record_value['rect']
        if not isinstance(rect_record_value,dict) or set(rect_record_value)!={'x','y','width','height'} or any(type(v)is not int or v<0 for v in rect_record_value.values()) or min(rect_record_value['width'],rect_record_value['height'])<1:raise ValueError('프레임 영역 오류')
        points_record_values=frame_record_value['points']
        expected_point_count={'anchor':1,'foot-centers':2,'endpoints':4}[document_record_value['coordinateMode']]
        if not isinstance(points_record_values,list) or len(points_record_values)!=expected_point_count:raise ValueError('좌표 개수 오류')
        for point_record_value in [*points_record_values,frame_record_value['anchor']]:
            if not isinstance(point_record_value,dict) or set(point_record_value)!={'x','y'}:raise ValueError('좌표 필드 오류')
            for axis_name_value,size_name_value in [('x','width'),('y','height')]:
                number_value=point_record_value[axis_name_value]
                if type(number_value) not in (int,float) or not math.isfinite(number_value) or not 0<=number_value<rect_record_value[size_name_value]:raise ValueError('셀 내부 유한 좌표 필요')
    return document_record_value

def execute_anchor_history_command(operation_command_name,command_payload_value):
    if operation_command_name=='anchor-save':
        if set(command_payload_value)!={'document'}:raise ValueError('저장 필드 오류')
        document_record_value=validate_anchor_document(command_payload_value['document'])
        created_time_value=datetime.now(ZoneInfo('Asia/Seoul'))
        time_directory_name=created_time_value.strftime('%Y-%m-%d_%H-%M-%S')
        history_identifier_value=time_directory_name+'-'+uuid.uuid4().hex[:8]
        history_directory_path=ANCHOR_HISTORY_ROOT/time_directory_name/history_identifier_value
        history_directory_path.mkdir(parents=True,exist_ok=False)
        write_record_atomically(history_directory_path/'request.json',command_payload_value)
        history_record_value={'id':history_identifier_value,'created_at':created_time_value.isoformat(),'status':'completed','source':document_record_value['source'],'frames':len(document_record_value['frames'])}
        write_record_atomically(history_directory_path/'coordinates.json',document_record_value)
        write_record_atomically(history_directory_path/'result.json',history_record_value)
        write_record_atomically(history_directory_path/'status.json',{'status':'completed'})
        return history_record_value
    if operation_command_name in ('anchor-history','anchor-history-reset'):
        if set(command_payload_value)!={'animation_id','animation_version'}:raise ValueError('이력 조회 필드 오류')
        history_record_values=[]
        for result_record_path in ANCHOR_HISTORY_ROOT.glob('*/*/result.json'):
            if (result_record_path.parent/'history-hidden.json').exists():continue
            history_record_value=json.loads(result_record_path.read_text())
            if history_record_value['source']['animationId']==command_payload_value['animation_id'] and history_record_value['source']['animationVersion']==command_payload_value['animation_version']:history_record_values.append(history_record_value)
        if operation_command_name=='anchor-history-reset':
            for history_record_value in history_record_values:
                history_identifier_value=history_record_value['id']
                write_record_atomically(ANCHOR_HISTORY_ROOT/history_identifier_value[:19]/history_identifier_value/'history-hidden.json',{'hidden':True})
            return {'cleared':len(history_record_values)}
        return {'items':sorted(history_record_values,key=lambda r:r['id'],reverse=True)}
    if operation_command_name=='anchor-load':
        if set(command_payload_value)!={'id'} or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',command_payload_value['id']):raise ValueError('이력 ID 오류')
        history_identifier_value=command_payload_value['id']
        return {'document':validate_anchor_document(json.loads((ANCHOR_HISTORY_ROOT/history_identifier_value[:19]/history_identifier_value/'coordinates.json').read_text()))}
    raise ValueError('지원하지 않는 앵커 명령')
