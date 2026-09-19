"""파이프라인 스펙(JSON) + 입력(JSON) 기반 실행기."""

from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
import threading
import time
import signal
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any
import traceback

from workflow.core.logger import log
from workflow.core.output_paths import local_runtime_output_path
from workflow.interfaces import PipelineContext
from workflow.core.node_docker_runner import run_node_in_container

# Legacy audio nodes are deprecated/removed. Keep optional imports for backward compatibility checks.
try:
    from workflow.nodes.audio_encoder_mp3.domain import WavToMp3EncodeRequest
    from workflow.nodes.audio_encoder_mp3_nodes import build_stage_executor_map as build_audio_encoder_executor_map
    from workflow.nodes.audio_render.domain import AudioChannelMix, MidiSoundfontRenderRequest
    from workflow.nodes.audio_render_nodes import build_stage_executor_map as build_audio_render_executor_map
except Exception:  # pragma: no cover - legacy path guard
    WavToMp3EncodeRequest = None  # type: ignore[assignment]
    build_audio_encoder_executor_map = None  # type: ignore[assignment]
    AudioChannelMix = None  # type: ignore[assignment]
    MidiSoundfontRenderRequest = None  # type: ignore[assignment]
    build_audio_render_executor_map = None  # type: ignore[assignment]

DEFAULT_HEARTBEAT_SECONDS = 5
DEFAULT_HEARTBEAT_STALL_LIMIT = 3
DEFAULT_STALL_TIMEOUT_SECONDS = 0
ANSI_RESET = "\033[0m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
PIPELINE_INPUT_COMPATIBILITY_ALIASES: dict[str, set[str]] = {}
GENERIC_NODE_ID_TO_CLI_MODULE: dict[str, str] = {
    "music.midi.plan.midillm": "workflow.nodes.midi_llm_planner.runtime.cli",
    "music.midi.generate.midillm": "workflow.nodes.midi_llm_composer.runtime.cli",
    "music.midi.trim.bars": "workflow.nodes.midi_trim_bars.runtime.cli",
    "music.midi.report": "workflow.nodes.music_midi_report.runtime.cli",
    "music.audio.plan.render": "workflow.nodes.audio_render_planner_v2.runtime.cli",
    "music.audio.render.wav": "workflow.nodes.audio_render_wav_v2.runtime.cli",
    "music.audio.encode.mp3": "workflow.nodes.audio_encode_mp3_v2.runtime.cli",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="파이프라인 spec/input JSON 실행기")
    parser.add_argument("--spec", required=True, help="파이프라인 스펙 JSON 경로")
    parser.add_argument("--input", required=True, help="파이프라인 입력 JSON 경로")
    parser.add_argument("--run-root", default="", help="런타임 루트 경로(오버라이드)")
    parser.add_argument("--output", default="", help="결과 JSON 출력 경로(오버라이드)")
    parser.add_argument("--no-write", action="store_true", help="실행 결과를 파일로 저장하지 않음")
    parser.add_argument(
        "--print-result-json",
        action="store_true",
        help="실행 결과 JSON을 stdout으로 출력",
    )
    return parser.parse_args(argv)


