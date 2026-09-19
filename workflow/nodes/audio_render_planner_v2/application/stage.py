"""MIDI 프롬프트/메타를 바탕으로 오디오 렌더 파라미터를 생성하는 LLM 플래너 노드."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class AudioRenderPlannerV2Module:
    name = "audio-render-planner-v2"
    node_id = "music.audio.plan.render"
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    soundfont_registry_path = Path("workflow/nodes/audio_render_wav_v2/packages/soundfont-registry.json")

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / self.node_id
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            self._fail(record_dir, "audio planner 입력 필수 필드 누락: prompt")
        compact_prompt = prompt.replace("\n", " ").strip()
        if len(compact_prompt) > 240:
            compact_prompt = compact_prompt[:240]

        if not torch.cuda.is_available():
            self._fail(record_dir, "GPU(CUDA)가 필요합니다. CPU 추론은 허용되지 않습니다")

        model_root = Path(str(payload.get("planner_model_root", "")).strip() or ".model/audio-render-planner")
        model_root.mkdir(parents=True, exist_ok=True)
        allowed_profiles = self._load_allowed_soundfont_profiles(record_dir)

        started = time.perf_counter()
        device = torch.device("cuda")
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, cache_dir=str(model_root), use_fast=False)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            cache_dir=str(model_root),
            low_cpu_mem_usage=True,
        ).to(device)

        system_prompt = "Return strict JSON only. No markdown or commentary."
        user_prompt = (
            "Create rendering parameters for converting MIDI to final MP3 for game BGM.\n"
            f"user_prompt_summary: {compact_prompt}\n"
            f"Allowed soundfont_profile values: {', '.join(allowed_profiles)}\n"
            "Output must be one compact JSON object only.\n"
            "notes must be a short plain sentence (<=80 chars), not array/object.\n"
            "JSON schema:\n"
            "{\n"
            "  \"soundfont_profile\": string (must be one of allowed values),\n"
            "  \"sample_rate\": integer (22050|32000|44100|48000),\n"
            "  \"tail_seconds\": number (0.0..8.0),\n"
            "  \"normalize_target_db\": number (-24.0..-10.0),\n"
            "  \"mp3_bitrate\": string (\"128k\"|\"160k\"|\"192k\"|\"256k\"|\"320k\"),\n"
            "  \"notes\": string\n"
            "}"
        )

        raw_text = ""
        prompt_tokens = 0
        generated_tokens = 0
        plan: dict[str, Any] | None = None
        validation_error = ""
        for attempt in range(1, 7):
            feedback = ""
            if validation_error:
                feedback = (
                    "\nValidation error from previous output:\n"
                    f"{validation_error}\n"
                    "Regenerate full JSON and fix all violations.\n"
                )
            attempt_user_prompt = user_prompt + feedback
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": attempt_user_prompt}]
            input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(input_text, return_tensors="pt")
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs["attention_mask"].to(device)
            prompt_tokens = int(input_ids.shape[-1])

            with torch.inference_mode():
                output_ids = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=128,
                    do_sample=False,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.eos_token_id,
                )

            gen_ids = output_ids[0][prompt_tokens:]
            generated_tokens = int(gen_ids.shape[-1])
            raw_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
            self._write_json(record_dir / f"raw_output_attempt_{attempt}.json", {"raw_text": raw_text})
            if not raw_text:
                validation_error = "audio planner 모델 출력이 비어 있습니다"
                continue
            try:
                plan = self._validate_plan(record_dir, raw_text, allowed_profiles)
                break
            except RuntimeError as exc:
                validation_error = str(exc)
                continue
        if plan is None:
            self._fail(record_dir, f"audio planner 재시도 실패: {validation_error}")

        out_dir = run_root / "outputs" / "audio-plan"
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = out_dir / "audio-render-planner.raw.txt"
        plan_path = out_dir / "audio-render-plan.json"
        report_path = out_dir / "audio-render-planner.report.json"

        raw_path.write_text(raw_text, encoding="utf-8")
        self._write_json(plan_path, plan)

        report = {
            "node_id": self.node_id,
            "model_id": self.model_id,
            "elapsed_seconds": time.perf_counter() - started,
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,
            "raw_output_path": str(raw_path),
            "plan_path": str(plan_path),
        }
        self._write_json(report_path, report)

        result = {
            "status": "planned",
            "render_plan": plan,
            "render_plan_path": str(plan_path),
            "report_path": str(report_path),
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)
        log(context, self.name, "INFO", f"audio render planner 완료: out={plan_path}")
        return result

    def _validate_plan(self, record_dir: Path, raw_text: str, allowed_profiles: set[str]) -> dict[str, Any]:
        json_text = self._extract_json_object(raw_text)
        try:
            plan = json.loads(json_text)
        except json.JSONDecodeError as exc:
            self._fail(record_dir, f"audio planner JSON 파싱 실패: {exc}")
            raise
        if not isinstance(plan, dict):
            self._fail(record_dir, "audio planner 출력은 JSON 객체여야 합니다")

        required = {"soundfont_profile", "sample_rate", "tail_seconds", "normalize_target_db", "mp3_bitrate", "notes"}
        if set(plan.keys()) != required:
            self._fail(record_dir, f"audio planner 출력 키 불일치: {sorted(plan.keys())}")

        sample_rate = int(plan["sample_rate"])
        if sample_rate not in {22050, 32000, 44100, 48000}:
            self._fail(record_dir, f"sample_rate 허용값 위반: {sample_rate}")

        tail = float(plan["tail_seconds"])
        if not 0.0 <= tail <= 8.0:
            self._fail(record_dir, f"tail_seconds 범위 위반: {tail}")

        norm = float(plan["normalize_target_db"])
        if not -24.0 <= norm <= -10.0:
            self._fail(record_dir, f"normalize_target_db 범위 위반: {norm}")

        bitrate = str(plan["mp3_bitrate"])
        if bitrate not in {"128k", "160k", "192k", "256k", "320k"}:
            self._fail(record_dir, f"mp3_bitrate 허용값 위반: {bitrate}")

        soundfont_profile = str(plan["soundfont_profile"]).strip()
        if not soundfont_profile:
            self._fail(record_dir, "soundfont_profile은 비어 있을 수 없습니다")
        if soundfont_profile not in allowed_profiles:
            self._fail(record_dir, f"soundfont_profile 허용값 위반: {soundfont_profile}, allowed={sorted(allowed_profiles)}")

        return {
            "soundfont_profile": soundfont_profile,
            "sample_rate": sample_rate,
            "tail_seconds": tail,
            "normalize_target_db": norm,
            "mp3_bitrate": bitrate,
            "notes": str(plan["notes"]).strip(),
        }

    def _load_allowed_soundfont_profiles(self, record_dir: Path) -> set[str]:
        if not self.soundfont_registry_path.is_file():
            self._fail(record_dir, f"사운드폰트 레지스트리 파일이 없습니다: {self.soundfont_registry_path}")
        try:
            registry = json.loads(self.soundfont_registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self._fail(record_dir, f"사운드폰트 레지스트리 JSON 파싱 실패: {exc}")
            raise
        profiles = registry.get("profiles") if isinstance(registry, dict) else None
        if not isinstance(profiles, dict) or not profiles:
            self._fail(record_dir, "사운드폰트 레지스트리 profiles가 비어있거나 형식이 잘못되었습니다")

        available: set[str] = set()
        for key, rel_path in profiles.items():
            profile = str(key).strip()
            if not profile:
                continue
            path = Path(str(rel_path).strip())
            if path.is_file():
                available.add(profile)

        if not available:
            self._fail(record_dir, "사용 가능한 사운드폰트 파일이 없습니다. 레지스트리 경로 또는 자산 준비 상태를 확인하세요")
        return available

    def _extract_json_object(self, raw_text: str) -> str:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0 or end < 0 or end < start:
            raise RuntimeError("audio planner 출력에서 JSON 객체를 찾지 못했습니다")
        return raw_text[start : end + 1].strip()

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fail(self, record_dir: Path, message: str) -> None:
        error = RuntimeError(message)
        self._write_json(record_dir / "error.json", {"error_type": type(error).__name__, "message": str(error)})
        raise error
