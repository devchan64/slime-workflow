"""워크플로우 실행과 단계 접수 권한을 SQLite 트랜잭션으로 저장한다."""
import base64
import hashlib
from io import BytesIO
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone

from .workflow_catalog import read_workflow_generator_catalog
from .workflow_definition import compile_workflow_dependencies


def encode_workflow_record(current_record_value):
    return json.dumps(current_record_value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":"))


def block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier, source_step_identifier, block_reason_text):
    blocked_step_records = current_database_connection.execute(
        """WITH RECURSIVE affected(step_id) AS (
               SELECT ? UNION SELECT child.step_id FROM workflow_step AS child,
                   json_each(child.dependencies) AS parent JOIN affected ON parent.value=affected.step_id
                   WHERE child.run_id=?
           ) UPDATE workflow_step SET state='blocked'
             WHERE run_id=? AND state='waiting' AND step_id IN (SELECT step_id FROM affected) RETURNING step_id""",
        (current_step_identifier, workflow_run_identifier, workflow_run_identifier)).fetchall()
    current_database_connection.executemany(
        "INSERT INTO workflow_block_reason VALUES (?, ?, ?, ?)",
        [(workflow_run_identifier, blocked_step_identifier, source_step_identifier, block_reason_text)
         for (blocked_step_identifier,) in blocked_step_records])


def read_step_records_locked(current_database_connection, workflow_run_identifier):
    current_database_connection.row_factory = sqlite3.Row
    return [dict(current_step_row) for current_step_row in current_database_connection.execute(
        """SELECT step.step_id, step.category, step.state, step.request_id,
                  contract.generator, contract.generator_version, contract.template_version,
                  blocked.source_step AS blocking_step, blocked.reason AS block_reason, observed.source_state, observed.observed_at, observed.source_job_id
           FROM workflow_step AS step LEFT JOIN workflow_step_contract AS contract USING(run_id, step_id)
           LEFT JOIN workflow_block_reason AS blocked USING(run_id, step_id)
           LEFT JOIN workflow_observation AS observed USING(request_id)
           WHERE step.run_id=? ORDER BY step.rowid""",
        (workflow_run_identifier,))]


def read_result_records_locked(current_database_connection, workflow_run_identifier):
    current_result_rows = current_database_connection.execute(
        """SELECT result.step_id, result.job_id, result.outputs, step.request_id, meta.output_name,
                  meta.media_type, meta.digest, meta.byte_size, meta.recorded_at
           FROM workflow_result AS result JOIN workflow_step AS step USING(run_id, step_id)
           LEFT JOIN workflow_output_metadata AS meta USING(run_id, step_id)
           WHERE result.run_id=? ORDER BY result.rowid""",
        (workflow_run_identifier,))
    return [{"step_id": step_id, "job_id": job_id, "outputs": json.loads(outputs), "attempt_id": request_id,
             "output_metadata": {"name": name, "media_type": media, "sha256": digest, "bytes": size, "recorded_at": stamp} if name else None}
            for step_id, job_id, outputs, request_id, name, media, digest, size, stamp in current_result_rows]


