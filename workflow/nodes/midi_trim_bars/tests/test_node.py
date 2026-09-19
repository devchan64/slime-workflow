"""midi_trim_bars 노드 테스트."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import mido

from workflow.interfaces import PipelineContext
from workflow.nodes.midi_trim_bars.application.stage import MidiTrimBarsModule


PACKAGE_PATH = Path("workflow/nodes/midi_trim_bars/packages/unit-midi-trim-bars.json")


class MidiTrimBarsNodeTest(unittest.TestCase):
    def test_package_exists(self) -> None:
        self.assertTrue(PACKAGE_PATH.is_file())
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["node_id"], "music.midi.trim.bars")

    def test_trim_32bars_4_4(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src.mid"
            self._write_test_midi(src)

            context = PipelineContext(run_id="test-trim", run_root=str(root), area="workflow", pipeline="music")
            result = MidiTrimBarsModule().process(context, {"midi_path": str(src), "bars": 32, "run_root": str(root)})

            out = Path(result["midi_path"])
            self.assertTrue(out.is_file())
            trimmed = mido.MidiFile(str(out))
            max_tick = self._max_abs_tick(trimmed)
            self.assertLessEqual(max_tick, 32 * 4 * trimmed.ticks_per_beat)

    def test_trim_uses_time_signature_from_any_track(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src-6-8.mid"
            self._write_test_midi_time_signature_in_second_track(src)

            context = PipelineContext(run_id="test-trim-6-8", run_root=str(root), area="workflow", pipeline="music")
            result = MidiTrimBarsModule().process(context, {"midi_path": str(src), "bars": 32, "run_root": str(root)})

            out = Path(result["midi_path"])
            self.assertTrue(out.is_file())
            trimmed = mido.MidiFile(str(out))
            max_tick = self._max_abs_tick(trimmed)
            # 6/8 기준 1마디 = 3 quarter beats
            self.assertLessEqual(max_tick, 32 * 3 * trimmed.ticks_per_beat)

    @staticmethod
    def _max_abs_tick(mid: mido.MidiFile) -> int:
        max_tick = 0
        for track in mid.tracks:
            t = 0
            for msg in track:
                t += msg.time
            max_tick = max(max_tick, t)
        return max_tick

    @staticmethod
    def _write_test_midi(path: Path) -> None:
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

        # 40 bars length melody (trim 대상으로 32 bars보다 길게 생성)
        bar_ticks = 4 * mid.ticks_per_beat
        for bar in range(40):
            note = 60 + (bar % 8)
            track.append(mido.Message("note_on", note=note, velocity=80, time=0, channel=0))
            track.append(mido.Message("note_off", note=note, velocity=0, time=bar_ticks // 2, channel=0))
            track.append(mido.Message("note_on", note=note + 5, velocity=72, time=0, channel=0))
            track.append(mido.Message("note_off", note=note + 5, velocity=0, time=bar_ticks // 2, channel=0))

        track.append(mido.MetaMessage("end_of_track", time=0))
        mid.save(str(path))

    @staticmethod
    def _write_test_midi_time_signature_in_second_track(path: Path) -> None:
        mid = mido.MidiFile(ticks_per_beat=480)
        melody_track = mido.MidiTrack()
        meta_track = mido.MidiTrack()
        mid.tracks.append(melody_track)
        mid.tracks.append(meta_track)

        meta_track.append(mido.MetaMessage("time_signature", numerator=6, denominator=8, time=0))
        meta_track.append(mido.MetaMessage("end_of_track", time=0))

        bar_ticks_6_8 = 3 * mid.ticks_per_beat
        for bar in range(48):
            note = 64 + (bar % 10)
            melody_track.append(mido.Message("note_on", note=note, velocity=84, time=0, channel=0))
            melody_track.append(mido.Message("note_off", note=note, velocity=0, time=bar_ticks_6_8, channel=0))
        melody_track.append(mido.MetaMessage("end_of_track", time=0))

        mid.save(str(path))


if __name__ == "__main__":
    unittest.main()
