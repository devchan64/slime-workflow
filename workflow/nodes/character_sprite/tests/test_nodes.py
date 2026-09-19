"""workflow 캐릭터 스프라이트 노드 패키지 회귀 테스트."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
import unittest

from PIL import Image

from workflow.interfaces import PipelineContext
from workflow.nodes.character_sprite.application.design_sheet_8dir_generation import create_test_design_sheet
from workflow.nodes.character_sprite_nodes import build_character_sprite_node_specs, build_stage_executor_map


PACKAGE_PATH = Path("workflow/nodes/character_sprite/packages/design-sheet-8dir.json")


class WorkflowCharacterSpriteNodeTest(unittest.TestCase):
    def test_character_sprite_node_matches_package(self) -> None:
        nodes = build_character_sprite_node_specs()
        self.assertEqual([node.node_id for node in nodes], ["sprite.generate"])

        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["node_id"], nodes[0].node_id)
        self.assertEqual(package["package_id"], nodes[0].package_id)
        self.assertTrue(package.get("tests"))

    def test_executor_is_workflow_node_module(self) -> None:
        executors = build_stage_executor_map()
        runner = executors["sprite.generate"]
        self.assertIn("workflow.nodes.character_sprite.application", runner.__module__)

    def test_generate_design_sheet_to_8dir_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            design_sheet = root / "design-sheet.png"
            output_png = root / "sprite.png"
            output_meta = root / "sprite.json"
            create_test_design_sheet(design_sheet, cell_width=80, cell_height=120)

            context = PipelineContext(run_id="test-character-sprite", run_root=str(root), pipeline="character")
            result = build_stage_executor_map()["sprite.generate"](
                context,
                {
                    "design_sheet": str(design_sheet),
                    "frame_width": 64,
                    "frame_height": 96,
                    "output_png": str(output_png),
                    "output_meta": str(output_meta),
                    "character_id": "test-hero",
                    "animation_id": "idle",
                },
            )

            self.assertEqual(result["sprite_sheet"]["path"], str(output_png))
            self.assertTrue(output_png.is_file())
            self.assertTrue(output_meta.is_file())
            with Image.open(output_png) as image:
                self.assertEqual(image.size, (512, 96))
            metadata = json.loads(output_meta.read_text(encoding="utf-8"))
            self.assertEqual(metadata["character_id"], "test-hero")
            self.assertEqual(metadata["frame"]["count"], 8)
            self.assertEqual(len(metadata["directions"]), 8)

    def test_cli_generates_test_resource_and_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            design_sheet = root / "design-sheet.png"
            run_root = root / "run"
            completed = subprocess.run(
                [
                    "scripts/workflow/run_character_sprite_pipeline.sh",
                    "--generate-test-resource",
                    str(design_sheet),
                    "--design-sheet",
                    str(design_sheet),
                    "--frame-width",
                    "64",
                    "--frame-height",
                    "96",
                    "--run-root",
                    str(run_root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("결과 저장 완료", completed.stdout)
            output_png = run_root / "sprite" / "character_8dir_64x96.png"
            output_meta = run_root / "sprite" / "character_8dir_64x96.json"
            self.assertTrue(output_png.is_file())
            self.assertTrue(output_meta.is_file())

    def test_character_sprite_workflow_does_not_call_framework_scripts(self) -> None:
        paths = [
            Path("scripts/workflow/run_character_sprite_pipeline.sh"),
            Path("workflow/nodes/character_sprite/runtime/cli.py"),
            Path("workflow/nodes/character_sprite/application/design_sheet_8dir_generation.py"),
        ]
        for path in paths:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("scripts/frameworks", source, msg=str(path))
            self.assertNotIn("frameworks/ai-design", source, msg=str(path))


if __name__ == "__main__":
    unittest.main()
