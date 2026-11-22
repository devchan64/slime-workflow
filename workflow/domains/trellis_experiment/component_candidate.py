"""Produce a non-destructive largest-component candidate for rigging assessment."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh


def main(source, output):
    if output.exists():
        raise FileExistsError(output)
    mesh = trimesh.load(source, process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not np.isfinite(mesh.vertices).all():
        raise ValueError("유효한 메시가 아닙니다")
    parts = sorted(mesh.split(only_watertight=False), key=lambda part: len(part.faces), reverse=True)
    if not parts or not len(parts[0].faces):
        raise ValueError("연결 성분이 없습니다")
    output.mkdir(parents=True)
    target = output / "largest-component.glb"
    parts[0].export(target)
    check = trimesh.load(target, force="mesh", process=False)
    if len(check.faces) != len(parts[0].faces) or len(check.vertices) != len(parts[0].vertices):
        raise ValueError("GLB 왕복 시 정점이나 면 수가 달라졌습니다")
    summary = {"source": str(source.resolve()), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
               "source_components": len(parts), "source_faces": len(mesh.faces),
               "retained_faces": len(parts[0].faces), "removed_faces": len(mesh.faces)-len(parts[0].faces),
               "warning": "Largest component is an experiment, not proof other components are debris or that rigging will work."}
    (output / "report.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: component_candidate.py INPUT.ply NEW_OUTPUT_DIR")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
