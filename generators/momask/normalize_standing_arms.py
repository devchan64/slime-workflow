"""대기 모션의 팔 간격과 가슴 중심 후방 호흡을 보정한다."""
from pathlib import Path
import argparse
import numpy as np
import yaml

ARMS = ((16,18,20),(17,19,21))  # shoulder, elbow, wrist
LOWER_BODY = (1,2,4,5,7,8,10,11)  # hips, knees, ankles, toes
UPPER_BODY = (0,3,6,9,12,13,14,15,16,17)  # pelvis-to-head and shoulders

STANDING_CORRECTION_VALUES=yaml.safe_load((Path(__file__).parent/'config/standing-corrections.yaml').read_text())
def correct_standing_posture(motion_joint_values, applied_correction_values=None):
    applied_correction_values=STANDING_CORRECTION_VALUES if applied_correction_values is None else applied_correction_values
    # 골반 기준 상체 전방 기울기를 제한하고 팔을 몸통 옆으로 소폭 벌린다.
    torso_direction_values=motion_joint_values[:,9]-motion_joint_values[:,0]
    torso_pitch_values=np.arctan2(torso_direction_values[:,2],torso_direction_values[:,1])
    correction_angle_values=np.clip(torso_pitch_values,-np.radians(applied_correction_values['max_torso_pitch_degrees']),np.radians(applied_correction_values['max_torso_pitch_degrees']))-torso_pitch_values
    upper_joint_indices=[3,6,9,12,13,14,15,16,17,18,19,20,21]
    relative_joint_values=motion_joint_values[:,upper_joint_indices]-motion_joint_values[:,0,None]
    original_height_values=relative_joint_values[:,:,1].copy()
    original_depth_values=relative_joint_values[:,:,2].copy()
    relative_joint_values[:,:,1]=np.cos(correction_angle_values)[:,None]*original_height_values-np.sin(correction_angle_values)[:,None]*original_depth_values
    relative_joint_values[:,:,2]=np.sin(correction_angle_values)[:,None]*original_height_values+np.cos(correction_angle_values)[:,None]*original_depth_values
    motion_joint_values[:,upper_joint_indices]=relative_joint_values+motion_joint_values[:,0,None]
    shoulder_lateral_values=motion_joint_values[:,16]-motion_joint_values[:,17]
    shoulder_lateral_values[:,1]=0
    shoulder_lateral_values/=np.maximum(np.linalg.norm(shoulder_lateral_values,axis=1)[:,None],1e-8)
    for shoulder_joint_index,elbow_joint_index,wrist_joint_index in ARMS:
        upper_length_values=np.linalg.norm(motion_joint_values[:,elbow_joint_index]-motion_joint_values[:,shoulder_joint_index],axis=1)
        lower_length_values=np.linalg.norm(motion_joint_values[:,wrist_joint_index]-motion_joint_values[:,elbow_joint_index],axis=1)
        outward_direction_values=shoulder_lateral_values*(1 if shoulder_joint_index==16 else -1)
        arm_direction_values=outward_direction_values*np.sin(np.radians(applied_correction_values['upper_arm_outward_degrees']))
        arm_direction_values[:,1]=-np.cos(np.radians(applied_correction_values['upper_arm_outward_degrees']))
        motion_joint_values[:,elbow_joint_index]=motion_joint_values[:,shoulder_joint_index]+arm_direction_values*upper_length_values[:,None]
        forearm_direction_values=outward_direction_values*np.sin(np.radians(applied_correction_values['forearm_outward_degrees']))
        forearm_direction_values[:,1]=-np.cos(np.radians(applied_correction_values['forearm_outward_degrees']))
        motion_joint_values[:,wrist_joint_index]=motion_joint_values[:,elbow_joint_index]+forearm_direction_values*lower_length_values[:,None]
    return motion_joint_values

