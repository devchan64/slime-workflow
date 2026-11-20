"""격리된 서비스 응답으로 재시작과 생성 결과 전달을 검증한다."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from tools.review.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
from tools.review.domains.hermes_agent.workflow_dispatch import advance_workflow_run
from tools.review.domains.hermes_agent.workflow_run_store import WorkflowRunStore


class HermesWorkflowChainTests(unittest.TestCase):
    def test_unusable_flux_output_blocks_revision_and_preserves_independent_branch(self):
        for image_file_condition in ("missing", "corrupt"):
            with self.subTest(condition=image_file_condition), tempfile.TemporaryDirectory() as temporary_root_name:
                temporary_root_path = Path(temporary_root_name)
                workflow_database_path = temporary_root_path / "workflow.sqlite3"
                workflow_run_store = WorkflowRunStore(workflow_database_path)
                image_step_record = create_workflow_step_draft("image", "flux-image", {"prompt": "forest"})
                revision_step_record = create_workflow_step_draft("revise", "flux-image", {"prompt": "flowers"})
                del revision_step_record["inputs"]["images"]
                revision_step_record["bindings"]["images"] = {"from_step": "image", "output": "images"}
                independent_step_record = create_workflow_step_draft("translate", "prompt-translation", {"text": "숲"})
                workflow_run_store.register_workflow_run("run", "session", [image_step_record, revision_step_record, independent_step_record])
                image_request_identifier = workflow_run_store.claim_ready_step("run", "image")["request_id"]
                image_job_identifier = "2026-11-21_01-01-01-00000001"
                image_result_directory = temporary_root_path / image_job_identifier
                image_result_directory.mkdir()
                if image_file_condition == "corrupt":
                    image_result_path = image_result_directory / "result.png"
                    Image.new("RGB", (32, 32), "green").save(image_result_path)
                    image_content_bytes = bytearray(image_result_path.read_bytes())
                    image_content_bytes[image_content_bytes.index(b"IDAT") + 5] ^= 1
                    image_result_path.write_bytes(image_content_bytes)
                image_preview_path = f"/flux-image-generator/jobs/{image_job_identifier}/result.png"
                dispatched_command_names = []

                def simulate_workflow_gateway(current_command_name, current_request_payload):
                    dispatched_command_names.append(current_command_name)
                    if current_command_name == "hermes-flux-delegation-status":
                        self.assertEqual(current_request_payload["request_id"], image_request_identifier)
                        return {"receipt": {"state": "accepted", "service": "flux-image", "job_id": image_job_identifier,
                                            "request_id": image_request_identifier},
                                "job": {"id": image_job_identifier, "status": "completed", "image": image_preview_path},
                                "result": {"status": "available", "image": image_preview_path}}
                    return {}

                with patch("tools.review.domains.image.flux_image_generation.FluxImageGenerationManager") as generator_manager_factory:
                    generator_manager_factory.return_value.job_storage_root = temporary_root_path
                    advance_workflow_run(workflow_run_store, "run", simulate_workflow_gateway)
                current_run_view = WorkflowRunStore(workflow_database_path).read_session_run_view("run", "session")
                self.assertEqual([step["state"] for step in current_run_view["steps"]], ["blocked", "blocked", "submitting"])
                self.assertEqual(current_run_view["steps"][0]["source_state"], "completed")
                self.assertEqual(current_run_view["steps"][1]["blocking_step"], "image")
                self.assertEqual(current_run_view["results"], [])
                self.assertEqual(dispatched_command_names, ["hermes-flux-delegation-status", "hermes-delegate-translation"])

    def test_flux_cancel_checks_source_identity_and_observes_terminal_after_response_loss(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            workflow_database_path = Path(temporary_root_name) / "workflow.sqlite3"
            workflow_run_store = WorkflowRunStore(workflow_database_path)
            image_step_record = create_workflow_step_draft("image", "flux-image", {"prompt": "forest"})
            workflow_run_store.register_workflow_run("run", "session", [image_step_record])
            current_request_identifier = workflow_run_store.claim_ready_step("run", "image")["request_id"]
            workflow_run_store.request_workflow_cancellation("run", "session")
            source_job_record = {"id": "other", "status": "cancelled"}
            cancellation_request_records = []

            def simulate_flux_command(current_command_name, current_payload_record):
                if current_command_name == "hermes-flux-delegation-status":
                    self.assertEqual(current_payload_record, {"request_id": current_request_identifier})
                    return {"receipt": {"state": "accepted", "service": "flux-image", "job_id": "job",
                                        "request_id": current_request_identifier}, "job": source_job_record}
                self.assertEqual(current_command_name, "hermes-flux-delegation-cancel")
                cancellation_request_records.append(current_payload_record)
                raise OSError("취소 응답 유실")

            advance_workflow_run(workflow_run_store, "run", simulate_flux_command)
            current_step_record = workflow_run_store.list_run_step_records("run")[0]
            self.assertEqual((current_step_record["state"], current_step_record["source_state"]), ("submitting", "unknown"))
            source_job_record.update(id="job", status="running")
            advance_workflow_run(workflow_run_store, "run", simulate_flux_command)
            workflow_run_store = WorkflowRunStore(workflow_database_path)
            advance_workflow_run(workflow_run_store, "run", simulate_flux_command)
            current_step_record = workflow_run_store.list_run_step_records("run")[0]
            self.assertEqual((current_step_record["state"], current_step_record["cancel_delivery"]), ("submitting", "unconfirmed"))
            source_job_record["status"] = "cancelled"
            advance_workflow_run(workflow_run_store, "run", simulate_flux_command)
            self.assertEqual(workflow_run_store.list_run_step_records("run")[0]["state"], "cancelled")
            self.assertEqual(cancellation_request_records, [{"request_id": current_request_identifier, "job_id": "job"}])

    def test_restarted_chain_uses_pinned_image_after_source_removal(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path = Path(temporary_root_name)
            workflow_database_path = temporary_root_path / "workflow.sqlite3"
            workflow_run_store = WorkflowRunStore(workflow_database_path)
            translation_step_record = create_workflow_step_draft("translate", "prompt-translation", {"text": "숲"})
            image_step_record = create_workflow_step_draft("image", "flux-image", {})
            image_step_record["bindings"]["prompt"] = {"from_step": "translate", "output": "text"}
            revision_step_record = create_workflow_step_draft("revise", "flux-image", {"prompt": "add flowers"})
            del revision_step_record["inputs"]["images"]
            revision_step_record["bindings"]["images"] = {"from_step": "image", "output": "images"}
            # 역순 정의로 후속 접수 전에 원본 삭제와 프로세스 재시작을 재현한다.
            workflow_run_store.register_workflow_run("run", "session", [revision_step_record, image_step_record, translation_step_record])
            submitted_job_records = {}
            pinned_image_bytes = None

            def simulate_generator_command(current_command_name, current_request_payload):
                nonlocal pinned_image_bytes
                current_request_identifier = current_request_payload["request_id"]
                if current_command_name.startswith("hermes-delegate"):
                    self.assertNotIn(current_request_identifier, submitted_job_records)
                    current_job_identifier = f"2026-11-21_01-01-01-{len(submitted_job_records):08x}"
                    submitted_job_records[current_request_identifier] = current_job_identifier
                    if current_command_name == "hermes-delegate-flux-image":
                        current_input_record = current_request_payload["request"]
                        if current_input_record["images"]:
                            self.assertEqual(current_input_record["prompt"], "add flowers")
                            self.assertEqual(base64.b64decode(current_input_record["images"][0]), pinned_image_bytes)
                        else:
                            self.assertEqual(current_input_record["prompt"], "forest")
                        current_job_directory = temporary_root_path / current_job_identifier
                        current_job_directory.mkdir()
                        Image.new("RGB", (32, 32), "green").save(current_job_directory / "result.png")
                        if not current_input_record["images"]:
                            pinned_image_bytes = (current_job_directory / "result.png").read_bytes()
                    return {}
                current_job_identifier = submitted_job_records[current_request_identifier]
                translation_status_requested = current_command_name == "hermes-translation-status"
                current_receipt_record = {"state": "accepted", "request_id": current_request_identifier,
                    "service": "prompt-translation" if translation_status_requested else "flux-image", "job_id": current_job_identifier}
                if translation_status_requested:
                    return {"receipt": current_receipt_record, "job": {"status": "completed", "result": {"text": "forest"}}}
                current_preview_path = f"/flux-image-generator/jobs/{current_job_identifier}/result.png"
                return {"receipt": current_receipt_record, "job": {"id": current_job_identifier,
                    "status": "completed", "image": current_preview_path}, "result": {"status": "available", "image": current_preview_path}}

            with patch("tools.review.domains.image.flux_image_generation.FluxImageGenerationManager") as generator_manager_factory:
                generator_manager_factory.return_value.job_storage_root = temporary_root_path
                for _ in range(6):
                    workflow_run_store = WorkflowRunStore(workflow_database_path)
                    advance_workflow_run(workflow_run_store, "run", simulate_generator_command)
                    for current_result_record in workflow_run_store.read_run_results("run"):
                        if current_result_record["step_id"] == "image":
                            (temporary_root_path / current_result_record["job_id"] / "result.png").unlink(missing_ok=True)
            current_run_view = workflow_run_store.read_session_run_view("run", "session")
            self.assertEqual(len(submitted_job_records), 3)
            self.assertEqual([record["state"] for record in current_run_view["steps"]], ["completed"] * 3)
            self.assertEqual(current_run_view["results"][1]["output_metadata"]["sha256"], hashlib.sha256(pinned_image_bytes).hexdigest())
