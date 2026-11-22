"""Retarget a HumanML-style BVH to the numbered UniRig experiment."""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix,Vector


MAPPING={'Hips':'bone_0','Spine':'bone_1','Spine1':'bone_2','Spine2':'bone_3','Neck':'bone_4','Head':'bone_5',
         'LeftShoulder':'bone_25','LeftArm':'bone_26','LeftForeArm':'bone_27','LeftHand':'bone_28',
         'RightShoulder':'bone_6','RightArm':'bone_7','RightForeArm':'bone_8','RightHand':'bone_9',
         'LeftUpLeg':'bone_48','LeftLeg':'bone_49','LeftFoot':'bone_50','LeftToe':'bone_51',
         'RightUpLeg':'bone_44','RightLeg':'bone_45','RightFoot':'bone_46','RightToe':'bone_47'}


def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def main(blend, bvh, output):
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene=bpy.context.scene
    target=scene.objects['Armature']; obj=scene.objects['repaired_character']; weapon=scene.objects['training_sword']
    target.animation_data_clear()
    for bone in target.pose.bones:
        bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=(1,0,0,0); bone.location=(0,0,0)
    bpy.ops.import_anim.bvh(filepath=str(bvh.resolve()),use_fps_scale=False,update_scene_fps=False)
    source=next(o for o in scene.objects if o.type=='ARMATURE' and o!=target)
    if any(src not in source.data.bones or dst not in target.data.bones for src,dst in MAPPING.items()):
        raise ValueError('missing source or target joints')
    if not source.animation_data or not source.animation_data.action:
        raise ValueError('BVH action missing')
    start,end=(round(v) for v in source.animation_data.action.frame_range)
    if (start,end)!=(1,132): raise ValueError('unexpected BVH frame range')
    scene.render.fps=20; scene.render.fps_base=1.0; scene.frame_start=start;scene.frame_end=end
    # The imported BVH is Z-up; this rig has Y-down vertical coordinates.
    align=Matrix(((1,0,0),(0,0,-1),(0,1,0))).to_quaternion()
    src_rest={k:source.data.bones[k].matrix_local.to_quaternion() for k in MAPPING}
    dst_rest={v:target.data.bones[v].matrix_local.to_quaternion() for v in MAPPING.values()}
    rest_alignment={}
    for src,dst in MAPPING.items():
        source_bone=source.data.bones[src]; target_bone=target.data.bones[dst]
        target_dir=(target_bone.tail_local-target_bone.head_local).normalized()
        source_dir=(align@(source_bone.tail_local-source_bone.head_local)).normalized()
        # BVH end joints have synthetic zero-length tails; their directions do
        # not encode a reliable target direction.
        rest_alignment[dst]=(target_dir.rotation_difference(source_dir)
                             if src not in ('Hips','Head','LeftHand','RightHand','LeftToe','RightToe')
                             else Matrix.Identity(3).to_quaternion())
    inverse_map={v:k for k,v in MAPPING.items()}
    neutral_hands=os.environ.get('RETARGET_NEUTRAL_HANDS')=='1'
    order=[b.name for b in target.data.bones if b.name in inverse_map]
    source_height=abs(source.data.bones['Hips'].head_local.z-source.data.bones['LeftFoot'].head_local.z)
    target_height=abs(target.data.bones['bone_0'].head_local.y-target.data.bones['bone_50'].head_local.y)
    if source_height<=0 or target_height<=0: raise ValueError('invalid skeleton dimensions')
    translation_scale=float(target_height/source_height)
    scene.frame_set(start);bpy.context.view_layer.update()
    source_root_start=(source.matrix_world@source.pose.bones['Hips'].head).copy()
    samples=[]
    for frame in range(start,end+1):
        scene.frame_set(frame); bpy.context.view_layer.update()
        desired={}
        rotations={}
        for dst in order:
            src=inverse_map[dst]; b=target.data.bones[dst]
            src_delta=source.pose.bones[src].matrix.to_quaternion()@src_rest[src].inverted()
            qworld=align@src_delta@align.inverted()@rest_alignment[dst]@dst_rest[dst]
            desired[dst]=qworld
            parent=b.parent.name if b.parent else None
            if parent:
                if parent not in desired: raise ValueError('mapped parent missing')
                rest_relative=dst_rest[parent].inverted()@dst_rest[dst]
                local=rest_relative.inverted()@desired[parent].inverted()@qworld
            else:
                local=dst_rest[dst].inverted()@qworld
            if neutral_hands and src in ('LeftHand','RightHand'):
                local=Matrix.Identity(3).to_quaternion()
                qworld=desired[parent]@rest_relative
                desired[dst]=qworld
            local.normalize(); target.pose.bones[dst].rotation_quaternion=local
            target.pose.bones[dst].keyframe_insert(data_path='rotation_quaternion',frame=frame,group=dst)
            rotations[dst]=list(local)
        delta=align@((source.matrix_world@source.pose.bones['Hips'].head)-source_root_start)*translation_scale
        target.pose.bones['bone_0'].location=target.data.bones['bone_0'].matrix_local.to_3x3().inverted()@delta
        target.pose.bones['bone_0'].keyframe_insert(data_path='location',frame=frame,group='bone_0')
        # BVH does not contain fingers; the grip is an explicit fixed test pose.
        for n in (() if neutral_hands else range(29,44)):
            pb=target.pose.bones[f'bone_{n}'];pb.rotation_mode='XYZ';pb.rotation_euler=(math.radians(20),0,0)
            pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=pb.name)
        samples.append({'frame':frame,'local_quaternion_wxyz':rotations,'root_delta_target':list(delta)})
    if target.animation_data and target.animation_data.action:
        target.animation_data.action.name='animationgpt_bvh_retarget'
        for curve in target.animation_data.action.fcurves:
            for point in curve.keyframe_points: point.interpolation='LINEAR'
    direction_checks=[]
    for frame in (1,34,67,100,132):
        scene.frame_set(frame);bpy.context.view_layer.update()
        for src,dst in MAPPING.items():
            if src in ('Hips','Head','LeftHand','RightHand','LeftToe','RightToe'): continue
            sp=source.pose.bones[src];tp=target.pose.bones[dst]
            sd=(align@(sp.tail-sp.head)).normalized();td=(tp.tail-tp.head).normalized()
            direction_checks.append({'frame':frame,'source_joint':src,'target_bone':dst,
                                     'angle_degrees':math.degrees(sd.angle(td,0.0))})
    bpy.data.objects.remove(source,do_unlink=True)
    active_action=target.animation_data.action
    for action in list(bpy.data.actions):
        if action!=active_action: bpy.data.actions.remove(action)
    deps=bpy.context.evaluated_depsgraph_get(); obj.data.calc_loop_triangles()
    faces=np.array([t.vertices[:] for t in obj.data.loop_triangles],dtype=np.int32)
    v=[];tip=[];grip=[];hand=[];weapon_vertices=[]
    for frame in range(start,end+1):
        scene.frame_set(frame);bpy.context.view_layer.update();e=obj.evaluated_get(deps);m=e.to_mesh()
        arr=np.empty((len(m.vertices),3),dtype=np.float32);m.vertices.foreach_get('co',arr.ravel());e.to_mesh_clear()
        if not np.isfinite(arr).all(): raise ValueError('nonfinite mesh')
        v.append(arr)
        mat=weapon.evaluated_get(deps).matrix_world.copy()
        tip.append(tuple(mat@Vector((0,-.025,.77))));grip.append(tuple(mat@Vector((0,-.025,0))))
        hand.append(tuple(target.matrix_world@target.pose.bones['bone_28'].tail))
        weapon_vertices.append(np.array([mat@x.co for x in weapon.data.vertices],dtype=np.float32))
    attr=obj.data.color_attributes['ReferenceColor'];rgb=np.array([item.color[:] for item in attr.data],dtype=np.float32)
    # Blender's color attribute is linear; the diagnostic renderer expects sRGB.
    c=rgb[:,:3]; srgb=np.where(c<=0.0031308,c*12.92,1.055*np.power(np.maximum(c,0),1/2.4)-.055)
    colors=np.column_stack(((srgb*255).clip(0,255).astype(np.uint8),np.full(len(c),255,np.uint8)))
    quads=np.array([p.vertices[:] for p in weapon.data.polygons],dtype=np.int32)
    np.savez_compressed(output/'frames.npz',positions=np.stack(v),faces=faces,weapon_vertices=np.stack(weapon_vertices),
                        weapon_faces=quads,colors=colors,tip=np.asarray(tip),grip=np.asarray(grip),hand=np.asarray(hand))
    scene.frame_set(start);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True);target.select_set(True);weapon.select_set(True);bpy.context.view_layer.objects.active=target
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'retarget.blend').resolve()))
    bpy.ops.export_scene.gltf(filepath=str((output/'retarget.glb').resolve()),export_format='GLB',use_selection=True,
                              export_skins=True,export_animations=True,export_animation_mode='ACTIONS')
    report={'source_bvh':str(bvh.resolve()),'source_sha256':sha(bvh),'fps':20,'frames':132,'joint_mapping':MAPPING,
            'source_up':'Z-up after Blender BVH import','target_up':'Y-down in rig space','translation_scale':translation_scale,
            'source_root_motion':'relative to frame 1','finger_policy':('neutral rest pose' if neutral_hands else 'synthetic fixed 20 degrees on holding hand; source has no finger joints'),
            'hand_policy':('neutral relative to forearm' if neutral_hands else 'source terminal-joint rotation'),
            'weapon_bone':'bone_28','weapon_tip':tip,'frames_rotations':samples,'direction_checks':direction_checks,
            'limitations':'Rest-direction aligned rotation transfer with heuristic joint mapping and root scale; no IK, motion correction, hand grasp or official retarget parity.'}
    (output/'retarget.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'frames':len(v),'mapped_joints':len(MAPPING),'translation_scale':translation_scale,'vertices':len(v[0])}),flush=True)


if __name__=='__main__': main(*(Path(x) for x in sys.argv[1:]))
