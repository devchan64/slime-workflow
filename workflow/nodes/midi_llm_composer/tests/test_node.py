"""MIDI-LLM 노드 테스트."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.midi_llm_composer.application.stage import MidiLlmComposerModule


PACKAGE_PATH = Path("workflow/nodes/midi_llm_composer/packages/unit-midi-llm-compose.json")
PROMPT_PATH = Path("workflow/nodes/midi_llm_composer/packages/test-input.prompt-intent.json")


class MidiLlmComposerNodeTest(unittest.TestCase):
    def test_package_contract_files_exist(self) -> None:
        self.assertTrue(PACKAGE_PATH.is_file())
        self.assertTrue(PROMPT_PATH.is_file())
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["node_id"], "music.midi.generate.midillm")
        self.assertIn("slseanwu/MIDI-LLM_Llama-3.2-1B", package["prepare"]["required_model_ids"])

    def test_real_generation(self) -> None:
        if os.getenv("WORKFLOW_MIDI_LLM_REAL_TEST", "").strip().lower() not in {"1", "true", "yes", "on"}:
            self.skipTest("실모델 테스트 비활성화")

        payload = json.loads(PROMPT_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            payload["run_root"] = temp_dir
            payload.setdefault("model_root", ".model/midi-llm")
            context = PipelineContext(run_id="test-midi-llm", run_root=temp_dir, area="workflow", pipeline="music")
            result = MidiLlmComposerModule().process(context, payload)

            self.assertEqual(result.get("status"), "generated")
            mid_path = Path(str(result.get("mid_path", "")).strip())
            raw_path = Path(str(result.get("raw_output_path", "")).strip())
            token_path = Path(str(result.get("token_output_path", "")).strip())
            report_path = Path(str(result.get("report_path", "")).strip())
            self.assertTrue(mid_path.is_file())
            self.assertTrue(raw_path.is_file())
            self.assertTrue(token_path.is_file())
            self.assertTrue(report_path.is_file())

            tokens = json.loads(token_path.read_text(encoding="utf-8")).get("tokens", [])
            self.assertGreater(len(tokens), 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertGreater(int(report.get("generated_tokens", 0)), 0)


if __name__ == "__main__":
    unittest.main()
