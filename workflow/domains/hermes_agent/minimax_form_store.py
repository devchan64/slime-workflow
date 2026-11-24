"""Versioned MiniMax form instances, independent of a browser or chat turn.

The submission snapshot is pinned before dispatch.  An interrupted dispatch
remains uncertain and must be reconciled with the receipt, never resubmitted
with a different version.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

SERVICES = frozenset(('minimax-h3-image', 'minimax-h3-i2v'))
ID = re.compile(r'[a-f0-9]{32}')
MAX_BYTES = 39000000


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('대화 또는 폼 식별자 형식 오류')
    return value


def _encode(request):
    if not isinstance(request, dict):
        raise ValueError('폼 입력은 객체여야 합니다.')
    data = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(data.encode('utf-8')) > MAX_BYTES:
        raise ValueError('폼 첨부를 포함해 39MB 이하여야 합니다.')
    return data, hashlib.sha256(data.encode('utf-8')).hexdigest()


class MiniMaxFormStore:
    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError('폼 저장 경로는 심볼릭 링크일 수 없습니다.')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('CREATE TABLE IF NOT EXISTS forms (session_id TEXT NOT NULL, form_id TEXT NOT NULL, service TEXT NOT NULL, source_job_id TEXT NOT NULL, revision INTEGER NOT NULL, state TEXT NOT NULL, request_id TEXT, job_id TEXT, PRIMARY KEY(session_id, form_id))')
        db.execute('CREATE TABLE IF NOT EXISTS versions (session_id TEXT NOT NULL, form_id TEXT NOT NULL, revision INTEGER NOT NULL, request TEXT NOT NULL, sha256 TEXT NOT NULL, saved_at TEXT NOT NULL, PRIMARY KEY(session_id, form_id, revision), FOREIGN KEY(session_id, form_id) REFERENCES forms(session_id, form_id))')
        return db

    def create(self, session_id, form_id, service, source_job_id, request):
        _id(session_id); _id(form_id)
        if service not in SERVICES or not isinstance(source_job_id, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', source_job_id):
            raise ValueError('생성기 또는 원 대화 작업 ID 형식 오류')
        data, digest = _encode(request)
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT * FROM forms WHERE session_id=? AND form_id=?', (session_id, form_id)).fetchone()
            if current:
                original = db.execute('SELECT sha256 FROM versions WHERE session_id=? AND form_id=? AND revision=1', (session_id, form_id)).fetchone()
                if current['service'] != service or current['source_job_id'] != source_job_id or not original or original['sha256'] != digest:
                    raise ValueError('같은 폼 ID의 원본이 다릅니다.')
                db.commit()
                return self.read(session_id, form_id)
            db.execute('INSERT INTO forms VALUES(?,?,?,?,?,?,?,?)', (session_id, form_id, service, source_job_id, 1, 'editing', None, None))
            db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?)', (session_id, form_id, 1, data, digest, datetime.now(timezone.utc).isoformat()))
            db.commit()
        return self.read(session_id, form_id)

    def read(self, session_id, form_id):
        _id(session_id); _id(form_id)
        with closing(self._connect()) as db:
            row = db.execute('SELECT f.*, v.request, v.sha256, v.saved_at FROM forms f JOIN versions v ON v.session_id=f.session_id AND v.form_id=f.form_id AND v.revision=f.revision WHERE f.session_id=? AND f.form_id=?', (session_id, form_id)).fetchone()
        if not row:
            raise ValueError('이 대화에서 폼을 찾을 수 없습니다.')
        result = dict(row)
        if hashlib.sha256(result['request'].encode('utf-8')).hexdigest() != result['sha256']:
            raise ValueError('폼 입력 해시가 일치하지 않습니다.')
        result['request'] = json.loads(result['request'])
        return result

    def list(self, session_id):
        _id(session_id)
        with closing(self._connect()) as db:
            rows = db.execute('SELECT f.session_id, f.form_id, f.service, f.source_job_id, f.revision, f.state, f.request_id, f.job_id, v.saved_at FROM forms f JOIN versions v ON v.session_id=f.session_id AND v.form_id=f.form_id AND v.revision=f.revision WHERE f.session_id=? ORDER BY v.saved_at DESC, f.form_id LIMIT 200', (session_id,)).fetchall()
        return [dict(row) for row in rows]

    def save(self, session_id, form_id, expected_revision, request):
        _id(session_id); _id(form_id)
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError('폼 버전 형식 오류')
        data, digest = _encode(request)
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,state FROM forms WHERE session_id=? AND form_id=?', (session_id, form_id)).fetchone()
            if not row or row['revision'] != expected_revision or row['state'] != 'editing':
                raise ValueError('폼이 변경됐거나 접수가 시작됐습니다. 최신 상태를 확인하세요.')
            revision = expected_revision + 1
            db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?)', (session_id, form_id, revision, data, digest, datetime.now(timezone.utc).isoformat()))
            db.execute('UPDATE forms SET revision=? WHERE session_id=? AND form_id=?', (revision, session_id, form_id))
            db.commit()
        return self.read(session_id, form_id)

    def pin_submission(self, session_id, form_id, expected_revision, request_id):
        _id(session_id); _id(form_id)
        if type(expected_revision) is not int or not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', request_id):
            raise ValueError('폼 버전 또는 접수 ID 오류')
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,state,request_id FROM forms WHERE session_id=? AND form_id=?', (session_id, form_id)).fetchone()
            if not row or row['revision'] != expected_revision:
                raise ValueError('폼이 변경됐습니다. 최신 버전을 확인하세요.')
            if row['state'] == 'editing':
                db.execute("UPDATE forms SET state='submitting',request_id=? WHERE session_id=? AND form_id=?", (request_id, session_id, form_id))
            elif row['request_id'] != request_id or row['state'] not in ('submitting', 'accepted'):
                raise ValueError('이미 다른 접수가 진행 중입니다.')
            db.commit()
        return self.read(session_id, form_id)

    def mark_accepted(self, session_id, form_id, request_id, job_id):
        _id(session_id); _id(form_id)
        if not isinstance(job_id, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', job_id):
            raise ValueError('생성 작업 ID 형식 오류')
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state,request_id,job_id FROM forms WHERE session_id=? AND form_id=?', (session_id, form_id)).fetchone()
            if not row or row['request_id'] != request_id or row['state'] not in ('submitting', 'accepted') or (row['job_id'] is not None and row['job_id'] != job_id):
                raise ValueError('폼 접수 기록이 일치하지 않습니다.')
            db.execute("UPDATE forms SET state='accepted',job_id=? WHERE session_id=? AND form_id=?", (job_id, session_id, form_id))
            db.commit()
        return self.read(session_id, form_id)
