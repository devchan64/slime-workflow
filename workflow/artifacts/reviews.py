"""검수 근거·검수 대상 해시를 보존한다. 사용자 승인 여부를 자동 추정하지 않는다."""
from .registry import database, registered_entry, resolve
from .sidecar import identifier, text, digest


def record_review(path, artifact_id, version, *, review_id, decision, reviewer, evidence_ref,
                  content_hash, metadata_hash, previous_review_id=None):
    identifier(review_id, 'reviewId')
    if type(decision) is not str or decision not in ('APPROVED', 'REJECTED'):
        raise ValueError('검수 결정은 APPROVED 또는 REJECTED여야 합니다.')
    text(reviewer, 'reviewer'); text(evidence_ref, 'evidenceRef')
    digest(content_hash); digest(metadata_hash)
    if previous_review_id is not None:
        identifier(previous_review_id, 'previousReviewId')
    entry = registered_entry(path, artifact_id, version)
    resolve(path, artifact_id, version)
    record = dict(review_id=review_id, artifact_id=artifact_id, version=version, decision=decision,
                  reviewer=reviewer, evidence_ref=evidence_ref, content_hash=content_hash,
                  metadata_hash=metadata_hash, previous_review_id=previous_review_id)
    with database(path, entry['root']) as connection:
        old = connection.execute('SELECT * FROM reviews WHERE review_id=?', (review_id,)).fetchone()
        if old is not None:
            if any(old[key] != value for key, value in record.items()):
                raise ValueError('검수 ID를 다른 내용으로 재사용할 수 없습니다.')
            return dict(old)
        if (content_hash, metadata_hash) != (entry['content_hash'], entry['metadata_hash']):
            raise ValueError('검수한 대상의 해시와 등록된 대상이 다릅니다.')
        head = connection.execute('SELECT review_id FROM review_heads WHERE artifact_id=? AND version=?',
                                  (artifact_id, version)).fetchone()
        if (head['review_id'] if head else None) != previous_review_id:
            raise ValueError('검수 상태가 변경되었습니다. 최신 이력을 확인하세요.')
        connection.execute('''INSERT INTO reviews
            (review_id,artifact_id,version,decision,reviewer,evidence_ref,content_hash,metadata_hash,previous_review_id)
            VALUES (:review_id,:artifact_id,:version,:decision,:reviewer,:evidence_ref,:content_hash,:metadata_hash,:previous_review_id)''', record)
        connection.execute('''INSERT INTO review_heads VALUES (?,?,?)
            ON CONFLICT(artifact_id,version) DO UPDATE SET review_id=excluded.review_id''',
            (artifact_id, version, review_id))
        return dict(connection.execute('SELECT * FROM reviews WHERE review_id=?', (review_id,)).fetchone())


def current_review(path, artifact_id, version):
    from contextlib import closing
    from pathlib import Path
    import sqlite3
    entry = registered_entry(path, artifact_id, version)
    resolve(path, artifact_id, version)
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        if connection.execute('PRAGMA user_version').fetchone()[0] == 1:
            return None
        row = connection.execute('''SELECT r.* FROM review_heads h JOIN reviews r ON r.review_id=h.review_id
            WHERE h.artifact_id=? AND h.version=?''', (artifact_id, version)).fetchone()
    if row is not None and (row['artifact_id'], row['version'], row['content_hash'], row['metadata_hash']) != (
            artifact_id, version, entry['content_hash'], entry['metadata_hash']):
        raise ValueError('검수 기록과 등록 대상이 일치하지 않습니다.')
    return dict(row) if row is not None else None
