"""Experimental localized voxel cut for the current reference character only."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh
from inspect_repair_mesh import stats
from clean_mesh import silhouettes


def main(source, output):
    if output.exists():
        raise FileExistsError(output)
    mesh = trimesh.load(source, force='mesh', process=False)
    if len(mesh.vertices) != 117308 or hashlib.sha256(source.read_bytes()).hexdigest() != 'eafa531eb633087d649b424fe9fea8a8d7c5d4cd6eb4c0284d5a9395d5b2f0f4':
        raise ValueError('Cut coordinates are calibrated only for the recorded colored-v1 mesh')
    pitch = float(max(mesh.extents) / 192)
    vox = mesh.voxelized(pitch=pitch).fill()
    mat = vox.matrix.copy()
    index = np.argwhere(mat)
    xyz = trimesh.transform_points(index, vox.transform)
    # Explicit experimental world-space cuts; these do not identify anatomy.
    cut = ((np.abs(np.abs(xyz[:, 0]) - 0.126) < 0.0075)
           & (xyz[:, 2] > -0.099) & (xyz[:, 2] < -0.058))
    removed = index[cut]
    mat[tuple(removed.T)] = False
    filled = trimesh.voxel.VoxelGrid(mat, transform=vox.transform)
    candidate = filled.marching_cubes
    candidate.apply_transform(filled.transform)
    candidate.visual.vertex_colors = np.asarray(mesh.visual.vertex_colors)[cKDTree(mesh.vertices).query(candidate.vertices)[1]]
    output.mkdir(parents=True)
    target = output / 'candidate.glb'
    candidate.export(target)
    candidate = trimesh.load(target, force='mesh', process=False)
    geometry = stats(candidate)
    center = mesh.bounds.mean(axis=0)
    scale = 220 / max(mesh.extents)
    before = silhouettes(mesh, center, scale)
    after = silhouettes(candidate, center, scale)
    loss = [float(np.count_nonzero((a != 0) & (b == 0)) / max(1, np.count_nonzero(a))) for a,b in zip(before, after)]
    gain = [float(np.count_nonzero((b != 0) & (a == 0)) / max(1, np.count_nonzero(a))) for a,b in zip(before, after)]
    sections=[]
    for z in [-.065,-.075,-.085,-.095]:
        section = candidate.section(plane_origin=[0,0,z], plane_normal=[0,0,1])
        paths = [] if section is None else section.discrete
        spans = [[float(p[:,0].min()),float(p[:,0].max())] for p in paths if len(p)>4]
        sections.append({'z':z,'spans':spans,
                         'left_bridging_contour':any(a < -.14 and b > -.11 for a,b in spans),
                         'right_bridging_contour':any(a < .11 and b > .14 for a,b in spans)})
    report = {'status':'not_approved', 'source':str(source.resolve()),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'candidate_sha256':hashlib.sha256(target.read_bytes()).hexdigest(), 'cut_voxels':len(removed),'pitch':pitch,
              'cut':{'absolute_x_center':.126,'half_width':.0075,'z_min':-.099,'z_max':-.058},
              'geometry':geometry,'sections':sections,'silhouette_loss_by_view':loss,'silhouette_gain_by_view':gain,
              'geometric_checks_passed':bool(geometry['self_intersecting_faces']==0 and geometry['watertight'] and geometry['winding_consistent'] and max(loss)<=.02 and max(gain)<=.02 and all(not x['left_bridging_contour'] and not x['right_bridging_contour'] for x in sections)),
              'limitations':'Experimental location-specific cut. Contour separation does not prove anatomical integrity; no skeleton, skinning, deformation or weapon test.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]))