def _load_json(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_file():
        raise RuntimeError(f"JSON 파일이 없다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _require_payload_value(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise RuntimeError(f"input payload 필수 필드 누락: {key}")
    value = payload.get(key)
    if isinstance(value, str) and not value.strip():
        raise RuntimeError(f"input payload 필수 필드가 비어 있습니다: {key}")
    return value


def _build_runtime_record_dir(pipeline_id: str, payload: dict[str, Any]) -> Path:
    """런타임 입출력 기록 디렉터리를 .result 하위로 결정한다."""
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return Path(local_runtime_output_path("records", pipeline_id, run_id))


def _write_runtime_record_json(record_dir: Path, file_name: str, data: dict[str, Any]) -> Path:
    """런타임 기록 JSON을 저장한다."""
    record_dir.mkdir(parents=True, exist_ok=True)
    output_path = record_dir / file_name
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _sanitize_record_name(raw_name: str) -> str:
    text = str(raw_name or "").strip().lower()
    if not text:
        return "unknown"
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in text)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-") or "unknown"


def _write_node_records_if_possible(
    record_dir: Path,
    node_ids: list[str],
    result: dict[str, Any],
) -> list[Path]:
    """파이프라인 결과에서 노드별 기록을 분리해 저장한다."""
    written: list[Path] = []
    result_payload = result.get("result")
    if not isinstance(result_payload, dict):
        return written

    # 1) node_id 키가 직접 있는 경우를 우선 처리한다.
    direct_hits = 0
    for index, node_id in enumerate(node_ids):
        if node_id in result_payload and isinstance(result_payload[node_id], dict):
            file_name = f"node-{index + 1:02d}-{_sanitize_record_name(node_id)}.json"
            path = _write_runtime_record_json(
                record_dir,
                file_name,
                {
                    "node_id": node_id,
                    "source_key": node_id,
                    "result": result_payload[node_id],
                },
            )
            written.append(path)
            direct_hits += 1

    if direct_hits > 0:
        return written

    # 2) node_id 직접 매핑이 없으면 result dict의 상위 키를 노드 순서와 매칭해 저장한다.
    result_items = [(key, value) for key, value in result_payload.items() if isinstance(value, dict)]
    if not result_items:
        return written
    for index, (key, value) in enumerate(result_items, start=1):
        node_id = node_ids[index - 1] if index - 1 < len(node_ids) else f"unknown-{index}"
        file_name = f"node-{index:02d}-{_sanitize_record_name(node_id)}.json"
        path = _write_runtime_record_json(
            record_dir,
            file_name,
            {
                "node_id": node_id,
                "source_key": key,
                "result": value,
            },
        )
        written.append(path)
    return written


def _validate_spec(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]], list[tuple[str, str]], list[str], list[str]]:
    pipeline_id = str(spec.get("pipeline_id", "")).strip()
    if not pipeline_id:
        raise RuntimeError("pipeline spec에 pipeline_id가 없다")
    nodes = spec.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        raise RuntimeError(f"pipeline spec {pipeline_id}에 nodes가 비어 있다")

    normalized_nodes: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise RuntimeError(f"pipeline spec {pipeline_id}의 노드[{index}]가 dict가 아니다")
        node_id = str(node.get("node_id", node.get("id", ""))).strip()
        if not node_id:
            raise RuntimeError(f"pipeline spec {pipeline_id}의 노드[{index}]에 node_id/id가 없다")
        if node_id in seen_node_ids:
            raise RuntimeError(f"pipeline spec {pipeline_id}에 중복 node_id가 있다: {node_id}")
        seen_node_ids.add(node_id)
        normalized_nodes.append({"node_id": node_id, **node})

    input_contract = spec.get("input_contract", [])
    if not isinstance(input_contract, list):
        raise RuntimeError(f"pipeline spec {pipeline_id}의 input_contract는 배열이어야 한다")
    output_contract = spec.get("output_contract", [])
    if not isinstance(output_contract, list):
        raise RuntimeError(f"pipeline spec {pipeline_id}의 output_contract는 배열이어야 한다")
    edges_raw = spec.get("edges", [])
    edges: list[tuple[str, str]] = []
    if edges_raw:
        if not isinstance(edges_raw, list):
            raise RuntimeError(f"pipeline spec {pipeline_id}의 edges는 배열이어야 한다")
        known = {str(item.get("node_id", "")).strip() for item in normalized_nodes}
        for idx, edge in enumerate(edges_raw):
            if not isinstance(edge, list) or len(edge) != 2:
                raise RuntimeError(f"pipeline spec {pipeline_id}의 edges[{idx}] 형식이 잘못되었습니다")
            src = str(edge[0]).strip()
            dst = str(edge[1]).strip()
            if not src or not dst:
                raise RuntimeError(f"pipeline spec {pipeline_id}의 edges[{idx}] 노드 ID가 비어 있습니다")
            if src not in known or dst not in known:
                raise RuntimeError(f"pipeline spec {pipeline_id}의 edges[{idx}]가 nodes에 없는 ID를 참조합니다: {src}->{dst}")
            edges.append((src, dst))

    return (
        pipeline_id,
        normalized_nodes,
        edges,
        [str(item).strip() for item in input_contract if str(item).strip()],
        [str(item).strip() for item in output_contract if str(item).strip()],
    )


def _resolve_execution_order(node_entries: list[dict[str, Any]], edges: list[tuple[str, str]]) -> list[dict[str, Any]]:
    if not edges:
        return list(node_entries)
    node_by_id = {str(item.get("node_id", "")).strip(): item for item in node_entries}
    indegree = {node_id: 0 for node_id in node_by_id}
    graph: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}
    for src, dst in edges:
        graph[src].append(dst)
        indegree[dst] += 1
    # spec에 정의된 node 순서를 우선 보존한다.
    queue = [str(item.get("node_id", "")).strip() for item in node_entries if indegree[str(item.get("node_id", "")).strip()] == 0]
    ordered_ids: list[str] = []
    while queue:
        node_id = queue.pop(0)
        ordered_ids.append(node_id)
        for nxt in graph[node_id]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(ordered_ids) != len(node_entries):
        raise RuntimeError("pipeline spec edges에 순환(cycle)이 있습니다")
    return [node_by_id[node_id] for node_id in ordered_ids]


