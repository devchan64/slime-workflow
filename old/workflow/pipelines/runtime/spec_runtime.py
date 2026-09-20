"""스펙 중심 파이프라인 런타임.

파이프라인별 별도 스크립트 없이 spec(JSON)의 노드/바인딩을 해석해 실행한다.
"""

from __future__ import annotations

import json
import importlib
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from workflow.interfaces import PipelineContext

Payload = dict[str, Any]
NodeExecutor = Callable[[PipelineContext, Payload], Payload]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_binding(binding_from: str, payload: Payload, node_results: dict[str, Payload]) -> Any:
    raw = str(binding_from or "").strip()
    if not raw or "." not in raw:
        raise RuntimeError(f"binding.from 형식이 잘못됐습니다: {binding_from}")

    if raw.startswith("input."):
        field = raw[len("input.") :].strip()
        if field not in payload:
            raise RuntimeError(f"입력 바인딩 필드가 없습니다: {binding_from}")
        return payload[field]

    matched_node = ""
    matched_field = ""
    for node_id in sorted(node_results.keys(), key=len, reverse=True):
        prefix = f"{node_id}."
        if raw.startswith(prefix):
            matched_node = node_id
            matched_field = raw[len(prefix) :].strip()
            break
    if not matched_node:
        raise RuntimeError(f"바인딩 source 노드를 찾지 못했습니다: {binding_from}")

    output_payload = node_results.get(matched_node, {})
    if matched_field not in output_payload:
        raise RuntimeError(f"노드 출력 바인딩 필드가 없습니다: {binding_from}")
    return output_payload[matched_field]


def _require_executor_model_ssot(node_id: str) -> dict[str, str]:
    model = _load_node_model_ssot().get(node_id, {})
    provider = str(model.get("provider", "")).strip()
    model_id = str(model.get("model_id", "")).strip()
    purpose = str(model.get("purpose", "")).strip()
    if not provider or not model_id:
        raise RuntimeError(f"node model SSOT 값이 유효하지 않습니다: node_id={node_id}")
    return {"provider": provider, "model_id": model_id, "purpose": purpose}


def _resolve_node_executor_from_entrypoint(node_id: str) -> NodeExecutor:
    module_path = f"workflow.nodes.{node_id.replace('.', '_')}.entrypoints"
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        raise RuntimeError(
            "node executor를 해석할 수 없습니다. "
            f"node_id={node_id}, module={module_path}. "
            "스펙 노드에 runtime.executor를 명시하거나 entrypoints를 구성하세요."
        ) from exc
    ordered_stages = getattr(module, "ordered_stages", None)
    if not callable(ordered_stages):
        raise RuntimeError(
            f"node entrypoint가 유효하지 않습니다: node_id={node_id}, module={module_path}, required=ordered_stages()"
        )
    stages = ordered_stages()
    if not isinstance(stages, list) or len(stages) != 1 or not hasattr(stages[0], "process"):
        raise RuntimeError(
            f"node stage 구성이 비정상입니다: node_id={node_id}, module={module_path}"
        )
    return stages[0].process


