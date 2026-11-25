import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.flux_reports import REPORT, advance_report, proposal_request_id, register_report
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class FluxReportTests(unittest.TestCase):
    def exercise(self, chat):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = "2026-11-23_10-00-00-11111111"
            proposal = "2026-11-23_09-00-00-22222222"
            report_job = "2026-11-23_11-00-00-33333333"
            service = "flux-image"
            session = "a" * 32
            sessions = HermesSessionStore(root / "sessions")
            sessions.create_session_record(session)
            directory = root / job
            directory.mkdir()
            origin = None
            receipts = HermesDelegationStore(root / "receipts")
            if chat:
                sessions.append_session_request(session, "test_flux", "이미지 생성")
                sessions.attach_session_job(session, "test_flux", proposal)
                identifier = proposal_request_id(session, proposal, service)
                origin = {"session_id": session, "proposal_job_id": proposal, "request_id": identifier}
                receipts.execute_service_delegation_once(identifier, service, {}, lambda _: {"id":job}, lambda _: None)
            register_report(directory, service, origin)
            write_record_atomically(directory / "request.json", {"width":32, "height":32, "prompt":"one blue umbrella"})
            write_record_atomically(directory / "status.json", {"status":"completed"})
            Image.new("RGB", (32, 32)).save(directory / "result.png")
            calls = []
            receipt = {}

            def dispatch(command, payload):
                calls.append(command)
                if command == "hermes-submit":
                    receipt.update(payload)
                    return {"id":report_job}
                return {"id": report_job, "request":receipt, "status":{"status":"completed"}, "final_response":"PNG 32×32, 시각 품질 미검수."}

            with patch("workflow.domains.hermes_agent.flux_reports.visual_observation", return_value={"observation":"a red chair"}) as vision, patch("workflow.domains.hermes_agent.flux_reports.HermesDelegationStore", return_value=receipts):
                for _ in range(2):
                    advance_report(directory, service, dispatch, sessions)
            vision.assert_called_once()
            self.assertIn("one blue umbrella", receipt["prompt"])
            self.assertIn("a red chair", receipt["prompt"])
            record = json.loads((directory / REPORT).read_text())
            self.assertEqual(record["evidence"]["checks"]["dimensions"], "pass")
            self.assertEqual(record["state"], "completed")
            self.assertEqual(record["hermes_job_id"], report_job)
            self.assertEqual(calls.count("hermes-submit"), 1)
            jobs = [m["job_id"] for m in sessions.read_session_record(session)["messages"]]
            self.assertEqual(jobs, [proposal, None, report_job] if chat else [])

    def test_chat_report_delivery(self):
        self.exercise(True)

    def test_direct_result_link_target(self):
        self.exercise(False)


    def test_corrupt_png_and_changed_digest(self):
        from workflow.domains.image.flux_report import inspect_flux_output
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            write_record_atomically(directory / "request.json", {"width": 16, "height": 16})
            path = directory / "result.png"
            self.assertEqual(inspect_flux_output(directory, "flux-image")["checks"]["output_file"], "fail")
            path.write_bytes(b"invalid png")
            self.assertEqual(inspect_flux_output(directory, "flux-image")["checks"]["png_decode"], "fail")
            Image.new("RGB", (32, 32)).save(path)
            write_record_atomically(directory / "result.json", {"image_sha256": "0" * 64})
            checks = inspect_flux_output(directory, "flux-image")["checks"]
            self.assertEqual((checks["dimensions"], checks["recorded_sha256"]), ("fail", "fail"))
            self.assertEqual(checks["visual_quality"], "unknown")

    def test_replaced_attempt_with_same_image_cannot_publish_previous_report(self):
        service = "flux-image"
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            register_report(directory, service, None)
            write_record_atomically(directory / "request.json", {"width": 32, "height": 32})
            write_record_atomically(directory / "status.json", {"status": "completed"})
            write_record_atomically(directory / "queue-telemetry.json", {"attempt_id": "1"})
            Image.new("RGB", (32, 32)).save(directory / "result.png")
            hermes_job = "2026-11-23_11-00-00-33333333"

            def dispatch(command, payload):
                if command == "hermes-submit":
                    return {"id": hermes_job}
                record = json.loads((directory / REPORT).read_text())
                write_record_atomically(directory / "queue-telemetry.json", {"attempt_id": "2"})
                return {"id": hermes_job, "request": {"request_id": record["request_id"]},
                        "status": {"status": "completed"}, "final_response": "검수 결과"}

            advance_report(directory, service, dispatch, None)
            self.assertEqual(json.loads((directory / REPORT).read_text())["state"], "failed")

    def test_handoff_origin_requires_matching_accepted_receipt(self):
        from unittest.mock import Mock
        from workflow.domains.hermes_agent.flux_reports import recover_handoff_origin
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = GpuHandoffStore(root / "handoffs")
            receipts = HermesDelegationStore(root / "receipts")
            session, job, service = "a" * 32, "2026-11-23_10-00-00-11111111", "flux-image"
            payload = {"prompt": "blue cup"}
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            store.approve("request_report", session, service, digest, target_request=payload,
                          resident_id="resident_123", confirmed=True)
            record = store.read("request_report")
            request_id = FluxHandoffAdapter().target_request_id(record)
            observed = Mock(delegation_storage_root=store.delegation_storage_root)
            observed.read.return_value = {**record, "job_id":job}
            with patch("workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore", return_value=observed), patch(
                    "workflow.domains.hermes_agent.flux_reports.HermesDelegationStore", return_value=receipts):
                self.assertIsNone(recover_handoff_origin(service, job))
                receipts.execute_service_delegation_once(request_id, service, payload, lambda _: {"id": job}, lambda _: None)
                self.assertEqual(recover_handoff_origin(service, job)["session_id"], session)
                self.assertIsNone(recover_handoff_origin(service, "2026-11-23_10-00-00-22222222"))
