"""사람형 재생성 리그 에셋의 출처와 파일 해시를 검증한다."""
from pathlib import Path
import hashlib
import json

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = WORKFLOW_ROOT / "assets/rigs/humanlike-walk/v1"


def validate_humanlike_rig_asset():
    manifest_path = ASSET_ROOT / "artifact.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for file_name, expected_hash in manifest["files"].items():
        file_path = ASSET_ROOT / file_name
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"사람형 리그 에셋 해시 불일치: {file_path}")
    if manifest["source_rig"] != "mannequin-walk/v1":
        raise ValueError("사람형 리그 출처 리그 불일치")
    return ASSET_ROOT


if __name__ == "__main__":
    print(validate_humanlike_rig_asset())
