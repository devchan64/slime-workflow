"""대기 모션의 팔을 몸통 옆 수직 자세로 정규화한다."""
from pathlib import Path
import argparse
import numpy as np

ARMS = ((16,18,20),(17,19,21))  # shoulder, elbow, wrist
LOWER_BODY = (1,2,4,5,7,8,10,11)  # hips, knees, ankles, toes
UPPER_BODY = (0,3,6,9,12,13,14,15,16,17)  # pelvis-to-head and shoulders

def normalize(path: Path) -> dict:
    bundle=np.load(path,allow_pickle=False)
    if 'joints' not in bundle.files: raise ValueError('joints 모션이 필요합니다.')
    joints=bundle['joints'].copy()
    if joints.ndim!=3 or joints.shape[1:]!=(22,3): raise ValueError('HumanML3D-22 관절 모션이 필요합니다.')
    # 대기는 이동·보행이 아니므로 골반 수평 위치와 양발 지지점을 첫 프레임에 고정한다.
    root_offset=joints[:,0,[0,2]]-joints[0,0,[0,2]]
    joints[:,:,[0,2]]-=root_offset[:,None,:]
    joints[:,LOWER_BODY]=joints[0,LOWER_BODY]
    # 발은 고정하고, 작은 좌우 이동보다 상체의 느린 상하 리듬을 분명하게 보인다.
    phase=np.linspace(0,2*np.pi,len(joints),endpoint=False)
    lateral_sway=0.015*np.sin(phase)
    vertical_sway=0.080*np.sin(phase)
    joints[:,UPPER_BODY,0]+=lateral_sway[:,None]
    joints[:,UPPER_BODY,1]+=vertical_sway[:,None]
    for shoulder,elbow,wrist in ARMS:
        upper_lengths=np.linalg.norm(joints[:,elbow]-joints[:,shoulder],axis=1)
        lower_lengths=np.linalg.norm(joints[:,wrist]-joints[:,elbow],axis=1)
        joints[:,elbow]=joints[:,shoulder]+np.column_stack((np.zeros(len(joints)), -upper_lengths, np.zeros(len(joints))))
        joints[:,wrist]=joints[:,elbow]+np.column_stack((np.zeros(len(joints)), -lower_lengths, np.zeros(len(joints))))
    result={name:bundle[name] for name in bundle.files};result['joints']=joints
    np.savez_compressed(path,**result)
    ratios=[]
    for shoulder,elbow,_ in ARMS:
        upper=joints[:,elbow]-joints[:,shoulder]
        ratios.extend((np.linalg.norm(upper[:,[0,2]],axis=1)/np.maximum(-upper[:,1],1e-6)).tolist())
    root_travel=float(np.linalg.norm(joints[:,0,[0,2]]-joints[0,0,[0,2]],axis=1).max())
    head_vertical_range=float(np.ptp(joints[:,15,1]))
    return {'max_upper_arm_horizontal_to_down_ratio':float(max(ratios)),'max_root_horizontal_displacement_m':root_travel,'head_vertical_range_m':head_vertical_range}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--motion',type=Path,required=True);args=parser.parse_args();print(normalize(args.motion))
