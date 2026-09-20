"""파이프라인 스펙/입력 JSON 실행기 테스트."""

from __future__ import annotations

import os
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any

from workflow.pipelines.runtime import pipeline_json_runner


class PipelineJsonRunnerTest(unittest.TestCase):
    def test_normalize_generation_contract_payload_accepts_minimum_contract(self) -> None:
        payload = {
            "style": {
                "reference": ["Stardew Valley"],
                "mood": ["bright"],
                "energy_curve": ["intro", "lift", "return"],
            },
            "instrumentation": {
                "strict": True,
                "allowed": ["violin", "keyboard", "drums", "bass", "guitar"],
                "melody_lead": "keyboard",
            },
            "composition_rules": {
                "structure": [
                    {"section": "A", "bars": [1, 4], "role": "theme_intro"},
                    {"section": "B", "bars": [5, 8], "role": "return_to_tonic"},
                ]
            },
        }
        normalized = pipeline_json_runner._normalize_generation_contract_payload(payload)
        self.assertEqual(normalized["instrumentation"]["melody_lead"], "keyboard")

    def test_normalize_generation_contract_payload_rejects_non_contiguous_structure(self) -> None:
        payload = {
            "style": {
                "reference": ["Stardew Valley"],
                "mood": ["bright"],
                "energy_curve": ["intro", "lift", "return"],
            },
            "instrumentation": {
                "strict": True,
                "allowed": ["violin", "keyboard", "drums", "bass", "guitar"],
                "melody_lead": "keyboard",
            },
            "composition_rules": {
                "structure": [
                    {"section": "A", "bars": [1, 4], "role": "theme_intro"},
                    {"section": "B", "bars": [6, 8], "role": "return_to_tonic"},
                ]
            },
        }
        with self.assertRaises(RuntimeError):
            pipeline_json_runner._normalize_generation_contract_payload(payload)

    def test_read_env_int_uses_alias_and_validates(self) -> None:
        with mock.patch.dict(os.environ, {"WORKFLOW_HEARTBEAT_SECONDS": "7"}, clear=False):
            self.assertEqual(
                pipeline_json_runner._read_env_int(
                    "WORKFLOW_RUNTIME_HEARTBEAT_SECONDS",
                    5,
                    aliases=["WORKFLOW_HEARTBEAT_SECONDS"],
                    min_value=0,
                ),
                7,
            )

        with mock.patch.dict(os.environ, {"WORKFLOW_RUNTIME_HEARTBEAT_SECONDS": "0"}, clear=False):
            self.assertEqual(
                pipeline_json_runner._read_env_int(
                    "WORKFLOW_RUNTIME_HEARTBEAT_SECONDS",
                    5,
                    min_value=0,
                ),
                0,
            )

    def test_read_env_int_raises_on_invalid_value(self) -> None:
        with mock.patch.dict(os.environ, {"WORKFLOW_RUNTIME_HEARTBEAT_SECONDS": "abc"}, clear=False):
            with self.assertRaises(RuntimeError):
                pipeline_json_runner._read_env_int("WORKFLOW_RUNTIME_HEARTBEAT_SECONDS", 5)

        with mock.patch.dict(os.environ, {"WORKFLOW_RUNTIME_HEARTBEAT_SECONDS": "0"}, clear=False):
            with self.assertRaises(RuntimeError):
                pipeline_json_runner._read_env_int("WORKFLOW_RUNTIME_HEARTBEAT_SECONDS", 5, min_value=1)

    def test_build_runtime_record_dir_under_result(self) -> None:
        record_dir = pipeline_json_runner._build_runtime_record_dir(
            "pipeline-sample",
            {"run_id": "test-run-id"},
        )
        self.assertEqual(
            str(record_dir),
            str(Path(".result/workflow/runtime/records/pipeline-sample/test-run-id")),
        )

    def test_write_node_records_if_possible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            record_dir = Path(temp_dir) / "records"
            written = pipeline_json_runner._write_node_records_if_possible(
                record_dir,
                ["concept.design.generate", "image.generate", "image.refine"],
                {
                    "result": {
                        "concept": {"status": "generated"},
                        "image_generate": {"status": "generated"},
                        "image_refine": {"status": "generated"},
                    }
                },
            )
            self.assertEqual(len(written), 3)
            for path in written:
                self.assertTrue(path.is_file())

    def test_run_declared_node_chain_resolves_contract_links(self) -> None:
        spec = {
            "pipeline_id": "unit-contract-chain",
            "version": "0.1.0",
            "input_contract": [
                "seed:txt",
                "note:txt(optional)",
            ],
            "output_contract": [
                "final_item:txt",
                "json:json",
            ],
            "node_contracts": [
                {
                    "node_id": "stage_one",
                    "inputs": [{"name": "seed", "source": "pipeline.input", "required": True}],
                    "outputs": [{"name": "generated"}],
                },
                {
                    "node_id": "stage_two",
                    "inputs": [{"name": "generated", "source": "stage_one", "required": True}],
                    "outputs": [{"name": "enriched"}],
                },
                {
                    "node_id": "stage_three",
                    "inputs": [
                        {"name": "enriched", "source": "stage_two", "required": True},
                        {"name": "note", "source": "pipeline.input", "required": False},
                    ],
                    "outputs": [{"name": "final_item"}],
                },
            ],
            "order": [
                "stage_one",
                "stage_two",
                "stage_three",
            ],
            "node_links": [
                {"from": "pipeline.input", "to": "stage_one", "mapping": {"seed": "seed"}},
                {"from": "stage_one", "to": "stage_two", "mapping": {"generated": "generated"}},
                {"from": "stage_two", "to": "stage_three", "mapping": {"enriched": "enriched"}},
                {"from": "pipeline.input", "to": "stage_three", "mapping": {"note": "note"}},
            ],
            "runtime": {"executor": "workflow.pipelines.runtime.pipeline_json_runner:run_declared_node_chain"},
        }
        contract = pipeline_json_runner._validate_spec(spec)

        def stage_one(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
            return {"generated": f"generated:{payload.get('seed')}"}

        def stage_two(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
            return {"enriched": f"enriched:{payload.get('generated')}"}

        def stage_three(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
            note = payload.get("note", "")
            return {"final_item": f"{payload.get('enriched')}:{note}"}

        with mock.patch(
            "workflow.pipelines.runtime.pipeline_json_runner._build_control_music_executors",
            return_value={
                "stage_one": stage_one,
                "stage_two": stage_two,
                "stage_three": stage_three,
            },
        ):
            result = pipeline_json_runner.run_declared_node_chain(
                {
                    "pipeline": "unit-contract-chain",
                    "run_id": "test-run-id",
                    "seed": "abc",
                    "note": "hello",
                    "run_root": "",
                },
                pipeline_id="unit-contract-chain",
                write_output=True,
                contract=contract,
            )

        self.assertEqual(result["outputs"]["final_item"], "enriched:generated:abc:hello")
        self.assertEqual(result["result"]["stage_one"]["generated"], "generated:abc")
        self.assertEqual(result["result"]["stage_two"]["enriched"], "enriched:generated:abc")

    def test_run_pipeline_from_files_uses_declared_node_chain(self) -> None:
        spec = {
            "pipeline_id": "unit-contract-chain",
            "version": "0.1.0",
            "input_contract": [
                "seed:txt",
                "note:txt(optional)",
            ],
            "output_contract": [
                "final_item:txt",
                "json:json",
            ],
            "node_contracts": [
                {
                    "node_id": "node_one",
                    "inputs": [{"name": "seed", "source": "pipeline.input", "required": True}],
                    "outputs": [{"name": "generated"}],
                },
                {
                    "node_id": "node_two",
                    "inputs": [{"name": "generated", "source": "node_one", "required": True}],
                    "outputs": [{"name": "enriched"}],
                },
                {
                    "node_id": "node_three",
                    "inputs": [
                        {"name": "enriched", "source": "node_two", "required": True},
                        {"name": "note", "source": "pipeline.input", "required": False},
                    ],
                    "outputs": [{"name": "final_item"}],
                },
            ],
            "order": ["node_one", "node_two", "node_three"],
            "node_links": [
                {"from": "pipeline.input", "to": "node_one", "mapping": {"seed": "seed"}},
                {"from": "node_one", "to": "node_two", "mapping": {"generated": "generated"}},
                {"from": "node_two", "to": "node_three", "mapping": {"enriched": "enriched"}},
                {"from": "pipeline.input", "to": "node_three", "mapping": {"note": "note"}},
            ],
            "runtime": {"executor": "workflow.pipelines.runtime.pipeline_json_runner:run_declared_node_chain"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_spec = Path(temp_dir) / "spec.json"
            temp_input = Path(temp_dir) / "input.json"
            temp_spec.write_text(
                json.dumps(spec, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_input.write_text(
                json.dumps(
                    {
                        "pipeline": "unit-contract-chain",
                        "seed": "seed",
                        "note": "ok",
                        "run_id": "run-from-file",
                        "run_root": temp_dir,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            def node_one(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {"generated": f"generated:{payload.get('seed')}"}

            def node_two(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {"enriched": f"enriched:{payload.get('generated')}"}

            def node_three(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {"final_item": f"{payload.get('enriched')}:{payload.get('note', '')}"}

            with mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._build_control_music_executors",
                return_value={
                    "node_one": node_one,
                    "node_two": node_two,
                    "node_three": node_three,
                },
            ):
                result = pipeline_json_runner.run_pipeline_from_files(
                    str(temp_spec),
                    str(temp_input),
                    run_root=temp_dir,
                    write_output=False,
                )

        self.assertEqual(result["outputs"]["final_item"], "enriched:generated:seed:ok")

    def test_run_pipeline_from_files_accepts_compatibility_alias_and_uses_effective_pipeline_id(self) -> None:
        spec = {
            "pipeline_id": "music-composer-magenta-orchestrated",
            "version": "0.1.0",
            "input_contract": [],
            "output_contract": ["json:json"],
            "nodes": [{"node_id": "dummy"}],
            "runtime": {"executor": "workflow.pipelines.runtime.spec_runtime:run_spec_pipeline"},
        }
        captured_pipeline_ids: list[str] = []

        def fake_executor(payload: dict[str, Any], *, pipeline_id: str, write_output: bool = True) -> dict[str, Any]:
            _ = payload, write_output
            captured_pipeline_ids.append(pipeline_id)
            return {"pipeline": pipeline_id, "outputs": {"json": {"ok": True}}, "result": {}, "run_root": "", "node_records_root": ""}

        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = Path(temp_dir) / "spec.json"
            input_path = Path(temp_dir) / "input.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            input_path.write_text(
                json.dumps({"pipeline": "music-composer-control-first"}, ensure_ascii=False),
                encoding="utf-8",
            )
            with mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._resolve_executor",
                return_value=fake_executor,
            ), mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._validate_result_against_output_contract",
                return_value=None,
            ):
                result = pipeline_json_runner.run_pipeline_from_files(
                    str(spec_path),
                    str(input_path),
                    run_root=temp_dir,
                    write_output=False,
                )
        self.assertEqual(captured_pipeline_ids, ["music-composer-control-first"])
        self.assertEqual(result["pipeline"], "music-composer-control-first")

    def test_run_declared_node_chain_bootstrap_model_commands(self) -> None:
        spec = {
            "pipeline_id": "unit-bootstrap-chain",
            "version": "0.1.0",
            "input_contract": [
                "seed:txt",
                "soundfont_profile:txt",
            ],
            "output_contract": [
                "final_item:txt",
                "json:json",
            ],
            "node_contracts": [
                {
                    "node_id": "node_bootstrap",
                    "inputs": [{"name": "seed", "source": "pipeline.input", "required": True}],
                    "outputs": [{"name": "seed_out"}],
                },
                {
                    "node_id": "node_finalize",
                    "inputs": [
                        {"name": "seed_out", "source": "node_bootstrap", "required": True},
                        {"name": "soundfont_profile", "source": "pipeline.input", "required": False},
                    ],
                    "outputs": [{"name": "final_item"}],
                },
            ],
            "order": ["node_bootstrap", "node_finalize"],
            "node_links": [
                {"from": "pipeline.input", "to": "node_bootstrap", "mapping": {"seed": "seed"}},
                {"from": "node_bootstrap", "to": "node_finalize", "mapping": {"seed_out": "seed_out"}},
                {"from": "pipeline.input", "to": "node_finalize", "mapping": {"soundfont_profile": "soundfont_profile"}},
            ],
            "runtime": {"executor": "workflow.pipelines.runtime.pipeline_json_runner:run_declared_node_chain"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "unit-bootstrap-package.json"
            dep_file = Path(temp_dir) / "deps.txt"
            dep_file.write_text("ok", encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "package_id": "unit-bootstrap",
                        "node_id": "node_bootstrap",
                        "bootstrap": {
                            "dependency_files": [str(dep_file)],
                            "dependency_fetch_commands": [
                                ["python3", "-c", "print('dep_fetch:{seed}')"]
                            ],
                            "install_commands": [
                                ["python3", "-c", "print('install')"]
                            ],
                            "model_commands": [
                                ["python3", "-c", "print('model:{soundfont_profile}')"],
                                ["python3", "-c", "print('run_root:{run_root}')"],
                            ],
                            "required_model_ids": ["{soundfont_profile}"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def node_bootstrap(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {"seed_out": f"seed-out:{payload.get('seed')}"}

            def node_finalize(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {
                    "final_item": (
                        f"{payload.get('seed_out')}:{payload.get('soundfont_profile', '')}"
                    )
                }

            with mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._resolve_node_manifest",
                side_effect=lambda node_id: manifest_path if node_id == "node_bootstrap" else None,
            ), mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._build_control_music_executors",
                return_value={
                    "node_bootstrap": node_bootstrap,
                    "node_finalize": node_finalize,
                },
            ), mock.patch("workflow.pipelines.runtime.pipeline_json_runner.run_prepare_command") as run_prepare:
                contract = pipeline_json_runner._validate_spec(spec)
                result = pipeline_json_runner.run_declared_node_chain(
                    {
                        "pipeline": "unit-bootstrap-chain",
                        "run_id": "run-bootstrap",
                        "seed": "seedvalue",
                        "soundfont_profile": "piano",
                        "run_root": temp_dir,
                    },
                    pipeline_id="unit-bootstrap-chain",
                    write_output=True,
                    contract=contract,
                )

            self.assertEqual(result["outputs"]["final_item"], "seed-out:seedvalue:piano")
            prepared_commands = [record.kwargs["command"] for record in run_prepare.call_args_list]
            self.assertIn(["python3", "-c", "print('dep_fetch:seedvalue')"], prepared_commands)
            self.assertIn(["python3", "-c", "print('install')"], prepared_commands)
            self.assertIn(["python3", "-c", "print('model:piano')"], prepared_commands)
            self.assertIn(["python3", "-c", f"print('run_root:{temp_dir}')"], prepared_commands)
            self.assertEqual(len(prepared_commands), 4)

    def test_run_declared_node_chain_bootstrap_docker_without_dockerfile_fails(self) -> None:
        spec = {
            "pipeline_id": "unit-bootstrap-chain-docker",
            "version": "0.1.0",
            "input_contract": [
                "seed:txt",
            ],
            "output_contract": [
                "final_item:txt",
                "json:json",
            ],
            "node_contracts": [
                {
                    "node_id": "node_bootstrap",
                    "inputs": [{"name": "seed", "source": "pipeline.input", "required": True}],
                    "outputs": [{"name": "final_item"}],
                },
            ],
            "order": ["node_bootstrap"],
            "node_links": [
                {"from": "pipeline.input", "to": "node_bootstrap", "mapping": {"seed": "seed"}},
            ],
            "runtime": {"executor": "workflow.pipelines.runtime.pipeline_json_runner:run_declared_node_chain"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "unit-bootstrap-package.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "package_id": "unit-bootstrap",
                        "node_id": "node_bootstrap",
                        "bootstrap": {
                            "runtime": {
                                "environment": "docker",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def node_bootstrap(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {"final_item": f"seed-out:{payload.get('seed')}"}

            with mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._resolve_node_manifest",
                side_effect=lambda node_id: manifest_path if node_id == "node_bootstrap" else None,
            ), mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._build_control_music_executors",
                return_value={"node_bootstrap": node_bootstrap},
            ):
                contract = pipeline_json_runner._validate_spec(spec)
                with self.assertRaises(RuntimeError) as context:
                    pipeline_json_runner.run_declared_node_chain(
                        {
                            "pipeline": "unit-bootstrap-chain-docker",
                            "run_id": "run-bootstrap-docker",
                            "seed": "seedvalue",
                            "run_root": temp_dir,
                        },
                        pipeline_id="unit-bootstrap-chain-docker",
                        write_output=True,
                        contract=contract,
                    )
                self.assertIn("dockerfile", str(context.exception))

    def test_run_declared_node_chain_bootstrap_missing_command_binary_fails(self) -> None:
        spec = {
            "pipeline_id": "unit-bootstrap-command-guard",
            "version": "0.1.0",
            "input_contract": [
                "seed:txt",
            ],
            "output_contract": [
                "final_item:txt",
                "json:json",
            ],
            "node_contracts": [
                {
                    "node_id": "node_bootstrap",
                    "inputs": [{"name": "seed", "source": "pipeline.input", "required": True}],
                    "outputs": [{"name": "final_item"}],
                },
            ],
            "order": ["node_bootstrap"],
            "node_links": [
                {"from": "pipeline.input", "to": "node_bootstrap", "mapping": {"seed": "seed"}},
            ],
            "runtime": {"executor": "workflow.pipelines.runtime.pipeline_json_runner:run_declared_node_chain"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "unit-bootstrap-package.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "package_id": "unit-bootstrap",
                        "node_id": "node_bootstrap",
                        "bootstrap": {
                            "dependency_fetch_commands": [
                                ["__no_such_python_binary__"]
                            ],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def node_bootstrap(payload: dict[str, Any], context: Any, run_root: Path) -> dict[str, Any]:
                return {"final_item": f"seed-out:{payload.get('seed')}"}

            with mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._resolve_node_manifest",
                side_effect=lambda node_id: manifest_path if node_id == "node_bootstrap" else None,
            ), mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner.run_prepare_command",
            ) as run_prepare:
                contract = pipeline_json_runner._validate_spec(spec)
                with self.assertRaises(RuntimeError) as context:
                    pipeline_json_runner.run_declared_node_chain(
                        {
                            "pipeline": "unit-bootstrap-command-guard",
                            "run_id": "run-bootstrap-command-guard",
                            "seed": "seedvalue",
                            "run_root": temp_dir,
                        },
                        pipeline_id="unit-bootstrap-command-guard",
                        write_output=True,
                        contract=contract,
                    )
                self.assertIn("실행명령을 찾을 수 없습니다", str(context.exception))
                run_prepare.assert_not_called()

    def test_run_declared_node_chain_runs_docker_mode(self) -> None:
        spec = {
            "pipeline_id": "unit-bootstrap-chain-docker",
            "version": "0.1.0",
            "input_contract": [
                "seed:txt",
            ],
            "output_contract": [
                "final_item:txt",
                "json:json",
            ],
            "node_contracts": [
                {
                    "node_id": "node_bootstrap",
                    "inputs": [{"name": "seed", "source": "pipeline.input", "required": True}],
                    "outputs": [{"name": "final_item"}],
                },
            ],
            "order": ["node_bootstrap"],
            "node_links": [
                {"from": "pipeline.input", "to": "node_bootstrap", "mapping": {"seed": "seed"}},
            ],
            "runtime": {"executor": "workflow.pipelines.runtime.pipeline_json_runner:run_declared_node_chain"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "unit-bootstrap-package.json"
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.10-slim\n", encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "package_id": "unit-bootstrap",
                        "node_id": "node_bootstrap",
                        "bootstrap": {
                            "runtime": {
                                "environment": "docker",
                                "dockerfile": str(dockerfile_path),
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner._resolve_node_manifest",
                side_effect=lambda node_id: manifest_path if node_id == "node_bootstrap" else None,
            ), mock.patch(
                "workflow.pipelines.runtime.pipeline_json_runner.run_node_in_container",
            ) as run_node_in_container:
                run_node_in_container.return_value = (
                    {"final_item": "container-output"},
                    [{"name": "node-bootstrap", "status": "completed"}],
                )
                contract = pipeline_json_runner._validate_spec(spec)
                result = pipeline_json_runner.run_declared_node_chain(
                    {
                        "pipeline": "unit-bootstrap-chain-docker",
                        "run_id": "run-bootstrap-docker",
                        "seed": "seedvalue",
                        "run_root": temp_dir,
                    },
                    pipeline_id="unit-bootstrap-chain-docker",
                    write_output=True,
                    contract=contract,
                )

                self.assertEqual(result["outputs"]["final_item"], "container-output")
                run_node_in_container.assert_called_once()
                called_kwargs = run_node_in_container.call_args.kwargs
                self.assertEqual(called_kwargs["node_id"], "node_bootstrap")
                self.assertEqual(called_kwargs["dockerfile_path"], str(dockerfile_path))



if __name__ == "__main__":
    unittest.main()
