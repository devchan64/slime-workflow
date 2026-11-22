"""Create an auditable topology-repair candidate; never overwrite the source."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh
from scipy.spatial import cKDTree


def inspect(mesh):
    inverse = mesh.edges_unique_inverse
    counts = np.bincount(inverse)
    signs = np.where(mesh.edges[:, 0] < mesh.edges[:, 1], 1, -1)
    sums = np.bincount(inverse, weights=signs)
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(mesh.vertices, dtype=np.float64),
                               face_matrix=np.asarray(mesh.faces, dtype=np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    return {'vertices':len(mesh.vertices), 'faces':len(mesh.faces),
            'components':len(mesh.split(only_watertight=False)),
            'watertight':bool(mesh.is_watertight), 'winding_consistent':bool(mesh.is_winding_consistent),
            'boundary_edges':int((counts == 1).sum()), 'nonmanifold_edges':int((counts > 2).sum()),
            'winding_conflict_edges':int(((counts == 2) & (sums != 0)).sum()),
            'self_intersection_faces':int(ms.current_mesh().face_selection_array().sum())}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def repair(source, output):
    if output.exists():
        raise FileExistsError(output)
    original = trimesh.load(source, force='mesh', process=False)
    if not len(original.faces) or not np.isfinite(original.vertices).all():
        raise ValueError('invalid mesh')
    before = inspect(original)
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(original.vertices,dtype=np.float64),
                               face_matrix=np.asarray(original.faces,dtype=np.int32)))
    steps = []
    ms.meshing_repair_non_manifold_edges(method='Remove Faces')
    ms.meshing_repair_non_manifold_vertices(vertdispratio=0)
    for iteration in range(4):
        ms.compute_selection_by_self_intersections_per_face()
        selected = int(ms.current_mesh().face_selection_array().sum())
        steps.append({'iteration':iteration, 'self_intersection_selected_faces':selected})
        if not selected:
            break
        ms.meshing_remove_selected_faces()
        ms.meshing_remove_unreferenced_vertices()
        ms.meshing_close_holes(maxholesize=100, selfintersection=True, newfaceselected=False)
        ms.meshing_repair_non_manifold_edges(method='Remove Faces')
        ms.meshing_repair_non_manifold_vertices(vertdispratio=0)
    ms.meshing_close_holes(maxholesize=100, selfintersection=True, newfaceselected=False)
    repaired = trimesh.Trimesh(vertices=ms.current_mesh().vertex_matrix().copy(),
                               faces=ms.current_mesh().face_matrix().copy(), process=False)
    if not len(repaired.faces) or not np.isfinite(repaired.vertices).all():
        raise ValueError('repair produced invalid geometry')
    if original.visual.kind == 'vertex':
        indices = cKDTree(np.asarray(original.vertices)).query(np.asarray(repaired.vertices), workers=1)[1]
        repaired.visual.vertex_colors = np.asarray(original.visual.vertex_colors)[indices]
    output.mkdir(parents=True)
    target = output / 'candidate.glb'
    repaired.export(target)
    checked = trimesh.load(target, force='mesh', process=False)
    after = inspect(checked)
    report = {'source':str(source.resolve()),'source_sha256':sha(source),'candidate_sha256':sha(target),
              'before':before,'after':after,'steps':steps,
              'roundtrip':bool(len(checked.vertices)==len(repaired.vertices) and np.allclose(checked.vertices,repaired.vertices,atol=1e-7) and np.array_equal(checked.faces,repaired.faces)),
              'rigging_approved':False,
              'limitations':'Automatic face deletion and hole filling can erase anatomy or join surfaces. Self-intersection detection is approximate. No skinning or animation test.'}
    (output/'repair-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    repair(Path(sys.argv[1]),Path(sys.argv[2]))
