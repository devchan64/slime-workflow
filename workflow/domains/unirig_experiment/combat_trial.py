"""Transfer a rig to a repaired mesh and build a diagnostic sword swing."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
import trimesh
from mathutils import Matrix, Vector
from scipy.spatial import cKDTree


def add_box(vertices, faces, center, half):
    start=len(vertices); cx,cy,cz=center; dx,dy,dz=half
    vertices.extend([(cx+x*dx,cy+y*dy,cz+z*dz) for z in (-1,1) for y in (-1,1) for x in (-1,1)])
    faces.extend([tuple(start+i for i in q) for q in [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]])


def evaluated_positions(obj, deps):
    evaluated=obj.evaluated_get(deps); mesh=evaluated.to_mesh()
    try:
        v=np.empty((len(mesh.vertices),3),dtype=np.float32); mesh.vertices.foreach_get('co',v.ravel())
        return v
    finally:
        evaluated.to_mesh_clear()


def main(fbx, repaired, output):
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(fbx.resolve()))
    scene=bpy.context.scene
    arm=next(o for o in scene.objects if o.type=='ARMATURE')
    old=next(o for o in scene.objects if o.type=='MESH' and len(o.vertex_groups))
    original=np.array([v.co[:] for v in old.data.vertices],dtype=np.float32)
    clean=trimesh.load(repaired,force='mesh',process=False)
    # Repaired mesh is Z-up, while the UniRig FBX uses Y-down.
    rv=np.asarray(clean.vertices,dtype=np.float64)[:,[0,2,1]]*np.array([1,-1,1])
    distance, index=cKDTree(original).query(rv,workers=1)
    if not np.isfinite(rv).all() or np.quantile(distance,.99)>0.02:
        raise ValueError('repair-to-rig mapping is too distant')
    names=[g.name for g in old.vertex_groups]
    weights=[[(g.group,float(g.weight)) for g in v.groups if g.weight>0] for v in old.data.vertices]
    mesh=bpy.data.meshes.new('repaired_character_mesh'); mesh.from_pydata(rv.tolist(),[],np.asarray(clean.faces).tolist()); mesh.update()
    obj=bpy.data.objects.new('repaired_character',mesh); bpy.context.collection.objects.link(obj)
    obj.parent=arm
    obj.matrix_world=old.matrix_world.copy()
    for name in names: obj.vertex_groups.new(name=name)
    for i,old_idx in enumerate(index):
        for group,weight in weights[int(old_idx)]: obj.vertex_groups[group].add([i],weight,'REPLACE')
    modifier=obj.modifiers.new('Skin','ARMATURE'); modifier.object=arm
    rgba=np.asarray(clean.visual.vertex_colors,dtype=np.float32)/255
    rgb=rgba[:,:3]; linear=np.where(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)**2.4)
    attr=mesh.color_attributes.new(name='ReferenceColor',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',np.column_stack((linear,np.ones(len(linear),dtype=np.float32))).astype(np.float32).ravel())
    material=bpy.data.materials.new('Reference vertex colors'); material.use_nodes=True
    node=material.node_tree.nodes.new('ShaderNodeVertexColor'); node.layer_name='ReferenceColor'
    material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    mesh.materials.append(material); bpy.data.objects.remove(old,do_unlink=True)

    # Sword coordinates are local to the hand bone tail. The hilt is near the palm.
    vertices=[]; faces=[]
    add_box(vertices,faces,(0,-.025,0),(0.018,0.018,0.12))
    add_box(vertices,faces,(0,-.025,0.135),(0.095,0.018,0.018))
    add_box(vertices,faces,(0,-.025,0.46),(0.032,0.009,0.31))
    wmesh=bpy.data.meshes.new('training_sword_mesh'); wmesh.from_pydata(vertices,[],faces); wmesh.update()
    weapon=bpy.data.objects.new('training_sword',wmesh); bpy.context.collection.objects.link(weapon)
    weapon.parent=arm; weapon.parent_type='BONE'; weapon.parent_bone='bone_28'; weapon.matrix_parent_inverse=Matrix.Identity(4)
    steel=bpy.data.materials.new('training_sword_steel'); steel.diffuse_color=(0.52,0.56,0.61,1); wmesh.materials.append(steel)

    # Each control is an XYZ Euler rotation in the bone's local rest basis.
    frames={1:{'bone_26':(-10,0,-15),'bone_27':(-15,0,0),'bone_28':(0,0,0)},
            7:{'bone_26':(-35,20,-60),'bone_27':(-55,0,0),'bone_28':(15,0,-10)},
            12:{'bone_26':(55,-15,35),'bone_27':(25,0,0),'bone_28':(-20,0,15)},
            17:{'bone_26':(30,-10,55),'bone_27':(40,0,0),'bone_28':(-10,0,10)},
            24:{'bone_26':(-10,0,-15),'bone_27':(-15,0,0),'bone_28':(0,0,0)}}
    fingers=[f'bone_{i}' for i in range(29,44)]
    finger_degrees={1:0,7:25,12:25,17:25,24:0}
    for frame,pose in frames.items():
        for name,angles in pose.items():
            b=arm.pose.bones[name]; b.rotation_mode='XYZ'; b.rotation_euler=tuple(math.radians(a) for a in angles); b.keyframe_insert(data_path='rotation_euler',frame=frame,group=name)
        for name in fingers:
            b=arm.pose.bones[name]; b.rotation_mode='XYZ'; b.rotation_euler=(math.radians(finger_degrees[frame]),0,0); b.keyframe_insert(data_path='rotation_euler',frame=frame,group=name)
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action.name='diagnostic_sword_swing'
        for curve in arm.animation_data.action.fcurves:
            for point in curve.keyframe_points: point.interpolation='LINEAR'
    scene.frame_start=1; scene.frame_end=24; scene.render.fps=24
    deps=bpy.context.evaluated_depsgraph_get(); obj.data.calc_loop_triangles()
    face_indices=np.array([x.vertices[:] for x in obj.data.loop_triangles],dtype=np.int32)
    all_positions=[]; tip=[]; grip=[]; hand=[]; swords=[]
    for frame in range(1,25):
        scene.frame_set(frame); bpy.context.view_layer.update()
        pos=evaluated_positions(obj,deps)
        if not np.isfinite(pos).all(): raise ValueError('nonfinite posed mesh')
        all_positions.append(pos)
        mat=weapon.evaluated_get(deps).matrix_world.copy()
        tip.append(tuple(mat@Vector((0,-.025,.77))))
        grip.append(tuple(mat@Vector((0,-.025,0))))
        hand.append(tuple(arm.matrix_world@arm.pose.bones['bone_28'].tail))
        swords.append(np.array([mat@Vector(v) for v in vertices],dtype=np.float32))
    np.savez_compressed(output/'frames.npz',positions=np.stack(all_positions),faces=face_indices,
                        weapon_vertices=np.stack(swords),weapon_faces=np.asarray(faces,dtype=np.int32),
                        colors=np.asarray(clean.visual.vertex_colors),tip=np.asarray(tip),grip=np.asarray(grip),hand=np.asarray(hand))
    scene.frame_set(1); bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); arm.select_set(True); weapon.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'combat-trial.blend').resolve()))
    bpy.ops.export_scene.gltf(filepath=str((output/'combat-trial.glb').resolve()),export_format='GLB',use_selection=True,
                              export_skins=True,export_animations=True,export_animation_mode='ACTIONS')
    lengths=np.linalg.norm(np.diff(np.asarray(tip),axis=0),axis=1)
    report={'fps':24,'frame_start':1,'frame_end':24,'hand_bone':'bone_28','finger_bones':fingers,
            'keyframes_degrees_xyz':{str(k):v for k,v in frames.items()},'finger_x_degrees':finger_degrees,'interpolation':'linear',
            'weapon_tip':tip,'weapon_grip_to_hand_tail_distance':np.linalg.norm(np.asarray(grip)-np.asarray(hand),axis=1).tolist(),
            'weapon_tip_path_length':float(lengths.sum()),'weapon_tip_max_frame_step':float(lengths.max()),
            'repair_mapping_median_distance':float(np.median(distance)),'repair_mapping_p99_distance':float(np.quantile(distance,.99)),
            'source_vertices':len(original),'repaired_vertices':len(rv),'repaired_faces':len(clean.faces),
            'limitations':'Heuristic local Euler test, numbered bones are not semantic labels. Nearest-vertex weights and color transfer are approximate. Grip and weapon collisions require separate checks.'}
    (output/'motion.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('weapon_tip_path_length','repair_mapping_median_distance','repair_mapping_p99_distance','repaired_vertices','repaired_faces')}),flush=True)


if __name__=='__main__': main(*(Path(v) for v in sys.argv[1:]))
