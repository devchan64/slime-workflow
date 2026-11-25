"""Prepare and atomically rename selected model directories without replacement.

The caller must first stop users of both paths; this module cannot establish
process quiescence or reload already-running services.
"""
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import stat


LAYOUTS = {'hermes-coding': ('hermes-agent', 'models/hermes-coding'),
           'writer-embedding': ('writer-agent', 'models/qwen3-embedding-0.6b'),
           'translation-model': ('prompt-translation', 'models/translategemma-4b'),
           'heartmula': ('music/music-heartmula', 'models/audio/heartmula'),
           'dasheng-audiogen': ('music/sfx-dasheng-audiogen', 'models/audio/dasheng-audiogen'),
           'flatten-hermes-coding': ('models/hermes-coding', 'hermes-coding'),
           'qwen-model-name': ('hermes-coding', 'qwen3.8-27b-iq4-xs'),
           'flatten-writer-embedding': ('models/qwen3-embedding-0.6b', 'qwen3-embedding-0.6b'),
           'flatten-translation': ('models/translategemma-4b', 'translategemma-4b'),
           'flatten-visual': ('models/flux-report-vision', 'flux-report-vision'),
           'flatten-audio': ('models/audio', 'audio'),
           'audio-demucs': ('audio/heartmula/demucs', 'audio/demucs'),
           'demucs-top': ('audio/demucs', 'demucs'),
           'heartcodec-reference-top': ('audio/heartmula/codec-reference-encoder', 'heartcodec-reference-encoder'),
           'heartcodec-top': ('audio/heartmula/bundle/HeartCodec-oss', 'heartcodec-oss'),
           'heartmula-core-top': ('audio/heartmula/bundle/HeartMuLa-oss-3B', 'heartmula-oss-3b'),
           'dasheng-core-top': ('audio/dasheng-audiogen/model', 'dasheng-audiogen'),
           'flan-t5-top': ('audio/dasheng-audiogen/text-encoder', 'flan-t5-large'),
           'dasheng-tokenizer-top': ('audio/dasheng-audiogen/audio-tokenizer', 'dasheng-tokenizer'),
           'minimax-hf-cache': ('huggingface', 'cache/huggingface'),
           'external-hf-cache': ('cache/huggingface', None)}


def storage_paths(root, name):
    old, new = LAYOUTS[name]
    return root / old, root.parent / '.cache/huggingface' if new is None else root / new


def assess_storage_move(root, name):
    root = Path(root)
    if name not in LAYOUTS or not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError('이관 대상이나 모델 루트가 올바르지 않습니다.')
    source, target = storage_paths(root, name)
    if source.parent.is_symlink() or source.is_symlink() or not source.is_dir():
        raise ValueError('기존 디렉터리를 확인할 수 없습니다.')
    parent = target.parent
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError('대상 상위 경로가 안전하지 않습니다.')
    if target.exists() or target.is_symlink():
        raise ValueError('대상 경로가 이미 존재합니다.')
    files, links = 0, []
    for directory, dirs, names in os.walk(source, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        for entry in dirs + names:
            path = Path(directory) / entry
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                value = os.readlink(path)
                if os.path.isabs(value):
                    raise ValueError('절대 심볼릭 링크가 있어 자동 이관할 수 없습니다.')
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(source):
                    raise ValueError('모델 밖을 참조하는 링크가 있어 자동 이관할 수 없습니다.')
                links.append(path.relative_to(source).as_posix())
            elif stat.S_ISREG(mode):
                files += 1
            elif not stat.S_ISDIR(mode):
                raise ValueError('일반 파일이나 디렉터리가 아닌 항목이 있습니다.')
    info = source.stat()
    return {'id': name, 'source': str(source), 'target': str(target), 'files': files,
            'source_identity': {'device': info.st_dev, 'inode': info.st_ino},
            'relative_links': links, 'requires_quiescence': True}


def _rename_noreplace(source, target):
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, 'renameat2'):
        raise OSError(errno.ENOSYS, 'renameat2를 사용할 수 없습니다.')
    result = libc.renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 1)
    if result != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))