def normalize(path: Path, correction_config_path=None) -> dict:
    applied_correction_values=yaml.safe_load(Path(correction_config_path).read_text()) if correction_config_path else STANDING_CORRECTION_VALUES
    bundle=np.load(path,allow_pickle=False)
    if 'joints' not in bundle.files: raise ValueError('joints 모션이 필요합니다.')
    joints=bundle['joints'].copy()
    if joints.ndim!=3 or joints.shape[1:]!=(22,3): raise ValueError('HumanML3D-22 관절 모션이 필요합니다.')
    # 대기는 이동·보행이 아니므로 골반 수평 위치와 양발 지지점을 첫 프레임에 고정한다.
    root_offset=joints[:,0,[0,2]]-joints[0,0,[0,2]]
    joints[:,:,[0,2]]-=root_offset[:,None,:]
    joints[:,LOWER_BODY]=joints[0,LOWER_BODY]
    # 전신 상하 이동 대신 가슴의 작은 팽창을 강조하고 어깨 움직임은 억제한다.
    phase=np.linspace(0,2*np.pi,len(joints),endpoint=False)
    breathing_cycle_values=(1-np.cos(phase))/2
    stable_upper_positions=joints[0,UPPER_BODY].copy()
    joints[:,UPPER_BODY]=stable_upper_positions
    for shoulder,elbow,wrist in ARMS:
        upper_lengths=np.linalg.norm(joints[:,elbow]-joints[:,shoulder],axis=1)
        lower_lengths=np.linalg.norm(joints[:,wrist]-joints[:,elbow],axis=1)
        joints[:,elbow]=joints[:,shoulder]+np.column_stack((np.zeros(len(joints)), -upper_lengths, np.zeros(len(joints))))
        joints[:,wrist]=joints[:,elbow]+np.column_stack((np.zeros(len(joints)), -lower_lengths, np.zeros(len(joints))))
    joints=correct_standing_posture(joints,applied_correction_values)
    # 가슴 아래 관절을 중심으로 상부를 뒤로 회전한다. 어깨 승모 동작은 추가하지 않는다.
    chest_upper_indices=[9,12,13,14,15,16,17]
    shoulder_before_values=joints[:,[16,17]].copy()
    chest_pivot_values=joints[:,6,None].copy()
    chest_relative_values=joints[:,chest_upper_indices]-chest_pivot_values
    chest_rotation_values=-np.radians(applied_correction_values['chest_backward_rotation_degrees'])*breathing_cycle_values
    chest_height_values=chest_relative_values[:,:,1].copy()
    chest_depth_values=chest_relative_values[:,:,2].copy()
    chest_relative_values[:,:,1]=np.cos(chest_rotation_values)[:,None]*chest_height_values-np.sin(chest_rotation_values)[:,None]*chest_depth_values
    chest_relative_values[:,:,2]=np.sin(chest_rotation_values)[:,None]*chest_height_values+np.cos(chest_rotation_values)[:,None]*chest_depth_values
    joints[:,chest_upper_indices]=chest_relative_values+chest_pivot_values
    # 팔은 가슴 회전각을 복제하지 않고 어깨 이동만 따라간다.
    for shoulder_side_index,(shoulder_joint_index,elbow_joint_index,wrist_joint_index) in enumerate(ARMS):
        shoulder_shift_values=joints[:,shoulder_joint_index]-shoulder_before_values[:,shoulder_side_index]
        joints[:,[elbow_joint_index,wrist_joint_index]]+=shoulder_shift_values[:,None]
    result={name:bundle[name] for name in bundle.files};result['joints']=joints
    np.savez_compressed(path,**result)
    (path.parent/'standing-corrections.yaml').write_text(yaml.safe_dump(applied_correction_values,sort_keys=False))
    ratios=[]
    for shoulder,elbow,_ in ARMS:
        upper=joints[:,elbow]-joints[:,shoulder]
        ratios.extend((np.linalg.norm(upper[:,[0,2]],axis=1)/np.maximum(-upper[:,1],1e-6)).tolist())
    root_travel=float(np.linalg.norm(joints[:,0,[0,2]]-joints[0,0,[0,2]],axis=1).max())
    head_vertical_range=float(np.ptp(joints[:,15,1]))
    return {'max_upper_arm_horizontal_to_down_ratio':float(max(ratios)),'max_root_horizontal_displacement_m':root_travel,'head_vertical_range_m':head_vertical_range}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--motion',type=Path,required=True);parser.add_argument('--correction-config',type=Path);args=parser.parse_args();print(normalize(args.motion,args.correction_config))
