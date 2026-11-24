"""공용 이력에 표시할 제한된 저장 입력 요약을 읽는다."""
import json
import math
import os
import re
import stat
from urllib.parse import urlsplit

from workflow.common.record_folders import resolve_record_folder
from workflow.common.management_transport import send_management_json_response


def read_history_summary(directory, service=''):
    descriptor=os.open(directory/'request.json', os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('입력 파일 형식 오류')
        raw=handle.read(1048577)
    if len(raw)>1048576:
        raise ValueError('입력 파일 크기 초과')
    request=json.loads(raw)
    if not isinstance(request,dict):
        raise ValueError('입력 기록 형식 오류')
    summary={}
    tag=request.get('tag')
    if isinstance(tag,str) and len(tag)<=80 and '\n' not in tag and '\r' not in tag and tag.strip():
        summary['tag']=tag.strip()
    for key in ('width','height','frames','steps','seed'):
        value=request.get(key)
        if type(value) is int and 0<=value<=4294967295:
            summary[key]=value
    for key in ('pose_include_hands','pose_include_face'):
        value=request.get(key)
        if type(value) is bool:
            summary[key]=value
    if service in ('wan21-i2v','wan21-t2v'):
        enabled=request.get('action_lora')
        variant=request.get('action_variant','fight')
        variants=('fight','attack_high','attack_low') if service=='wan21-i2v' else ('fight',)
        if type(enabled) is bool and (not enabled or variant in variants):
            summary['action_lora']=enabled
            if enabled:
                summary['action_variant']=variant
                strength=request.get('action_strength')
                if type(strength) in (int,float) and math.isfinite(strength) and 0 < strength <= 2:
                    summary['action_strength']=strength
    duration=request.get('duration_seconds')
    if type(duration) in (int,float) and math.isfinite(duration) and 0<duration<=3600:
        summary['duration_seconds']=duration
    return summary


def audio_result_available(directory,service):
    """완료된 시도의 관리 파일만 관측하며, 유효하지 않은 경로는 표시하지 않는다."""
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    try:
        status=read_bounded_delegation_record(directory/'status.json')
        result=read_bounded_delegation_record(directory/'result.json')
        if status.get('status')!='completed' or not isinstance(result,dict):return False
        attempt=result.get('attempt')
        if not isinstance(attempt,str) or not re.fullmatch(r'[a-f0-9]{32}',attempt):return False
        attempts=directory/'attempts';attempt_dir=attempts/attempt
        filename='sound.wav' if service=='sfx-dasheng-audiogen' else 'music.wav'
        audio=attempt_dir/filename
        return not attempts.is_symlink() and not attempt_dir.is_symlink() and not audio.is_symlink() and audio.is_file() and attempt_dir.resolve().parent==attempts.resolve()
    except (OSError,ValueError,TypeError,AttributeError):return False


def video_image_attempt(directory):
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    try:
        status_path = directory / 'status.json'
        status = read_bounded_delegation_record(status_path) if status_path.exists() else {}
        if not isinstance(status, dict) or status.get('status') == 'queued':
            return None
        if status.get('status') == 'running':
            pointer_path = directory / 'current-attempt.json'
            pointer = read_bounded_delegation_record(pointer_path)
            if not isinstance(pointer, dict) or pointer_path.stat().st_mtime_ns < status_path.stat().st_mtime_ns:
                return None
            attempt = pointer.get('id')
        else:
            result = read_bounded_delegation_record(directory / 'result.json')
            attempt = result.get('attempt') if isinstance(result, dict) else None
        if not isinstance(attempt,str) or not re.fullmatch(r'[a-f0-9]{32}',attempt):
            return None
        attempts=directory/'attempts'; attempt_dir=attempts/attempt; image=attempt_dir/'output-000.png'
        if attempts.is_symlink() or attempt_dir.is_symlink() or image.is_symlink() or not image.is_file() or attempt_dir.resolve().parent!=attempts.resolve():
            return None
        return attempt
    except (OSError,ValueError,TypeError):
        return None


def handle_history_summaries_request(handler, routes):
    if urlsplit(handler.path).path!='/management/history-summaries':
        return False
    try:
        from workflow.common.management_environment import validate_loopback_request_host
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES
        origin=validate_loopback_request_host(handler)
        if handler.headers.get('Origin')!=origin or handler.headers.get('Content-Type','').split(';')[0]!='application/json':
            raise ValueError('동일 출처 JSON 요청이 필요합니다.')
        length=int(handler.headers.get('Content-Length','0'))
        if not 0<length<=4096:
            raise ValueError('요청 크기 오류')
        payload=json.loads(handler.rfile.read(length))
        if not isinstance(payload,dict) or set(payload)!={'service','ids'} or not isinstance(payload['service'],str) or payload['service'] not in MANAGEMENT_SERVICE_ROUTES:
            raise ValueError('생성기 요청 오류')
        ids=payload['ids']
        if not isinstance(ids,list) or len(ids)>30 or len(set(ids))!=len(ids) or any(not isinstance(id,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',id) for id in ids):
            raise ValueError('이력 ID 목록 오류')
        route=MANAGEMENT_SERVICE_ROUTES[payload['service']]
        summaries={}
        for id in ids:
            try:
                directory=resolve_record_folder(routes,route,id)
                summaries[id]=read_history_summary(directory,payload['service'])
                if payload['service'] in {'minimax-h3-image','flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless','flux-expression'}:
                    image=directory/'result.png'
                    summaries[id]['image_available']=not image.is_symlink() and image.is_file()
                elif payload['service'] in {'wan22-fun-control','wan22-vace','wan22-i2v','minimax-h3-i2v','wan21-t2v','wan21-i2v','wan22-animate2','dwpose','kimodo'}:
                    summaries[id]['image_attempt']=video_image_attempt(directory)
                elif payload['service'] in {'music-heartmula','music-minimax','music-magenta','sfx-dasheng-audiogen'}:
                    summaries[id]['audio_available']=audio_result_available(directory,payload['service'])
            except (OSError,ValueError,TypeError):
                continue
        send_management_json_response(handler,200,{'summaries':summaries})
    except (ValueError,TypeError,OSError) as error:
        send_management_json_response(handler,400,{'error':str(error)})
    return True
