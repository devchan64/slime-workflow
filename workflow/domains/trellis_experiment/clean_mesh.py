"""Conservatively remove small disconnected mesh components and validate the result."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial import cKDTree
import trimesh


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def silhouettes(mesh, center, scale, size=256):
    vertices = np.asarray(mesh.vertices) - center
    faces = np.asarray(mesh.faces)
    result = []
    for index in range(8):
        angle = index * np.pi / 4
        horizontal = vertices[:, 0] * np.cos(angle) + vertices[:, 1] * np.sin(angle)
        points = np.column_stack((horizontal, -vertices[:, 2]))
        points = np.rint(points * scale + size / 2).astype(np.int32)
        mask = np.zeros((size, size), dtype=np.uint8)
        for face in faces:
            cv2.fillConvexPoly(mask, points[face], 1)
        result.append(mask)
    return result


def clean(source, output, max_component_area=0.001, max_component_faces=0.001,
          min_distance=0.002, max_area_loss=0.03, max_silhouette_loss=0.02,
          max_extent_change=0.03):
    if output.exists():
        raise FileExistsError(output)
    mesh = trimesh.load(source, process=False)
    if (not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces)
            or not np.isfinite(mesh.vertices).all() or not np.isfinite(mesh.area)
            or mesh.area <= 0):
        raise ValueError('Input must be a finite, nonempty mesh with positive area')
    parts = sorted(mesh.split(only_watertight=False), key=lambda p: p.area, reverse=True)
    diagonal = float(np.linalg.norm(mesh.extents))
    if diagonal <= 0:
        raise ValueError('Mesh has zero extent')
    tree = cKDTree(np.asarray(parts[0].vertices))
    kept, removed, records = [parts[0]], [], []
    for part in parts[1:]:
        distance = float(tree.query(np.asarray(part.vertices), k=1, workers=1)[0].min()) / diagonal
        area_fraction = float(part.area / mesh.area)
        face_fraction = len(part.faces) / len(mesh.faces)
        discard = area_fraction <= max_component_area and face_fraction <= max_component_faces and distance >= min_distance
        (removed if discard else kept).append(part)
        records.append({'faces': len(part.faces), 'area_fraction': area_fraction,
                        'distance_fraction': distance, 'removed': discard})
    candidate = trimesh.util.concatenate(kept)
    center = (mesh.bounds[0] + mesh.bounds[1]) / 2
    scale = 220 / max(mesh.extents)
    before, after = silhouettes(mesh, center, scale), silhouettes(candidate, center, scale)
    losses = [float(np.count_nonzero((a != 0) & (b == 0)) / max(1, np.count_nonzero(a))) for a, b in zip(before, after)]
    area_loss = max(0.0, float((mesh.area - candidate.area) / mesh.area))
    extent_change = float(np.max(np.abs(candidate.extents - mesh.extents)) / diagonal)
    checks = {'area': area_loss <= max_area_loss, 'silhouette': max(losses) <= max_silhouette_loss,
              'extent': extent_change <= max_extent_change}
    output.mkdir(parents=True)
    target = output / 'candidate.glb'
    candidate.export(target)
    reloaded = trimesh.load(target, force='mesh', process=False)
    checks['roundtrip'] = (len(reloaded.faces) == len(candidate.faces) and len(reloaded.vertices) == len(candidate.vertices)
                           and np.isfinite(reloaded.vertices).all()
                           and np.allclose(reloaded.vertices, candidate.vertices, rtol=1e-6, atol=1e-7)
                           and np.array_equal(reloaded.faces, candidate.faces))
    report = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
              'source': str(source.resolve()), 'source_sha256': digest(source), 'candidate_sha256': digest(target),
              'source_components': len(parts), 'removed_components': len(removed), 'retained_components': len(kept),
              'source_faces': len(mesh.faces), 'candidate_faces': len(candidate.faces),
              'area_loss': area_loss, 'silhouette_loss_by_view': losses, 'extent_change': extent_change,
              'thresholds': {'max_component_area': max_component_area, 'max_component_faces': max_component_faces,
                             'min_distance': min_distance, 'max_area_loss': max_area_loss,
                             'max_silhouette_loss': max_silhouette_loss, 'max_extent_change': max_extent_change},
              'components': records,
              'limitations': 'Geometric checks do not establish semantic correctness, rigging quality or reference-image fidelity.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='new output directory')
    parser.add_argument('--max-component-area', type=float, default=0.001)
    parser.add_argument('--max-component-faces', type=float, default=0.001)
    parser.add_argument('--min-distance', type=float, default=0.002)
    parser.add_argument('--max-area-loss', type=float, default=0.03)
    parser.add_argument('--max-silhouette-loss', type=float, default=0.02)
    parser.add_argument('--max-extent-change', type=float, default=0.03)
    args = parser.parse_args()
    options = vars(args).copy()
    source, output = options.pop('source'), options.pop('output')
    if any(not np.isfinite(v) or not 0 <= v <= 1 for v in options.values()):
        parser.error('thresholds must be finite numbers between 0 and 1')
    report = clean(source, output, **options)
    print(json.dumps({k: report[k] for k in ('status', 'checks', 'source_components', 'removed_components', 'area_loss', 'silhouette_loss_by_view', 'extent_change')}, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
