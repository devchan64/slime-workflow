"""MIDI를 WAV로 렌더링하는 신규 규약형 노드."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import mido
from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class AudioRenderWavV2Module:
    name = "audio-render-wav-v2"
    node_id = "music.audio.render.wav"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        midi_path = Path(str(payload.get("midi_path", "")).strip())
        if not midi_path.is_file():
            self._fail(record_dir, f"입력 MIDI 파일이 없습니다: {midi_path}")

        render_plan = payload.get("render_plan") if isinstance(payload.get("render_plan"), dict) else {}
        soundfont_profile = str(render_plan.get("soundfont_profile", payload.get("soundfont_profile", "fluidr3-gm"))).strip()
        sample_rate = int(render_plan.get("sample_rate", payload.get("sample_rate", 44100)) or 44100)
        tempo_bpm_raw = render_plan.get("tempo_bpm", payload.get("tempo_bpm"))
        tempo_bpm = int(tempo_bpm_raw) if tempo_bpm_raw is not None else None
        if tempo_bpm is not None and not 40 <= tempo_bpm <= 240:
            self._fail(record_dir, f"tempo_bpm 허용 범위 위반(40~240): {tempo_bpm}")

        soundfont_registry = Path("workflow/nodes/audio_render_wav_v2/packages/soundfont-registry.json")
        registry = json.loads(soundfont_registry.read_text(encoding="utf-8"))
        sf_map = registry.get("profiles", {}) if isinstance(registry, dict) else {}
        if soundfont_profile not in sf_map:
            self._fail(record_dir, f"soundfont_profile 미등록: {soundfont_profile}")

        soundfont_path = Path(str(sf_map[soundfont_profile]).strip())
        if not soundfont_path.is_file():
            self._fail(record_dir, f"사운드폰트 파일이 없습니다: {soundfont_path}")

        fluidsynth = shutil.which("fluidsynth")
        if not fluidsynth:
            self._fail(record_dir, "fluidsynth 바이너리를 찾을 수 없습니다")

        output_wav = Path(str(payload.get("output_wav_path", "")).strip() or (run_root / "outputs" / "audio" / "rendered.wav"))
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        render_midi_path = midi_path
        if tempo_bpm is not None:
            render_midi_path = run_root / "outputs" / "audio" / "tempo-applied.mid"
            self._apply_tempo_to_midi(source_midi=midi_path, dest_midi=render_midi_path, tempo_bpm=tempo_bpm)

        cmd = [
            fluidsynth,
            "-ni",
            str(soundfont_path),
            str(render_midi_path),
            "-F",
            str(output_wav),
            "-r",
            str(sample_rate),
        ]
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            self._fail(record_dir, f"fluidsynth 실행 실패: code={completed.returncode}, stderr={completed.stderr.strip()}")
        if not output_wav.is_file():
            self._fail(record_dir, f"WAV 출력 파일이 생성되지 않았습니다: {output_wav}")

        report = {
            "node_id": self.node_id,
            "midi_path": str(midi_path),
            "render_midi_path": str(render_midi_path),
            "wav_path": str(output_wav),
            "soundfont_profile": soundfont_profile,
            "soundfont_path": str(soundfont_path),
            "sample_rate": sample_rate,
            "tempo_bpm": tempo_bpm,
            "command": cmd,
        }
        report_path = run_root / "outputs" / "audio" / "audio-render-wav.report.json"
        self._write_json(report_path, report)

        result = {
            "status": "rendered",
            "wav_path": str(output_wav),
            "report_path": str(report_path),
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)
        log(context, self.name, "INFO", f"MIDI->WAV 렌더 완료: output={output_wav}")
        return result

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _apply_tempo_to_midi(source_midi: Path, dest_midi: Path, tempo_bpm: int) -> None:
        midi = mido.MidiFile(str(source_midi))
        tempo = mido.bpm2tempo(tempo_bpm)
        for track in midi.tracks:
            filtered = [msg for msg in track if msg.type != "set_tempo"]
            track.clear()
            track.extend(filtered)
        if not midi.tracks:
            midi.tracks.append(mido.MidiTrack())
        midi.tracks[0].insert(0, mido.MetaMessage("set_tempo", tempo=tempo, time=0))
        dest_midi.parent.mkdir(parents=True, exist_ok=True)
        midi.save(str(dest_midi))

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(record_dir / "error.json", {"error_type": type(error).__name__, "message": str(error)})
        raise error
