"""workflow 모델 레지스트리 동기화 실행기."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelPlan:
    """모델 동기화 계획."""

    model_id: str
    name: str
    version: str
    progress_level: str
    kind: str
    url: str
    repo_id: str
    revision: str
    allow_patterns: list[str]
    size_bytes: int
    sha256: str
    target_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="workflow 모델 레지스트리 동기화")
    parser.add_argument("--registry", required=True, help="모델 레지스트리 JSON 경로")
    parser.add_argument("--storage-config", required=True, help="모델 저장 경로 정책 JSON 경로")
    parser.add_argument("--models-root", default="", help="모델 루트 경로 override")
    parser.add_argument("--only-id", default="", help="지정 모델만 처리")
    parser.add_argument("--force", action="store_true", help="기존 모델을 무시하고 다시 준비")
    parser.add_argument("--dry-run", action="store_true", help="다운로드 없이 계획만 검증")
    return parser.parse_args()


def log(level: str, message: str) -> None:
    from datetime import datetime

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ai-workflow] [model-registry-sync] [{level}] {message}", flush=True)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"파일이 없다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_plans(registry: dict[str, Any], storage: dict[str, Any], *, models_root_override: str, only_id: str) -> tuple[Path, list[ModelPlan]]:
    models_root = Path(models_root_override or str(storage.get("models_root_default", "")).strip() or ".model")
    path_map = storage.get("paths", {})
    if not isinstance(path_map, dict) or not path_map:
        raise RuntimeError("저장 경로 정책 paths가 비어 있다")

    models = registry.get("models", [])
    if not isinstance(models, list) or not models:
        raise RuntimeError("레지스트리 models 항목이 비어 있다")

    plans: list[ModelPlan] = []
    for model in models:
        model_id = str(model.get("id", "")).strip()
        if only_id and model_id != only_id:
            continue
        distribution = model.get("distribution", {})
        artifact = model.get("artifact", {})
        lifecycle = model.get("lifecycle", {})
        storage_spec = model.get("storage", {})

        path_key = str(storage_spec.get("path_key", "")).strip()
        if path_key not in path_map:
            raise RuntimeError(f"정의되지 않은 path_key다: model={model_id}, path_key={path_key}")

        kind = str(distribution.get("kind", "http_file")).strip() or "http_file"
        allow_patterns = distribution.get("allow_patterns", [])
        if allow_patterns and not isinstance(allow_patterns, list):
            raise RuntimeError(f"allow_patterns는 배열이어야 한다: model={model_id}")

        file_name = str(artifact.get("file_name", "")).strip()
        repo_id = str(distribution.get("repo_id", "")).strip()
        url = str(distribution.get("url", "")).strip()
        if not model_id or not file_name:
            raise RuntimeError(f"모델 필수값이 없다: id={model_id or 'unknown'}")
        if kind == "huggingface_snapshot" and not repo_id:
            raise RuntimeError(f"huggingface_snapshot repo_id가 없다: model={model_id}")
        if kind == "http_file" and not url:
            raise RuntimeError(f"http_file url이 없다: model={model_id}")

        plans.append(
            ModelPlan(
                model_id=model_id,
                name=str(model.get("name", "")).strip(),
                version=str(model.get("version", "")).strip(),
                progress_level=str(lifecycle.get("progress_level", "")).strip(),
                kind=kind,
                url=url,
                repo_id=repo_id,
                revision=str(distribution.get("revision", "")).strip(),
                allow_patterns=[str(item).strip() for item in allow_patterns if str(item).strip()],
                size_bytes=int(artifact.get("size_bytes", 0) or 0),
                sha256=str(artifact.get("sha256", "-")).strip() or "-",
                target_path=models_root / str(path_map[path_key]).strip() / file_name,
            )
        )

    if only_id and not plans:
        raise RuntimeError(f"레지스트리에서 지정한 모델을 찾지 못했다: {only_id}")
    return models_root, plans


def sync_huggingface_snapshot(plan: ModelPlan) -> None:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        raise RuntimeError(f"huggingface_hub 의존성이 없다: {exc}") from exc

    if plan.target_path.exists():
        shutil.rmtree(plan.target_path)
    snapshot_download(
        repo_id=plan.repo_id,
        revision=plan.revision or None,
        local_dir=str(plan.target_path),
        local_dir_use_symlinks=False,
        allow_patterns=plan.allow_patterns or None,
    )


def sync_http_file(plan: ModelPlan) -> None:
    plan.target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = plan.target_path.with_suffix(plan.target_path.suffix + ".part")
    if tmp_path.exists():
        tmp_path.unlink()
    with urllib.request.urlopen(plan.url, timeout=30) as response:
        tmp_path.write_bytes(response.read())
    actual_size = tmp_path.stat().st_size
    if plan.size_bytes and actual_size != plan.size_bytes:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"용량 불일치: model={plan.model_id}, expected={plan.size_bytes}, actual={actual_size}")
    tmp_path.replace(plan.target_path)


def write_state(models_root: Path, records: list[dict[str, Any]]) -> None:
    models_root.mkdir(parents=True, exist_ok=True)
    state_path = models_root / "registry-state.json"
    state_path.write_text(json.dumps({"models": records}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    registry = load_json(Path(args.registry))
    storage = load_json(Path(args.storage_config))
    models_root, plans = build_plans(registry, storage, models_root_override=args.models_root, only_id=args.only_id)
    records: list[dict[str, Any]] = []
    downloaded = 0
    skipped = 0

    log("INFO", f"동기화 시작: registry={args.registry}, storage={args.storage_config}, models_root={models_root}, only_id={args.only_id or 'all'}, dry_run={str(args.dry_run).lower()}, force={str(args.force).lower()}")
    for plan in plans:
        log("INFO", f"모델 확인: id={plan.model_id}, version={plan.version}, progress={plan.progress_level}, kind={plan.kind}, target={plan.target_path}")
        if plan.target_path.exists() and not args.force:
            skipped += 1
            log("INFO", f"기존 파일 유지: id={plan.model_id}")
            records.append({"id": plan.model_id, "version": plan.version, "progress_level": plan.progress_level, "status": "skipped", "path": str(plan.target_path)})
            continue
        if args.dry_run:
            records.append({"id": plan.model_id, "version": plan.version, "progress_level": plan.progress_level, "status": "planned", "path": str(plan.target_path)})
            log("INFO", f"DRY-RUN 준비 예정: id={plan.model_id}")
            continue
        if plan.kind == "huggingface_snapshot":
            sync_huggingface_snapshot(plan)
        elif plan.kind == "http_file":
            sync_http_file(plan)
        else:
            raise RuntimeError(f"지원하지 않는 모델 배포 방식이다: model={plan.model_id}, kind={plan.kind}")
        downloaded += 1
        records.append({"id": plan.model_id, "version": plan.version, "progress_level": plan.progress_level, "status": "downloaded", "path": str(plan.target_path)})
        log("INFO", f"다운로드 완료: id={plan.model_id}")

    write_state(models_root, records)
    log("INFO", f"요약: planned={len(plans)}, downloaded={downloaded}, skipped={skipped}, failed=0, state={models_root / 'registry-state.json'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log("ERROR", str(exc))
        sys.exit(1)
