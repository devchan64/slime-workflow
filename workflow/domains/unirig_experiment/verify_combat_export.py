"""Reimport an upright animated GLB and compare body and weapon to captured frames."""
import json
import os
import sys
from pathlib import Path
import bpy
import numpy as np
from scipy.spatial import cKDTree


def world_vertices(obj):
    dg=bpy.context.evaluated_depsgraph_get();e=obj.evaluated_get(dg);m=e.to_mesh()
    try:
        v=np.empty((len(m.vertices),3),dtype=np.float32);m.vertices.foreach_get('co',v.ravel())
        matrix=np.asarray(e.matrix_world,dtype=np.float64);return v@matrix[:3,:3].T+matrix[:3,3]
    finally:e.to_mesh_clear()


def distance(a,b):
    x=cKDTree(a).query(b,workers=1)[0];y=cKDTree(b).query(a,workers=1)[0]
    return {'p99':float(max(np.quantile(x,.99),np.quantile(y,.99))),'max':float(max(x.max(),y.max()))}


def main(directory):
    d=np.load(directory/'frames.npz',allow_pickle=False)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.fps=20
    bpy.ops.import_scene.gltf(filepath=str((directory/'retarget.glb').resolve()))
    obj=bpy.context.scene.objects['repaired_character'];weapon=bpy.context.scene.objects['training_sword'];rows=[]
    for frame in (1,34,67,100,132):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        body=np.asarray(d['positions'][frame-1])[:,[0,2,1]]*np.array([1,1,-1])
        blade=np.asarray(d['weapon_vertices'][frame-1])[:,[0,2,1]]*np.array([1,1,-1])
        rows.append({'frame':frame,'body':distance(body,world_vertices(obj)),'weapon':distance(blade,world_vertices(weapon))})
    r={'fps':20,'frames':rows,'limitations':'Five sampled frames; compares nearest vertex sets, not all frames or semantic motion.'}
    (directory/'export-roundtrip.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r),flush=True)


if __name__=='__main__':main(Path(sys.argv[1]));sys.stdout.flush();sys.stderr.flush();os._exit(0)
