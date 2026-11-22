"""Rotate a whole rig upright, export a new GLB and verify pose round trips."""
import json
import math
import os
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
from scipy.spatial import cKDTree


def load(path):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.vertex_groups))
    return arm,mesh


def world_vertices(obj):
    dg=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(dg);mesh=ev.to_mesh()
    try:
        v=np.empty((len(mesh.vertices),3),dtype=np.float32);mesh.vertices.foreach_get('co',v.ravel())
        matrix=np.asarray(ev.matrix_world,dtype=np.float64);return v@matrix[:3,:3].T+matrix[:3,3]
    finally:ev.to_mesh_clear()


def pose(arm,rotations):
    for b in arm.pose.bones:
        b.rotation_mode='XYZ';b.rotation_euler=(0,0,0);b.location=(0,0,0)
    for name,angle in rotations.items():
        if name not in arm.pose.bones:raise ValueError(f'missing bone {name}')
        arm.pose.bones[name].rotation_euler.x=math.radians(angle)
    bpy.context.view_layer.update()


def main(source,out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    arm,obj=load(source)
    samples={'rest':{},'arms':{'bone_7':35,'bone_8':40,'bone_26':-35,'bone_27':-40},
             'legs':{'bone_44':25,'bone_45':35,'bone_48':-25,'bone_49':-35}}
    rotation=Matrix.Rotation(-math.pi/2,4,'X');rm=np.asarray(rotation,dtype=np.float64)[:3,:3]
    expected={}
    for name,values in samples.items():
        pose(arm,values);expected[name]=world_vertices(obj)@rm.T
    pose(arm,{})
    arm.matrix_world=rotation@arm.matrix_world;bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);obj.select_set(True);bpy.context.view_layer.objects.active=arm
    dest=out/'rigged-upright.glb'
    bpy.ops.export_scene.gltf(filepath=str(dest.resolve()),export_format='GLB',use_selection=True,
                              export_skins=True,export_animations=False)
    arm,obj=load(dest);checks=[]
    for name,values in samples.items():
        pose(arm,values);actual=world_vertices(obj);d1=cKDTree(expected[name]).query(actual,workers=1)[0]
        d2=cKDTree(actual).query(expected[name],workers=1)[0]
        checks.append({'pose':name,'source_vertices':len(expected[name]),'imported_vertices':len(actual),
                       'p99_bidirectional_distance':float(max(np.quantile(d1,.99),np.quantile(d2,.99))),
                       'max_bidirectional_distance':float(max(d1.max(),d2.max()))})
    pose(arm,{})
    actual=world_vertices(obj);extent=np.ptp(actual,axis=0)
    r={'upright_world_extents':extent.tolist(),'bones':len(arm.data.bones),'triangles':len(obj.data.polygons),
       'unweighted_vertices':sum(not any(g.weight>1e-7 for g in v.groups) for v in obj.data.vertices),
       'pose_roundtrip':checks,'limitations':'Distances compare vertex sets, not topology or bone semantic correctness; only three heuristic poses tested.'}
    if extent[2]<=max(extent[0],extent[1]) or any(x['p99_bidirectional_distance']>1e-4 for x in checks):
        raise ValueError('upright orientation or pose roundtrip failed: '+json.dumps(r))
    (out/'orientation-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)


if __name__=='__main__':
    main(*(Path(x) for x in sys.argv[1:]));sys.stdout.flush();sys.stderr.flush();os._exit(0)
