"""워크플로우 실행과 단계 접수 권한을 SQLite 트랜잭션으로 저장한다."""
import base64
import hashlib
from io import BytesIO
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import date, datetime, timezone

from .workflow_catalog import read_workflow_generator_catalog
from .workflow_definition import compile_workflow_dependencies, validate_fixed_workflow_input


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
             WHERE run_id=? AND state IN ('ready','waiting','awaiting_choice') AND step_id IN (SELECT step_id FROM affected) RETURNING step_id""",
        (current_step_identifier, workflow_run_identifier, workflow_run_identifier)).fetchall()
    current_database_connection.executemany(
        "INSERT INTO workflow_block_reason VALUES (?, ?, ?, ?)",
        [(workflow_run_identifier, blocked_step_identifier, source_step_identifier, block_reason_text)
         for (blocked_step_identifier,) in blocked_step_records])


def read_step_records_locked(current_database_connection, workflow_run_identifier):
    current_database_connection.row_factory = sqlite3.Row
    return [dict(current_step_row) for current_step_row in current_database_connection.execute(
        """SELECT step.step_id, step.category, step.state, step.request_id,
                  timing.created_at, timing.updated_at, contract.generator, contract.generator_version, contract.template_version,
                  blocked.source_step AS blocking_step, blocked.reason AS block_reason, cancellation.delivery AS cancel_delivery, observed.source_state, observed.observed_at, observed.source_job_id
           FROM workflow_step AS step LEFT JOIN workflow_step_contract AS contract USING(run_id, step_id)
           LEFT JOIN workflow_step_time AS timing USING(request_id)
           LEFT JOIN workflow_cancel_request AS cancellation USING(request_id)
           LEFT JOIN workflow_block_reason AS blocked USING(run_id, step_id)
           LEFT JOIN workflow_observation AS observed USING(request_id)
           WHERE step.run_id=? ORDER BY step.rowid""",
        (workflow_run_identifier,))]


def read_result_records_locked(current_database_connection, workflow_run_identifier):
    current_result_rows = current_database_connection.execute(
        """SELECT result.step_id, result.job_id, result.outputs, step.request_id, meta.output_name,
                  meta.media_type, meta.digest, meta.byte_size, meta.recorded_at,
                  json_remove(step.request_body, '$.images'), json_array_length(step.request_body, '$.images'),
                  step.request_digest
           FROM workflow_result AS result JOIN workflow_step AS step USING(run_id, step_id)
           LEFT JOIN workflow_output_metadata AS meta USING(run_id, step_id)
           WHERE result.run_id=? ORDER BY result.rowid""",
        (workflow_run_identifier,))
    return [{"step_id": step_id, "job_id": job_id, "outputs": json.loads(outputs), "attempt_id": request_id,
             "input_settings": json.loads(settings) if settings is not None else None,
             "reference_image_count": reference_count, "input_sha256": input_digest,
             "output_metadata": {"name": name, "media_type": media, "sha256": digest, "bytes": size, "recorded_at": stamp} if name else None}
            for step_id, job_id, outputs, request_id, name, media, digest, size, stamp, settings, reference_count, input_digest in current_result_rows]


class WorkflowRunStore:
    def __init__(self, workflow_database_path):
        self.workflow_database_path = workflow_database_path
        with closing(sqlite3.connect(workflow_database_path)) as current_database_connection:
            current_database_connection.executescript("""
                CREATE TABLE IF NOT EXISTS workflow_draft (
                    session_id TEXT PRIMARY KEY, revision TEXT NOT NULL, definition_text TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_run (
                    run_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, definition TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_observation (
                    request_id TEXT PRIMARY KEY, source_state TEXT NOT NULL, observed_at TEXT NOT NULL, source_job_id TEXT
                );
                CREATE TABLE IF NOT EXISTS workflow_retry (
                    source_request TEXT PRIMARY KEY, retry_run TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS workflow_choice (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, input_field TEXT NOT NULL,
                    source_request TEXT NOT NULL, digest TEXT NOT NULL, selected INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(run_id, step_id, input_field)
                );
                CREATE TABLE IF NOT EXISTS workflow_cancel_request (
                    request_id TEXT PRIMARY KEY, delivery TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_wav (
                    digest TEXT PRIMARY KEY, content BLOB NOT NULL
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
                CREATE TABLE IF NOT EXISTS workflow_step_time (
                    request_id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS workflow_step_created AFTER INSERT ON workflow_step BEGIN
                    INSERT INTO workflow_step_time VALUES (NEW.request_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                END;
                CREATE TRIGGER IF NOT EXISTS workflow_step_updated AFTER UPDATE OF state ON workflow_step BEGIN
                    INSERT INTO workflow_step_time VALUES (NEW.request_id, NULL, CURRENT_TIMESTAMP)
                    ON CONFLICT(request_id) DO UPDATE SET updated_at=CURRENT_TIMESTAMP;
                END;
            """)

    def read_session_draft(self, conversation_session_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            stored_draft_record = current_database_connection.execute(
                "SELECT revision, definition_text FROM workflow_draft WHERE session_id=?", (conversation_session_identifier,)).fetchone()
        current_revision_value, current_definition_text = stored_draft_record or ("", "")
        return {"session_id": conversation_session_identifier, "revision": current_revision_value,
                "definition_text": current_definition_text}

    def save_session_draft(self, conversation_session_identifier, expected_revision_value, current_definition_text):
        if (not isinstance(current_definition_text, str) or len(current_definition_text.encode("utf-8")) > 500000
                or not isinstance(expected_revision_value, str)):
            raise ValueError("초안 형식 또는 크기를 확인하세요.")
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            stored_draft_record = current_database_connection.execute(
                "SELECT revision, definition_text FROM workflow_draft WHERE session_id=?", (conversation_session_identifier,)).fetchone()
            if stored_draft_record and stored_draft_record[1] == current_definition_text:
                current_revision_value = stored_draft_record[0]
            else:
                if expected_revision_value != (stored_draft_record[0] if stored_draft_record else ""):
                    raise ValueError("다른 편집 내용이 저장되었습니다. 최신 초안을 불러와 변경 사항을 확인하세요.")
                current_revision_value = uuid.uuid4().hex
                current_database_connection.execute(
                    """INSERT INTO workflow_draft VALUES (?, ?, ?) ON CONFLICT(session_id)
                       DO UPDATE SET revision=excluded.revision, definition_text=excluded.definition_text""",
                    (conversation_session_identifier, current_revision_value, current_definition_text))
            return {"session_id": conversation_session_identifier, "revision": current_revision_value}

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

    def retry_failed_step(self, workflow_run_identifier, conversation_session_identifier, current_step_identifier,
                          source_attempt_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            source_attempt_record = current_database_connection.execute(
                """SELECT request_body, request_digest, generator, generator_version, template_version, category
                   FROM workflow_step JOIN workflow_run USING(run_id) JOIN workflow_step_contract USING(run_id,step_id)
                   WHERE run_id=? AND session_id=? AND step_id=? AND request_id=? AND state IN ('failed','cancelled')""",
                (workflow_run_identifier, conversation_session_identifier, current_step_identifier, source_attempt_identifier)).fetchone()
            if not source_attempt_record or source_attempt_record[0] is None:
                raise ValueError("접수 입력이 보존된 실패 또는 취소 시도를 선택하세요.")
            existing_retry_record = current_database_connection.execute(
                "SELECT retry_run FROM workflow_retry WHERE source_request=?", (source_attempt_identifier,)).fetchone()
            if existing_retry_record:
                return existing_retry_record[0]
            request_body_text, request_digest_text, generator_name, generator_version, template_version, category_name = source_attempt_record
            if hashlib.sha256(request_body_text.encode()).hexdigest() != request_digest_text:
                raise ValueError("원 시도의 고정 입력 해시가 일치하지 않습니다.")
            current_generator_catalog = read_workflow_generator_catalog()
            current_generator_contract = current_generator_catalog.get(generator_name, {})
            if (current_generator_contract.get("version"), current_generator_contract.get("template_version")) != (generator_version, template_version):
                raise ValueError("원 시도의 생성기 또는 템플릿 버전을 사용할 수 없습니다.")
            saved_inputs = json.loads(request_body_text)
            if generator_name == "kimodo":
                from generators.kimodo.contracts import validate_kimodo_request
                validate_kimodo_request(saved_inputs)
                saved_inputs = {field: saved_inputs[field] for field in current_generator_contract["inputs"]}
            retry_step_definition = [{"id": current_step_identifier, "generator": generator_name, "inputs": saved_inputs}]
            compile_workflow_dependencies(retry_step_definition, current_generator_catalog)
            retry_run_identifier = uuid.uuid4().hex
            current_database_connection.execute("INSERT INTO workflow_run VALUES (?, ?, ?)",
                (retry_run_identifier, conversation_session_identifier, encode_workflow_record(retry_step_definition)))
            current_database_connection.execute("INSERT INTO workflow_step_contract VALUES (?, ?, ?, ?, ?)",
                (retry_run_identifier, current_step_identifier, generator_name, generator_version, template_version))
            current_database_connection.execute("INSERT INTO workflow_step VALUES (?, ?, ?, '[]', 'ready', ?, ?, ?)",
                (retry_run_identifier, current_step_identifier, category_name, uuid.uuid4().hex, request_body_text, request_digest_text))
            current_database_connection.execute("INSERT INTO workflow_retry VALUES (?, ?)", (source_attempt_identifier, retry_run_identifier))
            return retry_run_identifier

    def claim_ready_step(self, workflow_run_identifier, current_step_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            current_step_row = current_database_connection.execute(
                """SELECT definition, state, request_id, generator, generator_version, template_version, request_body, request_digest
                   FROM workflow_run JOIN workflow_step USING(run_id) LEFT JOIN workflow_step_contract USING(run_id,step_id)
                   WHERE run_id=? AND step_id=?""", (workflow_run_identifier, current_step_identifier)).fetchone()
            if not current_step_row or current_step_row[1] not in ("waiting", "ready"):
                return None
            current_step_definition = next(record for record in json.loads(current_step_row[0])
                                           if record["id"] == current_step_identifier)
            current_generator_name = current_step_definition["generator"]
            current_generator_contract = read_workflow_generator_catalog().get(current_generator_name)
            if (current_generator_contract is None or current_step_row[3:6] != (
                    current_generator_name, current_generator_contract["version"], current_generator_contract["template_version"])):
                block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                    current_step_identifier, "등록 당시 생성기 또는 입력 템플릿 버전을 사용할 수 없습니다.")
                return None
            resolved_input_record = dict(current_step_definition.get("inputs", {}))
            for target_field_name, source_binding_record in current_step_definition.get("bindings", {}).items():
                source_result_row = current_database_connection.execute(
                    """SELECT outputs, meta.digest, meta.byte_size, producer.request_id FROM workflow_result
                       JOIN workflow_step AS producer USING(run_id, step_id)
                       LEFT JOIN workflow_output_metadata AS meta USING(run_id, step_id)
                       WHERE run_id=? AND step_id=?""",
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
                if source_output_name == "text":
                    translated_text_bytes = bound_output_value.encode("utf-8") if isinstance(bound_output_value, str) else None
                    if (translated_text_bytes is None or source_result_row[1] != hashlib.sha256(translated_text_bytes).hexdigest()
                            or source_result_row[2] != len(translated_text_bytes)):
                        block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                            source_binding_record["from_step"], "번역문 검증 기록이 없거나 저장된 내용과 일치하지 않습니다.")
                        return None
                if source_output_name == "images":
                    if (not isinstance(bound_output_value, dict) or not source_result_row[1]
                            or bound_output_value.get("sha256") != source_result_row[1]
                            or bound_output_value.get("size") != source_result_row[2]
                            or bound_output_value.get("media_type") != "image/png"):
                        block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                            source_binding_record["from_step"], "PNG 참조가 생산 단계의 출력 기록과 일치하지 않습니다.")
                        return None
                    stored_image_row = current_database_connection.execute(
                        "SELECT content FROM workflow_png WHERE digest=?", (bound_output_value["sha256"],)).fetchone()
                    if (not stored_image_row or len(stored_image_row[0]) != source_result_row[2]
                            or hashlib.sha256(stored_image_row[0]).hexdigest() != source_result_row[1]):
                        block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                            source_binding_record["from_step"], "보존된 PNG의 SHA-256이 일치하지 않습니다." if stored_image_row else "보존된 PNG가 없습니다.")
                        return None
                    bound_output_value = [base64.b64encode(stored_image_row[0]).decode("ascii")]
                target_field_contract = current_generator_contract["inputs"][target_field_name]
                try:
                    validate_fixed_workflow_input(target_field_name, target_field_contract, bound_output_value)
                except ValueError as invalid_bound_input:
                    block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                        source_binding_record["from_step"], str(invalid_bound_input))
                    return None
                if source_binding_record.get("selection") == "user_choice":
                    choice_key_fields = (workflow_run_identifier, current_step_identifier, target_field_name)
                    current_database_connection.execute(
                        "INSERT OR IGNORE INTO workflow_choice VALUES (?, ?, ?, ?, ?, 0)",
                        (*choice_key_fields, source_result_row[3], source_result_row[1]))
                    stored_choice_record = current_database_connection.execute(
                        "SELECT source_request, digest, selected FROM workflow_choice WHERE run_id=? AND step_id=? AND input_field=?",
                        choice_key_fields).fetchone()
                    if stored_choice_record[:2] != (source_result_row[3], source_result_row[1]):
                        block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                            source_binding_record["from_step"], "선택 대상의 생산 시도 또는 결과 해시가 달라졌습니다.")
                        return None
                    if not stored_choice_record[2]:
                        current_database_connection.execute(
                            "UPDATE workflow_step SET state='awaiting_choice' WHERE run_id=? AND step_id=?", choice_key_fields[:2])
                        return None
                resolved_input_record[target_field_name] = bound_output_value
            if current_step_row[6] is not None:
                encoded_request_body = current_step_row[6]
                if hashlib.sha256(encoded_request_body.encode()).hexdigest() != current_step_row[7]:
                    block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                        current_step_identifier, "재시도 입력의 해시가 일치하지 않습니다.")
                    return None
                resolved_input_record = json.loads(encoded_request_body)
            elif current_generator_name == "kimodo":
                from .delegation_proposal import validate_kimodo_proposal_inputs
                try:
                    resolved_input_record = validate_kimodo_proposal_inputs(resolved_input_record)
                except ValueError as error:
                    block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                        current_step_identifier, str(error))
                    return None
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
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        from workflow.domains.image.three_reference_generation import REFERENCE_IMAGE_LIMIT
        if not validate_service_job_identifier("flux-image", current_job_identifier):
            raise ValueError("이미지 작업 ID가 잘못되었습니다.")
        image_result_path = FluxImageGenerationManager("flux-image").job_storage_root / current_job_identifier / "result.png"
        if image_result_path.resolve(strict=True) != image_result_path.absolute() or not image_result_path.is_file():
            raise ValueError("원본 이미지 경로 오류")
        with image_result_path.open("rb") as current_image_stream:
            pinned_image_bytes = current_image_stream.read(REFERENCE_IMAGE_LIMIT + 1)
        self.store_png_completion(workflow_run_identifier, current_step_identifier, current_receipt_record,
                                  current_result_record["image"], pinned_image_bytes, "image")

    def record_kimodo_completion(self, run_id, step_id, status):
        from .kimodo_frame_observer import inspect_kimodo_source_frame, read_bounded_kimodo_source_file
        from workflow.domains.kimodo.generation import KIMODO_JOB_STORAGE
        from workflow.domains.image.three_reference_generation import REFERENCE_IMAGE_LIMIT
        receipt = status["receipt"]
        attempt = status["job"].get("attempt")
        frame = inspect_kimodo_source_frame(receipt["job_id"], attempt, 1)
        path = KIMODO_JOB_STORAGE / receipt["job_id"] / "attempts" / attempt / "output-000.png"
        content = read_bounded_kimodo_source_file(path, REFERENCE_IMAGE_LIMIT)
        if hashlib.sha256(content).hexdigest() != frame["image_sha256"]:
            raise ValueError("원본 프레임이 변경되었습니다.")
        self.store_png_completion(run_id, step_id, receipt, frame["image"], content, "motion")

    def store_png_completion(self, workflow_run_identifier, current_step_identifier, current_receipt_record,
                             preview_path, pinned_image_bytes, category):
        from PIL import Image
        from workflow.domains.image.three_reference_generation import REFERENCE_IMAGE_LIMIT
        current_job_identifier = current_receipt_record["job_id"]
        stored_output_record = {"preview": preview_path}
        if len(pinned_image_bytes) <= REFERENCE_IMAGE_LIMIT:
            try:
                with Image.open(BytesIO(pinned_image_bytes), formats=["PNG"]) as verified_image_file:
                    verified_image_file.verify()
            except (OSError, SyntaxError, Image.DecompressionBombError) as invalid_image_error:
                raise ValueError("생성 결과가 유효한 PNG가 아닙니다.") from invalid_image_error
            stored_output_record["images"] = {"sha256": hashlib.sha256(pinned_image_bytes).hexdigest(),
                                              "size": len(pinned_image_bytes), "media_type": "image/png"}
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            completed_step_record = current_database_connection.execute(
                """UPDATE workflow_step SET state='completed' WHERE run_id=? AND step_id=? AND category=?
                   AND state='submitting' AND request_id=? RETURNING step_id""",
                (workflow_run_identifier, current_step_identifier, category, current_receipt_record["request_id"])).fetchone()
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

    def record_effect_audio_completion(self, workflow_run_identifier, current_step_identifier, current_status_record):
        from workflow.domains.music.generation import MusicGenerationManager
        from .workflow_result_binding import read_workflow_effect_audio
        current_receipt_record = current_status_record["receipt"]
        source_service_name = "sfx-dasheng-audiogen"
        if current_receipt_record.get("service") != source_service_name or current_receipt_record.get("state") != "accepted":
            raise ValueError("효과음 접수 기록이 일치하지 않습니다.")
        source_job_identifier = current_receipt_record["job_id"]
        audio_content_bytes = read_workflow_effect_audio(MusicGenerationManager(source_service_name).job_storage_root,
            source_job_identifier, current_status_record["job"])
        audio_content_digest = hashlib.sha256(audio_content_bytes).hexdigest()
        audio_result_reference = {"sha256": audio_content_digest, "size": len(audio_content_bytes), "media_type": "audio/wav",
                                  "attempt": current_status_record["job"]["audio"].split("/")[-2]}
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            changed_step_count = current_database_connection.execute(
                """UPDATE workflow_step SET state='completed' WHERE run_id=? AND step_id=? AND request_id=?
                   AND state='submitting' AND EXISTS (SELECT 1 FROM workflow_step_contract AS contract
                   WHERE contract.run_id=workflow_step.run_id AND contract.step_id=workflow_step.step_id AND generator=?)""",
                (workflow_run_identifier, current_step_identifier, current_receipt_record["request_id"], source_service_name)).rowcount
            if changed_step_count:
                current_database_connection.execute("INSERT OR IGNORE INTO workflow_wav VALUES (?,?)", (audio_content_digest, audio_content_bytes))
                current_database_connection.execute("INSERT INTO workflow_output_metadata VALUES (?,?,?,?,?,?,?)",
                    (workflow_run_identifier, current_step_identifier, "audio", "audio/wav", audio_content_digest,
                     len(audio_content_bytes), datetime.now(timezone.utc).isoformat()))
                current_database_connection.execute("INSERT INTO workflow_result VALUES (?,?,?,?)",
                    (workflow_run_identifier, current_step_identifier, source_job_identifier, encode_workflow_record({"audio": audio_result_reference})))

    def read_pinned_effect_audio(self, workflow_run_identifier, conversation_session_identifier, current_step_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            stored_audio_record = current_database_connection.execute(
                """SELECT wav.content, meta.digest, meta.byte_size FROM workflow_output_metadata AS meta
                   JOIN workflow_run USING(run_id) JOIN workflow_wav AS wav ON wav.digest=meta.digest
                   WHERE run_id=? AND session_id=? AND step_id=? AND meta.output_name='audio' AND meta.media_type='audio/wav'""",
                (workflow_run_identifier, conversation_session_identifier, current_step_identifier)).fetchone()
        if not stored_audio_record:
            raise ValueError("이 세션의 단계에서 보존한 효과음이 없습니다.")
        audio_content_bytes, stored_audio_digest, stored_audio_size = stored_audio_record
        if len(audio_content_bytes) != stored_audio_size or hashlib.sha256(audio_content_bytes).hexdigest() != stored_audio_digest:
            raise ValueError("보존된 효과음의 크기 또는 해시가 일치하지 않습니다.")
        return audio_content_bytes

    def read_pinned_image_preview(self, workflow_run_identifier, conversation_session_identifier, current_step_identifier):
        from PIL import Image
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            pinned_image_record = current_database_connection.execute(
                """SELECT png.content, meta.digest, meta.byte_size FROM workflow_output_metadata AS meta
                   JOIN workflow_run USING(run_id) JOIN workflow_png AS png ON png.digest=meta.digest
                   WHERE run_id=? AND session_id=? AND step_id=? AND meta.output_name='images' AND meta.media_type='image/png'""",
                (workflow_run_identifier, conversation_session_identifier, current_step_identifier)).fetchone()
        if not pinned_image_record:
            raise ValueError("이 대화의 실행 단계에서 보존한 PNG를 찾을 수 없습니다.")
        image_content_bytes, expected_image_digest, expected_image_size = pinned_image_record
        if len(image_content_bytes) != expected_image_size or hashlib.sha256(image_content_bytes).hexdigest() != expected_image_digest:
            raise ValueError("보존된 이미지의 해시 또는 크기가 일치하지 않습니다.")
        with Image.open(BytesIO(image_content_bytes), formats=["PNG"]) as stored_image_value:
            stored_image_value.thumbnail((512, 512))
            with BytesIO() as preview_image_stream:
                stored_image_value.convert("RGBA").save(preview_image_stream, format="PNG")
                return {"preview_png": base64.b64encode(preview_image_stream.getvalue()).decode("ascii"),
                        "source_sha256": expected_image_digest}

    def read_run_results(self, workflow_run_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            return read_result_records_locked(current_database_connection, workflow_run_identifier)

    def block_unusable_result(self, workflow_run_identifier, current_step_record, result_failure_reason):
        current_step_identifier = current_step_record["step_id"]
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            changed_step_count = current_database_connection.execute(
                """UPDATE workflow_step SET state='blocked' WHERE run_id=? AND step_id=?
                   AND request_id=? AND state='submitting'""",
                (workflow_run_identifier, current_step_identifier, current_step_record["request_id"])).rowcount
            if changed_step_count:
                current_database_connection.execute("INSERT INTO workflow_block_reason VALUES (?, ?, ?, ?)",
                    (workflow_run_identifier, current_step_identifier, current_step_identifier, result_failure_reason))
                block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier,
                                         current_step_identifier, result_failure_reason)

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

    def select_workflow_output(self, workflow_run_identifier, conversation_session_identifier, current_step_identifier,
                               target_input_field, source_attempt_identifier, source_output_digest):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            choice_key_fields = (workflow_run_identifier, current_step_identifier, target_input_field,
                                 source_attempt_identifier, source_output_digest)
            matched_choice_record = current_database_connection.execute(
                """SELECT selected, state FROM workflow_choice JOIN workflow_step USING(run_id, step_id)
                   JOIN workflow_run USING(run_id) WHERE run_id=? AND step_id=? AND input_field=?
                   AND source_request=? AND digest=? AND session_id=?""",
                (*choice_key_fields, conversation_session_identifier)).fetchone()
            if matched_choice_record and matched_choice_record[0]:
                return
            if not matched_choice_record or matched_choice_record[1] != "awaiting_choice":
                raise ValueError("이 세션의 선택 대기 단계와 결과 식별자를 확인하세요.")
            current_database_connection.execute(
                "UPDATE workflow_choice SET selected=1 WHERE run_id=? AND step_id=? AND input_field=? AND source_request=? AND digest=?",
                choice_key_fields)
            current_database_connection.execute(
                "UPDATE workflow_step SET state='waiting' WHERE run_id=? AND step_id=?", choice_key_fields[:2])

    def request_workflow_cancellation(self, workflow_run_identifier, conversation_session_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute("BEGIN IMMEDIATE")
            if not current_database_connection.execute(
                    "SELECT 1 FROM workflow_run WHERE run_id=? AND session_id=?",
                    (workflow_run_identifier, conversation_session_identifier)).fetchone():
                raise ValueError("이 세션에서 해당 실행을 찾을 수 없습니다.")
            current_database_connection.execute(
                "UPDATE workflow_step SET state='cancelled' WHERE run_id=? AND state IN ('ready','waiting','awaiting_choice')",
                (workflow_run_identifier,))
            current_database_connection.execute(
                """INSERT OR IGNORE INTO workflow_cancel_request
                   SELECT request_id, 'pending' FROM workflow_step WHERE run_id=? AND state='submitting'""",
                (workflow_run_identifier,))

    def claim_pending_cancellation(self, current_request_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            return current_database_connection.execute(
                "UPDATE workflow_cancel_request SET delivery='unconfirmed' WHERE request_id=? AND delivery='pending'",
                (current_request_identifier,)).rowcount == 1

    def acknowledge_cancel_delivery(self, current_request_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            current_database_connection.execute(
                "UPDATE workflow_cancel_request SET delivery='acknowledged' WHERE request_id=? AND delivery='unconfirmed'",
                (current_request_identifier,))

    def list_active_run_identifiers(self):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            active_run_records = current_database_connection.execute(
                """SELECT DISTINCT run_id FROM workflow_step
                   WHERE state IN ('waiting','ready','submitting') ORDER BY run_id""")
            return [current_run_record[0] for current_run_record in active_run_records]

    def read_session_run_view(self, workflow_run_identifier, conversation_session_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_database_connection.execute("BEGIN")
            stored_run_definition = current_database_connection.execute(
                "SELECT definition FROM workflow_run WHERE run_id=? AND session_id=?",
                (workflow_run_identifier, conversation_session_identifier)).fetchone()
            if stored_run_definition is None:
                raise ValueError("이 세션에서 해당 실행을 찾을 수 없습니다.")
            bindings_by_step = {step["id"]: step.get("bindings", {}) for step in json.loads(stored_run_definition[0])}
            current_step_records = read_step_records_locked(current_database_connection, workflow_run_identifier)
            for current_step_record in current_step_records:
                current_step_record["bindings"] = bindings_by_step[current_step_record["step_id"]]
            return {"run_id": workflow_run_identifier, "steps": current_step_records,
                    "retries": [dict(current_retry_row) for current_retry_row in current_database_connection.execute(
                        """SELECT step.run_id AS source_run, step.step_id, retry.source_request, retry.retry_run FROM workflow_retry AS retry
                           JOIN workflow_step AS step ON step.request_id=retry.source_request WHERE step.run_id=? OR retry.retry_run=?""",
                        (workflow_run_identifier, workflow_run_identifier))],
                    "choices": [dict(current_choice_row) for current_choice_row in current_database_connection.execute(
                        """SELECT step_id, input_field, source_request, digest, selected FROM workflow_choice AS choice
                           JOIN workflow_step USING(run_id, step_id)
                           WHERE run_id=? AND (selected=1 OR state='awaiting_choice') ORDER BY choice.rowid""",
                        (workflow_run_identifier,))],
                    "results": read_result_records_locked(current_database_connection, workflow_run_identifier),
                    "queried_at": datetime.now(timezone.utc).isoformat()}

    def find_session_workflow_steps(self, conversation_session_identifier, current_category_name, current_state_name, search_filters=None):
        search_filters = {} if search_filters is None else search_filters
        allowed_filter_fields = {"generator", "run_id", "job_id", "created_from", "created_through"}
        if (not isinstance(search_filters, dict) or search_filters.keys() - allowed_filter_fields
                or any(not isinstance(value, str) for value in search_filters.values())):
            raise ValueError("작업 검색 필드를 확인하세요.")
        query_filter_values = dict.fromkeys(allowed_filter_fields, "") | search_filters
        for date_field_name in ("created_from", "created_through"):
            date_filter_text = query_filter_values[date_field_name]
            if date_filter_text and date.fromisoformat(date_filter_text).isoformat() != date_filter_text:
                raise ValueError("검색 날짜는 YYYY-MM-DD 형식입니다.")
        if query_filter_values["created_through"] and query_filter_values["created_from"] > query_filter_values["created_through"]:
            raise ValueError("검색 시작일이 종료일보다 늦습니다.")
        if current_category_name not in ("", "translation", "image", "audio", "motion"):
            raise ValueError("지원하지 않는 생성기 카테고리입니다.")
        if current_state_name not in ("", "ready", "waiting", "awaiting_choice", "submitting", "completed", "failed", "cancelled", "blocked", "queued", "running", "paused", "unknown"):
            raise ValueError("지원하지 않는 단계 상태입니다.")
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_database_connection.row_factory = sqlite3.Row
            matching_step_records = current_database_connection.execute(
                """SELECT step.run_id, step.step_id, step.category, step.state, contract.generator, step.request_id,
                          observation.source_job_id, timing.created_at, timing.updated_at, observation.source_state, observation.observed_at
                   FROM workflow_step AS step JOIN workflow_run AS run USING(run_id)
                   LEFT JOIN workflow_step_contract AS contract USING(run_id, step_id)
                   LEFT JOIN workflow_step_time AS timing USING(request_id)
                   LEFT JOIN workflow_observation AS observation USING(request_id)
                   WHERE run.session_id=:session AND (:category='' OR step.category=:category)
                     AND (:state='' OR step.state=:state OR (step.state='submitting'
                          AND :state IN ('queued','running','paused','unknown') AND observation.source_state=:state))
                     AND (:generator='' OR instr(lower(contract.generator),lower(:generator))>0)
                     AND (:run_id='' OR step.run_id=:run_id)
                     AND (:job_id='' OR instr(lower(step.request_id),lower(:job_id))>0 OR instr(lower(observation.source_job_id),lower(:job_id))>0 OR instr(lower(step.step_id),lower(:job_id))>0)
                     AND (:created_from='' OR date(timing.created_at, '+9 hours')>=:created_from)
                     AND (:created_through='' OR date(timing.created_at, '+9 hours')<=:created_through)
                   ORDER BY step.rowid DESC LIMIT 101""",
                query_filter_values | {"session": conversation_session_identifier, "category": current_category_name, "state": current_state_name}).fetchall()
        return {"steps": [dict(current_step_record) for current_step_record in matching_step_records[:100]],
                "truncated": len(matching_step_records) > 100, "queried_at": datetime.now(timezone.utc).isoformat()}
