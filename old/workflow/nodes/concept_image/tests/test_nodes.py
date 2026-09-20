"""workflow 콘셉트 이미지 노드 매핑 회귀 테스트."""

from __future__ import annotations

from pathlib import Path
import unittest

from workflow.interfaces import PipelineContext
from workflow.nodes.concept_image_nodes import build_concept_image_node_specs, build_stage_executor_map
from workflow.nodes.concept_image.runtime.node_runner import describe_concept_image_graph
from workflow.nodes.concept_image.runtime.unit_cli import load_unit_package, validate_io_contract, validate_package_tests


class WorkflowConceptImageNodeMappingTest(unittest.TestCase):
    def test_concept_stage_count_and_order(self) -> None:
        nodes, edges = build_concept_image_node_specs()
        self.assertEqual(
            [node.node_id for node in nodes],
            [
                "concept.design.generate",
                "concept.pixel.generate",
                "concept.keyframe.compose",
                "concept.animation.render",
            ],
        )
        self.assertEqual(len(edges), 3)
        self.assertEqual(edges[0].source, "concept.design.generate")
        self.assertEqual(edges[0].target, "concept.pixel.generate")

    def test_graph_metadata_shape(self) -> None:
        graph = describe_concept_image_graph()
        self.assertEqual(graph["pipeline_id"], "concept-image.node-graph")
        self.assertEqual(graph["version"], "0.1.0")
        self.assertEqual(len(graph["nodes"]), 4)
        self.assertEqual(len(graph["edges"]), 3)

    def test_executor_is_workflow_node_module(self) -> None:
        executors = build_stage_executor_map()
        runner = executors["concept.design.generate"]
        self.assertIn("workflow.nodes.concept_image.application", runner.__module__)

    def test_unit_packages_have_valid_io_contracts(self) -> None:
        nodes, _ = build_concept_image_node_specs()
        node_by_unit = {index + 1: node for index, node in enumerate(nodes)}
        for unit in range(1, 5):
            package = load_unit_package(unit)
            validate_io_contract(package)
            validate_package_tests(package)
            node = node_by_unit[unit]
            self.assertEqual(package.unit, unit)
            self.assertEqual(package.node_id, node.node_id)
            self.assertEqual(package.package_id, node.package_id)
            self.assertTrue(package.package_id.startswith("concept-image.unit-"))

    def test_unit_package_prepare_contracts_do_not_reference_framework_configs(self) -> None:
        for unit in range(1, 5):
            package = load_unit_package(unit)
            values = [
                *package.prepare.dependency_files,
                *(part for command in package.prepare.dependency_fetch_commands for part in command),
                *(part for command in package.prepare.install_commands for part in command),
                *(part for command in package.prepare.model_commands for part in command),
            ]
            self.assertFalse(any("frameworks/ai-design/configs" in value for value in values))
            self.assertFalse(any("frameworks/ai-design/requirements" in value for value in values))

    def test_workflow_concept_image_node_does_not_read_framework_configs(self) -> None:
        source = Path("workflow/nodes/concept_image/application/design_concept_generation.py").read_text(encoding="utf-8")
        self.assertNotIn("frameworks/ai-design/configs", source)
        self.assertIn("workflow/nodes/concept_image/packages", source)

    def test_workflow_model_sync_script_does_not_call_framework_script(self) -> None:
        source = Path("scripts/workflow/model_registry_sync.sh").read_text(encoding="utf-8")
        self.assertNotIn("scripts/frameworks", source)
        self.assertIn("workflow.nodes.concept_image.runtime.model_registry_sync", source)

    def test_default_pipeline_context_area_is_workflow(self) -> None:
        context = PipelineContext(run_id="test")
        self.assertEqual(context.area, "ai-workflow")


if __name__ == "__main__":
    unittest.main()
