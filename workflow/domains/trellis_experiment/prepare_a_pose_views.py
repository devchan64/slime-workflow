"""Prepare unmasked, provenance-recorded cells from the adopted 8-view sheet."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


EXPECTED_SHA256 = "caa5ff38eaa7877f5ff594247f4a8f40e48c67dd3292d4a701d9536daaefbd81"
LABELS = ("front", "front_right", "right", "back_right", "back", "back_left_uncertain", "left", "front_left")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, output):
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("참조 이미지 해시가 기준 기록과 다릅니다")
    if output.exists():
        raise FileExistsError("기존 출력 디렉터리를 덮어쓰지 않습니다")
    with Image.open(source) as img:
        if img.size != (1536, 1024):
            raise ValueError("참조 이미지 크기가 1536×1024가 아닙니다")
        output.mkdir(parents=True)
        views = []
        for index, label in enumerate(LABELS):
            x, y = (index % 4) * 384, (index // 4) * 512
            # This sheet has no cell divider.
            box = (x, y, x + 384, y + 512)
            path = output / f"{index + 1:02d}_{label}.png"
            img.crop(box).convert("RGB").save(path)
            views.append({"file": path.name, "sha256": sha256(path), "crop_xyxy": box,
                          "label": label, "direction_verified": False})
    manifest = {"schema": "trellis-reference-views-v1", "source": str(source.resolve()),
                "source_sha256": EXPECTED_SHA256, "background": "white; not masked",
                "note": "labels are intended order, not verified camera directions; view orientation and pose consistency remain unverified",
                "views": views}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
