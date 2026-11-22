"""Transfer a source FBX rig to a reduced version of its source mesh."""
import json
import math
import os
import sys
from pathlib import Path
import bpy
import numpy as np
from scipy.spatial import cKDTree
import trimesh


def vertices(obj,deps):
    evaluated=obj.evaluated_get(deps); m=evaluated.to_mesh()
    try:
        a=np.empty((len(m.vertices),3),dtype=np.float32);m.vertices.foreach_get('co',a.ravel());return a
    finally: evaluated.to_mesh_clear()


def main(fbx, original_path, reduced_path, out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(fbx.resolve()))
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    old=next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.vertex_groups))
    source=trimesh.load(original_path,force='mesh',process=False)
    reduced=trimesh.load(reduced_path,force='mesh',process=False)
    center=np.asarray(source.bounds).mean(axis=0);scale=2/max(source.extents)
    rv=(np.asarray(reduced.vertices)-center)*scale
    rv=rv[:,[0,2,1]]*np.array([1,-1,1])
    ov=np.array([v.co[:] for v in old.data.vertices],dtype=np.float32)
    distances,nearest=cKDTree(ov).query(rv,workers=1)
    if not np.isfinite(rv).all() or np.quantile(distances,.99)>.04:
        raise ValueError('reduced mesh does not match source rig')
    weights=[[(g.group,float(g.weight)) for g in v.groups if g.weight>0] for v in old.data.vertices]
    mesh=bpy.data.meshes.new('reduced_mesh');mesh.from_pydata(rv.tolist(),[],np.asarray(reduced.faces).tolist());mesh.update()
    obj=bpy.data.objects.new('reduced_character',mesh);bpy.context.collection.objects.link(obj)
    obj.parent=arm;obj.matrix_world=old.matrix_world.copy()
    for group in old.vertex_groups:obj.vertex_groups.new(name=group.name)
    for i,j in enumerate(nearest):
        for group,weight in weights[int(j)]:obj.vertex_groups[group].add([i],weight,'REPLACE')
    mod=obj.modifiers.new('Skin','ARMATURE');mod.object=arm
    rgb=np.asarray(reduced.visual.vertex_colors,dtype=np.float32)/255
    linear=np.where(rgb[:,:3]<=.04045,rgb[:,:3]/12.92,((rgb[:,:3]+.055)/1.055)**2.4)
    attr=mesh.color_attributes.new(name='ReferenceColor',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',np.column_stack((linear,np.ones(len(linear),dtype=np.float32))).astype(np.float32).ravel())
    material=bpy.data.materials.new('Reference colors');material.use_nodes=True
    node=material.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='ReferenceColor'
    material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    mesh.materials.append(material);bpy.data.objects.remove(old,do_unlink=True)
    deps=bpy.context.evaluated_depsgraph_get();baseline=vertices(obj,deps)
    groups={g.name:g.index for g in obj.vertex_groups}
    joints=['bone_7','bone_8','bone_26','bone_27','bone_44','bone_45','bone_48','bone_49']
    fingers=[f'bone_{i}' for i in list(range(10,25))+list(range(29,44))]
    tests=[]
    for name in joints+fingers:
        if name not in arm.pose.bones or name not in groups:
            tests.append({'bone':name,'status':'missing'});continue
        bone=arm.pose.bones[name];bone.rotation_mode='XYZ';bone.rotation_euler.x=math.radians(25)
        bpy.context.view_layer.update();pos=vertices(obj,deps);delta=np.linalg.norm(pos-baseline,axis=1)
        weight=np.array([next((g.weight for g in v.groups if g.group==groups[name]),0.) for v in mesh.vertices])
        strong=weight>=.05
        tests.append({'bone':name,'weighted_vertices_ge_005':int(strong.sum()),'weighted_vertices_moved':int(((delta>1e-4)&strong).sum()),
                      'moved_vertices':int((delta>1e-4).sum()),'max_displacement':float(delta.max()),'finite':bool(np.isfinite(pos).all())})
        bone.rotation_euler.x=0;bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.gltf(filepath=str((out/'rigged.glb').resolve()),export_format='GLB',use_selection=True,
                              export_skins=True,export_animations=False)
    for label,rot in [('rest',{}),('arms',{'bone_7':35,'bone_8':40,'bone_26':-35,'bone_27':-40}),
                      ('legs',{'bone_44':25,'bone_45':35,'bone_48':-25,'bone_49':-35}),('fingers',{n:20 for n in fingers})]:
        for name,angle in rot.items():
            bone=arm.pose.bones[name];bone.rotation_mode='XYZ';bone.rotation_euler.x=math.radians(angle)
        bpy.context.view_layer.update();pos=vertices(obj,deps)[:,[0,2,1]]*np.array([1,1,-1],dtype=np.float32)
        m=trimesh.Trimesh(vertices=pos,faces=np.asarray(reduced.faces),process=False)
        m.visual.vertex_colors=np.asarray(reduced.visual.vertex_colors);m.export(out/(label+'.ply'))
        for name in rot:arm.pose.bones[name].rotation_euler.x=0
        bpy.context.view_layer.update()
    sums=np.array([sum(g.weight for g in v.groups) for v in mesh.vertices])
    result={'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'bones':len(arm.data.bones),
            'unweighted_vertices':int((sums<1e-6).sum()),'weight_sum_min':float(sums.min()),'weight_sum_max':float(sums.max()),
            'transfer_distance_median':float(np.median(distances)),'transfer_distance_p99':float(np.quantile(distances,.99)),
            'bone_probes':tests,'limitations':'Nearest-vertex weights copied from a separately rigged 17,546-face source; mappings and test rotations are heuristic.'}
    (out/'deformation-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('vertices','faces','bones','unweighted_vertices','transfer_distance_p99')}),flush=True)


if __name__=='__main__':
    main(*(Path(x) for x in sys.argv[1:]));sys.stdout.flush();sys.stderr.flush();os._exit(0)