def _resolve_ref_value(ref: str, *, payload: dict[str, Any], node_results: dict[str, Any]) -> Any:
    token = str(ref).strip()
    if token.startswith("$payload."):
        key = token[len("$payload.") :]
        return payload.get(key)
    if token.startswith("$node."):
        rest = token[len("$node.") :]
        parts = rest.split(".")
        if len(parts) < 2:
            raise RuntimeError(f"input_from 참조 형식이 잘못되었습니다: {ref}")
        node_id = parts[0]
        path_parts = parts[1:]
        value = node_results.get(node_id)
        for part in path_parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    raise RuntimeError(f"지원하지 않는 input_from 참조 형식입니다: {ref}")


def _resolve_generic_cli_module(node_entry: dict[str, Any]) -> str:
    cli_module = str(node_entry.get("cli_module", "")).strip()
    if cli_module:
        return cli_module
    node_id = str(node_entry.get("node_id", "")).strip()
    mapped = GENERIC_NODE_ID_TO_CLI_MODULE.get(node_id, "")
    if not mapped:
        raise RuntimeError(
            f"범용 실행에서 cli_module을 찾을 수 없습니다: node_id={node_id}. "
            "spec.nodes[].cli_module을 명시하거나 GENERIC_NODE_ID_TO_CLI_MODULE에 등록하세요."
        )
    return mapped


def _merge_generic_payload(current_payload: dict[str, Any], node_result: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current_payload)
    if "composer_input" in node_result and isinstance(node_result["composer_input"], dict):
        merged.update(node_result["composer_input"])
    if "render_plan" in node_result and isinstance(node_result["render_plan"], dict):
        merged["render_plan"] = node_result["render_plan"]
    for key, value in node_result.items():
        if key.endswith("_path"):
            merged[key] = value
    if "mid_path" in node_result:
        merged["midi_path"] = node_result["mid_path"]
    return merged