def move_storage(root, name, journal):
    """Rename without replacement; caller is responsible for quiescence."""
    plan = assess_storage_move(root, name)
    source, target = Path(plan['source']), Path(plan['target'])
    target.parent.mkdir(exist_ok=True)
    if target.parent.is_symlink() or source.stat().st_dev != target.parent.stat().st_dev:
        raise ValueError('같은 파일시스템의 안전한 대상 경로가 필요합니다.')
    journal = Path(journal)
    if not journal.is_absolute() or journal.exists() or journal.is_symlink():
        raise ValueError('새 이관 기록 경로가 필요합니다.')
    with journal.open('x', encoding='utf-8') as stream:
        json.dump({**plan, 'rollback': f"{target} → {source}"}, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    # Linux renameat2 makes the no-overwrite check atomic.
    current = source.lstat()
    if source.is_symlink() or (current.st_dev, current.st_ino) != (plan['source_identity']['device'], plan['source_identity']['inode']):
        raise ValueError('기존 디렉터리가 이관 전 교체됐습니다.')
    _rename_noreplace(source, target)
    return plan


def rollback_storage(root, name, journal):
    """Restore the exact renamed directory without replacing another path."""
    root, journal = Path(root), Path(journal)
    if name not in LAYOUTS or not root.is_absolute() or root.is_symlink():
        raise ValueError('복구 대상이 올바르지 않습니다.')
    source, target = storage_paths(root, name)
    if journal.is_symlink() or source.parent.is_symlink() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError('복구 경로에 심볼릭 링크가 있습니다.')
    try:
        record = json.loads(journal.read_text(encoding='utf-8'))
        identity = record['source_identity']
        current = target.lstat()
        if (record['id'] != name or record['source'] != str(source) or record['target'] != str(target)
                or not stat.S_ISDIR(current.st_mode)
                or (current.st_dev, current.st_ino) != (identity['device'], identity['inode'])):
            raise ValueError('기록과 복구할 디렉터리가 일치하지 않습니다.')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('이관 기록 또는 디렉터리를 확인할 수 없습니다.') from error
    _rename_noreplace(target, source)


def move_verified_storage(root, journal, *, name):
    """Hash a quiescent tree before and after rename; roll back on failure.

    The caller is responsible for excluding active readers and writers and for
    verifying every consumer against the new location before accepting the move.
    """
    from workflow.common.model_backup_inventory import inventory_model_tree
    root = Path(root)
    if name not in LAYOUTS:
        raise ValueError('지원하지 않는 이관입니다.')
    plan = assess_storage_move(root, name)
    source, target = Path(plan['source']), Path(plan['target'])
    links = {name: os.readlink(source / name) for name in plan['relative_links']}
    before = inventory_model_tree(source, containment_root=source, hash_content=True)
    if not before['complete']:
        raise ValueError('파일 해시를 확인할 수 없습니다.')
    move_storage(root, name, journal)
    try:
        after = inventory_model_tree(target, containment_root=target, hash_content=True)
        if (not after['complete'] or before['files'].keys() != after['files'].keys()
                or any((value['size'], value['sha256']) != (after['files'][key]['size'], after['files'][key]['sha256'])
                       for key, value in before['files'].items())
                or any(not (target / name).is_symlink() or os.readlink(target / name) != value
                       for name, value in links.items())):
            raise ValueError('이관 후 파일 또는 링크가 일치하지 않습니다.')
    except BaseException:
        rollback_storage(root, name, journal)
        raise
    return {**plan, 'verified_files': len(before['files']), 'verified_links': len(links)}


def move_verified_cache(root, journal, *, name='minimax-hf-cache'):
    """Move the cache only after quiescence; roll back on verification failure."""
    if name not in ('minimax-hf-cache', 'external-hf-cache'):
        raise ValueError('지원하지 않는 캐시 이관입니다.')
    return move_verified_storage(root, journal, name=name)


def move_flattened_with_queue_guard(project_root, journal, *, name, validate, allow_verified_hermes=False):
    """Move one prepared installation while queue and backup admission are held.

    The caller must also exclude independently launched readers and writers.
    Validation runs under the locks and must check the affected consumers.
    """
    if name not in {'flatten-hermes-coding', 'flatten-writer-embedding', 'flatten-translation',
                    'flatten-visual', 'flatten-audio', 'audio-demucs', 'demucs-top', 'heartcodec-reference-top', 'heartcodec-top', 'qwen-model-name',
                    'dasheng-core-top', 'flan-t5-top', 'dasheng-tokenizer-top', 'heartmula-core-top'} or not callable(validate):
        raise ValueError('이관 대상과 소비자 검증이 필요합니다.')
    project_root = Path(project_root)
    model_root = project_root / '.model'
    queue = project_root / '.tmp/gpu-queue'
    active = queue / 'active'
    backup = project_root / '.local/hermes/model-backup-verification'
    for path in (project_root, model_root, queue, active, backup):
        if path.is_symlink() or not path.is_dir():
            raise ValueError('작업 또는 잠금 경로를 확인할 수 없습니다.')
    queue_fd = os.open(queue / 'execution.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(queue_fd, 'r+') as queue_lock:
        fcntl.flock(queue_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        reservations = list(active.iterdir())
        if reservations:
            if not allow_verified_hermes or name not in {'dasheng-core-top', 'flan-t5-top', 'dasheng-tokenizer-top', 'heartmula-core-top'}:
                raise ValueError('GPU 작업 예약이 남아 있어 모델을 이동할 수 없습니다.')
            from workflow.common.gpu_job_queue import open_verified_hermes_process_group
            for reservation in reservations:
                if reservation.is_symlink() or not reservation.is_file():
                    raise ValueError('GPU 예약을 확인할 수 없습니다.')
                record = json.loads(reservation.read_text())
                if record.get('service') != 'hermes-agent' or record.get('cleanup_unverified'):
                    raise ValueError('Hermes 외 GPU 작업 예약이 남아 있습니다.')
                fd = open_verified_hermes_process_group(record)
                if fd is None:
                    raise ValueError('Hermes 예약의 실제 프로세스를 확인할 수 없습니다.')
                os.close(fd)
        backup_fd = os.open(backup / 'worker.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(backup_fd, 'r+') as backup_lock:
            fcntl.flock(backup_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = move_verified_storage(model_root, journal, name=name)
            try:
                validate()
            except BaseException:
                rollback_storage(model_root, name, journal)
                raise
            return result


def move_cache_with_queue_guard(project_root, journal, *, validate=None, name='minimax-hf-cache'):
    """Block queue admission and backup starts while checking and moving cache.

    Independently launched users of the cache must still be checked by the caller.
    """
    from workflow.common.model_storage_layout import resolve_minimax_snapshot
    project_root = Path(project_root)
    model_root = project_root / '.model'
    queue = project_root / '.tmp/gpu-queue'
    active = queue / 'active'
    backup = project_root / '.local/hermes/model-backup-verification'
    for path in (project_root, model_root, queue, active, backup):
        if path.is_symlink() or not path.is_dir():
            raise ValueError('작업 또는 잠금 경로를 확인할 수 없습니다.')
    queue_fd = os.open(queue / 'execution.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(queue_fd, 'r+') as queue_lock:
        fcntl.flock(queue_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if any(active.iterdir()):
            raise ValueError('GPU 작업 예약이 남아 있어 캐시를 이동할 수 없습니다.')
        backup_fd = os.open(backup / 'worker.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(backup_fd, 'r+') as backup_lock:
            fcntl.flock(backup_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            original_snapshot = resolve_minimax_snapshot(model_root)
            if not (original_snapshot / 'text_encoder/config.json').is_file():
                raise ValueError('기존 캐시의 MiniMax 설정을 확인할 수 없습니다.')
            result = move_verified_cache(model_root, journal, name=name)
            try:
                new_snapshot = resolve_minimax_snapshot(model_root)
                expected_root = storage_paths(model_root, name)[1]
                if (not new_snapshot.is_relative_to(expected_root)
                        or not (new_snapshot / 'text_encoder/config.json').is_file()):
                    raise ValueError('새 캐시의 MiniMax 설정을 확인할 수 없습니다.')
                if validate is not None:
                    validate()
            except BaseException:
                rollback_storage(model_root, name, journal)
                raise
            return result
