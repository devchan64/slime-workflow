"""slseanwu/MIDI-LLM_Llama-3.2-1B 기반 텍스트-투-MIDI 토큰 생성 노드."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import torch
from anticipation.convert import events_to_midi
from transformers import AutoModelForCausalLM, AutoTokenizer

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class MidiLlmComposerModule:
    """자연어 프롬프트를 MIDI 튜플 문자열로 생성한다."""

    name = "midi-llm-composer"
    node_id = "music.midi.generate.midillm"
    model_id = "slseanwu/MIDI-LLM_Llama-3.2-1B"
    model_root = ".model/midi-llm"
    amt_gpt2_bos_id = 55026
    llama_vocab_size = 128256

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            self._fail(record_dir, "prompt 입력은 필수입니다")

        max_new_tokens = int(payload.get("max_new_tokens", 2048) or 2048)
        if max_new_tokens <= 0 or max_new_tokens > 8192:
            self._fail(record_dir, f"max_new_tokens 허용 범위 위반(1~8192): {max_new_tokens}")
        n_outputs = int(payload.get("n_outputs", 4) or 4)
        if n_outputs <= 0 or n_outputs > 8:
            self._fail(record_dir, f"n_outputs 허용 범위 위반(1~8): {n_outputs}")

        temperature = float(payload.get("temperature", 0.65) or 0.65)
        top_p = float(payload.get("top_p", 0.82) or 0.82)
        top_k = int(payload.get("top_k", 32) or 32)
        repetition_penalty = float(payload.get("repetition_penalty", 1.08) or 1.08)
        no_repeat_ngram_size = int(payload.get("no_repeat_ngram_size", 0) or 0)
        tempo_bpm = int(payload.get("tempo_bpm", 96) or 96)

        if not torch.cuda.is_available():
            self._fail(record_dir, "GPU(CUDA)가 필요합니다. CPU 추론은 허용되지 않습니다")

        model_root = Path(self.model_root)
        model_root.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        device = torch.device("cuda")
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, cache_dir=str(model_root), use_fast=False)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            cache_dir=str(model_root),
            low_cpu_mem_usage=True,
        ).to(device)

        section_plan = payload.get("section_plan") if isinstance(payload.get("section_plan"), list) else []
        instrumentation_plan = (
            payload.get("instrumentation_plan") if isinstance(payload.get("instrumentation_plan"), list) else []
        )
        section_lines: list[str] = []
        for sec in section_plan:
            if not isinstance(sec, dict):
                continue
            name = str(sec.get("name", "")).strip()
            role = str(sec.get("role", "")).strip()
            start_bar = sec.get("start_bar")
            end_bar = sec.get("end_bar")
            instruments = sec.get("section_instruments")
            instrument_text = ""
            if isinstance(instruments, list):
                cleaned = [str(x).strip() for x in instruments if str(x).strip()]
                if cleaned:
                    instrument_text = f" instruments={', '.join(cleaned)}"
            if name and role and start_bar is not None and end_bar is not None:
                section_lines.append(f"- bars {start_bar}-{end_bar}: {name} ({role}){instrument_text}")
        instrumentation_lines: list[str] = []
        for part in instrumentation_plan:
            if not isinstance(part, dict):
                continue
            part_name = str(part.get("part", "")).strip()
            role = str(part.get("role", "")).strip()
            register = str(part.get("register", "")).strip()
            density = str(part.get("density", "")).strip()
            if part_name and role and register and density:
                instrumentation_lines.append(f"- {part_name}: role={role}, register={register}, density={density}")

        section_block = "\n".join(section_lines) if section_lines else "- follow a coherent multi-section structure"
        instrumentation_block = (
            "\n".join(instrumentation_lines)
            if instrumentation_lines
            else "- use a balanced multi-instrument arrangement aligned to the prompt"
        )
        output_dir = run_root / "outputs" / "midi"
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / "midi-llm.raw.txt"
        token_path = output_dir / "midi-llm.tokens.json"
        midi_path = output_dir / "midi-llm.mid"
        report_path = output_dir / "midi-llm.report.json"
        prompt_tokens = 0
        generated_tokens = 0
        midi_tokens: list[int] = []
        midi_obj = None
        validation_error = ""
        selected_candidate_index = -1
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            retry_feedback = ""
            if validation_error:
                retry_feedback = (
                    "\nPrevious output was invalid and failed MIDI conversion:\n"
                    f"{validation_error}\n"
                    "Regenerate from scratch. Strictly keep each event as 5 tokens "
                    "where duration token must be < 1000 and pitch token must be < 128.\n"
                )
            input_text = (
                "You are a MIDI composition model. "
                "Output only pipe-separated numeric MIDI tuples.\n\n"
                f"Prompt: {prompt}\n"
                f"Target tempo: {tempo_bpm} BPM (keep this pace).\n"
                "Section directives:\n"
                f"{section_block}\n"
                "Instrumentation directives:\n"
                f"{instrumentation_block}\n"
                "Output rules:\n"
                "- Emit complete MIDI events in groups of 5 tokens.\n"
                "- Keep duration token values under 1000.\n"
                "- Keep pitch token values under 128.\n"
                "- Include melodic and harmonic notes on non-drum channels in addition to percussion.\n"
                f"{retry_feedback}"
                "MIDI tuples:"
            )
            inputs = tokenizer(input_text, return_tensors="pt")
            input_ids = inputs["input_ids"]
            midi_bos = torch.tensor([[self.amt_gpt2_bos_id + self.llama_vocab_size]], dtype=input_ids.dtype)
            input_ids = torch.cat([input_ids, midi_bos], dim=1).to(device)
            attention_mask = torch.ones_like(input_ids, device=device)
            prompt_tokens = int(input_ids.shape[-1])

            with torch.inference_mode():
                output_ids = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repetition_penalty=repetition_penalty,
                    no_repeat_ngram_size=no_repeat_ngram_size,
                    num_return_sequences=n_outputs,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.eos_token_id,
                )
            best_result = None
            best_score = None
            candidate_errors: list[str] = []
            attempt_summaries: list[dict[str, Any]] = []
            for idx in range(output_ids.shape[0]):
                gen_ids = output_ids[idx][prompt_tokens:]
                generated_tokens = int(gen_ids.shape[-1])
                raw_output = tokenizer.decode(gen_ids, skip_special_tokens=False).strip()
                (output_dir / f"midi-llm.raw.attempt-{attempt}.candidate-{idx+1}.txt").write_text(raw_output, encoding="utf-8")
                if not raw_output:
                    candidate_errors.append(f"candidate-{idx+1}: empty output")
                    attempt_summaries.append({"candidate": idx + 1, "status": "empty"})
                    continue
                local_tokens = self._to_midi_tokens(gen_ids, raw_output)
                self._write_json(
                    output_dir / f"midi-llm.tokens.attempt-{attempt}.candidate-{idx+1}.json",
                    {"tokens": local_tokens},
                )
                if not local_tokens:
                    candidate_errors.append(f"candidate-{idx+1}: empty midi tokens")
                    attempt_summaries.append({"candidate": idx + 1, "status": "empty_tokens"})
                    continue
                try:
                    local_midi = events_to_midi(local_tokens)
                    note_stats = self._collect_note_channel_stats(local_midi)
                    if note_stats["drum_only"]:
                        candidate_errors.append(f"candidate-{idx+1}: drum-only output")
                        attempt_summaries.append(
                            {
                                "candidate": idx + 1,
                                "status": "drum_only",
                                "note_stats": note_stats,
                            }
                        )
                        continue
                    score = (
                        int(note_stats["non_drum_notes"]) * 1000
                        + int(note_stats["non_drum_channels"]) * 100
                        - int(note_stats["drum_notes"])
                    )
                    attempt_summaries.append(
                        {
                            "candidate": idx + 1,
                            "status": "valid",
                            "score": score,
                            "note_stats": note_stats,
                        }
                    )
                    if best_score is None or score > best_score:
                        best_score = score
                        best_result = (idx, local_midi, local_tokens, raw_output)
                except Exception as exc:
                    candidate_errors.append(f"candidate-{idx+1}: {type(exc).__name__}: {exc}")
                    attempt_summaries.append(
                        {
                            "candidate": idx + 1,
                            "status": "convert_error",
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    continue

            self._write_json(
                output_dir / f"midi-llm.candidates.attempt-{attempt}.json",
                {"summaries": attempt_summaries},
            )
            if best_result is not None:
                idx, midi_obj, midi_tokens, raw_output = best_result
                selected_candidate_index = int(idx) + 1
                raw_path.write_text(raw_output, encoding="utf-8")
                break
            validation_error = "; ".join(candidate_errors) if candidate_errors else "유효한 candidate가 없습니다"
            continue

        if midi_obj is None:
            self._fail(record_dir, f"MIDI 이벤트 변환 재시도 실패: {validation_error}")

        midi_obj.save(str(midi_path))
        if not midi_path.is_file():
            self._fail(record_dir, f"MIDI 파일 저장 실패: {midi_path}")

        elapsed = time.perf_counter() - started
        self._write_json(token_path, {"tokens": midi_tokens})

        report = {
            "node_id": self.node_id,
            "model_id": self.model_id,
            "prompt": prompt,
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,
            "midi_token_count": len(midi_tokens),
            "elapsed_seconds": elapsed,
            "tokens_per_second": generated_tokens / max(elapsed, 1e-6),
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repetition_penalty": repetition_penalty,
            "no_repeat_ngram_size": no_repeat_ngram_size,
            "tempo_bpm": tempo_bpm,
            "raw_output_path": str(raw_path),
            "token_output_path": str(token_path),
            "mid_path": str(midi_path),
            "n_outputs": n_outputs,
            "selected_candidate_index": selected_candidate_index,
            "device": str(device),
        }
        self._write_json(report_path, report)

        result = {
            "status": "generated",
            "mid_path": str(midi_path),
            "raw_output_path": str(raw_path),
            "token_output_path": str(token_path),
            "report_path": str(report_path),
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)

        log(
            context,
            self.name,
            "INFO",
            (
                "midi-llm 생성 완료: "
                f"tokens={generated_tokens}, midi_tokens={len(midi_tokens)}, elapsed={elapsed:.2f}s, "
                f"tok/s={report['tokens_per_second']:.2f}"
            ),
        )
        return result

    def _to_midi_tokens(self, gen_ids: torch.Tensor, raw_output: str) -> list[int]:
        # Prefer explicit midi_token tags emitted by MIDI-LLM.
        tag_tokens = [int(match) for match in re.findall(r"<\|midi_token_(\d+)\|>", raw_output)]
        if tag_tokens:
            return tag_tokens

        output_ids = gen_ids.detach().to("cpu").tolist()
        midi_tokens = [int(token_id - self.llama_vocab_size) for token_id in output_ids]
        midi_tokens = [token for token in midi_tokens if token >= 0]
        return midi_tokens

    @staticmethod
    def _collect_note_channel_stats(midi_obj: Any) -> dict[str, Any]:
        note_channels: set[int] = set()
        non_drum_channels: set[int] = set()
        drum_notes = 0
        non_drum_notes = 0
        for track in getattr(midi_obj, "tracks", []):
            for msg in track:
                if getattr(msg, "type", "") == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                    ch = int(getattr(msg, "channel", 0))
                    note_channels.add(ch)
                    if ch == 9:
                        drum_notes += 1
                    else:
                        non_drum_notes += 1
                        non_drum_channels.add(ch)
        drum_only = bool(note_channels) and note_channels == {9}
        return {
            "total_notes": drum_notes + non_drum_notes,
            "drum_notes": drum_notes,
            "non_drum_notes": non_drum_notes,
            "non_drum_channels": len(non_drum_channels),
            "drum_only": drum_only or (drum_notes + non_drum_notes == 0),
        }


    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(
            record_dir / "error.json",
            {
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
        raise error
