"""경량 모델 관측과 생성기 우선순위를 별도로 저장한다."""
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / '.local/model-catalog/generator-availability.json'
PRIORITY_PATH = ROOT / 'workflow/config/generator-priorities.json'
INTERVAL_SECONDS = 300
MAX_AGE_SECONDS = 600
_ALLOWED = {'image': {'minimax-h3-image', 'flux-image'},
            'video_first_frame': {'minimax-h3-i2v', 'wan22-i2v', 'wan22-vace'}}


def read_priorities(path=PRIORITY_PATH):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 1 or set(data) != {'schema_version', *_ALLOWED}:
        raise ValueError('생성기 우선순위 형식 오류')
    for kind, allowed in _ALLOWED.items():
        values = data[kind]
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or v not in allowed for v in values) or len(values) != len(set(values)):
            raise ValueError('생성기 우선순위 항목 오류')
    return data


def collect_availability():
    from workflow.common.model_file_inventory import resolve_model_inventory_paths
    from workflow.common.model_download_records import observe_model_download_records
    from workflow.common.model_catalog import read_catalog
    from workflow.common.model_backup_service import read_model_source
    from workflow.common.model_backup_metadata import model_metadata
    from generators.minimax_h3.contracts import inspect_runtime as inspect_video
    from generators.minimax_h3_image.contracts import inspect_runtime as inspect_image
    from workflow.generators.minimax_h3_ref2va.assets import inspect_runtime as inspect_ref2va
    from generators.image.flux_model_prepare import FLUX_MODEL_DIRECTORY, inspect_flux_model_file_sizes, read_flux_model_lock
    def inspect_flux():
        ready = inspect_flux_model_file_sizes(FLUX_MODEL_DIRECTORY, read_flux_model_lock())
        return {'ready': ready, 'message': 'FLUX 모델 파일 크기 확인 · 실행 환경은 별도' if ready else 'FLUX 모델 파일 누락 또는 크기 불일치'}
    services = {}
    paths = resolve_model_inventory_paths()
    inspectors = {'minimax-h3-image': inspect_image, 'minimax-h3-i2v': inspect_video, 'minimax-h3-ref2va': inspect_ref2va, 'flux-image': inspect_flux}
    for name, entries in paths.items():
        try:
            missing = [str(Path(p).relative_to(ROOT)) for p in entries if not Path(p).exists()]
            if name in inspectors:
                result = inspectors[name]()
                state = 'ready' if result.get('ready') is True else 'missing'
                detail = str(result.get('message', ''))[:1000]
            else:
                state = 'missing' if missing else 'unknown'
                detail = '필수 경로 없음' if missing else '경로 존재만 확인됨 · 전체 준비 여부 미확인'
            services[name] = {'state': state, 'missing_paths': missing, 'detail': detail}
        except (OSError, ValueError, TypeError) as error:
            services[name] = {'state': 'unknown', 'missing_paths': [], 'detail': type(error).__name__}
    try:
        records = observe_model_download_records()
        downloads = [{k: item.get(k) for k in ('model', 'status', 'stage', 'bytes', 'total_bytes')} for item in records]
        download_error = None
    except (OSError, ValueError, TypeError) as error:
        downloads, download_error = [], type(error).__name__
    try:
        configured_source, _ = read_model_source()
        local_source_matches = Path(configured_source).resolve() == (ROOT / '.model').resolve()
    except (OSError, ValueError, TypeError):
        local_source_matches = False
    models = []
    for item in read_catalog()['components']:
        relative = item.get('path')
        try:
            path = ROOT / '.model' / relative
            presence = 'present' if path.exists() else 'missing'
        except (OSError, TypeError):
            presence = 'unknown'
        metadata = None
        if local_source_matches and isinstance(relative, str) and '/' not in relative and path.is_dir() and not path.is_symlink():
            try:
                metadata = model_metadata(relative, service_paths=paths)
            except (OSError, ValueError, TypeError, KeyError):
                metadata = {'manifest_state': 'unavailable'}
        models.append({'id': item['id'], 'label': item['label'], 'kind': item['kind'],
                       'path': relative, 'source': item.get('source'), 'revision': item.get('revision'),
                       'services': item.get('services', []), 'presence': presence,
                       'manifest': metadata,
                       'downloads': [record for record in downloads if item.get('source') and record.get('model') == item['source']]})
    return {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
            'models': models, 'services': services, 'downloads': downloads, 'download_error': download_error,
            'note': '경량 파일 상태 관측이며 해시·GPU 실행 가능성을 보증하지 않습니다.'}


def write_availability(data, path=STATUS_PATH):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix='.availability-', delete=False) as out:
            temporary = Path(out.name)
            json.dump(data, out, ensure_ascii=False, allow_nan=False)
            out.flush(); os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_fresh_availability(path=STATUS_PATH, *, now=None):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        observed = datetime.fromisoformat(data['observed_at'])
        if observed.tzinfo is None or data.get('schema_version') != 1 or not isinstance(data.get('services'), dict):
            return None
        age = ((now or datetime.now(timezone.utc)) - observed).total_seconds()
        return data if 0 <= age <= MAX_AGE_SECONDS else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def preferred_ready(kind, candidates, *, status_path=STATUS_PATH, priority_path=PRIORITY_PATH):
    try:
        priorities = read_priorities(priority_path)[kind]
        snapshot = read_fresh_availability(status_path)
        if snapshot is None:
            return None
        return next((name for name in priorities if name in candidates and snapshot['services'].get(name, {}).get('state') == 'ready'), None)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def start_availability_scheduler(stop_event, interval=INTERVAL_SECONDS):
    def run():
        while not stop_event.is_set():
            try:
                write_availability(collect_availability())
            except Exception:
                logging.getLogger(__name__).exception('모델 상태 수집 실패')
            if stop_event.wait(interval):
                return
    thread = threading.Thread(target=run, name='model-availability', daemon=True)
    thread.start()
    return thread
