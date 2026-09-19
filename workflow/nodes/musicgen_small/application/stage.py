"""facebook/musicgen-small 기반 텍스트-투-뮤직 생성 노드."""

from __future__ import annotations

import json
import time
import wave
from pathlib import Path
from typing import Any

import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext


class MusicgenSmallGenerationModule:
    """text prompt를 받아 musicgen-small로 WAV를 생성한다."""

    name = "musicgen-small-generation"
    model_id = "facebook/musicgen-small"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        run_root = Path(str(payload.get("run_root", "")).strip() or context.run_root or ".result/workflow/runtime/run")
        record_dir = run_root / "records" / "nodes" / "musicgen.small.generate"
        record_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(record_dir / "input.json", dict(payload))

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            error = RuntimeError("musicgen.small.generate 입력 필수 필드 누락: prompt")
            self._write_error(record_dir / "error.json", error)
            raise error

        duration_seconds = int(payload.get("duration_seconds", 0) or 0)
        if duration_seconds <= 0:
            error = RuntimeError("musicgen.small.generate 입력 필수 필드 누락/오류: duration_seconds")
            self._write_error(record_dir / "error.json", error)
            raise error
        if duration_seconds > 120:
            error = RuntimeError(f"duration_seconds 허용 범위 초과(<=120): {duration_seconds}")
            self._write_error(record_dir / "error.json", error)
            raise error

        guidance_scale = float(payload.get("guidance_scale", 5.0) or 5.0)
        temperature = float(payload.get("temperature", 0.7) or 0.7)
        top_k = int(payload.get("top_k", 64) or 64)
        top_p = float(payload.get("top_p", 0.95) or 0.95)
        tone_lowpass_hz = float(payload.get("tone_lowpass_hz", 14000.0) or 14000.0)

        if not torch.cuda.is_available():
            error = RuntimeError("GPU(CUDA)가 필요합니다. CPU 추론은 허용되지 않습니다")
            self._write_error(record_dir / "error.json", error)
            raise error

        output_wav = run_root / "outputs" / "audio" / "musicgen-small.wav"
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        model_root = Path(str(payload.get("model_root", "")).strip() or ".model/musicgen-small")
        model_root.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        device = torch.device("cuda")
        dtype = torch.float16

        processor = AutoProcessor.from_pretrained(self.model_id, cache_dir=str(model_root))
        model = MusicgenForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            cache_dir=str(model_root),
        ).to(device)

        frame_rate = int(getattr(model.config.audio_encoder, "frame_rate", 50))
        max_new_tokens = int(duration_seconds * frame_rate)
        if max_new_tokens <= 0:
            error = RuntimeError(
                f"max_new_tokens 계산 실패: duration_seconds={duration_seconds}, frame_rate={frame_rate}"
            )
            self._write_error(record_dir / "error.json", error)
            raise error

        inputs = processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)

        with torch.inference_mode():
            generated = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                guidance_scale=guidance_scale,
                do_sample=True,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
            )

        generated = generated.detach().to("cpu").float().squeeze(0)
        if generated.ndim == 2:
            waveform = generated[0]
        elif generated.ndim == 1:
            waveform = generated
        else:
            error = RuntimeError(f"생성 파형 차원이 비정상입니다: shape={tuple(generated.shape)}")
            self._write_error(record_dir / "error.json", error)
            raise error

        audio_encoder = getattr(model.config, "audio_encoder", None)
        sample_rate = int(getattr(audio_encoder, "sampling_rate", 32000))
        if tone_lowpass_hz > 0.0:
            waveform = self._apply_lowpass_fft(waveform, sample_rate, tone_lowpass_hz)
        self._write_wav_mono16(output_wav, waveform, sample_rate)

        elapsed = time.perf_counter() - started
        generated_seconds = float(waveform.numel()) / float(sample_rate)
        rtf = elapsed / max(generated_seconds, 1e-6)

        report = {
            "node_id": "musicgen.small.generate",
            "model_id": self.model_id,
            "prompt": prompt,
            "duration_seconds_requested": duration_seconds,
            "duration_seconds_generated": generated_seconds,
            "sample_rate": sample_rate,
            "max_new_tokens": max_new_tokens,
            "frame_rate": frame_rate,
            "elapsed_seconds": elapsed,
            "realtime_factor": rtf,
            "guidance_scale": guidance_scale,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "tone_lowpass_hz": tone_lowpass_hz,
            "output_wav": str(output_wav),
            "device": str(device),
            "dtype": str(dtype),
        }

        report_path = run_root / "outputs" / "audio" / "musicgen-small.report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        log(
            context,
            self.name,
            "INFO",
            (
                "musicgen-small 생성 완료: "
                f"duration_req={duration_seconds:.1f}s, duration_gen={generated_seconds:.2f}s, "
                f"elapsed={elapsed:.2f}s, rtf={rtf:.3f}, output={output_wav}"
            ),
        )

        result = {
            "wav_path": str(output_wav),
            "report_path": str(report_path),
            "status": "generated",
            "metadata": report,
        }
        self._write_json(record_dir / "output.json", result)
        return result

    @staticmethod
    def _write_wav_mono16(path: Path, waveform: torch.Tensor, sample_rate: int) -> None:
        data = waveform.clamp(-1.0, 1.0)
        pcm = (data * 32767.0).to(torch.int16).numpy().tobytes()
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)

    @staticmethod
    def _apply_lowpass_fft(waveform: torch.Tensor, sample_rate: int, cutoff_hz: float) -> torch.Tensor:
        if waveform.numel() == 0:
            return waveform
        nyquist = sample_rate * 0.5
        cutoff = max(200.0, min(float(cutoff_hz), nyquist - 200.0))
        spectrum = torch.fft.rfft(waveform)
        freqs = torch.fft.rfftfreq(waveform.numel(), d=1.0 / float(sample_rate))
        rolloff_start = cutoff * 0.85
        gain = torch.ones_like(freqs)
        transition = (freqs > rolloff_start) & (freqs < cutoff)
        gain[freqs >= cutoff] = 0.0
        if torch.any(transition):
            x = (freqs[transition] - rolloff_start) / max(cutoff - rolloff_start, 1.0)
            gain[transition] = torch.cos(x * 1.57079632679) ** 2
        filtered = torch.fft.irfft(spectrum * gain, n=waveform.numel())
        return filtered

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_error(path: Path, error: Exception) -> None:
        MusicgenSmallGenerationModule._write_json(
            path,
            {
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