def _run_generic_node_chain(
    payload: dict[str, Any],
    *,
    pipeline_id: str,
    node_entries: list[dict[str, Any]],
    edges: list[tuple[str, str]],
    write_output: bool = True,
) -> dict[str, Any]:
    run_id = str(payload.get("run_id", "")).strip() or datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run_root = Path(str(payload.get("run_root", "")).strip() or ".result/workflow/runtime/run").expanduser().resolve()
    run_root.mkdir(parents=True, exist_ok=True)

    current_payload = dict(payload)
    node_results: dict[str, Any] = {}
    execution_entries = _resolve_execution_order(node_entries, edges)

    for index, node_entry in enumerate(execution_entries, start=1):
        node_id = str(node_entry.get("node_id", "")).strip()
        cli_module = _resolve_generic_cli_module(node_entry)
        node_run_root = run_root / "nodes" / f"node-{index:02d}-{_sanitize_record_name(node_id)}"
        node_run_root.mkdir(parents=True, exist_ok=True)

        node_input = dict(current_payload)
        node_static_input = node_entry.get("input")
        if isinstance(node_static_input, dict):
            node_input.update(node_static_input)
        node_input_from = node_entry.get("input_from")
        if isinstance(node_input_from, dict):
            for field, ref in node_input_from.items():
                node_input[str(field)] = _resolve_ref_value(str(ref), payload=current_payload, node_results=node_results)
        # 파이프라인은 trace/run_root 경로만 전달하고, 실제 trace/산출물 기록은 노드가 담당한다.
        node_input["trace_root"] = str(node_run_root / "records")
        node_input["run_root"] = str(node_run_root)
        input_json_path = node_run_root / "node-input.json"
        input_json_path.write_text(json.dumps(node_input, ensure_ascii=False, indent=2), encoding="utf-8")

        cmd = [sys.executable, "-m", cli_module, "--input-json", str(input_json_path), "--run-root", str(node_run_root)]
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                f"노드 실행 실패: node_id={node_id}, cli={cli_module}, code={completed.returncode}, "
                f"stderr={completed.stderr.strip()}"
            )
        stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        result_json_path = Path(stdout_lines[-1]) if stdout_lines else (node_run_root / "result.json")
        if not result_json_path.is_file():
            raise RuntimeError(f"노드 result.json을 찾을 수 없습니다: node_id={node_id}, path={result_json_path}")
        node_result = json.loads(result_json_path.read_text(encoding="utf-8"))
        node_results[node_id] = node_result
        current_payload = _merge_generic_payload(current_payload, node_result)

    output_obj = payload.get("output", {})
    output_json_path = str(output_obj.get("path", "")).strip() if isinstance(output_obj, dict) else ""
    if not output_json_path:
        output_json_path = local_runtime_output_path("pipeline-result.json")

    outputs: dict[str, Any] = {"json": {"path": output_json_path, "format": "json", "status": "rendered"}}
    if "mp3_path" in current_payload:
        outputs["mp3"] = {"path": str(current_payload["mp3_path"]).strip(), "format": "mp3", "status": "encoded"}
    if "wav_path" in current_payload:
        outputs["wav"] = {"path": str(current_payload["wav_path"]).strip(), "format": "wav", "status": "rendered"}
    if "midi_path" in current_payload:
        outputs["mid"] = {"path": str(current_payload["midi_path"]).strip(), "format": "mid", "status": "generated"}

    result = {
        "pipeline": pipeline_id,
        "mode": str(payload.get("mode", "worker")).strip() or "worker",
        "run_id": run_id,
        "run_root": str(run_root),
        "node_records_root": str((run_root / "records" / "nodes").resolve()),
        "nodes": [{"node_id": str(item.get("node_id", "")).strip()} for item in node_entries],
        "outputs": outputs,
        "result": node_results,
        "stage_logs": [],
    }
    if write_output:
        path = Path(output_json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _parse_contract_field(item: str) -> tuple[str, list[str], bool]:
    raw = str(item or "").strip()
    if not raw:
        raise RuntimeError("계약 필드 정의가 비어 있습니다")
    is_optional = raw.endswith("(optional)")
    if is_optional:
        raw = raw[: -len("(optional)")].strip()
    if ":" not in raw:
        return raw, ["json"], is_optional
    field, kind_text = raw.split(":", 1)
    field_name = field.strip()
    if not field_name:
        raise RuntimeError(f"계약 필드명이 비어 있습니다: {item}")
    kinds = [token.strip() for token in kind_text.split("|") if token.strip()]
    if not kinds:
        raise RuntimeError(f"계약 타입이 비어 있습니다: {item}")
    return field_name, kinds, is_optional


def _matches_contract_type(value: Any, kind: str) -> bool:
    type_name = str(kind or "").strip().lower()
    if type_name in {"txt", "md"}:
        return isinstance(value, str)
    if type_name == "json":
        return isinstance(value, (dict, list, int, float, bool)) or value is None
    if type_name in {"wav", "mp3", "png"}:
        return isinstance(value, str)
    return True


def _validate_payload_against_input_contract(payload: dict[str, Any], input_contract: list[str]) -> None:
    if not input_contract:
        return
    allowed_fields: set[str] = {"pipeline", "run_root", "run_id"}
    required_fields: list[tuple[str, list[str]]] = []
    typed_fields: list[tuple[str, list[str], bool]] = []
    for item in input_contract:
        field_name, kinds, is_optional = _parse_contract_field(item)
        allowed_fields.add(field_name)
        typed_fields.append((field_name, kinds, is_optional))
        if not is_optional:
            required_fields.append((field_name, kinds))

    strict_unknown = (
        os.getenv("WORKFLOW_RUNTIME_STRICT_INPUT_FIELDS", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    unknown_fields = sorted(key for key in payload.keys() if key not in allowed_fields)
    if strict_unknown and unknown_fields:
        raise RuntimeError(
            "input payload에 스펙에 없는 필드가 포함되어 있습니다: "
            f"{unknown_fields}"
        )

    for field_name, _ in required_fields:
        if field_name not in payload:
            raise RuntimeError(f"input payload 필수 필드 누락: {field_name}")

    for field_name, kinds, is_optional in typed_fields:
        if field_name not in payload:
            continue
        value = payload.get(field_name)
        if is_optional and value is None:
            continue
        if not any(_matches_contract_type(value, kind) for kind in kinds):
            raise RuntimeError(
                f"input payload 타입 불일치: field={field_name}, "
                f"allowed={kinds}, actual_type={type(value).__name__}"
            )


def _validate_result_against_output_contract(result: dict[str, Any], output_contract: list[str]) -> None:
    if not output_contract:
        return
    strict_output = (
        os.getenv("WORKFLOW_RUNTIME_STRICT_OUTPUT_CONTRACT", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    outputs = result.get("outputs", {})
    if not isinstance(outputs, dict):
        if strict_output:
            raise RuntimeError("파이프라인 결과에 outputs 객체가 없습니다.")
        return
    for item in output_contract:
        name, _, _ = _parse_contract_field(item)
        if name == "json":
            continue
        if name not in outputs:
            if strict_output:
                raise RuntimeError(f"파이프라인 결과 output 누락: {name}")


def _read_rss_kb(pid: int) -> int:
    """현재 프로세스 RSS(KB)를 반환한다."""
    try:
        page_size = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
        with open(f"/proc/{pid}/statm", "r", encoding="utf-8") as handle:
            fields = handle.read().strip().split()
        if len(fields) >= 2:
            return (int(fields[1]) * page_size) // 1024
    except Exception:
        return -1
    return -1


def _read_meminfo_used_mb() -> float:
    try:
        total = None
        available = None
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    available = int(line.split()[1])
                if total is not None and available is not None:
                    break
        if total is None:
            return -1.0
        if available is None:
            return 0.0
        return round((total - available) / 1024.0, 2)
    except Exception:
        return -1.0


def _snapshot_children(parent_pid: int) -> list[str]:
    try:
        result = subprocess.run(
            [
                "ps",
                "-o",
                "pid=,ppid=,pcpu=,pmem=,rss=,vsz=,stat=,etime=,cmd=",
                "--ppid",
                str(parent_pid),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if not result.stdout.strip():
            return ["[child] 없음"]
        child_lines: list[str] = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # 하트비트 내부 진단용 ps 프로세스는 노이즈가 크므로 출력에서 제외한다.
            if " ps -o " in line and " --ppid " in line:
                continue
            child_lines.append(f"[child] {line}")
        if not child_lines:
            return ["[child] 없음"]
        return child_lines
    except Exception as exc:
        return [f"[child] 조회 실패: {exc}"]


def _child_activity_summary(child_lines: list[str]) -> tuple[int, float]:
    """자식 프로세스 개수와 CPU 합계를 계산한다."""
    count = 0
    cpu_total = 0.0
    for line in child_lines:
        if not line.startswith("[child] "):
            continue
        payload = line[len("[child] ") :].strip()
        if payload in {"없음"} or payload.startswith("조회 실패"):
            continue
        parts = payload.split()
        if len(parts) < 3:
            continue
        try:
            cpu_total += float(parts[2])
            count += 1
        except Exception:
            continue
    return count, round(cpu_total, 1)


def _snapshot_artifacts(run_root: str, *, ignore_paths: set[Path] | None = None) -> list[str]:
    if not run_root:
        return ["[artifact] run_root 미설정"]
    root = Path(run_root)
    if not root.exists():
        return ["[artifact] run_root 없음"]
    ignored = {path.resolve() for path in (ignore_paths or set())}
    try:
        files = [path for path in root.rglob("*") if path.is_file() and path.resolve() not in ignored]
    except Exception as exc:
        return [f"[artifact] 수집 실패: {exc}"]
    if not files:
        return ["[artifact] 파일 없음"]
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    return [
        f"[artifact] {path} ({path.stat().st_size}bytes, mtime={datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
        for path in files
    ]


def _snapshot_activity_token(run_root: str, *, ignore_paths: set[Path] | None = None) -> str:
    if not run_root:
        return "no-run-root"
    root = Path(run_root)
    if not root.exists():
        return "run-root-missing"
    ignored = {path.resolve() for path in (ignore_paths or set())}
    try:
        paths = [path for path in root.rglob("*") if path.is_file() and path.resolve() not in ignored]
    except Exception:
        return "snapshot-failed"
    if not paths:
        return "artifact-empty"
    latest = max(path.stat().st_mtime for path in paths)
    return f"{len(paths)}:{int(latest)}"


def _pipeline_heartbeat(
    pipeline_id: str,
    run_root: str,
    stop_at: threading.Event,
    heartbeat_seconds: int,
    stall_limit: int,
    stall_timeout_seconds: int,
    runtime_log_path: str,
    stdout_enabled: bool,
    *,
    child_detail: bool = False,
    artifact_detail: bool = False,
) -> None:
    pid = os.getpid()
    start_ts = time.time()
    last_activity_token = ""
    stale_count = 0
    child_busy_cpu_threshold = 5.0

    tick = 0
    heartbeat_file_only = (
        os.getenv("WORKFLOW_RUNTIME_HEARTBEAT_FILE_ONLY", "1").strip().lower() in {"1", "true", "on", "yes"}
    )

    inline_progress = (
        os.getenv("WORKFLOW_RUNTIME_HEARTBEAT_PROGRESS_MODE", "").strip().lower() in {"inline", "1", "true", "on", "yes"}
    )
    inline_active = False
    inline_width = 0

    def _append_runtime_log(message: str) -> None:
        if not runtime_log_path:
            return
        try:
            path = Path(runtime_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(message)
                handle.write("\n")
        except Exception:
            # 런타임 로깅 실패는 파이프라인 실행을 중단시키지 않는다.
            pass

    def _clear_inline() -> None:
        nonlocal inline_active, inline_width
        if inline_active and stdout_enabled:
            print("", flush=True)
        inline_active = False
        inline_width = 0

    def _print_inline(message: str) -> None:
        nonlocal inline_active, inline_width
        if not stdout_enabled or heartbeat_file_only:
            return
        padded = message
        if len(message) < inline_width:
            padded = message + (" " * (inline_width - len(message)))
        inline_width = max(inline_width, len(message))
        sys.stdout.write("\r" + padded)
        sys.stdout.flush()
        inline_active = True

    ignored_runtime_paths: set[Path] = set()
    if runtime_log_path:
        try:
            ignored_runtime_paths.add(Path(runtime_log_path).resolve())
        except Exception:
            pass
    if run_root:
        try:
            # heartbeat가 같은 파일에 계속 append될 때 activity가 매 tick 바뀌는 것을 막는다.
            ignored_runtime_paths.add((Path(run_root) / "pipeline-runtime.log").resolve())
        except Exception:
            pass

    while not stop_at.wait(heartbeat_seconds):
        tick += 1
        elapsed = int(time.time() - start_ts)

        rss_kb = _read_rss_kb(pid)
        mem_mb = _read_meminfo_used_mb()
        child_lines = _snapshot_children(pid)
        child_count, child_cpu_total = _child_activity_summary(child_lines)
        child_busy = child_count > 0 and child_cpu_total >= child_busy_cpu_threshold

        current_activity_token = _snapshot_activity_token(run_root, ignore_paths=ignored_runtime_paths)
        activity_changed = current_activity_token != last_activity_token
        can_inline = inline_progress and (not activity_changed) and child_busy

        if can_inline:
            progress_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ai-workflow] [pipeline-runtime] [HEARTBEAT] "
                f"progress tick={tick} elapsed={elapsed}s child_cpu_total={child_cpu_total} activity={current_activity_token}"
            )
            _print_inline(progress_message)
            _append_runtime_log(progress_message)
        else:
            _clear_inline()
            heartbeat_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ai-workflow] [pipeline-runtime] [HEARTBEAT] "
                f"pipeline={pipeline_id}, tick={tick}, elapsed={elapsed}s, pid={pid}, rss_kb={rss_kb}, mem_used_mb={mem_mb}, "
                f"child_count={child_count}, child_cpu_total={child_cpu_total}, run_root={run_root}"
            )
            if stdout_enabled and not heartbeat_file_only:
                print(heartbeat_message, flush=True)
            _append_runtime_log(heartbeat_message)
            if child_detail and child_lines:
                for line in child_lines:
                    if stdout_enabled and not heartbeat_file_only:
                        print(line, flush=True)
                    _append_runtime_log(line)
        if artifact_detail or activity_changed:
            for line in _snapshot_artifacts(run_root, ignore_paths=ignored_runtime_paths):
                if stdout_enabled and not heartbeat_file_only:
                    print(line, flush=True)
                _append_runtime_log(line)
        if last_activity_token and last_activity_token == current_activity_token:
            if child_busy:
                stale_count = 0
            else:
                stale_count += 1
        else:
            stale_count = 0
        last_activity_token = current_activity_token
        if not can_inline:
            activity_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ai-workflow] [pipeline-runtime] [HEARTBEAT] "
                f"activity={current_activity_token}, stalled={stale_count}, child_busy={child_busy}"
            )
            if stdout_enabled and not heartbeat_file_only:
                print(activity_message, flush=True)
            _append_runtime_log(activity_message)
        if stale_count > 0 and stale_count % stall_limit == 0:
            _clear_inline()
            warning_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ai-workflow] [pipeline-runtime] [WARN] "
                f"pipeline={pipeline_id} 산출물 정체 감지(모니터 연속 {stall_limit}회): "
                f"elapsed={elapsed}s, pid={pid}, activity={current_activity_token}"
            )
            if stdout_enabled and not heartbeat_file_only:
                print(_color("WARN", warning_message), flush=True)
            _append_runtime_log(warning_message)
        if (
            stall_timeout_seconds > 0
            and stale_count >= max(1, (stall_timeout_seconds + heartbeat_seconds - 1) // heartbeat_seconds)
        ):
            _clear_inline()
            error_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ai-workflow] [pipeline-runtime] [ERROR] "
                f"활동 정지 진단 임계치 초과: pipeline={pipeline_id}, elapsed={elapsed}s, stall_timeout={stall_timeout_seconds}s, "
                f"activity={current_activity_token}, pid={pid}"
            )
            if stdout_enabled and not heartbeat_file_only:
                print(_color("ERROR", error_message), flush=True)
            _append_runtime_log(error_message)
            os.kill(os.getpid(), signal.SIGTERM)
    _clear_inline()


