"""MoMask HumanML3D 관절 모션을 Anny 모델 프레임으로 리타깃·렌더한다."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
import numpy as np
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/motion-sheet/mannequin-walk-v6'
BLENDER=ROOT/'.local/blender-runtime/bin/python'
DIRECTIONS={'down_left','down_right','up_left','up_right'}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def render(motion_path, output_dir, directions, sample_indices, animate_hand_closure=False):
    motion_path=Path(motion_path).resolve();output_dir=Path(output_dir).resolve()
    if not output_dir.is_relative_to(ROOT/'.tmp'): raise ValueError('Anny 출력은 .tmp 하위여야 합니다.')
    joints=np.load(motion_path,allow_pickle=False)['joints']
    if joints.ndim!=3 or joints.shape[1:]!=(22,3): raise ValueError('HumanML3D-22 관절 모션이 필요합니다.')
    if not sample_indices or min(sample_indices)<0 or max(sample_indices)>=len(joints): raise ValueError('유효한 샘플 인덱스가 필요합니다.')
    if not set(directions) or set(directions)-DIRECTIONS: raise ValueError('방향 선택 오류')
    output_dir.mkdir(parents=True,exist_ok=False);(output_dir/'inputs').mkdir()
    source_motion=output_dir/'inputs/mannequin-motion.npz';np.savez_compressed(source_motion,joints=joints,rest=joints[0],contacts=np.zeros((len(joints),2),dtype=np.float32),sample_indices=np.array(sample_indices))
    (output_dir/'inputs/artifact.json').write_text(json.dumps({'files':{'mannequin-motion.npz':digest(source_motion)}},ensure_ascii=False))
    baseline_selection_record=yaml.safe_load((ROOT/'generators/animation/config/anny_model_baseline.yaml').read_text())
    baseline_manifest_record=yaml.safe_load((ROOT/baseline_selection_record['manifest_path']).read_text())
    baseline_blend_path=ROOT/baseline_selection_record['blend_path']
    baseline_blend_hash=digest(baseline_blend_path)
    if baseline_blend_hash!=baseline_manifest_record['files'][baseline_blend_path.name]['sha256']:raise ValueError('기준 모델 Blender 해시 불일치')
    baseline_model_record={'baseline_id':baseline_selection_record['baseline_id'],'source_generation_id':baseline_manifest_record['source_generation_id'],'blend_sha256':baseline_blend_hash,'attributes_sha256':baseline_selection_record['attributes_sha256']}
    (output_dir/'baseline-model.json').write_text(json.dumps(baseline_model_record,ensure_ascii=False,indent=2))
    print('ANNY 기준 모델: '+baseline_selection_record['baseline_id'],flush=True)
    shutil.copy2(baseline_blend_path,output_dir/'inputs/anny-reference-fit-rig.blend')
    for name in ('run_stage.py','retarget_loop.py','render_asset.py'):
        shutil.copy2(SOURCE/name,output_dir/name)
    shutil.copy2(ROOT/'generators/momask/anny_hand_pose.py',output_dir/'anny_hand_pose.py')
    shutil.copy2(ROOT/'generators/momask/anny_arm_retarget.py',output_dir/'anny_arm_retarget.py')
    retarget=(output_dir/'retarget_loop.py').read_text()
    retarget=retarget.replace('from mathutils import Vector, Matrix','from mathutils import Vector, Matrix\nfrom anny_hand_pose import build_fist_rotations, calculate_fist_weight')
    retarget=retarget.replace('rig_object_value.animation_data_clear();', 'finger_rotation_values=build_fist_rotations(rig_object_value)\nrig_object_value.animation_data_clear();')
    retarget=retarget.replace("  current_pose_bone.keyframe_insert('rotation_quaternion',frame=current_frame_number)", "  if current_bone_name in finger_rotation_values:current_pose_bone.rotation_quaternion=finger_rotation_values[current_bone_name].__class__((1,0,0,0)).slerp(finger_rotation_values[current_bone_name], calculate_fist_weight(current_frame_number,len(source_joint_frames),ANIMATE_HAND_CLOSURE))\n  current_pose_bone.keyframe_insert('rotation_quaternion',frame=current_frame_number)")
    # 팔을 올릴 때 쇄골도 원본 어깨 관절을 따라가도록 한다.
    retarget=retarget.replace("def calculate_body_rotation(current_joint_points,current_upper_index):", "for current_side_label,current_joint_ids in [('L',(13,16)),('R',(14,17))]:\n for current_bone_prefix in ('clavicle','shoulder01'):\n  segment_mapping_values[current_bone_prefix+'.'+current_side_label]=('clavicle.'+current_side_label,'upperarm01.'+current_side_label,*current_joint_ids)\ndef calculate_body_rotation(current_joint_points,current_upper_index):")
    retarget=retarget.replace("rig_object_value.animation_data_clear();", "for current_skin_modifier in body_object_value.modifiers:\n if current_skin_modifier.type=='ARMATURE':current_skin_modifier.use_deform_preserve_volume=True\nrig_object_value.animation_data_clear();")
    retarget=retarget.replace('from anny_hand_pose import', 'from anny_arm_retarget import calculate_arm_rotations\nfrom anny_hand_pose import')
    retarget=retarget.replace("CURRENT_PROGRESS_STATE['stage']='retarget'", "previous_arm_planes={}\nCURRENT_PROGRESS_STATE['stage']='retarget'")
    retarget=retarget.replace(' pelvis_rotation_value=calculate_body_rotation', ' arm_rotation_values=calculate_arm_rotations(current_joint_points,rest_bone_positions,rest_bone_rotations,previous_arm_planes)\n pelvis_rotation_value=calculate_body_rotation')
    retarget=retarget.replace("  if target_rotation_value is not None:", "  if current_bone_name in arm_rotation_values:target_rotation_value=arm_rotation_values[current_bone_name]\n  if target_rotation_value is not None:")
    retarget=retarget.replace("scene_render_value=bpy.context.scene;", "joint_corrective_modifier=body_object_value.modifiers.new('AnnyJointCorrective','CORRECTIVE_SMOOTH')\njoint_corrective_modifier.factor=.5\njoint_corrective_modifier.iterations=4\njoint_corrective_modifier.smooth_type='LENGTH_WEIGHTED'\nscene_render_value=bpy.context.scene;")
    retarget=retarget.replace('ANIMATE_HAND_CLOSURE',repr(animate_hand_closure))
    retarget=retarget.replace("assert source_joint_frames.shape==(25,22,3) and np.isfinite(source_joint_frames).all()", "assert source_joint_frames.ndim==3 and source_joint_frames.shape[1:]==(22,3) and np.isfinite(source_joint_frames).all()")
    retarget=retarget.replace("scene_render_value.frame_start=1;scene_render_value.frame_end=25", "scene_render_value.frame_start=1;scene_render_value.frame_end=len(source_joint_frames)")
    retarget=retarget.replace("for current_frame_number in [1,25]:", "for current_frame_number in [1,len(source_joint_frames)]:")
    retarget=retarget.replace("for current_frame_number in range(1,26):", "for current_frame_number in range(1,len(source_joint_frames)+1):")
    if (motion_path.parent/'standing-corrections.yaml').is_file():
        # 대기 호흡은 골반→가슴 전체 기울기가 아닌 가슴 구간의 상대 회전을 전달한다.
        retarget=retarget.replace("torso_rotation_value=calculate_body_rotation(current_joint_points,9)", "torso_rotation_value=calculate_body_rotation(current_joint_points,9)\n source_chest_reference=Vector(source_joint_frames[0,9]-source_joint_frames[0,6])\n current_chest_direction=Vector(current_joint_points[9]-current_joint_points[6])\n chest_rotation_delta=source_chest_reference.rotation_difference(current_chest_direction)")
        retarget=retarget.replace("elif current_bone_name.startswith('spine'):target_rotation_value=torso_rotation_value@rest_bone_rotations[current_bone_name]", "elif current_bone_name in ('spine01','spine02'):target_rotation_value=chest_rotation_delta@rest_bone_rotations[current_bone_name]\n  elif current_bone_name=='spine03':target_rotation_value=chest_rotation_delta.__class__((1,0,0,0)).slerp(chest_rotation_delta,.5)@rest_bone_rotations[current_bone_name]\n  elif current_bone_name.startswith('spine'):target_rotation_value=rest_bone_rotations[current_bone_name]")
    (output_dir/'retarget_loop.py').write_text(retarget)
    cameras={key:value for key,value in {'down_left':(26**.5,-26**.5,3),'down_right':(-26**.5,-26**.5,3),'up_left':(26**.5,26**.5,3),'up_right':(-26**.5,26**.5,3)}.items() if key in directions}
    renderer=(output_dir/'render_asset.py').read_text()
    renderer=renderer.replace('OUTPUT_SAMPLE_FRAMES=[1,4,7,10,13,16,19,22]',f'OUTPUT_SAMPLE_FRAMES={[index+1 for index in sample_indices]!r}')
    renderer=renderer.replace("DIRECTION_CAMERA_POINTS={'down_left':(CAMERA_HORIZONTAL_OFFSET,-CAMERA_HORIZONTAL_OFFSET,3),'down_right':(-CAMERA_HORIZONTAL_OFFSET,-CAMERA_HORIZONTAL_OFFSET,3),'up_left':(CAMERA_HORIZONTAL_OFFSET,CAMERA_HORIZONTAL_OFFSET,3),'up_right':(-CAMERA_HORIZONTAL_OFFSET,CAMERA_HORIZONTAL_OFFSET,3)}",f'DIRECTION_CAMERA_POINTS={cameras!r}')
    renderer=renderer.replace("scene_render_value.cycles.samples=64", "scene_render_value.cycles.samples=16")
    renderer=renderer.replace("if endpoint_max_error>1e-5:raise ValueError(f'루프 끝점 불일치 {endpoint_max_error}')", "print(f'비루프 모션 끝점 차이 {endpoint_max_error}')")
    (output_dir/'render_asset.py').write_text(renderer)
    for script in ('retarget_loop.py','render_asset.py'):
        subprocess.run([str(BLENDER),str(output_dir/'run_stage.py'),str(output_dir/script)],cwd=output_dir,check=True)
    for direction in directions:
        target=output_dir/direction/'frames';target.mkdir()
        for number in range(1,len(sample_indices)+1): shutil.copy2(output_dir/direction/f'preview-{number:04d}.png',target/f'anny-{number:04d}.png')
    (output_dir/'result.json').write_text(json.dumps({'renderer':'Anny Blender retarget','frames':len(sample_indices),'directions':directions,'samples':16,'hand_pose':'fist-v3','arm_retarget':'elbow-plane-limited-v1','skinning':'dual-quaternion-corrective-v1','hand_closure_animation':animate_hand_closure,'baseline_model':baseline_model_record},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--motion',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--directions',required=True);p.add_argument('--sample-indices',required=True);p.add_argument('--animate-hand-closure',action='store_true');a=p.parse_args();render(a.motion,a.output_dir,a.directions.split(','),[int(x) for x in a.sample_indices.split(',')],a.animate_hand_closure)
