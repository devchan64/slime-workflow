"""디자인 컨셉 생성 단계."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from workflow.interfaces import Payload, PipelineContext

from workflow.core.logger import log


CONCEPT_IMAGE_PACKAGE_DIR = Path("workflow/nodes/concept_image/packages")
MODEL_STORAGE_CONFIG_PATH = CONCEPT_IMAGE_PACKAGE_DIR / "model-storage-paths.json"
MODEL_REGISTRY_CONFIG_PATH = CONCEPT_IMAGE_PACKAGE_DIR / "model-registry.json"


class DesignConceptGenerationModule:
    name = "design-concept-generation"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        style = payload.get("style", "rpg")
        prompt = payload.get("prompt", "")
        negative_prompt = payload.get("negative_prompt", "")
        generation_prompt = payload.get("generation_prompt", "")
        generation_negative_prompt = payload.get("generation_negative_prompt", "")
        references = payload.get("reference_images", [])
        reference_paths = self._resolve_reference_paths(references)

        concept = self._build_concept_metadata(prompt, style, references)

        output = dict(payload)
        output["design_concept"] = concept
        concept_image, generation_status = self._materialize_concept_image(
            context,
            payload,
            prompt,
            negative_prompt,
            generation_prompt,
            generation_negative_prompt,
            style,
            references,
            reference_paths,
        )
        output["design_concept_generation"] = generation_status
        if concept_image is not None:
            candidate_images = generation_status.get("candidate_images", [])
            if candidate_images:
                output["design_concept_candidates"] = candidate_images
            if self._prefer_sheet_output(prompt, generation_prompt):
                presentation_image = self._materialize_concept_sheet(context.run_id, payload, concept_image, references)
                if presentation_image is not None:
                    output["design_concept_sheet_image"] = presentation_image
                    output["design_concept_render_image"] = concept_image
                    concept_image = presentation_image
            output["design_concept_image"] = concept_image
            log(context, self.name, "INFO", f"콘셉트 이미지 결과를 기록했다 ({concept_image['path']})")
        log(context, self.name, "INFO", f"디자인 컨셉 초안을 생성했다 (reference_count={len(references)})")
        return output

    def _materialize_concept_image(
        self,
        context: PipelineContext,
        payload: Payload,
        prompt: str,
        negative_prompt: str,
        generation_prompt: str,
        generation_negative_prompt: str,
        style: str,
        references: list[dict],
        reference_paths: list[Path],
    ) -> tuple[dict | None, dict]:
        generated_image, generation_status = self._generate_with_local_model(
            context.run_id,
            payload,
            prompt,
            negative_prompt,
            generation_prompt,
            generation_negative_prompt,
            style,
            references,
            reference_paths,
        )
        if generated_image is not None:
            log(context, self.name, "INFO", f"로컬 생성 모델 추론을 완료했다 ({generated_image['model_path']})")
            return generated_image, generation_status

        reason = generation_status.get("error", "알 수 없는 생성 실패")
        raise RuntimeError(f"콘셉트 이미지 생성에 실패했다: {reason}")

    def _materialize_concept_sheet(
        self,
        run_id: str,
        payload: Payload,
        concept_image: dict,
        references: list[dict],
    ) -> dict | None:
        image_path = Path(str(concept_image.get("path", "")))
        if not image_path.is_file():
            return None

        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception:
            return None

        try:
            main_image = Image.open(image_path).convert("RGB")
        except Exception:
            return None

        reference_image = self._resolve_sheet_reference_image(payload, references, main_image)
        face_image = self._resolve_sheet_face_image(payload, references, reference_image)

        output_dir = self._run_output_dir_from_run_id(payload, run_id, "sheet")
        destination_path = output_dir / "sheet.png"

        canvas = Image.new("RGB", (1280, 1536), (235, 233, 229))
        draw = ImageDraw.Draw(canvas)
        title_font = self._load_font(28)
        section_font = self._load_font(22)
        body_font = self._load_font(18)
        small_font = self._load_font(16)

        self._draw_panel(draw, (50, 80, 420, 530), "FACE", title_font)
        self._paste_centered(canvas, face_image, (85, 120, 300, 380))

        self._draw_panel(draw, (440, 80, 840, 1460), "BODY", title_font)
        self._paste_centered(canvas, main_image, (460, 110, 360, 1320))

        self._draw_panel(draw, (880, 80, 1230, 460), "SHIRT", title_font)
        self._paste_centered(canvas, self._crop_relative(reference_image, (0.24, 0.14, 0.76, 0.48)), (905, 115, 300, 315))
        self._draw_panel(draw, (880, 500, 1230, 880), "SHORTS", title_font)
        self._paste_centered(canvas, self._crop_relative(reference_image, (0.26, 0.43, 0.74, 0.70)), (905, 535, 300, 315))
        self._draw_panel(draw, (880, 920, 1230, 1300), "SHOES", title_font)
        self._paste_centered(canvas, self._crop_relative(reference_image, (0.18, 0.76, 0.82, 0.98)), (905, 955, 300, 315))

        draw.text((60, 560), "COLOR PALETTE", fill=(40, 40, 40), font=section_font)
        palette_labels = ["HAIR", "SKIN", "SHIRT", "SHORTS", "SHOES"]
        for index, color in enumerate(self._sample_palette(reference_image)):
            top = 610 + index * 92
            draw.rectangle((60, top, 110, top + 50), fill=color, outline=(60, 60, 60), width=1)
            draw.text((135, top + 16), palette_labels[index], fill=(55, 55, 55), font=body_font)

        draw.text((60, 1120), "CHARACTER INFO", fill=(40, 40, 40), font=section_font)
        info_lines = [
            f"PROMPT  {self._sanitize_text(str(payload.get('prompt', '')).strip(), 40)}",
            f"MODEL   {str(concept_image.get('model_id', '-')).strip()}",
            f"STYLE   {str(payload.get('style', 'cartoon')).strip()}",
            f"SEED    {str(payload.get('seed', 42)).strip()}",
        ]
        for index, line in enumerate(info_lines):
            draw.text((60, 1170 + index * 52), line, fill=(65, 65, 65), font=small_font)

        canvas.save(destination_path)
        return {
            "path": str(destination_path),
            "mode": "sheet-template-composited",
            "source_image": str(image_path),
        }

    def _generate_with_local_model(
        self,
        run_id: str,
        payload: Payload,
        prompt: str,
        negative_prompt: str,
        generation_prompt: str,
        generation_negative_prompt: str,
        style: str,
        references: list[dict],
        reference_paths: list[Path],
    ) -> tuple[dict | None, dict]:
        model_id = str(payload.get("model_id", "sd15-base")).strip() or "sd15-base"
        controlnet_id = str(payload.get("controlnet_id", "")).strip()
        ip_adapter_id = str(payload.get("ip_adapter_id", "")).strip()
        model_spec = _concept_model_spec(model_id)
        model_path = model_spec["path"]
        loader_kind = str(model_spec.get("loader_kind", "directory"))
        controlnet_spec = _control_model_spec(controlnet_id) if controlnet_id else None
        ip_adapter_spec = _adapter_model_spec(ip_adapter_id) if ip_adapter_id else None
        control_image_path = self._resolve_control_image_path(payload, references)
        generation_status = {
            "attempted": True,
            "fallback_used": False,
            "model_id": model_id,
            "controlnet_id": controlnet_id or None,
            "ip_adapter_id": ip_adapter_id or None,
            "used_reference_images": bool(references),
            "used_reference_image_count": len(reference_paths),
            "used_control_image": control_image_path is not None,
            "num_outputs_requested": max(1, int(payload.get("num_outputs", 1))),
        }
        if reference_paths:
            generation_status["reference_input_paths"] = [str(path) for path in reference_paths]
        if loader_kind == "directory" and not model_path.is_dir():
            generation_status["error"] = f"모델 경로가 없다: {model_path}"
            return None, generation_status
        if loader_kind == "single_file" and not model_path.is_file():
            generation_status["error"] = f"모델 파일이 없다: {model_path}"
            return None, generation_status

        try:
            from PIL import Image
            import torch
            from diffusers import (
                AutoPipelineForImage2Image,
                ControlNetModel,
                DiffusionPipeline,
                DPMSolverMultistepScheduler,
                StableDiffusionControlNetPipeline,
                StableDiffusionImg2ImgPipeline,
                StableDiffusionPipeline,
            )
        except Exception as exc:
            generation_status["error"] = f"로컬 생성 의존성 로드 실패: {exc}"
            return None, generation_status

        output_dir = self._run_output_dir_from_run_id(payload, run_id, "concept")

        if not torch.cuda.is_available():
            generation_status["error"] = "GPU를 사용할 수 없어 로컬 생성 모델 추론을 중단했다. CPU fallback은 허용되지 않는다."
            return None, generation_status

        device = "cuda"
        torch_dtype = torch.float16
        pipeline = self._build_pipeline(
            model_path=model_path,
            torch_dtype=torch_dtype,
            use_img2img=bool(references),
            auto_img2img_cls=AutoPipelineForImage2Image,
            diffusion_cls=DiffusionPipeline,
            sd_img2img_cls=StableDiffusionImg2ImgPipeline,
            sd_pipeline_cls=StableDiffusionPipeline,
            controlnet_cls=ControlNetModel,
            controlnet_pipeline_cls=StableDiffusionControlNetPipeline,
            model_spec=model_spec,
            controlnet_spec=controlnet_spec,
            ip_adapter_spec=ip_adapter_spec,
        )
        if pipeline is None:
            generation_status["error"] = "파이프라인 생성 실패"
            return None, generation_status
        try:
            pipeline.scheduler = self._resolve_scheduler(pipeline.scheduler, DPMSolverMultistepScheduler)
            pipeline = pipeline.to(device)
            if hasattr(pipeline, "safety_checker"):
                pipeline.safety_checker = None
            ip_adapter_scale = float(payload.get("ip_adapter_scale", 0.55))
            controlnet_conditioning_scale = float(payload.get("controlnet_conditioning_scale", 1.0))
            self._load_ip_adapter(pipeline, ip_adapter_spec, ip_adapter_scale)

            generator = torch.Generator(device=device).manual_seed(int(payload.get("seed", 42)))
            steps = max(12, int(payload.get("steps", 28)))
            guidance_scale = float(payload.get("guidance_scale", 8.0))
            ip_adapter_scale = float(payload.get("ip_adapter_scale", 0.55))
            controlnet_conditioning_scale = float(payload.get("controlnet_conditioning_scale", 1.0))
            strength = float(payload.get("strength", 0.35))
            width = int(payload.get("width", 512))
            height = int(payload.get("height", 512))
            num_outputs = max(1, int(payload.get("num_outputs", 1)))

            prompt_text = self._build_positive_prompt(prompt, generation_prompt, style, references)
            negative_prompt_text = self._build_negative_prompt(negative_prompt, generation_negative_prompt)
            ip_adapter_image, ip_adapter_source_path = self._resolve_ip_adapter_image(payload, reference_paths, width, height)
            if ip_adapter_source_path is not None:
                generation_status["ip_adapter_source_path"] = str(ip_adapter_source_path)
            retry_plan = self._build_retry_plan(width, height)
            candidate_images = []
            mode = ""
            retry_records = []
            last_error = None
            source_path = reference_paths[0] if reference_paths else None
            if references and source_path is None:
                generation_status["error"] = f"참조 이미지 파일이 없다: {source_path}"
                return None, generation_status
            if controlnet_spec is not None and control_image_path is None:
                generation_status["error"] = "ControlNet 조건 이미지를 찾지 못했다"
                return None, generation_status

            for attempt_index, (attempt_width, attempt_height) in enumerate(retry_plan, start=1):
                try:
                    if controlnet_spec is not None:
                        control_source = Image.open(control_image_path).convert("RGB")
                        control_image = self._prepare_control_image(control_source, attempt_width, attempt_height, controlnet_spec)
                        mode = f"local-model-controlnet-{controlnet_id or 'generic'}"
                        for candidate_index in range(num_outputs):
                            call_kwargs = {
                                "prompt": prompt_text,
                                "negative_prompt": negative_prompt_text,
                                "image": control_image,
                                "num_inference_steps": steps,
                                "guidance_scale": guidance_scale,
                                "controlnet_conditioning_scale": controlnet_conditioning_scale,
                                "generator": torch.Generator(device=device).manual_seed(int(payload.get("seed", 42)) + candidate_index),
                            }
                            if ip_adapter_image is not None:
                                call_kwargs["ip_adapter_image"] = ip_adapter_image
                            image = pipeline(**call_kwargs).images[0]
                            candidate_images.append(
                                self._save_candidate_image(output_dir, run_id, candidate_index, image, mode, attempt_width, attempt_height)
                            )
                    elif references:
                        init_image = self._prepare_reference_image(Image.open(source_path).convert("RGB"), attempt_width, attempt_height)
                        mode = "local-model-img2img"
                        for candidate_index in range(num_outputs):
                            call_kwargs = {
                                "prompt": prompt_text,
                                "negative_prompt": negative_prompt_text,
                                "image": init_image,
                                "strength": strength,
                                "num_inference_steps": steps,
                                "guidance_scale": guidance_scale,
                                "generator": torch.Generator(device=device).manual_seed(int(payload.get("seed", 42)) + candidate_index),
                            }
                            if ip_adapter_image is not None:
                                call_kwargs["ip_adapter_image"] = ip_adapter_image
                            image = pipeline(**call_kwargs).images[0]
                            candidate_images.append(
                                self._save_candidate_image(output_dir, run_id, candidate_index, image, mode, attempt_width, attempt_height)
                            )
                    else:
                        mode = "local-model-text2img"
                        for candidate_index in range(num_outputs):
                            call_kwargs = {
                                "prompt": prompt_text,
                                "negative_prompt": negative_prompt_text,
                                "num_inference_steps": steps,
                                "guidance_scale": guidance_scale,
                                "height": attempt_height,
                                "width": attempt_width,
                                "generator": torch.Generator(device=device).manual_seed(int(payload.get("seed", 42)) + candidate_index),
                            }
                            if ip_adapter_image is not None:
                                call_kwargs["ip_adapter_image"] = ip_adapter_image
                            image = pipeline(**call_kwargs).images[0]
                            candidate_images.append(
                                self._save_candidate_image(output_dir, run_id, candidate_index, image, mode, attempt_width, attempt_height)
                            )
                    retry_records.append(
                        {
                            "attempt": attempt_index,
                            "width": attempt_width,
                            "height": attempt_height,
                            "status": "success",
                        }
                    )
                    generation_status["retry_plan"] = retry_records
                    generation_status["num_outputs_generated"] = len(candidate_images)
                    generation_status["candidate_images"] = candidate_images
                    generation_status["used_width"] = attempt_width
                    generation_status["used_height"] = attempt_height
                    generation_status["degraded_resolution"] = attempt_index > 1
                    primary_candidate = dict(candidate_images[0])
                    primary_candidate.update(
                        {
                            "model_path": str(model_path),
                            "model_id": model_id,
                            "model_repo_id": model_spec["repo_id"],
                            "controlnet_id": controlnet_id or None,
                            "controlnet_repo_id": controlnet_spec["repo_id"] if controlnet_spec is not None else None,
                            "ip_adapter_id": ip_adapter_id or None,
                            "ip_adapter_repo_id": ip_adapter_spec["repo_id"] if ip_adapter_spec is not None else None,
                            "device": device,
                            "prompt": prompt,
                            "generation_prompt": prompt_text,
                            "negative_prompt": negative_prompt_text,
                            "steps": steps,
                            "guidance_scale": guidance_scale,
                            "ip_adapter_scale": ip_adapter_scale if ip_adapter_spec is not None else None,
                            "controlnet_conditioning_scale": controlnet_conditioning_scale if controlnet_spec is not None else None,
                            "strength": strength if references else None,
                        }
                    )
                    return primary_candidate, generation_status
                except Exception as exc:
                    last_error = exc
                    candidate_images = []
                    retry_records.append(
                        {
                            "attempt": attempt_index,
                            "width": attempt_width,
                            "height": attempt_height,
                            "status": "failed",
                            "error": str(exc),
                        }
                    )
                    continue
        except Exception as exc:
            generation_status["error"] = f"로컬 생성 추론 실패: {exc}"
            return None, generation_status

        generation_status["retry_plan"] = retry_records
        generation_status["error"] = f"로컬 생성 추론 실패: {last_error}" if last_error is not None else "로컬 생성 추론 실패"
        return None, generation_status

    def _build_pipeline(
        self,
        model_path,
        torch_dtype,
        use_img2img,
        auto_img2img_cls,
        diffusion_cls,
        sd_img2img_cls,
        sd_pipeline_cls,
        controlnet_cls,
        controlnet_pipeline_cls,
        model_spec,
        controlnet_spec,
        ip_adapter_spec,
    ):
        try:
            loader_kind = str(model_spec.get("loader_kind", "directory"))
            if controlnet_spec is not None:
                controlnet_path = controlnet_spec["path"]
                if not controlnet_path.is_dir():
                    return None
                controlnet = controlnet_cls.from_pretrained(
                    str(controlnet_path),
                    torch_dtype=torch_dtype,
                    local_files_only=True,
                )
                if loader_kind == "single_file":
                    single_file_kwargs = self._single_file_kwargs(model_spec)
                    return controlnet_pipeline_cls.from_single_file(
                        str(model_path),
                        controlnet=controlnet,
                        torch_dtype=torch_dtype,
                        **single_file_kwargs,
                    )
                return controlnet_pipeline_cls.from_pretrained(
                    str(model_path),
                    controlnet=controlnet,
                    torch_dtype=torch_dtype,
                    local_files_only=True,
                )
            if loader_kind == "single_file":
                single_file_kwargs = self._single_file_kwargs(model_spec)
                if use_img2img:
                    return sd_img2img_cls.from_single_file(
                        str(model_path),
                        torch_dtype=torch_dtype,
                        **single_file_kwargs,
                    )
                return sd_pipeline_cls.from_single_file(
                    str(model_path),
                    torch_dtype=torch_dtype,
                    **single_file_kwargs,
                )
            if use_img2img:
                return auto_img2img_cls.from_pretrained(
                    str(model_path),
                    torch_dtype=torch_dtype,
                    local_files_only=True,
                )

            return diffusion_cls.from_pretrained(
                str(model_path),
                torch_dtype=torch_dtype,
                local_files_only=True,
            )
        except Exception:
            return None

    def _build_concept_metadata(self, prompt: str, style: str, references: list[dict]) -> dict:
        lowered = prompt.lower()
        if any(token in lowered for token in ["monster", "슬라임", "괴물", "몬스터"]):
            concept_type = "monster"
            shape_language = "rounded"
            color_direction = ["lime", "teal", "dark-green"]
        elif any(token in lowered for token in ["background", "배경", "맵", "stage", "environment"]):
            concept_type = "background"
            shape_language = "environmental"
            color_direction = ["prompt-driven"]
        elif any(token in lowered for token in ["item", "weapon", "아이템", "무기", "prop"]):
            concept_type = "item"
            shape_language = "prop-driven"
            color_direction = ["prompt-driven"]
        else:
            concept_type = "character"
            shape_language = "proportional"
            color_direction = ["prompt-driven"]

        return {
            "theme": style,
            "concept_type": concept_type,
            "shape_language": shape_language,
            "color_direction": color_direction,
            "visual_prompt": f"{prompt} / {style} style, game-ready concept",
            "reference_count": len(references),
            "reference_names": [x.get("name", "") for x in references][:5],
        }

    def _run_output_dir(self, context: PipelineContext, area: str) -> Path:
        return self._run_output_dir_from_root(Path(context.run_root), area)

    def _run_output_dir_from_run_id(self, payload: Payload, run_id: str, area: str) -> Path:
        run_root = Path(str(payload.get("run_root", ""))).expanduser()
        if str(run_root):
            return self._run_output_dir_from_root(run_root, area)
        return self._run_output_dir_from_root(Path(".test/ai-design/visual") / run_id, area)

    def _run_output_dir_from_root(self, run_root: Path, area: str) -> Path:
        output_dir = run_root / area
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _build_retry_plan(self, width: int, height: int) -> list[tuple[int, int]]:
        primary = (max(64, width), max(64, height))
        fallback = (
            max(64, ((primary[0] * 3) // 4 // 64) * 64 or 64),
            max(64, ((primary[1] * 3) // 4 // 64) * 64 or 64),
        )
        if fallback == primary:
            return [primary]
        return [primary, fallback]

    def _save_candidate_image(self, output_dir: Path, run_id: str, candidate_index: int, image, mode: str, width: int, height: int) -> dict:
        suffix = "" if candidate_index == 0 else f"-candidate{candidate_index + 1}"
        destination_path = output_dir / f"concept{suffix}.png"
        image.save(destination_path)
        return {
            "path": str(destination_path),
            "mode": mode,
            "candidate_index": candidate_index,
            "width": width,
            "height": height,
        }

    def _load_ip_adapter(self, pipeline, ip_adapter_spec, ip_adapter_scale: float):
        if ip_adapter_spec is None:
            return
        model_path = ip_adapter_spec["path"]
        if not model_path.is_dir():
            return
        try:
            pipeline.load_ip_adapter(
                str(model_path),
                subfolder="models",
                weight_name=str(ip_adapter_spec.get("weight_name", "ip-adapter_sd15.safetensors")),
                image_encoder_folder=str(ip_adapter_spec.get("image_encoder_folder", "models/image_encoder")),
                local_files_only=True,
            )
            pipeline.set_ip_adapter_scale(ip_adapter_scale)
        except Exception:
            return

    def _single_file_kwargs(self, model_spec):
        config_path = model_spec.get("config_path")
        kwargs = {"local_files_only": True}
        if config_path:
            kwargs["config"] = str(config_path)
        return kwargs

    def _resolve_scheduler(self, scheduler, dpm_cls):
        try:
            return dpm_cls.from_config(scheduler.config)
        except Exception:
            return scheduler

    def _build_positive_prompt(self, prompt: str, generation_prompt: str, style: str, references: list[dict]) -> str:
        if generation_prompt.strip():
            return generation_prompt.strip()

        base = [
            prompt.strip(),
            f"{style} style",
            "single full body character",
            "front-facing character concept art" if references else "character concept art",
            "clean silhouette",
            "plain background",
        ]
        return ", ".join(x for x in base if x)

    def _build_negative_prompt(self, negative_prompt: str, generation_negative_prompt: str) -> str:
        if generation_negative_prompt.strip():
            return generation_negative_prompt.strip()

        defaults = [
            "multiple panels",
            "character sheet",
            "collage",
            "extra heads",
            "extra arms",
            "extra legs",
            "duplicate character",
            "cropped body",
            "deformed face",
            "distorted hands",
            "text",
            "watermark",
            "logo",
            "blurry",
            "low quality",
        ]
        if negative_prompt.strip():
            defaults.insert(0, negative_prompt.strip())
        return ", ".join(defaults)

    def _prefer_sheet_output(self, prompt: str, generation_prompt: str) -> bool:
        combined = f"{prompt}\n{generation_prompt}".lower()
        return any(token in combined for token in ["sheet", "시트", "panel", "layout", "multiple views"])

    def _resolve_sheet_reference_image(self, payload: Payload, references: list[dict], fallback_image):
        try:
            from PIL import Image
        except Exception:
            return fallback_image

        explicit = str(payload.get("reference_sheet_image_path", "")).strip()
        candidate_paths = [explicit] if explicit else []
        candidate_paths.extend(str(item.get("path", "")).strip() for item in references)
        for raw in candidate_paths:
            if not raw:
                continue
            path = Path(raw)
            if path.is_file():
                try:
                    return Image.open(path).convert("RGB")
                except Exception:
                    continue
        return fallback_image

    def _resolve_sheet_face_image(self, payload: Payload, references: list[dict], fallback_image):
        try:
            from PIL import Image
        except Exception:
            return fallback_image

        explicit = str(payload.get("ip_adapter_image_path", "")).strip()
        if explicit:
            path = Path(explicit)
            if path.is_file():
                try:
                    return Image.open(path).convert("RGB")
                except Exception:
                    pass
        reference_source = self._resolve_sheet_reference_image(payload, references, fallback_image)
        return self._crop_relative(reference_source, (0.22, 0.02, 0.78, 0.28))

    def _draw_panel(self, draw, box, title: str, font) -> None:
        left, top, right, bottom = box
        draw.text((left, top - 34), title, fill=(35, 35, 35), font=font)
        draw.rectangle((left, top, right, bottom), outline=(90, 90, 90), width=2)

    def _paste_centered(self, canvas, image, layout_box) -> None:
        left, top, width, height = layout_box
        fitted = self._fit_box(image.size, width, height)
        resized = image.resize(fitted)
        x = left + (width - fitted[0]) // 2
        y = top + (height - fitted[1]) // 2
        canvas.paste(resized, (x, y))

    def _fit_box(self, image_size, max_width: int, max_height: int) -> tuple[int, int]:
        width, height = image_size
        if width <= 0 or height <= 0:
            return (max_width, max_height)
        scale = min(max_width / width, max_height / height)
        return (max(1, int(width * scale)), max(1, int(height * scale)))

    def _crop_relative(self, image, box_ratio):
        width, height = image.size
        left = int(width * box_ratio[0])
        top = int(height * box_ratio[1])
        right = int(width * box_ratio[2])
        bottom = int(height * box_ratio[3])
        return image.crop((left, top, right, bottom))

    def _sample_palette(self, image) -> list[tuple[int, int, int]]:
        width, height = image.size
        points = [
            (int(width * 0.50), int(height * 0.07)),
            (int(width * 0.50), int(height * 0.20)),
            (int(width * 0.45), int(height * 0.32)),
            (int(width * 0.46), int(height * 0.57)),
            (int(width * 0.40), int(height * 0.88)),
        ]
        return [image.getpixel(point) for point in points]

    def _load_font(self, size: int):
        try:
            from PIL import ImageFont
        except Exception:
            return None

        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        ]
        for path in candidates:
            font_path = Path(path)
            if not font_path.is_file():
                continue
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _sanitize_text(self, text: str, max_length: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 1] + "..."

    def _prepare_reference_image(self, image, width: int, height: int):
        from PIL import Image as PILImage
        from PIL import ImageOps

        resampling = getattr(PILImage, "Resampling", None)
        method = resampling.LANCZOS if resampling is not None else PILImage.LANCZOS
        background = self._estimate_background_color(image)
        focused = self._focus_single_character(image, background)
        return ImageOps.pad(
            focused,
            (width, height),
            method=method,
            color=background,
            centering=(0.5, 0.5),
        )

    def _prepare_control_image(self, image, width: int, height: int, controlnet_spec: dict | None):
        from PIL import Image as PILImage
        from PIL import ImageOps

        background = self._estimate_background_color(image)
        focused = self._focus_single_character(image, background)
        resampling = getattr(PILImage, "Resampling", None)
        method = resampling.LANCZOS if resampling is not None else PILImage.LANCZOS
        prepared = ImageOps.pad(
            focused,
            (width, height),
            method=method,
            color=background,
            centering=(0.5, 0.5),
        )
        controlnet_repo_id = str((controlnet_spec or {}).get("repo_id", "")).strip().lower()
        if "lineart_anime" in controlnet_repo_id:
            detector = _lineart_anime_detector()
            if detector is None:
                return prepared
            try:
                return detector(prepared)
            except Exception:
                return prepared

        detector = _openpose_detector()
        if detector is None:
            return prepared
        try:
            return detector(prepared, hand_and_face=False)
        except Exception:
            return prepared

    def _resolve_reference_paths(self, references: list[dict]) -> list[Path]:
        resolved: list[Path] = []
        for item in references:
            raw = str(item.get("path", "")).strip()
            if not raw:
                continue
            path = Path(raw)
            if path.is_file():
                resolved.append(path)
        return resolved

    def _resolve_control_image_path(self, payload: Payload, references: list[dict]) -> Path | None:
        explicit = str(payload.get("control_image_path", "")).strip()
        if explicit:
            path = Path(explicit)
            return path if path.is_file() else None
        reference_paths = self._resolve_reference_paths(references)
        if not reference_paths:
            return None
        return reference_paths[0]

    def _resolve_ip_adapter_image(self, payload: Payload, reference_paths: list[Path], width: int, height: int):
        if not payload.get("ip_adapter_id"):
            return None, None
        explicit = str(payload.get("ip_adapter_image_path", "")).strip()
        face_mode = "face" in str(payload.get("ip_adapter_id", "")).strip().lower()
        if explicit:
            source_path = Path(explicit)
            if not source_path.is_file():
                return None, None
        else:
            if not reference_paths:
                return None, None
            source_path = reference_paths[1] if len(reference_paths) > 1 else reference_paths[0]
        if source_path is None:
            return None, None
        try:
            from PIL import Image
        except Exception:
            return None, None
        source = Image.open(source_path).convert("RGB")
        if face_mode:
            source = self._crop_relative(source, (0.22, 0.02, 0.78, 0.28))
            side = max(256, min(width, height))
            return self._prepare_reference_image(source, side, side), source_path
        return self._prepare_reference_image(source, width, height), source_path

    def _focus_single_character(self, image, background):
        from PIL import ImageChops
        from PIL import Image as PILImage

        width, height = image.size
        band_left = int(width * 0.28)
        band_right = int(width * 0.72)
        band_top = int(height * 0.05)
        band_bottom = int(height * 0.995)
        band = image.crop((band_left, band_top, band_right, band_bottom)).convert("RGB")
        background_image = PILImage.new("RGB", band.size, background)
        diff = ImageChops.difference(band, background_image).convert("L")
        mask = diff.point(lambda value: 255 if value > 14 else 0)
        bbox = mask.getbbox()
        if bbox is None:
            return image.crop((band_left, band_top, band_right, band_bottom))

        left, top, right, bottom = bbox
        left += band_left
        right += band_left
        top += band_top
        bottom += band_top

        margin_x = max(24, int((right - left) * 0.12))
        margin_top = max(32, int((bottom - top) * 0.06))
        margin_bottom = max(36, int((bottom - top) * 0.03))
        crop_left = max(0, left - margin_x)
        crop_right = min(width, right + margin_x)
        crop_top = max(0, top - margin_top)
        crop_bottom = min(height, bottom + margin_bottom)
        return image.crop((crop_left, crop_top, crop_right, crop_bottom))

    def _estimate_background_color(self, image):
        rgb = image.convert("RGB")
        width, height = rgb.size
        sample_points = [
            rgb.getpixel((4, 4)),
            rgb.getpixel((width - 5, 4)),
            rgb.getpixel((4, height - 5)),
            rgb.getpixel((width - 5, height - 5)),
        ]
        channels = list(zip(*sample_points))
        return tuple(sum(channel) // len(channel) for channel in channels)


@lru_cache(maxsize=1)
def _default_concept_model_spec() -> dict[str, str | Path]:
    try:
        storage = json.loads(MODEL_STORAGE_CONFIG_PATH.read_text(encoding="utf-8"))
        registry = json.loads(MODEL_REGISTRY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "path": Path(".model/base/stable-diffusion-v1-5"),
            "repo_id": "stable-diffusion-v1-5/stable-diffusion-v1-5",
            "loader_kind": "directory",
        }

    models_root = str(storage.get("models_root_default", "")).strip() or ".model"
    base_dir = str(storage.get("paths", {}).get("base_models", "base")).strip() or "base"
    first_model = (registry.get("models") or [{}])[0]
    file_name = str(first_model.get("artifact", {}).get("file_name", "")).strip() or "stable-diffusion-v1-5"
    repo_id = str(first_model.get("distribution", {}).get("repo_id", "")).strip() or "stable-diffusion-v1-5/stable-diffusion-v1-5"
    return {
        "path": Path(models_root) / base_dir / file_name,
        "repo_id": repo_id,
        "loader_kind": "directory",
    }


@lru_cache(maxsize=16)
def _concept_model_spec(model_id: str) -> dict[str, str | Path]:
    fallback = _default_concept_model_spec()
    try:
        storage = json.loads(MODEL_STORAGE_CONFIG_PATH.read_text(encoding="utf-8"))
        registry = json.loads(MODEL_REGISTRY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return fallback

    models_root = str(storage.get("models_root_default", "")).strip() or ".model"
    path_map = storage.get("paths", {})
    for item in registry.get("models") or []:
        if str(item.get("id", "")).strip() != model_id:
            continue
        path_key = str(item.get("storage", {}).get("path_key", "")).strip() or "base_models"
        rel_dir = str(path_map.get(path_key, "base")).strip() or "base"
        file_name = str(item.get("artifact", {}).get("file_name", "")).strip()
        repo_id = str(item.get("distribution", {}).get("repo_id", "")).strip()
        if not file_name or not repo_id:
            return fallback
        loader = item.get("loader", {}) or {}
        loader_kind = str(loader.get("kind", "directory")).strip() or "directory"
        if loader_kind == "single_file":
            entry_file = str(loader.get("entry_file", "")).strip()
            if not entry_file:
                return fallback
            config_model_id = str(loader.get("config_model_id", "")).strip()
            config_path = None
            if config_model_id:
                config_spec = _concept_model_spec(config_model_id)
                config_path = config_spec.get("path")
            return {
                "path": Path(models_root) / rel_dir / file_name / entry_file,
                "repo_id": repo_id,
                "loader_kind": "single_file",
                "config_path": config_path or fallback["path"],
            }
        return {
            "path": Path(models_root) / rel_dir / file_name,
            "repo_id": repo_id,
            "loader_kind": "directory",
        }

    return fallback


@lru_cache(maxsize=16)
def _control_model_spec(model_id: str) -> dict[str, str | Path] | None:
    if not model_id:
        return None

    try:
        storage = json.loads(MODEL_STORAGE_CONFIG_PATH.read_text(encoding="utf-8"))
        registry = json.loads(MODEL_REGISTRY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    models_root = str(storage.get("models_root_default", "")).strip() or ".model"
    path_map = storage.get("paths", {})
    for item in registry.get("models") or []:
        if str(item.get("id", "")).strip() != model_id:
            continue
        path_key = str(item.get("storage", {}).get("path_key", "")).strip()
        rel_dir = str(path_map.get(path_key, "")).strip()
        file_name = str(item.get("artifact", {}).get("file_name", "")).strip()
        repo_id = str(item.get("distribution", {}).get("repo_id", "")).strip()
        if not path_key or not rel_dir or not file_name or not repo_id:
            return None
        return {
            "path": Path(models_root) / rel_dir / file_name,
            "repo_id": repo_id,
        }

    return None


@lru_cache(maxsize=16)
def _adapter_model_spec(model_id: str) -> dict[str, str | Path] | None:
    if not model_id:
        return None

    try:
        storage = json.loads(MODEL_STORAGE_CONFIG_PATH.read_text(encoding="utf-8"))
        registry = json.loads(MODEL_REGISTRY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    models_root = str(storage.get("models_root_default", "")).strip() or ".model"
    path_map = storage.get("paths", {})
    for item in registry.get("models") or []:
        if str(item.get("id", "")).strip() != model_id:
            continue
        path_key = str(item.get("storage", {}).get("path_key", "")).strip()
        rel_dir = str(path_map.get(path_key, "")).strip()
        file_name = str(item.get("artifact", {}).get("file_name", "")).strip()
        repo_id = str(item.get("distribution", {}).get("repo_id", "")).strip()
        adapter = item.get("adapter", {}) or {}
        if not path_key or not rel_dir or not file_name or not repo_id:
            return None
        return {
            "path": Path(models_root) / rel_dir / file_name,
            "repo_id": repo_id,
            "weight_name": str(adapter.get("weight_name", "ip-adapter_sd15.safetensors")).strip() or "ip-adapter_sd15.safetensors",
            "image_encoder_folder": str(adapter.get("image_encoder_folder", "models/image_encoder")).strip() or "models/image_encoder",
        }

    return None


@lru_cache(maxsize=1)
def _openpose_detector():
    try:
        from controlnet_aux import OpenposeDetector
    except Exception:
        return None

    try:
        return OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
    except Exception:
        return None


@lru_cache(maxsize=1)
def _lineart_anime_detector():
    try:
        from controlnet_aux import LineartAnimeDetector
    except Exception:
        return None

    try:
        return LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")
    except Exception:
        return None
