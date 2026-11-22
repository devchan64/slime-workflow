"""HumanML3D 22관절에 Kimodo BODY18 참조의 팔다리·폭 비율 적용.

이 모듈은 편집 계산만 제공하며 독립 생성기나 DWPose 추론을 시작하지 않는다.
"""
import numpy as np

from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS, REFERENCE_RATIO_SCHEMA

# HumanML3D: pelvis, L/R hip, spine1, L/R knee, spine2, L/R ankle,
# spine3, L/R foot, neck, L/R collar, head, L/R shoulder, elbow, wrist.
HUMANML3D_22_CHAINS = {
    'left': {'hip': 1, 'knee': 4, 'ankle': 7, 'foot': 10, 'collar': 13, 'shoulder': 16, 'elbow': 18, 'wrist': 20},
    'right': {'hip': 2, 'knee': 5, 'ankle': 8, 'foot': 11, 'collar': 14, 'shoulder': 17, 'elbow': 19, 'wrist': 21},
}


def _unit(vector, name):
    lengths = np.linalg.norm(vector, axis=-1, keepdims=True)
    if (lengths <= 1e-8).any():
        raise ValueError(f'{name}: 길이가 0인 관절 구간이 있습니다.')
    return vector / lengths


def adjust_humanml3d_proportions(joints, reference):
    """비율을 몸통 중앙값 기준으로 적용하고 골반·프레임별 루트 이동을 유지한다.

    참조의 코/얼굴 기반 몸통 축은 HumanML3D에 대응 관절이 없어 적용하지 않는다.
    칼라·척추·목·머리의 상대 벡터와 발의 발목 상대 벡터를 유지한다.
    """
    raw = np.asarray(joints)
    if raw.dtype.kind not in 'fiu' or raw.ndim != 3 or raw.shape[1:] != (22, 3) or not 1 <= len(raw) <= 10000:
        raise ValueError('관절 입력은 1~10000프레임의 숫자 배열 [프레임,22,3]이어야 합니다.')
    original = raw.astype(np.float64, copy=True)
    if not np.isfinite(original).all():
        raise ValueError('관절 좌표에 비유한 값이 있습니다.')
    if not isinstance(reference, dict) or reference.get('schema') != REFERENCE_RATIO_SCHEMA:
        raise ValueError('Kimodo BODY18 v4 참조 비율 기록이 필요합니다.')
    ratios = reference.get('ratios')
    if not isinstance(ratios, dict) or set(ratios) != set(REFERENCE_SEGMENT_GROUPS):
        raise ValueError('참조 신체 비율 필드 오류')
    for name, value in ratios.items():
        if type(value) not in (int, float) or not np.isfinite(value) or not 0.05 <= value <= 5:
            raise ValueError(f'{name}: 참조 비율이 허용 범위를 벗어났습니다.')
    result = original.copy()
    l, r = HUMANML3D_22_CHAINS['left'], HUMANML3D_22_CHAINS['right']
    shoulders = original[:, [l['shoulder'], r['shoulder']]].mean(axis=1)
    hips = original[:, [l['hip'], r['hip']]].mean(axis=1)
    torso = np.linalg.norm(shoulders - hips, axis=-1)
    if (torso <= 1e-8).any():
        raise ValueError('몸통 기준 길이가 0인 프레임이 있습니다.')
    base = float(np.median(torso))
    for group, center, names in [('shoulder_width', shoulders, ('shoulder',)), ('hip_width', hips, ('hip',))]:
        key = names[0]
        direction = _unit(original[:, r[key]] - original[:, l[key]], group)
        half = direction * (ratios[group] * base / 2)
        result[:, l[key]] = center - half
        result[:, r[key]] = center + half
    for side in (l, r):
        # 상완 방향, 전완 방향은 원본 그대로 유지한다.
        for group, parent, child in [('upper_arm', 'shoulder', 'elbow'), ('forearm', 'elbow', 'wrist'),
                                      ('thigh', 'hip', 'knee'), ('shin', 'knee', 'ankle')]:
            direction = _unit(original[:, side[child]] - original[:, side[parent]], group)
            result[:, side[child]] = result[:, side[parent]] + direction * (ratios[group] * base)
        # 발은 발목에 고정하며 발 형상과 원본의 발목 상대 방향을 보존한다.
        result[:, side['foot']] = result[:, side['ankle']] + original[:, side['foot']] - original[:, side['ankle']]
    if not np.isfinite(result).all():
        raise ValueError('보정 관절에 비유한 값이 있습니다.')
    return result.astype(raw.dtype if raw.dtype.kind == 'f' else np.float64), {
        'schema': 'humanml3d-reference-proportions-v1', 'skeleton': 'humanml3d-22',
        'reference_schema': REFERENCE_RATIO_SCHEMA, 'torso_length_median': base,
        'applied': ['shoulder_width', 'hip_width', 'upper_arm', 'forearm', 'thigh', 'shin'],
        'not_applied': ['face_and_head', 'torso_axis', 'weapon', 'finger_joints'],
        'limitations': '2D 추정 비율이며 절대 3D 체형, 발 접지, 충돌, 손·무기 접촉은 보장하지 않습니다.',
    }
