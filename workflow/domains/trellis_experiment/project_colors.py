"""Project eight approximate orthographic reference views onto mesh vertex colors."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import trimesh


def main(source, reference_dir, output):
    if output.exists():
        raise FileExistsError(output)
    paths = sorted(reference_dir.glob('[0-9][0-9]_*.png'))
    if len(paths) != 8:
        raise ValueError('Exactly eight numbered PNG reference images are required')
    mesh = trimesh.load(source, force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('Invalid mesh')
    vertices = np.asarray(mesh.vertices)
    normals = np.asarray(mesh.vertex_normals)
    extent = float(np.linalg.norm(mesh.extents))
    if extent <= 0 or not np.isfinite(normals).all():
        raise ValueError('Invalid extent or normals')
    colors = np.zeros((len(vertices), 3), dtype=np.float64)
    weights = np.zeros(len(vertices), dtype=np.float64)
    observations = []
    for index, path in enumerate(paths):
        rgba = np.asarray(Image.open(path).convert('RGBA'))
        # Exclude background, including the white holes left by the provisional mask.
        foreground = (rgba[:, :, 3] > 240) & (np.min(rgba[:, :, :3], axis=2) < 245)
        ys, xs = np.nonzero(foreground)
        if len(xs) < 100:
            raise ValueError(f'Empty reference: {path}')
        angle = index * np.pi / 4
        right = np.array([np.cos(angle), np.sin(angle), 0.0])
        toward = np.array([-np.sin(angle), np.cos(angle), 0.0])
        horizontal = vertices @ right
        vertical = vertices[:, 2]
        # Independent silhouette bounding boxes give only an approximate camera fit.
        if np.ptp(horizontal) <= 0 or np.ptp(vertical) <= 0:
            raise ValueError('Degenerate projection')
        u = np.rint(xs.min() + (horizontal - horizontal.min()) / np.ptp(horizontal) * (xs.max() - xs.min())).astype(int)
        v = np.rint(ys.max() - (vertical - vertical.min()) / np.ptp(vertical) * (ys.max() - ys.min())).astype(int)
        depth = vertices @ toward
        h, w = foreground.shape
        depth_buffer = np.full(h * w, -np.inf)
        np.maximum.at(depth_buffer, v * w + u, depth)
        visible = depth >= depth_buffer[v * w + u] - 0.02 * extent
        facing = np.maximum(normals @ toward, 0.0)
        weight = facing ** 2 * foreground[v, u] * visible
        colors += rgba[v, u, :3] * weight[:, None]
        weights += weight
        observations.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'sampled_vertices': int(np.count_nonzero(weight))})
    valid = weights > 1e-8
    if not valid.any():
        raise ValueError('No colored vertices')
    colors[valid] /= weights[valid, None]
    # Fill unseen vertices from the nearest observed point, not from background pixels.
    from scipy.spatial import cKDTree
    missing = ~valid
    if missing.any():
        closest = cKDTree(vertices[valid]).query(vertices[missing], k=1)[1]
        colors[missing] = colors[valid][closest]
    mesh.visual.vertex_colors = np.column_stack((np.clip(np.rint(colors), 0, 255).astype(np.uint8), np.full(len(vertices), 255, np.uint8)))
    output.mkdir(parents=True)
    target = output / 'colored.glb'
    mesh.export(target)
    check = trimesh.load(target, force='mesh', process=False)
    if len(check.faces) != len(mesh.faces) or len(check.vertices) != len(mesh.vertices) or not np.array_equal(check.visual.vertex_colors, mesh.visual.vertex_colors):
        raise ValueError('GLB geometry or color roundtrip failed')
    report = {'source': str(source.resolve()), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'vertices': len(vertices),
              'directly_sampled_vertices': int(valid.sum()), 'nearest_color_fill_vertices': int(missing.sum()),
              'views': observations, 'status': 'generated',
              'limitations': 'Approximate uncalibrated orthographic projections, vertex colors rather than UV texture; source views and mesh directions are not calibrated; vertex depth approximation misses occlusion; no fidelity or rigging validation.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'vertices', 'directly_sampled_vertices', 'nearest_color_fill_vertices')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('reference_dir', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    main(args.source, args.reference_dir, args.output)
