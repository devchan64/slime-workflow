"""입력 프롬프트를 분석해 MIDI-LLM composer 파라미터를 생성하는 LLM 플래너 노드."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class MidiLlmPlannerModule:
    """프롬프트 기반 composer 파라미터 계획을 생성한다."""

    name = "midi-llm-planner"
    node_id = "music.midi.plan.midillm"
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    planner_model_root = ".model/midi-llm-planner"
    composer_model_root = ".model/midi-llm"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            self._fail(record_dir, "planner 입력 필수 필드 누락: prompt")

        if not torch.cuda.is_available():
            self._fail(record_dir, "GPU(CUDA)가 필요합니다. CPU 추론은 허용되지 않습니다")

        model_root = Path(self.planner_model_root)
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

        prompt_en, tr_prompt_tokens, tr_gen_tokens = self._translate_prompt_to_english(
            record_dir=record_dir,
            tokenizer=tokenizer,
            model=model,
            device=device,
            prompt=prompt,
        )
        composer_prompt, cmp_prompt_tokens, cmp_gen_tokens = self._generate_composer_prompt(
            record_dir=record_dir,
            tokenizer=tokenizer,
            model=model,
            device=device,
            prompt=prompt_en,
        )
        tempo_bpm, tempo_prompt_tokens, tempo_gen_tokens = self._generate_tempo_bpm(
            record_dir=record_dir,
            tokenizer=tokenizer,
            model=model,
            device=device,
            prompt=prompt_en,
            composer_prompt=composer_prompt,
        )
        max_new_tokens, mnt_prompt_tokens, mnt_gen_tokens = self._generate_max_new_tokens(
            record_dir=record_dir,
            tokenizer=tokenizer,
            model=model,
            device=device,
            prompt=prompt_en,
            composer_prompt=composer_prompt,
        )
        sampling_params, samp_prompt_tokens, samp_gen_tokens = self._generate_sampling_params(
            record_dir=record_dir,
            tokenizer=tokenizer,
            model=model,
            device=device,
            prompt=prompt_en,
            composer_prompt=composer_prompt,
        )
        n_outputs, nout_prompt_tokens, nout_gen_tokens = self._generate_n_outputs(
            record_dir=record_dir,
            tokenizer=tokenizer,
            model=model,
            device=device,
            prompt=prompt_en,
            composer_prompt=composer_prompt,
        )
        if not composer_prompt:
            self._fail(record_dir, "composer_prompt 생성 실패")

        plan = {
            "composer_prompt": composer_prompt,
            "tempo_bpm": tempo_bpm,
            "max_new_tokens": max_new_tokens,
            "temperature": sampling_params["temperature"],
            "top_p": sampling_params["top_p"],
            "top_k": sampling_params["top_k"],
            "repetition_penalty": sampling_params["repetition_penalty"],
            "n_outputs": n_outputs,
        }
        elapsed = time.perf_counter() - started

        composer_input = {
            "prompt": plan["composer_prompt"],
            "tempo_bpm": plan["tempo_bpm"],
            "max_new_tokens": plan["max_new_tokens"],
            "temperature": plan["temperature"],
            "top_p": plan["top_p"],
            "top_k": plan["top_k"],
            "repetition_penalty": plan["repetition_penalty"],
            "n_outputs": plan["n_outputs"],
            "run_root": str(run_root),
            "model_root": self.composer_model_root,
        }

        out_dir = run_root / "outputs" / "planner"
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = out_dir / "midi-llm-planner.composer-prompt.txt"
        composer_input_path = out_dir / "midi-llm-planner.composer-input.json"
        report_path = out_dir / "midi-llm-planner.report.json"

        raw_path.write_text(composer_prompt, encoding="utf-8")
        self._write_json(composer_input_path, composer_input)

        report = {
            "node_id": self.node_id,
            "model_id": self.model_id,
            "elapsed_seconds": elapsed,
            "prompt_tokens_composer_prompt": cmp_prompt_tokens,
            "generated_tokens_composer_prompt": cmp_gen_tokens,
            "prompt_tokens_translate_english": tr_prompt_tokens,
            "generated_tokens_translate_english": tr_gen_tokens,
            "prompt_tokens_tempo_bpm": tempo_prompt_tokens,
            "generated_tokens_tempo_bpm": tempo_gen_tokens,
            "prompt_tokens_max_new_tokens": mnt_prompt_tokens,
            "generated_tokens_max_new_tokens": mnt_gen_tokens,
            "prompt_tokens_sampling_params": samp_prompt_tokens,
            "generated_tokens_sampling_params": samp_gen_tokens,
            "prompt_tokens_n_outputs": nout_prompt_tokens,
            "generated_tokens_n_outputs": nout_gen_tokens,
            "raw_output_path": str(raw_path),
            "composer_input_path": str(composer_input_path),
        }
        self._write_json(report_path, report)

        result = {
            "status": "planned",
            "composer_input": composer_input,
            "composer_input_path": str(composer_input_path),
            "report_path": str(report_path),
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)

        log(
            context,
            self.name,
            "INFO",
            (
                "midi-llm planner 완료: "
                f"elapsed={elapsed:.2f}s, out={composer_input_path}"
            ),
        )
        return result

    def _translate_prompt_to_english(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
    ) -> tuple[str, int, int]:
        system_prompt = "Return plain text only."
        user_prompt = (
            "Translate the following music composition request into clear, natural English.\n"
            "Preserve intent, mood, genre, and constraints exactly. Do not add new constraints.\n"
            f"user_request: {prompt}\n"
            "Output only the translated English request."
        )
        raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 512)
        translated = raw_text.strip()
        if not translated:
            self._fail(record_dir, "영문 번역 결과가 비어 있습니다")
        self._write_json(record_dir / "raw_output_prompt_english.json", {"raw_text": translated})
        return translated, p_tok, g_tok

    def _generate_section_plan(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
        target_bars: int,
    ) -> tuple[list[dict[str, Any]], int, int]:
        system_prompt = "Return strict JSON only."
        user_prompt_base = (
            "Generate section plan JSON for music composition.\n"
            f"user_request: {prompt}\n"
            f"target_bars: {target_bars}\n"
            "Schema:\n"
            "{\"section_plan\":[{\"name\":string,\"start_bar\":int,\"end_bar\":int,\"role\":string,\"section_instruments\":[string]}]}\n"
            "Rules: start at 1 (1-based bars; never use 0), contiguous ranges, final end_bar must equal target_bars."
        )
        validation_error = ""
        last_p_tok = 0
        last_g_tok = 0
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate full section_plan JSON and fix all violations.\n"
                )
            user_prompt = user_prompt_base + feedback
            raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 512)
            last_p_tok = p_tok
            last_g_tok = g_tok
            self._write_json(record_dir / f"raw_output_section_plan_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "section_plan 생성 출력이 비어 있습니다"
                continue
            try:
                parsed = self._load_json_object(record_dir, raw_text, "section_plan")
                section_plan = parsed.get("section_plan") if isinstance(parsed, dict) else None
                if not isinstance(section_plan, list) or not section_plan:
                    raise RuntimeError("section_plan은 비어 있지 않은 배열이어야 합니다")
                normalized = self._normalize_section_plan(
                    record_dir=record_dir,
                    section_plan=section_plan,
                    target_bars=target_bars,
                )
                return normalized, last_p_tok, last_g_tok
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        self._fail(record_dir, f"section_plan 생성 재시도 실패: {validation_error}")
        return [], last_p_tok, last_g_tok

    def _generate_instrumentation_plan(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
        section_plan: list[dict[str, Any]],
    ) -> tuple[list[dict[str, str]], int, int]:
        system_prompt = "Return strict JSON only."
        user_prompt_base = (
            "Generate instrumentation plan JSON for composition.\n"
            f"user_request: {prompt}\n"
            f"section_plan: {json.dumps(section_plan, ensure_ascii=False)}\n"
            "Schema:\n"
            "{\"instrumentation_plan\":[{\"part\":string,\"role\":string,\"register\":string,\"density\":string}]}\n"
            "Use multiple complementary parts."
        )
        validation_error = ""
        last_p_tok = 0
        last_g_tok = 0
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate full instrumentation_plan JSON and fix all violations.\n"
                )
            user_prompt = user_prompt_base + feedback
            raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 384)
            last_p_tok = p_tok
            last_g_tok = g_tok
            self._write_json(record_dir / f"raw_output_instrumentation_plan_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "instrumentation_plan 생성 출력이 비어 있습니다"
                continue
            try:
                parsed = self._load_json_object(record_dir, raw_text, "instrumentation_plan")
                instrumentation_plan = parsed.get("instrumentation_plan") if isinstance(parsed, dict) else None
                if not isinstance(instrumentation_plan, list) or not instrumentation_plan:
                    raise RuntimeError("instrumentation_plan은 비어 있지 않은 배열이어야 합니다")
                normalized = self._normalize_instrumentation_plan(
                    record_dir=record_dir,
                    instrumentation_plan=instrumentation_plan,
                )
                return normalized, last_p_tok, last_g_tok
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        self._fail(record_dir, f"instrumentation_plan 생성 재시도 실패: {validation_error}")
        return [], last_p_tok, last_g_tok

    def _generate_composer_prompt(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
    ) -> tuple[str, int, int]:
        system_prompt = "Return plain text only."
        user_prompt = (
            "Create a detailed composer prompt for MIDI generation.\n"
            f"user_request: {prompt}\n"
            "Rules:\n"
            "- Keep genre/mood/tempo intent from user request.\n"
            "- Provide concrete musical direction for melody shape, rhythmic feel, harmonic motion, and dynamic development.\n"
            "- Include guidance on motif variation, phrase evolution, and tension/release across the full piece length.\n"
            "- Encourage richer arrangement layering without forcing fixed instrument lists.\n"
            "- Keep instructions specific enough for direct model execution, not vague adjectives only.\n"
            "- Do NOT include section-by-section descriptions.\n"
            "- Do NOT include instrument-by-instrument descriptions.\n"
            "- Keep output as one coherent paragraph in English.\n"
            "- Do NOT duplicate structured plans already provided separately."
        )
        raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 896)
        self._write_json(record_dir / "raw_output_composer_prompt.json", {"raw_text": raw_text})
        return raw_text.strip(), p_tok, g_tok

    def _generate_tempo_bpm(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
        composer_prompt: str,
    ) -> tuple[int, int, int]:
        system_prompt = "Return strict JSON only."
        user_prompt_base = (
            "Generate a tempo value for MIDI composition.\n"
            f"user_request: {prompt}\n"
            f"composer_prompt: {composer_prompt}\n"
            "Schema:\n"
            "{\"tempo_bpm\": integer}\n"
            "Rules: return one integer in range 40..140. "
            "For slow/gentle exploration music, choose lower tempo."
        )
        validation_error = ""
        last_p_tok = 0
        last_g_tok = 0
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate strict JSON only.\n"
                )
            user_prompt = user_prompt_base + feedback
            raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 96)
            last_p_tok = p_tok
            last_g_tok = g_tok
            self._write_json(record_dir / f"raw_output_tempo_bpm_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "tempo_bpm 생성 출력이 비어 있습니다"
                continue
            try:
                parsed = self._load_json_object(record_dir, raw_text, "tempo_bpm")
                if "tempo_bpm" not in parsed:
                    raise RuntimeError("tempo_bpm 키가 누락되었습니다")
                tempo_bpm = int(parsed["tempo_bpm"])
                if not 40 <= tempo_bpm <= 140:
                    raise RuntimeError(f"tempo_bpm 범위 위반: {tempo_bpm}")
                return tempo_bpm, last_p_tok, last_g_tok
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        self._fail(record_dir, f"tempo_bpm 생성 재시도 실패: {validation_error}")
        return 0, last_p_tok, last_g_tok

    def _generate_max_new_tokens(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
        composer_prompt: str,
    ) -> tuple[int, int, int]:
        system_prompt = "Return strict JSON only."
        user_prompt_base = (
            "Generate max_new_tokens for MIDI composition generation.\n"
            f"user_request: {prompt}\n"
            f"composer_prompt: {composer_prompt}\n"
            "Schema:\n"
            "{\"max_new_tokens\": integer}\n"
            "Rules:\n"
            "- If the user explicitly requests longer structure/length/detail, increase tokens appropriately.\n"
            "- If there is no explicit additional length requirement, return 3072.\n"
            "- Keep sufficient lower bound for multi-instrument continuity.\n"
            "- Allowed range is 2304..3072."
        )
        validation_error = ""
        last_p_tok = 0
        last_g_tok = 0
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate strict JSON only.\n"
                )
            user_prompt = user_prompt_base + feedback
            raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 96)
            last_p_tok = p_tok
            last_g_tok = g_tok
            self._write_json(record_dir / f"raw_output_max_new_tokens_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "max_new_tokens 생성 출력이 비어 있습니다"
                continue
            try:
                parsed = self._load_json_object(record_dir, raw_text, "max_new_tokens")
                if "max_new_tokens" not in parsed:
                    raise RuntimeError("max_new_tokens 키가 누락되었습니다")
                max_new_tokens = int(parsed["max_new_tokens"])
                if not 2304 <= max_new_tokens <= 3072:
                    raise RuntimeError(f"max_new_tokens 범위 위반(2304~3072): {max_new_tokens}")
                return max_new_tokens, last_p_tok, last_g_tok
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        self._fail(record_dir, f"max_new_tokens 생성 재시도 실패: {validation_error}")
        return 0, last_p_tok, last_g_tok

    def _generate_sampling_params(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
        composer_prompt: str,
    ) -> tuple[dict[str, Any], int, int]:
        system_prompt = "Return strict JSON only."
        user_prompt_base = (
            "Generate sampling parameters for MIDI composition model.\n"
            f"user_request: {prompt}\n"
            f"composer_prompt: {composer_prompt}\n"
            "Schema:\n"
            "{\"temperature\": number, \"top_p\": number, \"top_k\": integer, \"repetition_penalty\": number}\n"
            "Rules:\n"
            "- Balance coherence and variation for musical continuity.\n"
            "- Use conservative values when prompt asks for serene/slow/gentle atmosphere.\n"
            "- Prefer stable rhythmic spacing and avoid bursty token emission patterns.\n"
            "- Ranges: temperature 0.55..0.72, top_p 0.72..0.88, top_k 16..40, repetition_penalty 1.08..1.20.\n"
        )
        validation_error = ""
        last_p_tok = 0
        last_g_tok = 0
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate strict JSON only.\n"
                )
            user_prompt = user_prompt_base + feedback
            raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 128)
            last_p_tok = p_tok
            last_g_tok = g_tok
            self._write_json(record_dir / f"raw_output_sampling_params_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "sampling params 생성 출력이 비어 있습니다"
                continue
            try:
                parsed = self._load_json_object(record_dir, raw_text, "sampling_params")
                required = {"temperature", "top_p", "top_k", "repetition_penalty"}
                missing = sorted(required - set(parsed.keys()))
                if missing:
                    raise RuntimeError(f"sampling params 필드 누락: {missing}")
                temperature = float(parsed["temperature"])
                top_p = float(parsed["top_p"])
                top_k = int(parsed["top_k"])
                repetition_penalty = float(parsed["repetition_penalty"])
                if not 0.55 <= temperature <= 0.72:
                    raise RuntimeError(f"temperature 범위 위반: {temperature}")
                if not 0.72 <= top_p <= 0.88:
                    raise RuntimeError(f"top_p 범위 위반: {top_p}")
                if not 16 <= top_k <= 40:
                    raise RuntimeError(f"top_k 범위 위반: {top_k}")
                if not 1.08 <= repetition_penalty <= 1.20:
                    raise RuntimeError(f"repetition_penalty 범위 위반: {repetition_penalty}")
                return {
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k,
                    "repetition_penalty": repetition_penalty,
                }, last_p_tok, last_g_tok
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        self._fail(record_dir, f"sampling params 생성 재시도 실패: {validation_error}")
        return {}, last_p_tok, last_g_tok

    def _generate_n_outputs(
        self,
        record_dir: Path,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        prompt: str,
        composer_prompt: str,
    ) -> tuple[int, int, int]:
        system_prompt = "Return strict JSON only."
        user_prompt_base = (
            "Generate n_outputs for MIDI candidate sampling.\n"
            f"user_request: {prompt}\n"
            f"composer_prompt: {composer_prompt}\n"
            "Schema:\n"
            "{\"n_outputs\": integer}\n"
            "Rules:\n"
            "- Return integer in range 2..6.\n"
            "- Prefer 4 for typical prompts.\n"
            "- Use 5 or 6 only when prompt is complex and likely to benefit from more candidate diversity.\n"
        )
        validation_error = ""
        last_p_tok = 0
        last_g_tok = 0
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate strict JSON only.\n"
                )
            user_prompt = user_prompt_base + feedback
            raw_text, p_tok, g_tok = self._generate_text(tokenizer, model, device, system_prompt, user_prompt, 96)
            last_p_tok = p_tok
            last_g_tok = g_tok
            self._write_json(record_dir / f"raw_output_n_outputs_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "n_outputs 생성 출력이 비어 있습니다"
                continue
            try:
                parsed = self._load_json_object(record_dir, raw_text, "n_outputs")
                if "n_outputs" not in parsed:
                    raise RuntimeError("n_outputs 키가 누락되었습니다")
                n_outputs = int(parsed["n_outputs"])
                if not 2 <= n_outputs <= 6:
                    raise RuntimeError(f"n_outputs 범위 위반(2~6): {n_outputs}")
                return n_outputs, last_p_tok, last_g_tok
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        self._fail(record_dir, f"n_outputs 생성 재시도 실패: {validation_error}")
        return 4, last_p_tok, last_g_tok

    def _load_json_object(self, record_dir: Path, raw_text: str, name: str) -> dict[str, Any]:
        json_text = self._extract_json_object(raw_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            self._fail(record_dir, f"{name} JSON 파싱 실패: {exc}")
            raise
        if not isinstance(parsed, dict):
            self._fail(record_dir, f"{name} 출력은 JSON 객체여야 합니다")
        return parsed

    def _normalize_section_plan(
        self,
        record_dir: Path,
        section_plan: list[Any],
        target_bars: int,
    ) -> list[dict[str, Any]]:
        normalized_sections: list[dict[str, Any]] = []
        for idx, item in enumerate(section_plan):
            if not isinstance(item, dict):
                self._fail(record_dir, f"section_plan[{idx}]는 객체여야 합니다")
            name = str(item.get("name", "")).strip()
            role = str(item.get("role", "")).strip()
            if not name or not role:
                self._fail(record_dir, f"section_plan[{idx}] name/role 누락")
            try:
                start_bar = int(item.get("start_bar"))
                end_bar = int(item.get("end_bar"))
            except Exception:
                self._fail(record_dir, f"section_plan[{idx}] start_bar/end_bar는 정수여야 합니다")
            if start_bar <= 0 or end_bar < start_bar:
                self._fail(record_dir, f"section_plan[{idx}] bar 범위 위반: {start_bar}-{end_bar}")
            section_instruments_raw = item.get("section_instruments")
            if not isinstance(section_instruments_raw, list) or not section_instruments_raw:
                self._fail(record_dir, f"section_plan[{idx}] section_instruments는 비어있지 않은 배열이어야 합니다")
            section_instruments = [str(x).strip() for x in section_instruments_raw if str(x).strip()]
            if not section_instruments:
                self._fail(record_dir, f"section_plan[{idx}] section_instruments 유효값이 없습니다")
            normalized_sections.append(
                {
                    "name": name,
                    "start_bar": start_bar,
                    "end_bar": end_bar,
                    "role": role,
                    "section_instruments": section_instruments,
                }
            )
        normalized_sections.sort(key=lambda x: x["start_bar"])
        if normalized_sections[0]["start_bar"] != 1:
            self._fail(record_dir, "section_plan은 1마디부터 시작해야 합니다")
        prev_end = 0
        for sec in normalized_sections:
            if sec["start_bar"] != prev_end + 1:
                self._fail(record_dir, "section_plan bar 범위가 연속적이어야 합니다")
            prev_end = sec["end_bar"]
        if prev_end != target_bars:
            self._fail(record_dir, f"section_plan 마지막 마디({prev_end})가 target_bars({target_bars})와 일치해야 합니다")
        return normalized_sections

    def _normalize_instrumentation_plan(
        self,
        record_dir: Path,
        instrumentation_plan: list[Any],
    ) -> list[dict[str, str]]:
        normalized_instruments: list[dict[str, str]] = []
        for idx, item in enumerate(instrumentation_plan):
            if not isinstance(item, dict):
                self._fail(record_dir, f"instrumentation_plan[{idx}]는 객체여야 합니다")
            part = str(item.get("part", "")).strip()
            role = str(item.get("role", "")).strip()
            register = str(item.get("register", "")).strip()
            density = str(item.get("density", "")).strip()
            if not part or not role or not register or not density:
                self._fail(record_dir, f"instrumentation_plan[{idx}] 필수 필드 누락")
            normalized_instruments.append(
                {"part": part, "role": role, "register": register, "density": density}
            )
        return normalized_instruments

    def _parse_and_validate_plan(self, record_dir: Path, raw_text: str, target_bars: int) -> dict[str, Any]:
        json_text = self._extract_json_object(raw_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            self._fail(record_dir, f"planner JSON 파싱 실패: {exc}")
            raise

        if not isinstance(parsed, dict):
            self._fail(record_dir, "planner 출력은 JSON 객체여야 합니다")

        required_keys = {
            "composer_prompt",
            "section_plan",
            "instrumentation_plan",
        }
        optional_generation_keys = {
            "max_new_tokens",
            "temperature",
            "top_p",
            "top_k",
            "repetition_penalty",
            "no_repeat_ngram_size",
        }
        allowed_keys = required_keys | optional_generation_keys
        actual = set(parsed.keys())
        missing = required_keys - actual
        extra = actual - allowed_keys
        if missing or extra:
            self._fail(record_dir, f"planner 출력 키 불일치: missing={sorted(missing)}, extra={sorted(extra)}")

        composer_prompt = str(parsed["composer_prompt"]).strip()
        if not composer_prompt:
            self._fail(record_dir, "composer_prompt는 비어 있을 수 없습니다")

        section_plan = parsed["section_plan"]
        if not isinstance(section_plan, list) or not section_plan:
            self._fail(record_dir, "section_plan은 비어 있지 않은 배열이어야 합니다")
        normalized_sections: list[dict[str, Any]] = []
        for idx, item in enumerate(section_plan):
            if not isinstance(item, dict):
                self._fail(record_dir, f"section_plan[{idx}]는 객체여야 합니다")
            name = str(item.get("name", "")).strip()
            role = str(item.get("role", "")).strip()
            if not name or not role:
                self._fail(record_dir, f"section_plan[{idx}] name/role 누락")
            try:
                start_bar = int(item.get("start_bar"))
                end_bar = int(item.get("end_bar"))
            except Exception:
                self._fail(record_dir, f"section_plan[{idx}] start_bar/end_bar는 정수여야 합니다")
            if start_bar <= 0 or end_bar < start_bar:
                self._fail(record_dir, f"section_plan[{idx}] bar 범위 위반: {start_bar}-{end_bar}")
            section_instruments_raw = item.get("section_instruments")
            if not isinstance(section_instruments_raw, list) or not section_instruments_raw:
                self._fail(record_dir, f"section_plan[{idx}] section_instruments는 비어있지 않은 배열이어야 합니다")
            section_instruments = [str(x).strip() for x in section_instruments_raw if str(x).strip()]
            if not section_instruments:
                self._fail(record_dir, f"section_plan[{idx}] section_instruments 유효값이 없습니다")
            normalized_sections.append(
                {
                    "name": name,
                    "start_bar": start_bar,
                    "end_bar": end_bar,
                    "role": role,
                    "section_instruments": section_instruments,
                }
            )
        normalized_sections.sort(key=lambda x: x["start_bar"])
        if normalized_sections[0]["start_bar"] != 1:
            self._fail(record_dir, "section_plan은 1마디부터 시작해야 합니다")
        prev_end = 0
        for sec in normalized_sections:
            if sec["start_bar"] != prev_end + 1:
                self._fail(record_dir, "section_plan bar 범위가 연속적이어야 합니다")
            prev_end = sec["end_bar"]
        if prev_end != target_bars:
            self._fail(record_dir, f"section_plan 마지막 마디({prev_end})가 target_bars({target_bars})와 일치해야 합니다")

        instrumentation_plan = parsed["instrumentation_plan"]
        if not isinstance(instrumentation_plan, list) or not instrumentation_plan:
            self._fail(record_dir, "instrumentation_plan은 비어 있지 않은 배열이어야 합니다")
        normalized_instruments: list[dict[str, str]] = []
        for idx, item in enumerate(instrumentation_plan):
            if not isinstance(item, dict):
                self._fail(record_dir, f"instrumentation_plan[{idx}]는 객체여야 합니다")
            part = str(item.get("part", "")).strip()
            role = str(item.get("role", "")).strip()
            register = str(item.get("register", "")).strip()
            density = str(item.get("density", "")).strip()
            if not part or not role or not register or not density:
                self._fail(record_dir, f"instrumentation_plan[{idx}] 필수 필드 누락")
            normalized_instruments.append(
                {"part": part, "role": role, "register": register, "density": density}
            )

        max_new_tokens = int(parsed.get("max_new_tokens", 3072))
        temperature = float(parsed.get("temperature", 0.72))
        top_p = float(parsed.get("top_p", 0.86))
        top_k = int(parsed.get("top_k", 40))
        repetition_penalty = float(parsed.get("repetition_penalty", 1.14))
        no_repeat_ngram_size = int(parsed.get("no_repeat_ngram_size", 0))

        if not 256 <= max_new_tokens <= 4096:
            self._fail(record_dir, f"max_new_tokens 범위 위반: {max_new_tokens}")
        if not 0.6 <= temperature <= 0.9:
            self._fail(record_dir, f"temperature 범위 위반: {temperature}")
        if not 0.8 <= top_p <= 0.95:
            self._fail(record_dir, f"top_p 범위 위반: {top_p}")
        if not 20 <= top_k <= 80:
            self._fail(record_dir, f"top_k 범위 위반: {top_k}")
        if not 1.05 <= repetition_penalty <= 1.20:
            self._fail(record_dir, f"repetition_penalty 범위 위반: {repetition_penalty}")
        if not 0 <= no_repeat_ngram_size <= 8:
            self._fail(record_dir, f"no_repeat_ngram_size 범위 위반: {no_repeat_ngram_size}")

        return {
            "composer_prompt": composer_prompt,
            "section_plan": normalized_sections,
            "instrumentation_plan": normalized_instruments,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repetition_penalty": repetition_penalty,
            "no_repeat_ngram_size": no_repeat_ngram_size,
        }

    def _extract_json_object(self, raw_text: str) -> str:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0 or end < 0 or end < start:
            raise RuntimeError("planner 출력에서 JSON 객체를 찾지 못했습니다")
        return raw_text[start : end + 1].strip()

    def _generate_text(
        self,
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int,
    ) -> tuple[str, int, int]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(input_text, return_tensors="pt")
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)
        prompt_tokens = int(input_ids.shape[-1])
        with torch.inference_mode():
            output_ids = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=0.0,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
            )
        gen_ids = output_ids[0][prompt_tokens:]
        raw_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
        return raw_text, prompt_tokens, int(gen_ids.shape[-1])

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(record_dir / "error.json", {"error_type": type(error).__name__, "message": str(error)})
        raise error
