"""Build a non-destructive MeshFix candidate; inspect anatomy and rigging separately."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pymeshfix
import trimesh
from scipy.spatial import cKDTree


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main(source, output):
    if output.exists():
        raise FileExistsError(output)
    original = trimesh.load(source, force='mesh', process=False)
    if not len(original.faces) or not np.isfinite(original.vertices).all():
        raise ValueError('invalid source mesh')
    vertices, faces = pymeshfix.clean_from_arrays(
        np.ascontiguousarray(original.vertices, dtype=np.float64),
        np.ascontiguousarray(original.faces, dtype=np.int32),
        verbose=False, joincomp=False, remove_smallest_components=False)
    if not len(faces) or not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError('invalid repaired mesh')
    result = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if original.visual.kind == 'vertex':
        indices = cKDTree(np.asarray(original.vertices)).query(vertices, workers=1)[1]
        result.visual.vertex_colors = np.asarray(original.visual.vertex_colors)[indices]
    output.mkdir(parents=True)
    target = output / 'candidate.glb'
    result.export(target)
    result.export(output / 'candidate.ply')
    reloaded = trimesh.load(target, force='mesh', process=False)
    roundtrip = len(reloaded.faces) == len(result.faces) and np.array_equal(reloaded.faces,result.faces) and np.allclose(reloaded.vertices,result.vertices,rtol=1e-6,atol=1e-7)
    report = {'source':str(source.resolve()), 'source_sha256':sha(source), 'candidate_sha256':sha(target),
              'source_vertices':len(original.vertices),'source_faces':len(original.faces),
              'vertices':len(vertices),'faces':len(faces),'roundtrip':bool(roundtrip),
              'join_components':False,'remove_smallest_components':False,
              'rigging_approved':False,'limitations':'MeshFix may remove or alter anatomy; inspect topology, self-intersection, silhouette, clearance, skeleton and deformation separately.'}
    (output/'generation-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    if not roundtrip:
        raise ValueError('GLB roundtrip failed')


if __name__ == '__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]))
