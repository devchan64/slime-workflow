"""MIDI 산출물 통계 리포트를 생성하는 노드."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mido

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class MusicMidiReportModule:
    """입력 MIDI를 분석해 채널/노트 통계 리포트를 생성한다."""

    name = "music-midi-report"
    node_id = "music.midi.report"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        midi_path = Path(str(payload.get("midi_path", "")).strip())
        if not midi_path.is_file():
            self._fail(record_dir, f"midi_path 파일이 없습니다: {midi_path}")

        mid = mido.MidiFile(str(midi_path))
        channel_note_counts: dict[int, int] = {}
        total_notes = 0
        drum_notes = 0
        non_drum_notes = 0
        for track in mid.tracks:
            for msg in track:
                if msg.type == "note_on" and int(msg.velocity) > 0:
                    ch = int(getattr(msg, "channel", 0))
                    channel_note_counts[ch] = channel_note_counts.get(ch, 0) + 1
                    total_notes += 1
                    if ch == 9:
                        drum_notes += 1
                    else:
                        non_drum_notes += 1

        drum_ratio = (drum_notes / total_notes) if total_notes > 0 else 1.0
        report = {
            "node_id": self.node_id,
            "midi_path": str(midi_path),
            "tracks": len(mid.tracks),
            "ticks_per_beat": int(mid.ticks_per_beat),
            "total_notes": total_notes,
            "drum_notes": drum_notes,
            "non_drum_notes": non_drum_notes,
            "drum_ratio": drum_ratio,
            "channel_note_counts": {str(k): int(v) for k, v in sorted(channel_note_counts.items())},
        }

        report_path = run_root / "outputs" / "midi" / "midi-note-report.json"
        self._write_json(report_path, report)

        result = {
            "status": "reported",
            "midi_path": str(midi_path),
            "midi_report_path": str(report_path),
            "midi_report": report,
        }
        self._write_json(record_dir / "output.json", result)
        log(context, self.name, "INFO", f"MIDI 리포트 생성 완료: {report_path}")
        return result

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(record_dir / "error.json", {"error_type": type(error).__name__, "message": str(error)})
        raise error
