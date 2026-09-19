"""노드 준비(prepare) 공통 유틸."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Callable, Sequence, TypeVar

from workflow.interfaces import PipelineContext

from .logger import log


T = TypeVar("T")


def run_prepare_step(
    context: PipelineContext,
    *,
    step: str,
    name: str,
    action: Callable[[], T],
) -> T:
    """준비 단계의 시작/완료/실패 로그를 공통 포맷으로 남긴다."""

    start = time.monotonic()
    log(context, step, "INFO", f"prepare 시작: {name}")
    try:
        result = action()
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        log(context, step, "ERROR", f"prepare 실패: {name}, elapsed_ms={elapsed_ms}, error={exc}")
        raise
    elapsed_ms = int((time.monotonic() - start) * 1000)
    log(context, step, "INFO", f"prepare 완료: {name}, elapsed_ms={elapsed_ms}")
    return result


def ensure_python_module(
    context: PipelineContext,
    *,
    step: str,
    module_name: str,
    pip_spec: str,
    timeout_seconds: int = 900,
) -> None:
    """파이썬 모듈 존재를 보장하고, 없으면 pip 설치 후 재확인한다."""

    if importlib.util.find_spec(module_name) is not None:
        log(context, step, "INFO", f"prepare 점검 통과: module={module_name}")
        return

    command = [sys.executable, "-m", "pip", "install", *shlex.split(pip_spec)]
    log(context, step, "WARN", f"prepare 의존성 자동 설치 시작: module={module_name}, command={command}")
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"prepare 의존성 자동 설치 타임아웃({timeout_seconds}s): module={module_name}, command={command}"
        ) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(
            f"prepare 의존성 자동 설치 실패: module={module_name}, code={completed.returncode}, stderr={stderr}"
        )

    if importlib.util.find_spec(module_name) is None:
        raise RuntimeError(f"prepare 의존성 설치 후 모듈을 찾지 못했습니다: module={module_name}")
    log(context, step, "INFO", f"prepare 의존성 설치 완료: module={module_name}")


def run_prepare_command(
    context: PipelineContext,
    *,
    step: str,
    phase: str,
    command: Sequence[str],
    timeout_seconds: int = 1800,
) -> None:
    """prepare 명령을 공통 포맷으로 실행하고 결과를 로깅한다."""

    rendered = [str(part) for part in command]

    def _execute() -> None:
        try:
            completed = subprocess.run(
                rendered,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"prepare 명령 타임아웃({timeout_seconds}s): phase={phase}, command={rendered}"
            ) from exc
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise RuntimeError(
                "prepare 명령 실행 실패: "
                f"phase={phase}, code={completed.returncode}, command={rendered}, stderr={stderr}"
            )

    run_prepare_step(
        context,
        step=step,
        name=f"{phase}: {' '.join(rendered)}",
        action=_execute,
    )


def ensure_required_files(
    context: PipelineContext,
    *,
    step: str,
    files: Sequence[str],
    package_id: str,
) -> None:
    """prepare에 필요한 파일 존재를 검증하고 결과를 로깅한다."""

    def _check() -> None:
        for file_path in files:
            path = Path(file_path)
            if not path.is_file():
                raise RuntimeError(f"패키지 의존성 파일이 없다: package={package_id}, path={file_path}")

    run_prepare_step(
        context,
        step=step,
        name=f"의존성 파일 확인: package={package_id}",
        action=_check,
    )
