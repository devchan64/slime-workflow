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
    # 대기 중에는 발을 떼지 않고 1.2cm 범위에서만 체중을 좌우로 옮긴다.
    sway=0.036*np.sin(np.linspace(0,2*np.pi,len(joints),endpoint=False))
    joints[:,UPPER_BODY,0]+=sway[:,None]
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
    return {'max_upper_arm_horizontal_to_down_ratio':float(max(ratios)),'max_root_horizontal_displacement_m':root_travel}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--motion',type=Path,required=True);args=parser.parse_args();print(normalize(args.motion))
