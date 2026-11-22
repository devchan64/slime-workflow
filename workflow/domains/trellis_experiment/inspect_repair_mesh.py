"""Inspect mesh self-intersections and produce a conservative voxel repair candidate."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pymeshlab
from scipy.spatial import cKDTree
import trimesh
from clean_mesh import silhouettes


def inspect(mesh):
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(mesh.vertices, dtype=np.float64),
                                face_matrix=np.asarray(mesh.faces, dtype=np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    return int(ms.current_mesh().face_selection_array().sum())


def stats(mesh):
    edges = np.asarray(mesh.edges_sorted)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return {'vertices': len(mesh.vertices), 'faces': len(mesh.faces),
            'components': len(mesh.split(only_watertight=False)), 'watertight': bool(mesh.is_watertight),
            'winding_consistent': bool(mesh.is_winding_consistent),
            'boundary_edges': int((counts == 1).sum()), 'nonmanifold_edges': int((counts > 2).sum()),
            'self_intersecting_faces': inspect(mesh)}


def main(source, output, resolution):
    if output.exists():
        raise FileExistsError(output)
    mesh = trimesh.load(source, force='mesh', process=False)
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all() or max(mesh.extents) <= 0:
        raise ValueError('Invalid mesh')
    before = stats(mesh)
    output.mkdir(parents=True)
    report = {'source': str(source.resolve()), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'before': before, 'status': 'not_approved', 'anatomical_connections': 'not_verified',
              'limitations': ['MeshLab self-intersection selection has numerical and detection limits.',
                              'Anatomically incorrect bridges cannot be identified reliably from topology alone.',
                              'Voxel repair may merge limbs, close gaps, or erase details; no automatic rigging approval.']}
    if before['self_intersecting_faces']:
        pitch = float(max(mesh.extents) / resolution)
        vox = mesh.voxelized(pitch=pitch).fill()
        repaired = vox.marching_cubes
        repaired.apply_transform(vox.transform)
        if mesh.visual.kind == 'vertex':
            nearest = cKDTree(np.asarray(mesh.vertices)).query(np.asarray(repaired.vertices))[1]
            repaired.visual.vertex_colors = np.asarray(mesh.visual.vertex_colors)[nearest]
        target = output / 'voxel-candidate.glb'
        repaired.export(target)
        check = trimesh.load(target, force='mesh', process=False)
        after = stats(check)
        center = (mesh.bounds[0] + mesh.bounds[1]) / 2
        scale = 220 / max(mesh.extents)
        a, b = silhouettes(mesh, center, scale), silhouettes(check, center, scale)
        losses = [float(np.count_nonzero((x != 0) & (y == 0)) / max(1, np.count_nonzero(x))) for x,y in zip(a,b)]
        gains = [float(np.count_nonzero((y != 0) & (x == 0)) / max(1, np.count_nonzero(x))) for x,y in zip(a,b)]
        report.update({'after': after, 'pitch': pitch, 'silhouette_loss_by_view': losses,
                       'silhouette_gain_by_view': gains,
                       'candidate_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                       'geometric_checks_passed': bool(after['self_intersecting_faces'] == 0 and after['watertight']
                                                       and after['winding_consistent'] and after['components'] == before['components']
                                                       and max(losses) <= 0.02 and max(gains) <= 0.02)})
    else:
        report['message'] = 'No self-intersecting faces detected; no repair applied.'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--resolution', type=int, default=128, choices=range(32, 257))
    a = parser.parse_args()
    main(a.source, a.output, a.resolution)
