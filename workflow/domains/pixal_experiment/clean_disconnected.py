"""Remove small, distant disconnected components from a generated mesh candidate."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from numba import njit
from scipy.spatial import cKDTree


@njit
def vertex_components(n, faces):
    parent = np.arange(n, dtype=np.int32)
    for face in faces:
        for b in (face[1], face[2]):
            x, y = face[0], b
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            while parent[y] != y:
                parent[y] = parent[parent[y]]
                y = parent[y]
            if x != y:
                parent[y] = x
    for i in range(n):
        x = i
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        parent[i] = x
    return parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clean(source, output):
    if output.exists():
        raise FileExistsError(output)
    mesh = trimesh.load(source, force='mesh', process=False)
    vertices, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    if not len(faces) or not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError('invalid mesh')
    roots = vertex_components(len(vertices), faces)
    face_roots = roots[faces[:, 0]]
    ids, counts = np.unique(face_roots, return_counts=True)
    main = ids[np.argmax(counts)]
    diag = float(np.linalg.norm(mesh.extents))
    if diag <= 0:
        raise ValueError('zero extent')
    tree = cKDTree(vertices[roots == main])
    removed, details = [], []
    for component, count in zip(ids, counts):
        if component == main:
            continue
        points = vertices[roots == component]
        distance = float(tree.query(points, workers=1)[0].min()) / diag
        fraction = float(count / len(faces))
        discard = fraction <= 0.03 and distance >= 0.10
        if discard:
            removed.append(int(component))
        details.append({'faces':int(count), 'face_fraction':fraction, 'distance_fraction':distance,
                        'bounds': [points.min(axis=0).tolist(), points.max(axis=0).tolist()], 'removed':discard})
    mask = ~np.isin(face_roots, removed)
    candidate = trimesh.Trimesh(vertices=vertices.copy(), faces=faces[mask].copy(), process=False)
    candidate.remove_unreferenced_vertices()
    output.mkdir(parents=True)
    target = output / 'cleaned.glb'
    candidate.export(target)
    reloaded = trimesh.load(target, force='mesh', process=False)
    same = len(reloaded.faces) == len(candidate.faces) and len(reloaded.vertices) == len(candidate.vertices) and np.array_equal(reloaded.faces, candidate.faces) and np.allclose(reloaded.vertices, candidate.vertices, rtol=1e-6, atol=1e-7)
    report = {'source':str(source.resolve()), 'source_sha256':sha(source), 'candidate_sha256':sha(target),
              'source_faces':len(faces), 'candidate_faces':len(candidate.faces), 'components_before':len(ids),
              'components_removed':len(removed), 'components_remaining':len(ids)-len(removed),
              'rule':{'maximum_face_fraction':0.03, 'minimum_distance_over_bbox_diagonal':0.10},
              'roundtrip_passed':bool(same), 'components':details,
              'limitations':'Distance is measured to the largest component vertices. Detached anatomy is possible. No rigging or deformation guarantee.'}
    (output / 'clean-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:report[k] for k in ('source_faces','candidate_faces','components_before','components_removed','components_remaining','roundtrip_passed')}), flush=True)
    if not same:
        raise ValueError('mesh export roundtrip failed')


if __name__ == '__main__':
    clean(Path(sys.argv[1]), Path(sys.argv[2]))