class WorkflowRunStore:
    def __init__(self, workflow_database_path):
        self.workflow_database_path = workflow_database_path
        with closing(sqlite3.connect(workflow_database_path)) as current_database_connection:
            current_database_connection.executescript("""
                CREATE TABLE IF NOT EXISTS workflow_run (
                    run_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, definition TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_observation (
                    request_id TEXT PRIMARY KEY, source_state TEXT NOT NULL, observed_at TEXT NOT NULL, source_job_id TEXT
                );
                CREATE TABLE IF NOT EXISTS workflow_png (
                    digest TEXT PRIMARY KEY, content BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_step_contract (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, generator TEXT NOT NULL,
                    generator_version INTEGER NOT NULL, template_version INTEGER NOT NULL,
                    PRIMARY KEY(run_id, step_id)
                );
                CREATE TABLE IF NOT EXISTS workflow_block_reason (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, source_step TEXT NOT NULL,
                    reason TEXT NOT NULL, PRIMARY KEY(run_id, step_id)
                );
                CREATE TABLE IF NOT EXISTS workflow_output_metadata (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, output_name TEXT NOT NULL,
                    media_type TEXT NOT NULL, digest TEXT NOT NULL, byte_size INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL, PRIMARY KEY(run_id,step_id)
                );
                CREATE TABLE IF NOT EXISTS workflow_result (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, job_id TEXT NOT NULL,
                    outputs TEXT NOT NULL, PRIMARY KEY(run_id, step_id)
                );
                CREATE TABLE IF NOT EXISTS workflow_step (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, category TEXT NOT NULL,
                    dependencies TEXT NOT NULL, state TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
                    request_body TEXT, request_digest TEXT, PRIMARY KEY(run_id, step_id)
                );
            """)

    def register_workflow_run(self, workflow_run_identifier, conversation_session_identifier, workflow_step_records):
        encoded_workflow_definition = encode_workflow_record(workflow_step_records)
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            existing_run_record = current_database_connection.execute(
                "SELECT session_id, definition FROM workflow_run WHERE run_id=?", (workflow_run_identifier,)
            ).fetchone()
            if existing_run_record:
                if existing_run_record != (conversation_session_identifier, encoded_workflow_definition):
                    raise ValueError("같은 실행 ID에 다른 세션 또는 정의가 있습니다.")
                return
            current_generator_catalog = read_workflow_generator_catalog()
            current_dependency_records = compile_workflow_dependencies(workflow_step_records, current_generator_catalog)
            current_database_connection.execute("INSERT INTO workflow_run VALUES (?, ?, ?)",
                (workflow_run_identifier, conversation_session_identifier, encoded_workflow_definition))
            for current_step_record in workflow_step_records:
                current_step_identifier = current_step_record["id"]
                current_step_dependencies = current_dependency_records[current_step_identifier]
                current_generator_name = current_step_record["generator"]
                current_generator_contract = current_generator_catalog[current_generator_name]
                current_database_connection.execute("INSERT INTO workflow_step_contract VALUES (?, ?, ?, ?, ?)",
                    (workflow_run_identifier, current_step_identifier, current_generator_name,
                     current_generator_contract["version"], current_generator_contract["template_version"]))
                current_database_connection.execute(
                    "INSERT INTO workflow_step VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)",
                    (workflow_run_identifier, current_step_identifier,
                     current_generator_catalog[current_step_record["generator"]]["category"],
                     encode_workflow_record(current_step_dependencies),
                     "waiting" if current_step_dependencies else "ready", uuid.uuid4().hex))

    def claim_ready_step(self, workflow_run_identifier, current_step_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            current_step_row = current_database_connection.execute(
                """SELECT definition, state, request_id FROM workflow_run JOIN workflow_step USING(run_id)
                   WHERE run_id=? AND step_id=?""", (workflow_run_identifier, current_step_identifier)).fetchone()
            if not current_step_row or current_step_row[1] not in ("waiting", "ready"):
                return None
            current_step_definition = next(record for record in json.loads(current_step_row[0])
                                           if record["id"] == current_step_identifier)
            resolved_input_record = dict(current_step_definition.get("inputs", {}))
            for target_field_name, source_binding_record in current_step_definition.get("bindings", {}).items():
                source_result_row = current_database_connection.execute(
                    "SELECT outputs FROM workflow_result WHERE run_id=? AND step_id=?",
                    (workflow_run_identifier, source_binding_record["from_step"])).fetchone()
                if source_result_row is None:
                    return None
                source_output_name = source_binding_record["output"]
                source_output_values = json.loads(source_result_row[0])
                if source_output_name not in source_output_values:
                    block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                        source_binding_record["from_step"], "선행 작업의 출력 항목이 없습니다.")
                    return None
                bound_output_value = source_output_values[source_output_name]
                if source_output_name == "images":
                    stored_image_row = current_database_connection.execute(
                        "SELECT content FROM workflow_png WHERE digest=?", (bound_output_value["sha256"],)).fetchone()
                    if not stored_image_row or hashlib.sha256(stored_image_row[0]).hexdigest() != bound_output_value["sha256"]:
                        block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                            source_binding_record["from_step"], "보존된 PNG의 SHA-256이 일치하지 않습니다." if stored_image_row else "보존된 PNG가 없습니다.")
                        return None
                    bound_output_value = [base64.b64encode(stored_image_row[0]).decode("ascii")]
                resolved_input_record[target_field_name] = bound_output_value
            encoded_request_body = encode_workflow_record(resolved_input_record)
            current_database_connection.execute(
                """UPDATE workflow_step SET state='submitting', request_body=?, request_digest=?
                   WHERE run_id=? AND step_id=?""",
                (encoded_request_body, hashlib.sha256(encoded_request_body.encode()).hexdigest(),
                 workflow_run_identifier, current_step_identifier))
            return {"request_id": current_step_row[2], "request": resolved_input_record}

    def record_translation_completion(self, workflow_run_identifier, current_step_identifier,
                                      expected_job_identifier, translation_status_record):
        from .workflow_result_binding import bind_translation_prompt_input
        pinned_translation_record = bind_translation_prompt_input(translation_status_record, expected_job_identifier, {})
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            completed_step_record = current_database_connection.execute(
                """UPDATE workflow_step SET state='completed'
                   WHERE run_id=? AND step_id=? AND category='translation' AND state='submitting'
                   AND request_id=? RETURNING step_id""",
                (workflow_run_identifier, current_step_identifier,
                 translation_status_record["receipt"].get("request_id"))).fetchone()
            if not completed_step_record:
                raise ValueError("번역 시도와 접수 기록이 일치하지 않습니다.")
            current_database_connection.execute("INSERT INTO workflow_output_metadata VALUES (?, ?, ?, ?, ?, ?, ?)",
                (workflow_run_identifier, current_step_identifier, "text", "text/plain; charset=utf-8",
                 pinned_translation_record["source"]["sha256"], len(pinned_translation_record["request"]["prompt"].encode("utf-8")),
                 datetime.now(timezone.utc).isoformat()))
            current_database_connection.execute("INSERT INTO workflow_result VALUES (?, ?, ?, ?)",
                (workflow_run_identifier, current_step_identifier, expected_job_identifier,
                 encode_workflow_record({"text": pinned_translation_record["request"]["prompt"]})))

    def list_run_step_records(self, workflow_run_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            return read_step_records_locked(current_database_connection, workflow_run_identifier)

    def record_flux_completion(self, workflow_run_identifier, current_step_identifier, current_status_record):
        from .flux_profile_operations import inspect_hermes_flux_result
        current_receipt_record = current_status_record.get("receipt", {})
        if current_receipt_record.get("service") != "flux-image" or current_receipt_record.get("state") != "accepted":
            raise ValueError("FLUX 접수를 확인할 수 없습니다.")
        current_job_identifier = current_receipt_record["job_id"]
        current_result_record = inspect_hermes_flux_result("flux-image", current_job_identifier, current_status_record["job"])
        if current_result_record["status"] != "available" or current_result_record != current_status_record.get("result"):
            raise ValueError("FLUX 완료 이미지 경로를 확인할 수 없습니다.")
        from PIL import Image
        from .delegation_store import validate_service_job_identifier
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        from tools.review.domains.image.three_reference_generation import REFERENCE_IMAGE_LIMIT
        if not validate_service_job_identifier("flux-image", current_job_identifier):
            raise ValueError("이미지 작업 ID가 잘못되었습니다.")
        image_result_path = FluxImageGenerationManager("flux-image").job_storage_root / current_job_identifier / "result.png"
        if image_result_path.resolve(strict=True) != image_result_path.absolute() or not image_result_path.is_file():
            raise ValueError("원본 이미지 경로 오류")
        with image_result_path.open("rb") as current_image_stream:
            pinned_image_bytes = current_image_stream.read(REFERENCE_IMAGE_LIMIT + 1)
        stored_output_record = {"preview": current_result_record["image"]}
        if len(pinned_image_bytes) <= REFERENCE_IMAGE_LIMIT:
            with Image.open(BytesIO(pinned_image_bytes), formats=["PNG"]) as verified_image_file:
                verified_image_file.verify()
            stored_output_record["images"] = {"sha256": hashlib.sha256(pinned_image_bytes).hexdigest(),
                                              "size": len(pinned_image_bytes), "media_type": "image/png"}
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            completed_step_record = current_database_connection.execute(
                """UPDATE workflow_step SET state='completed' WHERE run_id=? AND step_id=? AND category='image'
                   AND state='submitting' AND request_id=? RETURNING step_id""",
                (workflow_run_identifier, current_step_identifier, current_receipt_record["request_id"])).fetchone()
            if completed_step_record:
                if "images" in stored_output_record:
                    current_database_connection.execute("INSERT INTO workflow_output_metadata VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (workflow_run_identifier, current_step_identifier, "images", "image/png",
                         stored_output_record["images"]["sha256"], len(pinned_image_bytes), datetime.now(timezone.utc).isoformat()))
                    current_database_connection.execute("INSERT OR IGNORE INTO workflow_png VALUES (?, ?)",
                        (stored_output_record["images"]["sha256"], pinned_image_bytes))
                current_database_connection.execute("INSERT INTO workflow_result VALUES (?, ?, ?, ?)",
                    (workflow_run_identifier, current_step_identifier, current_job_identifier,
                     encode_workflow_record(stored_output_record)))

    def read_run_results(self, workflow_run_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            return read_result_records_locked(current_database_connection, workflow_run_identifier)

    def close_unsuccessful_step(self, workflow_run_identifier, current_step_record, terminal_state_name):
        if terminal_state_name not in ("failed", "cancelled"):
            raise ValueError("실패 또는 취소 상태가 필요합니다.")
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            changed_step_count = current_database_connection.execute(
                """UPDATE workflow_step SET state=? WHERE run_id=? AND step_id=? AND request_id=?
                   AND state='submitting'""", (terminal_state_name, workflow_run_identifier,
                   current_step_record["step_id"], current_step_record["request_id"])).rowcount
            if changed_step_count:
                block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_record["step_id"],
                    current_step_record["step_id"], "선행 작업이 취소되었습니다." if terminal_state_name == "cancelled" else "선행 작업이 실패했습니다.")

    def record_source_observation(self, current_request_identifier, observed_source_state, source_job_identifier=None):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute(
                """INSERT INTO workflow_observation(request_id,source_state,observed_at,source_job_id)
                   SELECT request_id, ?, ?, ? FROM workflow_step WHERE request_id=? AND state='submitting'
                   ON CONFLICT(request_id) DO UPDATE SET source_state=excluded.source_state,
                   observed_at=excluded.observed_at, source_job_id=COALESCE(excluded.source_job_id, source_job_id)""",
                (observed_source_state, datetime.now(timezone.utc).isoformat(), source_job_identifier, current_request_identifier))

    def list_active_run_identifiers(self):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            active_run_records = current_database_connection.execute(
                """SELECT DISTINCT run_id FROM workflow_step
                   WHERE state IN ('waiting','ready','submitting') ORDER BY run_id""")
            return [current_run_record[0] for current_run_record in active_run_records]

    def read_session_run_view(self, workflow_run_identifier, conversation_session_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_database_connection.execute("BEGIN")
            current_session_match = current_database_connection.execute(
                "SELECT 1 FROM workflow_run WHERE run_id=? AND session_id=?",
                (workflow_run_identifier, conversation_session_identifier)).fetchone()
            if current_session_match is None:
                raise ValueError("이 세션에서 해당 실행을 찾을 수 없습니다.")
            return {"run_id": workflow_run_identifier, "steps": read_step_records_locked(current_database_connection, workflow_run_identifier),
                    "results": read_result_records_locked(current_database_connection, workflow_run_identifier),
                    "queried_at": datetime.now(timezone.utc).isoformat()}

    def find_session_workflow_steps(self, conversation_session_identifier, current_category_name, current_state_name):
        if current_category_name not in ("", "translation", "image"):
            raise ValueError("지원하지 않는 생성기 카테고리입니다.")
        if current_state_name not in ("", "ready", "waiting", "submitting", "completed", "failed", "cancelled", "blocked", "queued", "running", "paused", "unknown"):
            raise ValueError("지원하지 않는 단계 상태입니다.")
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_database_connection.row_factory = sqlite3.Row
            matching_step_records = current_database_connection.execute(
                """SELECT step.run_id, step.step_id, step.category, step.state, observation.source_state, observation.observed_at
                   FROM workflow_step AS step JOIN workflow_run AS run USING(run_id)
                   LEFT JOIN workflow_observation AS observation USING(request_id)
                   WHERE run.session_id=? AND (?='' OR step.category=?)
                     AND (?='' OR step.state=? OR (step.state='submitting' AND observation.source_state=?))
                   ORDER BY step.rowid DESC LIMIT 101""",
                (conversation_session_identifier, current_category_name, current_category_name,
                 current_state_name, current_state_name, current_state_name)).fetchall()
        return {"steps": [dict(current_step_record) for current_step_record in matching_step_records[:100]],
                "truncated": len(matching_step_records) > 100, "queried_at": datetime.now(timezone.utc).isoformat()}