def _color(level: str, message: str) -> str:
    force_color = (
        os.getenv("WORKFLOW_RUNTIME_FORCE_COLOR", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    if not force_color and not sys.stdout.isatty():
        return message
    if "[ai-workflow]" not in message:
        return message
    if level == "WARN":
        return f"{ANSI_YELLOW}{message}{ANSI_RESET}"
    if level == "ERROR":
        return f"{ANSI_RED}{message}{ANSI_RESET}"
    return message


def _normalize_input_payload(
    input_data: dict[str, Any],
    *,
    run_root: str,
    output_path: str,
) -> dict[str, Any]:
    payload = dict(input_data)
    if run_root:
        payload["run_root"] = run_root
    if not str(payload.get("pipeline", "")).strip():
        raise RuntimeError("input.json에 pipeline 필드가 없다")

    output = payload.get("output", {})
    if not isinstance(output, dict):
        output = {}
    if output_path:
        output["path"] = output_path
    output.setdefault("path", local_runtime_output_path("pipeline-result.json"))
    payload["output"] = output
    return payload


def _read_env_int(
    name: str,
    default: int,
    *,
    aliases: list[str] | None = None,
    min_value: int = 1,
) -> int:
    """환경변수에서 정수값을 읽는다.

    값이 없으면 기본값을 반환하고, 값이 정수 변환에 실패하거나 최소값 미만이면
    RuntimeError를 발생시켜 즉시 실패한다.
    """

    candidate_names = [name]
    if aliases:
        candidate_names.extend(aliases)

    for env_name in candidate_names:
        raw_value = os.environ.get(env_name)
        if raw_value is None or str(raw_value).strip() == "":
            continue
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"{env_name} 값이 정수가 아닙니다: {raw_value}") from exc
        if parsed < min_value:
            raise RuntimeError(f"{env_name} 값은 {min_value} 이상이어야 합니다: {parsed}")
        return parsed

    return default


def _parse_node_id_list(raw: str) -> list[str]:
    if not raw:
        return []
    node_ids: list[str] = []
    for chunk in raw.replace(";", ",").replace("|", ",").split(","):
        for token in chunk.split():
            value = token.strip()
            if value:
                node_ids.append(value)
    return node_ids


def _load_node_docker_list() -> set[str] | None:
    """노드별 도커 실행 대상 목록을 읽는다.

    값이 지정되면 해당 node_id만 도커로 실행한다. 지정되지 않으면 None을 반환한다.
    """
    raw = os.getenv("WORKFLOW_NODE_DOCKER_NODES", "").strip()
    if not raw:
        return None
    node_ids = _parse_node_id_list(raw)
    if not node_ids:
        raise RuntimeError(
            "WORKFLOW_NODE_DOCKER_NODES가 비어 있습니다. 예: music.structure.plan,music.midi.generate.magenta"
        )
    return set(node_ids)


def _should_run_nodes_in_docker() -> bool:
    raw_mode = os.getenv("WORKFLOW_NODE_DOCKER", "auto").strip().lower()
    if raw_mode in {"", "auto"}:
        return sys.version_info >= (3, 12) and shutil.which("docker") is not None
    if raw_mode in {"1", "true", "on", "yes"}:
        return True
    if raw_mode in {"0", "false", "off", "no"}:
        return False
    return False


def _should_run_node_in_docker(node_id: str, *, default_mode: bool, node_list: set[str] | None) -> bool:
    if node_id == "music.structure.plan" and node_list is None:
        # AGENTS 요청: music.structure.plan은 기본 비도커 운영으로 복원.
        # 필요 시 WORKFLOW_NODE_DOCKER_NODES에 명시할 경우만 강제로 도커 실행한다.
        return False
    if node_list is not None:
        return node_id in node_list
    return default_mode


def run_declared_node_chain(
    payload: dict[str, Any],
    *,
    pipeline_id: str,
    write_output: bool = True,
) -> dict[str, Any]:
    """레거시 실행기는 폐기되었다."""
    raise RuntimeError(
        "run_declared_node_chain은 폐기되었습니다. "
        "spec.nodes/edges를 해석하는 범용 실행 경로를 사용하세요."
    )


def run_pipeline_from_files(
    spec_path: str,
    input_path: str,
    *,
    run_root: str = "",
    output_path: str = "",
    write_output: bool = True,
) -> dict[str, Any]:
    spec = _load_json(spec_path)
    input_data = _load_json(input_path)

    pipeline_id, node_entries, edges, input_contract, output_contract = _validate_spec(spec)
    node_ids = [str(item.get("node_id", "")).strip() for item in node_entries]
    input_pipeline = str(input_data.get("pipeline", "")).strip()
    alias_from_spec_raw = spec.get("compatibility_input_pipelines", [])
    alias_from_spec = (
        {str(item).strip() for item in alias_from_spec_raw if str(item).strip()}
        if isinstance(alias_from_spec_raw, list)
        else set()
    )
    allowed_aliases = PIPELINE_INPUT_COMPATIBILITY_ALIASES.get(pipeline_id, set()) | alias_from_spec
    allowed_pipelines = {pipeline_id} | allowed_aliases
    if input_pipeline not in allowed_pipelines:
        raise RuntimeError(f"input pipeline이 일치하지 않는다: spec={pipeline_id}, input={input_pipeline}")
    effective_pipeline_id = input_pipeline if input_pipeline in allowed_aliases else pipeline_id

    payload = _normalize_input_payload(input_data, run_root=run_root, output_path=output_path)
    _validate_payload_against_input_contract(payload, input_contract)
    payload["__runtime_expected_node_order"] = list(node_ids)
    payload["__runtime_spec"] = spec
    record_dir = _build_runtime_record_dir(pipeline_id, payload)
    _write_runtime_record_json(
        record_dir,
        "pipeline-input.original.json",
        {
            "pipeline_id": pipeline_id,
            "spec_path": str(Path(spec_path).resolve()),
            "input_path": str(Path(input_path).resolve()),
            "input": input_data,
        },
    )
    _write_runtime_record_json(
        record_dir,
        "pipeline-input.normalized.json",
        {
            "pipeline_id": pipeline_id,
            "payload": payload,
        },
    )
    _write_runtime_record_json(
        record_dir,
        "pipeline-spec.json",
        {
            "pipeline_id": pipeline_id,
            "spec": spec,
        },
    )
    runtime_run_root = str(payload.get("run_root", ""))
    if runtime_run_root:
        Path(runtime_run_root).mkdir(parents=True, exist_ok=True)

    heartbeat_seconds = _read_env_int(
        "WORKFLOW_RUNTIME_HEARTBEAT_SECONDS",
        DEFAULT_HEARTBEAT_SECONDS,
        aliases=["WORKFLOW_HEARTBEAT_SECONDS"],
        min_value=0,
    )
    stall_limit = _read_env_int(
        "WORKFLOW_RUNTIME_HEARTBEAT_STALL_LIMIT",
        DEFAULT_HEARTBEAT_STALL_LIMIT,
        aliases=["WORKFLOW_HEARTBEAT_STALL_LIMIT"],
        min_value=1,
    )
    stall_timeout_seconds = _read_env_int(
        "WORKFLOW_RUNTIME_STALL_TIMEOUT_SECONDS",
        DEFAULT_STALL_TIMEOUT_SECONDS,
        aliases=["WORKFLOW_STALL_TIMEOUT_SECONDS"],
        min_value=0,
    )

    heartbeat = None
    stop_event: threading.Event | None = None
    runtime_log_path = ""
    runtime_log_override = os.getenv("WORKFLOW_RUNTIME_LOG_PATH", "").strip()
    if runtime_log_override:
        runtime_log_path = runtime_log_override
    elif runtime_run_root:
        runtime_log_path = str(Path(runtime_run_root) / "pipeline-runtime.log")
    heartbeat_child_detail = (
        os.getenv("WORKFLOW_RUNTIME_HEARTBEAT_CHILD_DETAIL", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    heartbeat_artifact_detail = (
        os.getenv("WORKFLOW_RUNTIME_HEARTBEAT_ARTIFACT_DETAIL", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    heartbeat_stdout_enabled = (
        os.getenv("WORKFLOW_RUNTIME_HEARTBEAT_STDOUT", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    if heartbeat_seconds > 0:
        stop_event = threading.Event()
        heartbeat = threading.Thread(
            target=_pipeline_heartbeat,
            args=(
                effective_pipeline_id,
                str(payload.get("run_root", "")),
                stop_event,
                heartbeat_seconds,
                stall_limit,
                stall_timeout_seconds,
                runtime_log_path,
                heartbeat_stdout_enabled,
            ),
            kwargs={
                "child_detail": heartbeat_child_detail,
                "artifact_detail": heartbeat_artifact_detail,
            },
            daemon=True,
        )
        heartbeat.start()

    try:
        result = _run_generic_node_chain(
            payload,
            pipeline_id=effective_pipeline_id,
            node_entries=node_entries,
            edges=edges,
            write_output=write_output,
        )
        _validate_result_against_output_contract(result, output_contract)
        node_record_paths = _write_node_records_if_possible(record_dir, node_ids, result)
        _write_runtime_record_json(
            record_dir,
            "pipeline-output.json",
            {
                "pipeline_id": effective_pipeline_id,
                "result": result,
                "node_record_paths": [str(path) for path in node_record_paths],
            },
        )
        return result
    except Exception as exc:
        _write_runtime_record_json(
            record_dir,
            "pipeline-error.json",
            {
                "pipeline_id": effective_pipeline_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise
    finally:
        if stop_event is not None and heartbeat is not None:
            stop_event.set()
            heartbeat.join(timeout=heartbeat_seconds + 1)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = run_pipeline_from_files(
        args.spec,
        args.input,
        run_root=args.run_root,
        output_path=args.output,
        write_output=not args.no_write,
    )
    env_print_result = (
        os.getenv("WORKFLOW_RUNTIME_PRINT_RESULT_JSON", "").strip().lower() in {"1", "true", "on", "yes"}
    )
    if args.print_result_json or env_print_result:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
