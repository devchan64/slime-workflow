"""휴식 동작의 시작·유지·종료 자세를 원본 관절로 검수한다."""
import numpy as np


def inspect_resting_motion(joint_frame_values):
    warnings = []
    def standing_score(frame):
        leg_lengths = [np.linalg.norm(frame[hip]-frame[knee])+np.linalg.norm(frame[knee]-frame[ankle]) for hip,knee,ankle in ((1,4,7),(2,5,8))]
        leg_extension = [(frame[hip,1]-frame[ankle,1])/length for (hip,ankle),length in zip(((1,7),(2,8)),leg_lengths)]
        torso_vector = frame[12]-frame[0]
        return min(leg_extension), torso_vector[1]/max(np.linalg.norm(torso_vector),1e-6)
    endpoint_count = max(1, len(joint_frame_values)//10)
    for label, frames in [('시작',joint_frame_values[:endpoint_count]),('종료',joint_frame_values[-endpoint_count:])]:
        scores = [standing_score(frame) for frame in frames]
        extension, upright = np.min(scores, axis=0)
        if extension < .85 or upright < .9:
            warnings.append(f'{label} 직립 미충족: 다리 수직 신장률={extension:.2f}, 몸통 직립률={upright:.2f}')
    # 중간 구간의 낮은 골반 유지 여부만 검사하며 접촉·앉은 자세의 완전성을 보장하지 않는다.
    reference_length = sum(np.linalg.norm(joint_frame_values[0,a]-joint_frame_values[0,b]) for a,b in ((1,4),(4,7)))
    middle_frames = joint_frame_values[len(joint_frame_values)//3:2*len(joint_frame_values)//3]
    pelvis_heights = middle_frames[:,0,1]-np.minimum(middle_frames[:,7,1],middle_frames[:,8,1])
    if np.mean(pelvis_heights < reference_length*.6) < .8:
        warnings.append('중간 낮은 자세 유지 미충족: 앉아서 머무르는 구간을 확인하세요.')
    pelvis_range = float(np.ptp(pelvis_heights)/max(reference_length,1e-6))
    local_middle = middle_frames-middle_frames[:,0:1,:]
    joint_drift = float(np.max(np.linalg.norm(local_middle-np.median(local_middle,axis=0),axis=2))/max(reference_length,1e-6))
    if pelvis_range > .12 or joint_drift > .20:
        warnings.append(f'앉은 자세 안정성 미충족: 골반 높이 변화/다리길이={pelvis_range:.2f}, 관절 최대 편차/다리길이={joint_drift:.2f}')
    return warnings
