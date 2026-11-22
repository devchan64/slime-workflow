"""Build baseline and cautiously corrected rigs for the same BVH experiment."""
import json
import os
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
from scipy.spatial import cKDTree
from workflow.domains.unirig_experiment.combat_trial import add_box


def read_weight(v,index):
    return next((float(g.weight) for g in v.groups if g.group==index),0.)


def main(source,out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.vertex_groups))
    arm.name='Armature';obj.name='repaired_character'
    if obj.matrix_world != Matrix.Identity(4) or arm.matrix_world != Matrix.Identity(4):
        raise ValueError('expected original Y-down rig with identity object transforms')
    col=obj.data.color_attributes.get('Color')
    if col is None or col.domain!='CORNER':raise ValueError('expected corner colors')
    rgb=np.zeros((len(obj.data.vertices),4),dtype=np.float32);counts=np.zeros(len(rgb),dtype=np.int32)
    for loop in obj.data.loops:
        rgb[loop.vertex_index]+=col.data[loop.index].color;counts[loop.vertex_index]+=1
    if (counts==0).any():raise ValueError('uncolored vertex')
    rgb/=counts[:,None]
    new=obj.data.color_attributes.new(name='ReferenceColor',type='FLOAT_COLOR',domain='POINT')
    new.data.foreach_set('color',rgb.ravel())
    verts=[];faces=[]
    add_box(verts,faces,(0,-.025,0),(.018,.018,.12));add_box(verts,faces,(0,-.025,.135),(.095,.018,.018))
    add_box(verts,faces,(0,-.025,.46),(.032,.009,.31))
    wm=bpy.data.meshes.new('training_sword_mesh');wm.from_pydata(verts,[],faces);wm.update()
    weapon=bpy.data.objects.new('training_sword',wm);bpy.context.collection.objects.link(weapon)
    weapon.parent=arm;weapon.parent_type='BONE';weapon.parent_bone='bone_28';weapon.matrix_parent_inverse=Matrix.Identity(4)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str((out/'baseline.blend').resolve()))
    # Copy the better-supported contralateral arm weights only within a bounded
    # forearm neighbourhood. Preserve the pre-existing arm-group weight sum.
    coords=np.array([v.co[:] for v in obj.data.vertices],dtype=np.float64)
    index={g.name:g.index for g in obj.vertex_groups}
    src=['bone_7','bone_8','bone_9'];dst=['bone_26','bone_27','bone_28']
    original=np.array([[read_weight(v,index[name]) for name in src+dst] for v in obj.data.vertices])
    opposite=np.flatnonzero(coords[:,0]<-.05);tree=cKDTree(coords[opposite])
    mirrored=coords.copy();mirrored[:,0]*=-1
    distances,near=tree.query(mirrored,workers=1);near=opposite[near]
    b=arm.data.bones['bone_27'];h=np.asarray(b.head_local);tail=np.asarray(b.tail_local);axis=tail-h
    t=((coords-h)@axis)/(axis@axis)
    radius=np.linalg.norm(coords-(h+np.clip(t,0,1)[:,None]*axis),axis=1)
    selected=np.flatnonzero((coords[:,0]>.1)&(t>=-.1)&(t<=1.1)&(radius<.12)&(distances<.06))
    changed=[]
    for i in selected:
        total=original[i,3:].sum();mirror=original[near[i],:3]
        if total<.2 or mirror.sum()<.2:continue
        wanted=mirror/mirror.sum()*total
        if wanted[1]<=original[i,4]:continue
        new_w=.8*wanted+.2*original[i,3:]
        for name,value in zip(dst,new_w):obj.vertex_groups[name].add([int(i)],float(value),'REPLACE')
        changed.append(int(i))
    if len(changed)<10:raise ValueError('forearm correction did not affect enough vertices')
    # Move only terminal toe tails toward their existing weighted toe vertices;
    # keep each joint head and all non-toe bones fixed.
    old_tails={};new_tails={};centroids={}
    for name in ('bone_47','bone_51'):
        group=index[name];weight=np.array([read_weight(v,group) for v in obj.data.vertices]);sel=weight>.2
        if sel.sum()<3:raise ValueError('toe has insufficient weighted vertices')
        centroid=np.average(coords[sel],axis=0,weights=weight[sel]);centroids[name]=centroid
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='EDIT')
    for name in ('bone_47','bone_51'):
        bone=arm.data.edit_bones[name];head=np.asarray(bone.head[:]);old_tails[name]=list(bone.tail)
        direction=centroids[name]-head
        if np.linalg.norm(direction)<.01:raise ValueError('ambiguous toe direction')
        direction=direction/np.linalg.norm(direction)*.09
        bone.tail=Vector(head+direction);new_tails[name]=list(bone.tail)
    bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
    sums=np.array([sum(g.weight for g in v.groups) for v in obj.data.vertices])
    if np.max(np.abs(sums-1))>1e-4:raise ValueError('weight normalization changed')
    bpy.ops.wm.save_as_mainfile(filepath=str((out/'corrected.blend').resolve()))
    details={'changed_vertices':len(changed),'mirrored_distance_median':float(np.median(distances[changed])),
             'mirrored_distance_p99':float(np.quantile(distances[changed],.99)),
             'bone_27_max_before':float(original[:,4].max()),
             'bone_27_max_after':float(max(read_weight(v,index['bone_27']) for v in obj.data.vertices)),
             'toe_tail_before':old_tails,'toe_tail_after':new_tails,'weight_sum_max_error':float(np.max(np.abs(sums-1))),
             'limitations':'Symmetric local transfer is heuristic; toe direction uses skin centroids. BVH has no finger or weapon motion; neither elbow anatomy nor toe pivot correctness is guaranteed.'}
    (out/'correction.json').write_text(json.dumps(details,indent=2)+'\n');print(json.dumps(details),flush=True)


if __name__=='__main__':
    main(*(Path(x) for x in sys.argv[1:]));sys.stdout.flush();sys.stderr.flush();os._exit(0)
