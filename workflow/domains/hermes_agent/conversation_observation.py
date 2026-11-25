"""대화 작업과 상주 모델의 관측 신호를 구분해 읽는다."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re


_PROMPT_PROGRESS = re.compile(r'task\s+(\d+)\s+\| prompt processing, n_tokens\s*=\s*(\d+), progress\s*=\s*([0-9.]+),.*?/\s*([0-9.]+) tokens per second')
_GENERATION = re.compile(r'\bn_gen\s*=\s*(\d+),\s*tg\s*=\s*[\d.]+ t/s,\s*tg_3s\s*=\s*(\d+(?:\.\d+)?) t/s')
_FINAL_SPEED = re.compile(r'task\s+(\d+)\s+\|\s+eval time\s*=.*?\s+(\d+) tokens.*?([0-9.]+) tokens per second')
_TASK = re.compile(r'task\s+(\d+)\s+\|')

def model_token_signal(log):
    """상주 모델 전체 로그의 최신 작업만 해석한다. 대화 작업별 신호가 아니다."""
    try:
        with log.open('rb') as f:
            f.seek(max(0,log.stat().st_size-131072)); lines=f.read().decode('utf-8',errors='replace').splitlines()
        task=None;progress=None;speed=None;generation=None
        for line in lines:
            match=_TASK.search(line)
            if not match: continue
            if match.group(1)!=task: task=match.group(1);progress=None;speed=None;generation=None
            match=_PROMPT_PROGRESS.search(line)
            if match: progress={'tokens':int(match.group(2)),'fraction':float(match.group(3)),'tokens_per_second':float(match.group(4))}
            sample=_GENERATION.search(line)
            if sample: generation={'tokens':int(sample[1]), 'tokens_per_second':float(sample[2])}
            match=_FINAL_SPEED.search(line)
            if match: speed={'tokens':int(match.group(2)),'tokens_per_second':float(match.group(3))}
        result={}
        if progress: result['input']=progress
        if speed: result['output_completed']=speed
        elif generation: result['output_sample']=generation
        return result
    except (OSError,ValueError,OverflowError): return {}

def conversation_observation(job_path, status, session_id):
    result={'executor': 'not_running', 'last_event_at':None, 'model':{'state':'unknown'}}
    if status.get('status') not in ('queued','running','unknown'): return result
    path=Path(job_path)
    try:
        from workflow.domains.hermes_agent.resident_chat_executor import observe_resident_chat_status
        from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
        request=read_bounded_delegation_record(path/'request.json')
        if isinstance(request,dict) and request.get('resident_id'):
            observed=observe_resident_chat_status(path,status)
            result['executor']='verified' if observed.get('status') in ('queued','running') else 'unknown'
            from workflow.domains.hermes_agent.resident_queue import RESIDENT_ROOT, inspect_resident
            resident_id=request['resident_id']
            if not isinstance(request.get('context'),dict) or request['context'].get('session_id') != session_id:
                raise ValueError('session mismatch')
            model=inspect_resident(resident_id,session_id)
            result['model']={'state':model.get('state','unknown')}
            if result['executor']=='verified':
                try:
                    observation=read_bounded_delegation_record(path/'model-observation.json')
                    if isinstance(observation,dict) and type(observation.get('active')) is int and 0 <= observation['active'] <= 100:
                        result['request']={key:observation.get(key) for key in ('active','last_request_at','last_response_at','last_end_at')}
                except (OSError,ValueError,TypeError): pass
            if model.get('state')=='ready' and re.fullmatch(r'[A-Za-z0-9_-]{8,80}',resident_id):
                log=RESIDENT_ROOT/resident_id/'server.log'
                if log.is_file() and not log.is_symlink():
                    stat=log.stat()
                    result['model']['last_log_at']=datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat()
                    result['model']['tokens']=model_token_signal(log)
    except (OSError,ValueError,TypeError,KeyError):
        result['executor']='unknown'
    try:
        event=path/'hermes-events.jsonl'
        if event.is_file() and not event.is_symlink():
            with event.open('rb') as f:
                f.seek(max(0,event.stat().st_size-128000));lines=f.read().decode('utf-8',errors='replace').splitlines()
            for line in reversed(lines):
                try: item=json.loads(line)
                except (ValueError,TypeError): continue
                if not isinstance(item,dict): continue
                stamp=item.get('timestamp')
                if item.get('type') in ('tool_use','tool_result','result') and isinstance(stamp,(int,float)) and not isinstance(stamp,bool):
                    result['last_event_at']=datetime.fromtimestamp(stamp/1000,timezone.utc).isoformat();break
    except (OSError,ValueError,OverflowError,TypeError): pass
    return result
