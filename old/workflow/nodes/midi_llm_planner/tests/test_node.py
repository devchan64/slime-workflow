"""midi_llm_planner 노드 테스트."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.midi_llm_planner.application.stage import MidiLlmPlannerModule


PACKAGE_PATH = Path("workflow/nodes/midi_llm_planner/packages/unit-midi-llm-plan.json")
INPUT_PATH = Path("workflow/nodes/midi_llm_planner/packages/prompt-plan.input.json")


class MidiLlmPlannerNodeTest(unittest.TestCase):
    def test_package_contract_files_exist(self) -> None:
        self.assertTrue(PACKAGE_PATH.is_file())
        self.assertTrue(INPUT_PATH.is_file())
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["node_id"], "music.midi.plan.midillm")
        self.assertIn("Qwen/Qwen2.5-1.5B-Instruct", package["prepare"]["required_model_ids"])

    def test_real_planning(self) -> None:
        if os.getenv("WORKFLOW_MIDI_LLM_PLANNER_REAL_TEST", "").strip().lower() not in {"1", "true", "yes", "on"}:
            self.skipTest("실모델 planner 테스트 비활성화")

        payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            payload["run_root"] = temp_dir
            context = PipelineContext(run_id="test-midi-llm-planner", run_root=temp_dir, area="workflow", pipeline="music")
            result = MidiLlmPlannerModule().process(context, payload)
            self.assertEqual(result.get("status"), "planned")

            composer_input = result.get("composer_input")
            self.assertIsInstance(composer_input, dict)
            for key in [
                "prompt",
                "tempo_bpm",
                "max_new_tokens",
                "temperature",
                "top_p",
                "top_k",
                "repetition_penalty",
                "n_outputs",
            ]:
                self.assertIn(key, composer_input)


if __name__ == "__main__":
    unittest.main()
