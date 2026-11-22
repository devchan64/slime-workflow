"""Check the first experiment's recorded hashes and geometry without modifying it."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(job, masks):
    record = json.loads((job / "result.json").read_text())
    manifest = masks / "manifest.json"
    if sha256(manifest) != record["input_manifest_sha256"]:
        raise ValueError("입력 매니페스트 해시가 기록과 다릅니다")
    views = json.loads(manifest.read_text())["views"]
    if len(views) != record["views"]:
        raise ValueError("참조 이미지 수가 기록과 다릅니다")
    for view in views:
        if sha256(masks / view["file"]) != view["sha256"]:
            raise ValueError(f"참조 해시 불일치: {view['file']}")
    mesh_path = job / "mesh.ply"
    if sha256(mesh_path) != record["mesh_sha256"]:
        raise ValueError("메시 해시가 기록과 다릅니다")
    mesh = trimesh.load(mesh_path, force="mesh", process=False)
    if len(mesh.vertices) != record["vertices"] or len(mesh.faces) != record["faces"]:
        raise ValueError("메시 크기가 기록과 다릅니다")
    if not np.isfinite(mesh.vertices).all() or mesh.faces.min() < 0 or mesh.faces.max() >= len(mesh.vertices):
        raise ValueError("메시에 비유한 정점 또는 잘못된 면이 있습니다")
    rig_input = trimesh.load(job / "unirig-input.glb", force="mesh", process=False)
    if not np.array_equal(mesh.vertices, rig_input.vertices) or not np.array_equal(mesh.faces, rig_input.faces):
        raise ValueError("GLB가 원본 메시와 다릅니다")
    print(json.dumps({"views": len(views), "mesh_sha256": record["mesh_sha256"],
                      "vertices": len(mesh.vertices), "faces": len(mesh.faces),
                      "glb_roundtrip_equal": True,
                      "scope": "integrity and finite geometry only; no quality or license approval"}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_result.py JOB_DIR MASK_DIR")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
