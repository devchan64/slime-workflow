"""Propose, but never automatically approve, a MeshFix candidate."""
import json
import sys
from pathlib import Path
import numpy as np
import pymeshfix
from scipy.spatial import cKDTree
import trimesh


def main(source, output):
    if output.exists(): raise FileExistsError(output)
    m=trimesh.load(source,force='mesh',process=False)
    fix=pymeshfix.MeshFix(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.int32))
    fix.repair(joincomp=False,remove_smallest_components=False)
    r=trimesh.Trimesh(vertices=fix.points,faces=fix.faces,process=False)
    if not len(r.faces) or not np.isfinite(r.vertices).all(): raise ValueError('invalid repair')
    d,near=cKDTree(np.asarray(m.vertices)).query(np.asarray(r.vertices),workers=1)
    r.visual.vertex_colors=np.asarray(m.visual.vertex_colors)[near]
    output.mkdir(parents=True)
    r.export(output/'candidate.glb')
    (output/'repair.json').write_text(json.dumps({'input_faces':len(m.faces),'output_faces':len(r.faces),
        'input_vertices':len(m.vertices),'output_vertices':len(r.vertices),
        'color_distance_p99':float(np.percentile(d,99)),
        'limitations':'Repair can remove hands or alter anatomy; independent geometry and silhouette validation required.'},indent=2)+'\n')
    print(json.dumps({'input_faces':len(m.faces),'output_faces':len(r.faces)}),flush=True)


if __name__=='__main__': main(*(Path(x) for x in sys.argv[1:]))
