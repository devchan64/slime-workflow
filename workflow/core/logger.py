"""일관된 프레임워크 로그 포맷 유틸."""

from __future__ import annotations

from datetime import datetime

from workflow.interfaces import PipelineContext


ANSI_RESET = "\033[0m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"


def _colorize_line(level: str, line: str) -> str:
    normalized = str(level).strip().upper()
    if normalized == "WARN":
        return f"{ANSI_YELLOW}{line}{ANSI_RESET}"
    if normalized == "ERROR":
        return f"{ANSI_RED}{line}{ANSI_RESET}"
    return line


def log(context: PipelineContext, step: str, level: str, message: str) -> None:
    """시간/영역/단계를 포함한 단일 로그 라인을 출력한다."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{context.area}] [{step}] [{level}] {message}"
    print(_colorize_line(level, line), flush=True)
    context.stage_logs.append(
        {
            "time": timestamp,
            "step": step,
            "level": level,
            "message": message,
        }
    )
