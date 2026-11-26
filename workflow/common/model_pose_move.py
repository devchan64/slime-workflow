"""Move one pose component with a durable recovery record and admission locks."""
import fcntl
import hashlib
import json
import os
from pathlib import Path

from workflow.common.model_storage_move import _rename_noreplace

COMPONENTS = {
    'yolox-l': ('yolox_l.onnx', 'yolox_l.cuda.onnx'),
    'dwpose-ll-ucoco-384': ('dw-ll_ucoco_384.onnx', 'dw-ll_ucoco_384.cuda.onnx'),
}


def _digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('포즈 모델 파일을 확인할 수 없습니다.')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('포즈 모델 검사 중 파일이 변경됐습니다.')
    return digest, before


def move_pose_component(project_root, component, journal, validate):
    """Move a pair under locks; caller must exclude independent file users."""
    project_root = Path(project_root)
    root = project_root/'.model'
    source, target = root/'wan22-fun-pose', root/component
    journal = Path(journal)
    if component not in COMPONENTS or not callable(validate) or not journal.is_absolute() or journal.exists() or journal.is_symlink():
        raise ValueError('이관 대상 또는 기록이 올바르지 않습니다.')
    queue = project_root/'.tmp/gpu-queue'
    backup = project_root/'.local/hermes/model-backup-verification'
    for path in (project_root, root, source, queue, queue/'active', backup):
        if path.is_symlink() or not path.is_dir():
            raise ValueError('이관 또는 잠금 경로를 확인할 수 없습니다.')
    if target.exists() or target.is_symlink():
        raise ValueError('대상 경로가 이미 존재합니다.')
    with os.fdopen(os.open(queue/'execution.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK), 'r+') as queue_lock:
        fcntl.flock(queue_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if any((queue/'active').iterdir()):
            raise ValueError('GPU 작업 예약이 남아 있습니다.')
        with os.fdopen(os.open(backup/'worker.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK), 'r+') as backup_lock:
            fcntl.flock(backup_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            record_path = source/'prepared.json'
            if record_path.is_symlink():
                raise ValueError('준비 기록에 심볼릭 링크가 있습니다.')
            prepared = json.loads(record_path.read_text())
            hashes = prepared['files']
            identities = {}
            for name in COMPONENTS[component]:
                digest, info = _digest(source/name)
                if hashes.get(name) != digest:
                    raise ValueError('준비 기록과 파일 해시가 다릅니다.')
                identities[name] = {'device': info.st_dev, 'inode': info.st_ino, 'size': info.st_size, 'sha256': digest}
            record = {'component': component, 'source': str(source), 'target': str(target), 'files': identities,
                      'revision': prepared['revision'], 'rollback': '각 파일의 기록된 inode를 확인하고 원래 디렉터리로 덮어쓰기 없이 이동'}
            with journal.open('x', encoding='utf-8') as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            target.mkdir()
            moved = []
            try:
                for name in COMPONENTS[component]:
                    _rename_noreplace(source/name, target/name)
                    moved.append(name)
                for name in moved:
                    digest, info = _digest(target/name)
                    expected = identities[name]
                    if (digest, info.st_dev, info.st_ino, info.st_size) != (expected['sha256'], expected['device'], expected['inode'], expected['size']):
                        raise ValueError('이관 후 파일이 일치하지 않습니다.')
                prepared_path = target/'prepared.json'
                with prepared_path.open('x', encoding='utf-8') as stream:
                    json.dump({'revision': prepared['revision'], 'files': {name: hashes[name] for name in moved}}, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                validate()
            except BaseException:
                # Refuse to replace anything if an external actor changed the paths.
                for name in reversed(moved):
                    current = (target/name).lstat()
                    expected = identities[name]
                    if (current.st_dev, current.st_ino) != (expected['device'], expected['inode']):
                        raise RuntimeError('파일이 바뀌어 자동 복구를 중단했습니다. 이관 기록을 확인하세요.')
                    _rename_noreplace(target/name, source/name)
                if (target/'prepared.json').exists():
                    (target/'prepared.json').unlink()
                target.rmdir()
                raise
            return record
