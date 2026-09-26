"""실제 CUDA 프로세스와 부모 실행 명령을 읽는 공용 GPU 상태 조회."""
import csv
import io
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
    for marker, name in [('character-animation','캐릭터 애니메이션'),('momask','MoMask 모션 생성'),('anny-attribute','ANNY 속성 렌더'),('tile-map','타일맵 생성'),('run_qwen_2511','Qwen 2511 참조 생성'),('run_qwen_2512','Qwen 2512 이미지 생성')]:
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
            result = subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3,check=True)
            processes = []
            for row in csv.reader(io.StringIO(result.stdout)):
                if len(row)!=2:
                    continue
                pid = int(row[0].strip())
                processes.append({'pid':pid,'memory_mib':int(row[1].strip()) if row[1].strip().isdigit() else None,**identify_gpu_command(pid)})
            record = {'status':'busy' if processes else 'idle','processes':processes}
        except (OSError,subprocess.SubprocessError,ValueError):
            record = {'status':'unavailable','processes':[]}
        _status_cache = (time.monotonic(),record)
        return record