def _resolve_node_executor_from_runtime(node_id: str, runtime: Any) -> NodeExecutor | None:
    if not isinstance(runtime, dict):
        return None
    process_command = runtime.get("process_command")
    if process_command:
        if isinstance(process_command, str):
            command_template = [token for token in process_command.strip().split(" ") if token.strip()]
        elif isinstance(process_command, list):
            command_template = [str(token).strip() for token in process_command if str(token).strip()]
        else:
            raise RuntimeError(
                f"node runtime.process_command 형식이 잘못됐습니다: node_id={node_id}"
            )
        if not command_template:
            raise RuntimeError(
                f"node runtime.process_command가 비어 있습니다: node_id={node_id}"
            )

        def _process_executor(context: PipelineContext, node_input: Payload) -> Payload:
            run_root = Path(str(node_input.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
            work_dir = run_root / "process-exec" / node_id.replace(".", "-")
            work_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(work_dir), suffix=".input.json") as in_file:
                json.dump(node_input, in_file, ensure_ascii=False, indent=2)
                input_json = Path(in_file.name)
            output_json = input_json.with_suffix(".output.json")
            log_json = input_json.with_suffix(".log.txt")
            replacements = {
                "input_json": str(input_json),
                "output_json": str(output_json),
                "run_root": str(run_root),
                "node_id": node_id,
            }
            command = [token.format(**replacements) for token in command_template]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(Path.cwd()),
            )
            log_json.write_text(
                "\n".join(
                    [
                        f"command={command}",
                        f"exit_code={result.returncode}",
                        "stdout:",
                        result.stdout or "",
                        "stderr:",
                        result.stderr or "",
                    ]
                ),
                encoding="utf-8",
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"node process_command 실행 실패: node_id={node_id}, exit={result.returncode}, log={log_json}"
                )
            if not output_json.is_file():
                raise RuntimeError(
                    f"node process_command output.json 누락: node_id={node_id}, output={output_json}, log={log_json}"
                )
            raw = json.loads(output_json.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise RuntimeError(
                    f"node process_command 출력은 객체여야 합니다: node_id={node_id}, output={output_json}"
                )
            return raw

        return _process_executor

    entrypoint_module = str(runtime.get("entrypoint_module", "")).strip()
    if entrypoint_module:
        module = importlib.import_module(entrypoint_module)
        ordered_stages = getattr(module, "ordered_stages", None)
        if not callable(ordered_stages):
            raise RuntimeError(
                f"node runtime.entrypoint_module가 유효하지 않습니다: node_id={node_id}, module={entrypoint_module}"
            )
        stages = ordered_stages()
        if not isinstance(stages, list) or len(stages) != 1 or not hasattr(stages[0], "process"):
            raise RuntimeError(
                f"node runtime.entrypoint_module stage 구성이 비정상입니다: node_id={node_id}, module={entrypoint_module}"
            )
        return stages[0].process
    executor_path = str(runtime.get("executor", "")).strip()
    if not executor_path:
        return None
    if ":" not in executor_path:
        raise RuntimeError(f"node runtime.executor 형식이 잘못됐습니다: node_id={node_id}, value={executor_path}")
    module_path, attr_name = executor_path.split(":", 1)
    module = importlib.import_module(module_path)
    attr = getattr(module, attr_name, None)
    if attr is None:
        raise RuntimeError(f"node runtime.executor를 찾을 수 없습니다: node_id={node_id}, value={executor_path}")
    if callable(attr):
        return attr
    raise RuntimeError(f"node runtime.executor가 callable이 아닙니다: node_id={node_id}, value={executor_path}")


@lru_cache(maxsize=1)
def _load_node_model_ssot() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parents[2] / "nodes" / "node_model_ssot.json"
    if not path.is_file():
        raise RuntimeError(f"NODE_MODEL_SSOT 파일이 없습니다: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or not obj:
        raise RuntimeError(f"NODE_MODEL_SSOT 형식이 잘못됐습니다: {path}")
    normalized: dict[str, dict[str, str]] = {}
    for node_id, item in obj.items():
        if not isinstance(item, dict):
            raise RuntimeError(f"NODE_MODEL_SSOT 항목 형식이 잘못됐습니다: node_id={node_id}")
        provider = str(item.get("provider", "")).strip()
        model_id = str(item.get("model_id", "")).strip()
        purpose = str(item.get("purpose", "")).strip()
        if not provider or not model_id:
            raise RuntimeError(f"NODE_MODEL_SSOT 필수값 누락: node_id={node_id}")
        normalized[str(node_id).strip()] = {
            "provider": provider,
            "model_id": model_id,
            "purpose": purpose,
        }
    return normalized

def run_spec_pipeline(payload: Payload, *, pipeline_id: str, write_output: bool = True) -> Payload:
    spec = payload.get("__runtime_spec")
    if not isinstance(spec, dict):
        raise RuntimeError("payload.__runtime_spec가 필요합니다")

    run_root = Path(str(payload.get("run_root", "")).strip() or ".result/workflow/runtime/run")
    run_root.mkdir(parents=True, exist_ok=True)

    node_results: dict[str, Payload] = {}
    context = PipelineContext(run_id="spec-runtime", run_root=str(run_root), area="workflow", pipeline=pipeline_id)
    for index, node in enumerate(spec.get("nodes", []), start=1):
        if not isinstance(node, dict):
            raise RuntimeError(f"spec.nodes[{index}]는 객체여야 합니다")
        node_id = str(node.get("node_id", "")).strip()
        if not node_id:
            raise RuntimeError(f"spec.nodes[{index}] node_id가 비어 있습니다")
        input_bindings = node.get("input_bindings")
        if not isinstance(input_bindings, list) or not input_bindings:
            raise RuntimeError(f"노드 input_bindings가 필요합니다: {node_id}")

        executor = _resolve_node_executor_from_runtime(node_id, node.get("runtime"))
        if executor is None:
            executor = _resolve_node_executor_from_entrypoint(node_id)
        node_model = _require_executor_model_ssot(node_id)

        node_input: Payload = {}
        for binding in input_bindings:
            if not isinstance(binding, dict):
                raise RuntimeError(f"binding 정의는 객체여야 합니다: node={node_id}")
            field = str(binding.get("field", "")).strip()
            source = str(binding.get("from", "")).strip()
            optional = bool(binding.get("optional", False))
            if not field or not source:
                raise RuntimeError(f"binding field/from 누락: node={node_id}")
            try:
                node_input[field] = _resolve_binding(source, payload, node_results)
            except RuntimeError:
                if optional:
                    # 해석기는 값 생성/치환을 하지 않는다.
                    # optional 입력이 없으면 필드를 주입하지 않고 노드 기본 동작에 위임한다.
                    continue
                else:
                    raise
        node_input["__node_model"] = dict(node_model)

        node_input["run_root"] = str(run_root)
        node_trace = run_root / "records" / "nodes" / f"node-{index:02d}-{node_id.replace('.', '-')}"
        _write_json(node_trace / "input.json", node_input)
        try:
            node_output = executor(context, node_input)
            if not isinstance(node_output, dict):
                raise RuntimeError(f"노드 출력은 객체여야 합니다: node={node_id}")
            node_output.setdefault("model", dict(node_model))
            node_results[node_id] = node_output
            _write_json(node_trace / "output.json", node_output)
        except Exception as exc:
            _write_json(
                node_trace / "error.json",
                {
                    "node_id": node_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise

    outputs: dict[str, Any] = {}
    for item in spec.get("pipeline_outputs", []):
        if not isinstance(item, dict):
            raise RuntimeError("spec.pipeline_outputs 항목은 객체여야 합니다")
        name = str(item.get("name", "")).strip()
        source = str(item.get("from", "")).strip()
        if not name or not source:
            raise RuntimeError("pipeline_outputs.name/from이 필요합니다")
        outputs[name] = _resolve_binding(source, payload, node_results)

    result = {
        "pipeline": pipeline_id,
        "run_root": str(run_root),
        "node_records_root": str((run_root / "records" / "nodes").resolve()),
        "outputs": outputs,
        "result": node_results,
        "json": {"pipeline": pipeline_id, "outputs": outputs},
    }
    if write_output:
        output_obj = payload.get("output")
        output_from_contract = (
            str(output_obj.get("path", "")).strip()
            if isinstance(output_obj, dict)
            else ""
        )
        out = Path(
            str(payload.get("output_path", "")).strip()
            or output_from_contract
            or run_root / "pipeline-result.json"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
