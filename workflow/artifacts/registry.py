"""로컬 산출물 ID/버전 색인. 원본 변경은 조회 시 재검증하며 덮어쓰지 않는다."""
from contextlib import contextmanager, closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from .sidecar import validate_pair, identifier


def metadata_hash(data):
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@contextmanager
def database(path, root):
    path, root = Path(path).resolve(), Path(root).resolve(strict=True)
    if path.is_relative_to(root):
        raise ValueError('registry DB는 산출물 루트 밖에 지정해야 합니다.')
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        connection.execute('BEGIN IMMEDIATE')
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if version == 0 and not tables:
            connection.execute('''CREATE TABLE artifacts (
                artifact_id TEXT NOT NULL, version TEXT NOT NULL,
                root TEXT NOT NULL, sidecar_path TEXT NOT NULL,
                content_hash TEXT NOT NULL, metadata_hash TEXT NOT NULL,
                PRIMARY KEY(artifact_id, version))''')
            version = 1
            tables = [{'name': 'artifacts'}]
        expected = {'artifacts'} if version == 1 else {'artifacts', 'reviews', 'review_heads'}
        if version not in (1, 2) or {row['name'] for row in tables} != expected:
            raise ValueError('지원하지 않는 산출물 registry DB입니다.')
        if version == 1:
            connection.execute('''CREATE TABLE reviews (
                review_id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL, version TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('APPROVED','REJECTED')),
                reviewer TEXT NOT NULL, evidence_ref TEXT NOT NULL,
                content_hash TEXT NOT NULL, metadata_hash TEXT NOT NULL, previous_review_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(artifact_id,version) REFERENCES artifacts(artifact_id,version))''')
            connection.execute('''CREATE TABLE review_heads (
                artifact_id TEXT NOT NULL, version TEXT NOT NULL, review_id TEXT NOT NULL REFERENCES reviews(review_id),
                PRIMARY KEY(artifact_id,version),
                FOREIGN KEY(artifact_id,version) REFERENCES artifacts(artifact_id,version))''')
            for action in ('UPDATE', 'DELETE'):
                connection.execute(f"CREATE TRIGGER reviews_no_{action.lower()} BEFORE {action} ON reviews BEGIN SELECT RAISE(ABORT, '검수 이력 변경 금지'); END")
            connection.execute('PRAGMA user_version=2')
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def register(path, root, sidecar):
    data = validate_pair(root, sidecar)
    root = Path(root).resolve(strict=True)
    entry = dict(artifact_id=data['artifactId'], version=data['version'], root=str(root),
                 sidecar_path=str(Path(sidecar).resolve(strict=True).relative_to(root)),
                 content_hash=data['sha256'], metadata_hash=metadata_hash(data))
    with database(path, root) as connection:
        old = connection.execute('SELECT * FROM artifacts WHERE artifact_id=? AND version=?',
                                 (entry['artifact_id'], entry['version'])).fetchone()
        if old is not None:
            if dict(old) != entry:
                raise ValueError('같은 산출물 ID/버전은 다른 내용이나 경로로 덮어쓸 수 없습니다.')
            return entry
        connection.execute('INSERT INTO artifacts VALUES (:artifact_id,:version,:root,:sidecar_path,:content_hash,:metadata_hash)', entry)
    return entry


def registered_entry(path, artifact_id, version):
    identifier(artifact_id, 'artifactId')
    identifier(version, 'version')
    path = Path(path).resolve(strict=True)
    # 조회는 DB나 스키마를 생성·갱신하지 않는다.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        if connection.execute('PRAGMA user_version').fetchone()[0] not in (1, 2):
            raise ValueError('지원하지 않는 산출물 registry DB입니다.')
        row = connection.execute('SELECT * FROM artifacts WHERE artifact_id=? AND version=?',
                                 (artifact_id, version)).fetchone()
    if row is None:
        raise ValueError('등록되지 않은 산출물 ID/버전입니다.')
    return dict(row)


def resolve(path, artifact_id, version):
    row = registered_entry(path, artifact_id, version)
    data = validate_pair(row['root'], Path(row['root']) / row['sidecar_path'])
    if (data['artifactId'] != artifact_id or data['version'] != version
            or data['sha256'] != row['content_hash'] or metadata_hash(data) != row['metadata_hash']):
        raise ValueError('등록 이후 산출물 또는 sidecar가 변경되었습니다. 새 버전으로 등록해야 합니다.')
    return data


def archive_register(path, root, sidecar):
    """검증된 원본 쌍을 버전별 보관소에 복사한 뒤 같은 트랜잭션에서 색인한다."""
    import os
    import shutil
    import tempfile

    data = validate_pair(root, sidecar)
    root, sidecar = Path(root).resolve(strict=True), Path(sidecar).resolve(strict=True)
    relative = sidecar.relative_to(root)
    store = Path(path).resolve().with_suffix('.artifacts')
    destination = store / data['artifactId'] / data['version']
    if destination.is_relative_to(root):
        raise ValueError('보관소는 원본 루트 밖에 있어야 합니다.')
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError('보관소 경로의 심볼릭 링크는 허용하지 않습니다.')
    entry = dict(artifact_id=data['artifactId'], version=data['version'], root=str(destination),
                 sidecar_path=str(relative), content_hash=data['sha256'], metadata_hash=metadata_hash(data))
    def check(directory):
        copied = validate_pair(directory, directory / relative)
        if copied != data:
            raise ValueError('보관본이 등록하려는 원본과 다릅니다. 덮어쓰지 않습니다.')
    with database(path, root) as connection:
        old = connection.execute('SELECT * FROM artifacts WHERE artifact_id=? AND version=?',
                                 (entry['artifact_id'], entry['version'])).fetchone()
        if old is not None and dict(old) != entry:
            raise ValueError('기존 ID/버전의 등록 내용이나 보관 경로를 변경할 수 없습니다.')
        if destination.exists():
            check(destination)
        elif old is not None:
            raise ValueError('등록된 보관본이 없습니다. 자동 재생성하지 않습니다.')
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.pending-', dir=destination.parent) as temporary:
                staging = Path(temporary) / 'pair'
                staged_sidecar = staging / relative
                staged_source = staging / data['sourcePath']
                staged_sidecar.parent.mkdir(parents=True)
                shutil.copyfile(root / data['sourcePath'], staged_source)
                shutil.copyfile(sidecar, staged_sidecar)
                check(staging)
                # 완성된 쌍만 노출하고 보관 파일에는 쓰기 비트를 부여하지 않는다.
                for file in (staged_source, staged_sidecar):
                    with file.open('rb') as stream:
                        os.fsync(stream.fileno())
                    file.chmod(0o444)
                os.rename(staging, destination)
        if old is None:
            connection.execute('INSERT INTO artifacts VALUES (:artifact_id,:version,:root,:sidecar_path,:content_hash,:metadata_hash)', entry)
    return entry
