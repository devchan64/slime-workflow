"""AMD GPU 프로세스와 부모 실행 명령을 읽는 공용 상태 조회."""
import json
import re
import subprocess
import threading
import time
from pathlib import Path

_status_lock = threading.Lock()
_status_cache = (0, {})


def identify_gpu_command(process_identifier):
    process_chain = []
    for _ in range(12):
        try:
            root = Path('/proc') / str(process_identifier)
            process_chain.append((root/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace'))
            status = (root/'status').read_text()
            process_identifier = int(re.search(r'^PPid:\s+(\d+)', status, re.M)[1])
            if process_identifier <= 1:
                break
        except (OSError, ValueError, TypeError):
            break
    combined = ' '.join(process_chain)
    generation_id = re.search(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', combined)
    anny_id = re.search(r'anny-attribute-renderer/([a-f0-9]{8})', combined)
    label = '외부 GPU 작업'
    for marker, name in [('generators/kimodo/','Kimodo 모션·ANNY 렌더'),('character-animation','캐릭터 애니메이션'),('momask','MoMask 모션 생성'),('anny-attribute','ANNY 속성 렌더'),('tile-map','타일맵 생성'),('run_qwen_2511','Qwen 2511 참조 생성'),('run_qwen_2512','Qwen 2512 이미지 생성')]:
        if marker in combined:
            label = name
            break
    return {'command':label,'id':generation_id[0] if generation_id else anny_id[1] if anny_id else None}


def read_gpu_status():
    global _status_cache
    with _status_lock:
        if time.monotonic()-_status_cache[0] < 3:
            return _status_cache[1]
        try:
            result = subprocess.run(['amd-smi','process','-G','--json'],capture_output=True,text=True,timeout=10,check=True)
            processes = []
            for current_gpu_record in json.loads(result.stdout):
                for current_process_record in current_gpu_record.get('process_list', []):
                    current_process_values = current_process_record['process_info']
                    if current_process_values == 'No running processes detected':
                        continue
                    pid = current_process_values['pid']
                    current_memory_record = current_process_values['mem_usage']
                    current_memory_value = (current_memory_record['value'] + 1048575) // 1048576 if current_memory_record['unit'] == 'B' else None
                    processes.append({'pid':pid,'memory_mib':current_memory_value,**identify_gpu_command(pid)})
            memory_result = subprocess.run(['amd-smi','metric','-m','--json'],capture_output=True,text=True,timeout=10,check=True)
            memory_total_mib = memory_used_mib = memory_free_mib = 0
            for current_gpu_record in json.loads(memory_result.stdout)['gpu_data']:
                current_memory_values = current_gpu_record['mem_usage']
                memory_total_mib += int(current_memory_values['total_gtt']['value'])
                memory_used_mib += int(current_memory_values['used_gtt']['value'])
                memory_free_mib += int(current_memory_values['free_gtt']['value'])
            if memory_total_mib <= 0:
                raise ValueError('GPU 메모리 정보를 읽을 수 없습니다.')
            record = {'status':'busy' if processes else 'idle','processes':processes,
                'memory_total_mib':memory_total_mib,'memory_used_mib':memory_used_mib,'memory_free_mib':memory_free_mib}
        except (OSError,subprocess.SubprocessError,ValueError,KeyError,TypeError):
            record = {'status':'unavailable','processes':[]}
        _status_cache = (time.monotonic(),record)
        return record
