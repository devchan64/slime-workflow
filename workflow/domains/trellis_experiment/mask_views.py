"""Make provisional alpha masks by removing near-white, border-connected pixels."""
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image


def main(source: Path, output: Path):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    results = []
    for view in manifest["views"]:
        path = source / view["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != view["sha256"]:
            raise ValueError(f"입력 해시 불일치: {path}")
        rgb = np.asarray(Image.open(path).convert("RGB"))
        # Only near-white pixels connected to an image edge are background.
        candidate = (rgb.min(axis=2) >= 245).astype(np.uint8)
        _, labels = cv2.connectedComponents(candidate, connectivity=8)
        edge = np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
        background = np.isin(labels, np.unique(edge[edge > 0]))
        alpha = np.where(background, 0, 255).astype(np.uint8)
        if not background.any() or not (alpha > 0).any():
            raise ValueError(f"마스크가 비어 있거나 배경을 찾지 못함: {path}")
        dest = output / path.name
        Image.fromarray(np.dstack((rgb, alpha)), "RGBA").save(dest)
        results.append({"file": dest.name, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                        "source_sha256": view["sha256"], "background_pixels": int(background.sum())})
    (output / "manifest.json").write_text(json.dumps({"method": "border-connected RGB >= 245; binary alpha",
        "limitations": "provisional; may retain halos or remove light details touching background", "views": results}, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: mask_views.py INPUT_DIR OUTPUT_DIR")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
