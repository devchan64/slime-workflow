"""완료된 FLUX 시도의 PNG와 요청을 검사해 Hermes 입력 근거를 만든다."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

RULE_VERSION = 2


def inspect_flux_output(directory: Path, service: str) -> dict:
    request_path = directory / "request.json"
    if request_path.is_symlink() or directory.is_symlink():
        raise ValueError("FLUX 작업 경로를 확인하세요.")
    request = json.loads(request_path.read_text())
    pointer = directory / "queue-telemetry.json"
    attempt = json.loads(pointer.read_text()).get("attempt_id") if pointer.is_file() and not pointer.is_symlink() else None
    evidence = {
        "attempt_id": attempt,
        "service": service,
        "job_id": directory.name,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "rule_version": RULE_VERSION,
        "generation_prompt": request.get("prompt"),
        "user_prompt": request.get("user_prompt"),
        "settings": {key: request[key] for key in ("width", "height", "steps", "seed", "flux_model_revision") if key in request},
        "checks": {"visual_quality": "unknown"},
    }
    path = directory / "result.png"
    checks = evidence["checks"]
    if path.is_symlink() or not path.is_file():
        checks["output_file"] = "fail"
        return evidence
    checks["output_file"] = "pass"
    evidence["result_url"] = f"/{service}-generator/jobs/{directory.name}/result.png"
    with path.open("rb") as stream:
        evidence["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        stream.seek(0)
        try:
            with Image.open(stream, formats=["PNG"]) as image:
                image.load()
                evidence["size"] = list(image.size)
        except (OSError, ValueError, Image.DecompressionBombError):
            checks["png_decode"] = "fail"
            return evidence
    checks["png_decode"] = "pass"
    metadata_path = directory / "result.json"
    try:
        metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() and not metadata_path.is_symlink() else {}
    except (OSError, ValueError):
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    expected_hash = metadata.get("image_sha256")
    checks["recorded_sha256"] = ("pass" if evidence["sha256"] == expected_hash else "fail") if expected_hash else "unknown"
    evidence["actual_settings"] = {key:metadata[key] for key in ("width", "height", "steps", "seed", "model_revision") if key in metadata}
    expected = [request.get("width"), request.get("height")]
    checks["dimensions"] = ("pass" if expected == evidence["size"] else "fail") if all(type(n) is int for n in expected) else "unknown"
    return evidence
