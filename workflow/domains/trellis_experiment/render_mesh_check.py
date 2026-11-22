"""Render a raw mesh from eight unlabeled azimuths for geometric review."""
import sys
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image


def main(source, output):
    mesh = trimesh.load(source, process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not np.isfinite(mesh.vertices).all():
        raise ValueError("유효한 메시가 아닙니다")
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    vertices = vertices - (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    extent = np.ptp(vertices, axis=0).max()
    if extent <= 0:
        raise ValueError("메시 크기가 0입니다")
    normals = np.asarray(mesh.face_normals)
    panels = []
    for index in range(8):
        angle = index * np.pi / 4
        right = np.array([np.cos(angle), np.sin(angle), 0.0])
        depth = np.array([-np.sin(angle), np.cos(angle), 0.0])
        projected = np.stack((vertices @ right, vertices[:, 2]), axis=1)
        pixels = np.rint(projected * (440 / extent) + [256, 256]).astype(np.int32)
        pixels[:, 1] = 512 - pixels[:, 1]
        face_depth = (vertices @ depth)[faces].mean(axis=1)
        shade = np.clip(0.3 + 0.7 * np.abs(normals @ np.array([0.4, -0.6, 0.69])), 0, 1)
        image = np.full((512, 512, 3), 240, dtype=np.uint8)
        for face_id in np.argsort(face_depth):
            color = int(45 + shade[face_id] * 175)
            cv2.fillConvexPoly(image, pixels[faces[face_id]], (color, color, color), lineType=cv2.LINE_8)
        cv2.putText(image, f"view {index+1}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
        panels.append(image)
    montage = np.concatenate([np.concatenate(panels[:4], axis=1), np.concatenate(panels[4:], axis=1)], axis=0)
    Image.fromarray(montage).save(output)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: render_mesh_check.py INPUT.ply OUTPUT.png")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
