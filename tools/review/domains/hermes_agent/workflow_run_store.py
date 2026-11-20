"""워크플로우 실행과 단계 접수 권한을 SQLite 트랜잭션으로 저장한다."""
import base64
import hashlib
from io import BytesIO
import json
import sqlite3
import uuid
from contextlib import closing

from .workflow_catalog import read_workflow_generator_catalog
from .workflow_definition import compile_workflow_dependencies


def encode_workflow_record(current_record_value):
    return json.dumps(current_record_value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":"))


def block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier):
    current_database_connection.execute(
        """WITH RECURSIVE affected(step_id) AS (
               SELECT ? UNION SELECT child.step_id FROM workflow_step AS child,
                   json_each(child.dependencies) AS parent JOIN affected ON parent.value=affected.step_id
                   WHERE child.run_id=?
           ) UPDATE workflow_step SET state='blocked'
             WHERE run_id=? AND state='waiting' AND step_id IN (SELECT step_id FROM affected)""",
        (current_step_identifier, workflow_run_identifier, workflow_run_identifier))


class WorkflowRunStore:
    def __init__(self, workflow_database_path):
        self.workflow_database_path = workflow_database_path
        with closing(sqlite3.connect(workflow_database_path)) as current_database_connection:
            current_database_connection.executescript("""
                CREATE TABLE IF NOT EXISTS workflow_run (
                    run_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, definition TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_png (
                    digest TEXT PRIMARY KEY, content BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_step_contract (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, generator TEXT NOT NULL,
                    generator_version INTEGER NOT NULL, template_version INTEGER NOT NULL,
                    PRIMARY KEY(run_id, step_id)
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
                    block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier)
                    return None
                bound_output_value = source_output_values[source_output_name]
                if source_output_name == "images":
                    stored_image_row = current_database_connection.execute(
                        "SELECT content FROM workflow_png WHERE digest=?", (bound_output_value["sha256"],)).fetchone()
                    if not stored_image_row or hashlib.sha256(stored_image_row[0]).hexdigest() != bound_output_value["sha256"]:
                        block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_identifier)
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
            current_database_connection.execute("INSERT INTO workflow_result VALUES (?, ?, ?, ?)",
                (workflow_run_identifier, current_step_identifier, expected_job_identifier,
                 encode_workflow_record({"text": pinned_translation_record["request"]["prompt"]})))

    def list_run_step_records(self, workflow_run_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_database_connection.row_factory = sqlite3.Row
            return [dict(current_step_row) for current_step_row in current_database_connection.execute(
                """SELECT step.step_id, step.category, step.state, step.request_id,
                          contract.generator, contract.generator_version, contract.template_version
                   FROM workflow_step AS step LEFT JOIN workflow_step_contract AS contract USING(run_id, step_id)
                   WHERE step.run_id=? ORDER BY step.rowid""",
                (workflow_run_identifier,))]

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
                    current_database_connection.execute("INSERT OR IGNORE INTO workflow_png VALUES (?, ?)",
                        (stored_output_record["images"]["sha256"], pinned_image_bytes))
                current_database_connection.execute("INSERT INTO workflow_result VALUES (?, ?, ?, ?)",
                    (workflow_run_identifier, current_step_identifier, current_job_identifier,
                     encode_workflow_record(stored_output_record)))

    def read_run_results(self, workflow_run_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_result_rows = current_database_connection.execute(
                "SELECT step_id, job_id, outputs FROM workflow_result WHERE run_id=? ORDER BY rowid",
                (workflow_run_identifier,))
            return [{"step_id": step_id, "job_id": job_id, "outputs": json.loads(outputs)}
                    for step_id, job_id, outputs in current_result_rows]

    def close_unsuccessful_step(self, workflow_run_identifier, current_step_record, terminal_state_name):
        if terminal_state_name not in ("failed", "cancelled"):
            raise ValueError("실패 또는 취소 상태가 필요합니다.")
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection, current_database_connection:
            changed_step_count = current_database_connection.execute(
                """UPDATE workflow_step SET state=? WHERE run_id=? AND step_id=? AND request_id=?
                   AND state='submitting'""", (terminal_state_name, workflow_run_identifier,
                   current_step_record["step_id"], current_step_record["request_id"])).rowcount
            if changed_step_count:
                block_waiting_dependents(current_database_connection, workflow_run_identifier, current_step_record["step_id"])

    def list_active_run_identifiers(self):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            active_run_records = current_database_connection.execute(
                """SELECT DISTINCT run_id FROM workflow_step
                   WHERE state IN ('waiting','ready','submitting') ORDER BY run_id""")
            return [current_run_record[0] for current_run_record in active_run_records]

    def read_session_run_view(self, workflow_run_identifier, conversation_session_identifier):
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_session_match = current_database_connection.execute(
                "SELECT 1 FROM workflow_run WHERE run_id=? AND session_id=?",
                (workflow_run_identifier, conversation_session_identifier)).fetchone()
        if current_session_match is None:
            raise ValueError("이 세션에서 해당 실행을 찾을 수 없습니다.")
        return {"run_id": workflow_run_identifier, "steps": self.list_run_step_records(workflow_run_identifier),
                "results": self.read_run_results(workflow_run_identifier)}

    def find_session_workflow_steps(self, conversation_session_identifier, current_category_name, current_state_name):
        if current_category_name not in ("", "translation", "image"):
            raise ValueError("지원하지 않는 생성기 카테고리입니다.")
        if current_state_name not in ("", "ready", "waiting", "submitting", "completed", "failed", "cancelled", "blocked"):
            raise ValueError("지원하지 않는 단계 상태입니다.")
        with closing(sqlite3.connect(self.workflow_database_path)) as current_database_connection:
            current_database_connection.row_factory = sqlite3.Row
            matching_step_records = current_database_connection.execute(
                """SELECT step.run_id, step.step_id, step.category, step.state
                   FROM workflow_step AS step JOIN workflow_run AS run USING(run_id)
                   WHERE run.session_id=? AND (?='' OR step.category=?) AND (?='' OR step.state=?)
                   ORDER BY step.rowid DESC LIMIT 101""",
                (conversation_session_identifier, current_category_name, current_category_name,
                 current_state_name, current_state_name)).fetchall()
        return {"steps": [dict(current_step_record) for current_step_record in matching_step_records[:100]],
                "truncated": len(matching_step_records) > 100}
