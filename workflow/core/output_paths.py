"""workflow 노드 실행 산출물 경로 유틸."""

from __future__ import annotations

from pathlib import Path

LOCAL_OUTPUT_ROOT = Path(".result/workflow/generated")
LOCAL_RUNTIME_OUTPUT_ROOT = Path(".result/workflow/runtime")
LOCAL_RUNS_ROOT = Path(".result/workflow/runs")


def local_output_path(*parts: str) -> str:
    """workflow 기본 산출물 상대 경로를 반환한다."""

    return str(LOCAL_OUTPUT_ROOT.joinpath(*parts))


def local_runtime_output_path(*parts: str) -> str:
    """workflow 런타임 결과 상대 경로를 반환한다."""

    return str(LOCAL_RUNTIME_OUTPUT_ROOT.joinpath(*parts))


def local_run_root(pipeline: str, run_id: str) -> str:
    """파이프라인/실행 ID 기준 run root 경로를 반환한다."""

    pipeline_dir = str(pipeline).strip() or "concept-image"
    return str(LOCAL_RUNS_ROOT.joinpath(pipeline_dir, run_id))
