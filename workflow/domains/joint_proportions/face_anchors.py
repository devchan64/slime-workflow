"""참조 얼굴 형태와 위치 관절로 근사한 머리 방향을 결합한다."""
import numpy as np

FACE_INDICES = (0, 14, 15, 16, 17)


def estimate_face_anchors(joints, *, local_offset=(0.0, 0.0, 0.0)):
    """BODY18 순서 다섯 3D 점. 독립 머리 회전·가림은 관측하지 않는다."""
    from generators.kimodo.reference_face_anchors import load_reference_face_template

    try:
        edit_offset = np.asarray(local_offset, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError('얼굴 오프셋은 세 유한 숫자여야 합니다.') from exc
    if edit_offset.shape != (3,) or not np.isfinite(edit_offset).all() or np.any(np.abs(edit_offset) > 1):
        raise ValueError('얼굴 오프셋은 몸통 길이 기준 각 축 -1~1이어야 합니다.')
    frames = np.asarray(joints, dtype=np.float64)
    if frames.ndim != 3 or frames.shape[1:] != (22, 3) or not len(frames) or not np.isfinite(frames).all():
        raise ValueError('유한한 HumanML3D [frames,22,3] 관절이 필요합니다.')
    template, source = load_reference_face_template()
    face = np.asarray(template['face_joint_positions'], dtype=np.float64)
    reference_body = np.asarray(template['body_joint_positions'], dtype=np.float64)
    reference_shoulder = reference_body[[0, 3]].mean(axis=0)
    eye_reference = (face[1] + face[2]) / 2 - reference_shoulder
    face_local = face - (face[1] + face[2]) / 2
    shoulders = frames[:, 16] - frames[:, 17]  # right -> left
    up = frames[:, 15] - frames[:, 12]
    up_length = np.linalg.norm(up, axis=1)
    torso_length = np.linalg.norm((frames[:, 16] + frames[:, 17] - frames[:, 1] - frames[:, 2]) / 2, axis=1)
    if np.any(up_length < 1e-8) or np.any(torso_length < 1e-8):
        raise ValueError('목·머리 또는 몸통 기준 길이가 0입니다.')
    up = up / up_length[:, None]
    side = shoulders - np.sum(shoulders * up, axis=1)[:, None] * up
    side_length = np.linalg.norm(side, axis=1)
    if np.any(side_length < 1e-8):
        raise ValueError('어깨 방향과 목·머리 방향이 평행합니다.')
    side = side / side_length[:, None]
    forward = np.cross(side, up)
    head_basis = np.stack((side, up, forward), axis=-1)
    body_side = shoulders / np.linalg.norm(shoulders, axis=1)[:,None]
    body_up = (frames[:, 16] + frames[:, 17] - frames[:, 1] - frames[:, 2]) / 2
    body_up -= body_side * np.sum(body_up * body_side, axis=1)[:, None]
    body_length = np.linalg.norm(body_up, axis=1)
    if np.any(body_length < 1e-8):
        raise ValueError('몸통 방향과 어깨 기준축이 평행합니다.')
    body_up /= body_length[:, None]
    body_basis = np.stack((body_side, body_up, np.cross(body_side, body_up)), axis=-1)
    shoulder_center = (frames[:, 16] + frames[:, 17]) / 2
    size = float(torso_length[0])
    head_local = np.einsum('fji,fj->fi', body_basis, frames[:, 15]-shoulder_center) / size
    head_in_body = np.einsum('fji,fjk->fik', body_basis, head_basis)
    relative_rotation = head_in_body @ head_in_body[0].T
    offset = eye_reference + head_local - head_local[0]
    relative_face = np.einsum('fij,kj->fki', relative_rotation, face_local) + offset[:,None,:]
    positions = shoulder_center[:,None,:] + np.einsum('fij,fkj->fki', body_basis, relative_face) * size
    positions += np.einsum('fij,j->fi', head_basis, edit_offset)[:,None,:] * size
    return positions, {'method': 'reference-face-first-frame-body-alignment-v2',
        'reference': source, 'scale_torso_first_frame': size,
        'local_offset': edit_offset.tolist(), 'local_offset_axes': 'shoulder right-to-left, neck-to-head, cross product; units: first-frame torso length',
        'head_origin': 'reference face aligned to body at first frame; subsequent head displacement relative to first frame',
        'orientation': 'neck-head axis and shoulder axis; independent head yaw unobserved',
        'visibility': 'not estimated', 'limitations': '첫 프레임의 머리 방향이 참조의 정면과 일치한다고 가정합니다. 참조는 정면·측면 정사영과 대칭 가정이며 독립 시선과 가림을 복원하지 않습니다.'}
