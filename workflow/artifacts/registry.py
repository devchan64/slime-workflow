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
            connection.execute('PRAGMA user_version=1')
        elif version != 1 or [row['name'] for row in tables] != ['artifacts']:
            raise ValueError('지원하지 않는 산출물 registry DB입니다.')
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


def resolve(path, artifact_id, version):
    identifier(artifact_id, 'artifactId')
    identifier(version, 'version')
    path = Path(path).resolve(strict=True)
    # 조회는 DB나 스키마를 생성·갱신하지 않는다.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        if connection.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('지원하지 않는 산출물 registry DB입니다.')
        row = connection.execute('SELECT * FROM artifacts WHERE artifact_id=? AND version=?',
                                 (artifact_id, version)).fetchone()
    if row is None:
        raise ValueError('등록되지 않은 산출물 ID/버전입니다.')
    data = validate_pair(row['root'], Path(row['root']) / row['sidecar_path'])
    if (data['artifactId'] != artifact_id or data['version'] != version
            or data['sha256'] != row['content_hash'] or metadata_hash(data) != row['metadata_hash']):
        raise ValueError('등록 이후 산출물 또는 sidecar가 변경되었습니다. 새 버전으로 등록해야 합니다.')
    return data
