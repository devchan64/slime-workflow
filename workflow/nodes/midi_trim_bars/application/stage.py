"""MIDI를 지정 마디 수로 자르는 노드."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mido

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class MidiTrimBarsModule:
    """입력 MIDI를 bars 기준으로 하드 트림한다."""

    name = "midi-trim-bars"
    node_id = "music.midi.trim.bars"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        midi_path = Path(str(payload.get("midi_path", "")).strip())
        if not midi_path.is_file():
            self._fail(record_dir, f"입력 MIDI 파일이 없습니다: {midi_path}")

        bars = int(payload.get("bars", 0) or 0)
        if bars <= 0:
            self._fail(record_dir, f"bars는 1 이상이어야 합니다: {bars}")

        output_path_raw = str(payload.get("output_path", "")).strip()
        output_path = Path(output_path_raw) if output_path_raw else None
        if output_path is None:
            output_path = run_root / "outputs" / "midi" / f"{midi_path.stem}.trimmed-{bars}bars.mid"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mid = mido.MidiFile(str(midi_path))
        if not mid.tracks:
            self._fail(record_dir, "MIDI 트랙이 비어 있습니다")

        # 기본 4/4, 파일 전체에서 첫 time_signature 메타를 우선 적용
        numerator = 4
        denominator = 4
        found_time_signature = False
        for track in mid.tracks:
            for msg in track:
                if msg.type == "time_signature":
                    numerator = int(msg.numerator)
                    denominator = int(msg.denominator)
                    found_time_signature = True
                    break
            if found_time_signature:
                break

        if denominator <= 0 or (denominator & (denominator - 1)) != 0:
            self._fail(record_dir, f"지원하지 않는 박자 분모입니다: {denominator}")

        beat_unit = 4 / denominator
        beats_per_bar = numerator * beat_unit
        ticks_per_bar = int(round(mid.ticks_per_beat * beats_per_bar))
        if ticks_per_bar <= 0:
            self._fail(record_dir, f"ticks_per_bar 계산 실패: ticks_per_beat={mid.ticks_per_beat}, ts={numerator}/{denominator}")

        cut_tick = bars * ticks_per_bar
        if cut_tick <= 0:
            self._fail(record_dir, f"cut_tick 계산 실패: bars={bars}, ticks_per_bar={ticks_per_bar}")

        out_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
        for track in mid.tracks:
            out_mid.tracks.append(self._trim_track(track, cut_tick))

        output_max_tick = self._max_abs_tick(out_mid)
        if output_max_tick > cut_tick:
            self._fail(
                record_dir,
                f"트림 검증 실패: output_max_tick({output_max_tick}) > cut_tick({cut_tick})",
            )

        out_mid.save(str(output_path))
        if not output_path.is_file():
            self._fail(record_dir, f"출력 MIDI 저장 실패: {output_path}")

        report = {
            "node_id": self.node_id,
            "input_midi_path": str(midi_path),
            "output_midi_path": str(output_path),
            "bars": bars,
            "time_signature": f"{numerator}/{denominator}",
            "ticks_per_beat": mid.ticks_per_beat,
            "ticks_per_bar": ticks_per_bar,
            "cut_tick": cut_tick,
            "input_max_tick": self._max_abs_tick(mid),
            "output_max_tick": output_max_tick,
        }
        report_path = run_root / "outputs" / "midi" / "midi-trim-bars.report.json"
        self._write_json(report_path, report)

        result = {
            "status": "trimmed",
            "midi_path": str(output_path),
            "report_path": str(report_path),
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)
        log(context, self.name, "INFO", f"MIDI 트림 완료: bars={bars}, cut_tick={cut_tick}, output={output_path}")
        return result

    def _trim_track(self, track: mido.MidiTrack, cut_tick: int) -> mido.MidiTrack:
        kept: list[tuple[int, mido.Message]] = []
        abs_tick = 0
        active: set[tuple[int, int]] = set()

        for msg in track:
            abs_tick += msg.time
            if msg.type == "end_of_track":
                continue

            if abs_tick <= cut_tick:
                kept.append((abs_tick, msg.copy(time=0)))
                if not msg.is_meta:
                    if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                        active.add((int(getattr(msg, "channel", 0)), int(getattr(msg, "note", 0))))
                    elif msg.type in {"note_off", "note_on"}:
                        active.discard((int(getattr(msg, "channel", 0)), int(getattr(msg, "note", 0))))
            else:
                break

        # 컷 지점까지 열린 노트를 닫는다.
        for channel, note in sorted(active):
            kept.append((cut_tick, mido.Message("note_off", channel=channel, note=note, velocity=0, time=0)))

        kept.sort(key=lambda item: item[0])
        out = mido.MidiTrack()
        prev_tick = 0
        for tick, msg in kept:
            delta = max(0, tick - prev_tick)
            out.append(msg.copy(time=delta))
            prev_tick = tick
        out.append(mido.MetaMessage("end_of_track", time=0))
        return out

    @staticmethod
    def _max_abs_tick(mid: mido.MidiFile) -> int:
        max_tick = 0
        for track in mid.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += int(msg.time)
                if abs_tick > max_tick:
                    max_tick = abs_tick
        return max_tick

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(record_dir / "error.json", {"error_type": type(error).__name__, "message": str(error)})
        raise error
