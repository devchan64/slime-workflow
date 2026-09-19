"""WAV를 MP3로 인코딩하는 신규 규약형 노드."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class AudioEncodeMp3V2Module:
    name = "audio-encode-mp3-v2"
    node_id = "music.audio.encode.mp3"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        wav_path = Path(str(payload.get("wav_path", "")).strip())
        if not wav_path.is_file():
            self._fail(record_dir, f"입력 WAV 파일이 없습니다: {wav_path}")

        render_plan = payload.get("render_plan") if isinstance(payload.get("render_plan"), dict) else {}
        bitrate = str(payload.get("bitrate", render_plan.get("mp3_bitrate", "192k"))).strip() or "192k"
        if bitrate not in {"128k", "160k", "192k", "256k", "320k"}:
            self._fail(record_dir, f"허용되지 않는 MP3 비트레이트: {bitrate}")

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self._fail(record_dir, "ffmpeg 바이너리를 찾을 수 없습니다")

        output_mp3 = Path(str(payload.get("output_mp3_path", "")).strip() or (run_root / "outputs" / "audio" / "mixdown.mp3"))
        output_mp3.parent.mkdir(parents=True, exist_ok=True)

        cmd = [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", bitrate, str(output_mp3)]
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            self._fail(record_dir, f"ffmpeg 인코딩 실패: code={completed.returncode}, stderr={completed.stderr.strip()}")
        if not output_mp3.is_file():
            self._fail(record_dir, f"MP3 출력 파일이 생성되지 않았습니다: {output_mp3}")

        report = {
            "node_id": self.node_id,
            "wav_path": str(wav_path),
            "mp3_path": str(output_mp3),
            "bitrate": bitrate,
            "command": cmd,
        }
        report_path = run_root / "outputs" / "audio" / "audio-encode-mp3.report.json"
        self._write_json(report_path, report)

        result = {
            "status": "encoded",
            "mp3_path": str(output_mp3),
            "report_path": str(report_path),
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)
        log(context, self.name, "INFO", f"WAV->MP3 인코딩 완료: output={output_mp3}")
        return result

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(record_dir / "error.json", {"error_type": type(error).__name__, "message": str(error)})
        raise error
