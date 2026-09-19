"""musicgen-small 노드 테스트."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.musicgen_small.application.stage import MusicgenSmallGenerationModule


PACKAGE_PATH = Path("workflow/nodes/musicgen_small/packages/unit-musicgen-small-generate.json")
PROMPT_PATH = Path("workflow/nodes/musicgen_small/packages/prompt-max-duration.json")


class MusicgenSmallNodeTest(unittest.TestCase):
    def test_package_contract_files_exist(self) -> None:
        self.assertTrue(PACKAGE_PATH.is_file())
        self.assertTrue(PROMPT_PATH.is_file())
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["node_id"], "musicgen.small.generate")
        self.assertIn("facebook/musicgen-small", package["prepare"]["required_model_ids"])

    def test_real_generation_max_duration(self) -> None:
        if os.getenv("WORKFLOW_MUSICGEN_SMALL_REAL_TEST", "").strip().lower() not in {"1", "true", "yes", "on"}:
            self.skipTest("실모델 테스트 비활성화")

        payload = json.loads(PROMPT_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            payload["run_root"] = temp_dir
            payload.setdefault("model_root", ".model/musicgen-small")
            context = PipelineContext(run_id="test-musicgen-small", run_root=temp_dir, area="workflow", pipeline="audio")
            result = MusicgenSmallGenerationModule().process(context, payload)
            self.assertEqual(result.get("status"), "generated")
            wav_path = Path(str(result.get("wav_path", "")).strip())
            report_path = Path(str(result.get("report_path", "")).strip())
            self.assertTrue(wav_path.is_file())
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(float(report.get("duration_seconds_generated", 0.0)), 20.0)


if __name__ == "__main__":
    unittest.main()
