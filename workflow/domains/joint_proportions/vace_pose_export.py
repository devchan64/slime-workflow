"""HumanML3D 관절을 VideoX-Fun BODY18 색상의 VACE 제어 영상으로 투영한다."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

# OpenPose BODY18 index -> HumanML3D index. 코·눈·귀는 없는 관절이다.
BODY18_FROM_HUMANML3D = {1:12, 2:17, 3:19, 4:21, 5:16, 6:18, 7:20,
                         8:2, 9:5, 10:8, 11:1, 12:4, 13:7}
OUTPUT_FPS = 16
WIDTH, HEIGHT = 832, 480


def prepare_pose_frames(joints, source_fps, yaw_degrees=0, scale=0.8, *, include_face=False, face_local_offset=(0.0, 0.0, 0.0)):
    """Y축 위쪽 정사영, 클립 전체 고정 카메라. 재생시간을 유지하도록 선형 보간한다."""
    joints = np.asarray(joints)
    if joints.dtype.kind not in 'fiu' or joints.ndim != 3 or joints.shape[1:] != (22, 3) or not 2 <= len(joints) <= 10000 or not np.isfinite(joints).all():
        raise ValueError('관절 입력은 유한한 숫자 배열 [2~10000,22,3]이어야 합니다.')
    if type(source_fps) not in (int, float) or not math.isfinite(source_fps) or not 1 <= source_fps <= 120:
        raise ValueError('원본 FPS는 1~120이어야 합니다.')
    if type(yaw_degrees) not in (int, float) or not math.isfinite(yaw_degrees) or not -180 <= yaw_degrees <= 180:
        raise ValueError('카메라 각도는 -180~180도여야 합니다.')
    if type(scale) not in (int, float) or not math.isfinite(scale) or not .1 <= scale <= 1:
        raise ValueError('화면 크기 배율은 0.1~1이어야 합니다.')
    last_time = (len(joints)-1)/source_fps
    n = math.floor(last_time*OUTPUT_FPS + 1e-9)+1
    if n < 5:
        raise ValueError('16fps 변환 결과는 최소 5프레임이어야 합니다.')
    indices = np.arange(n, dtype=np.float64)*source_fps/OUTPUT_FPS
    low = np.floor(indices).astype(int)
    high = np.minimum(low+1, len(joints)-1)
    fraction = (indices-low)[:,None,None]
    sampled = joints[low].astype(np.float64)*(1-fraction) + joints[high].astype(np.float64)*fraction
    if type(include_face) is not bool:
        raise ValueError("얼굴 옵션은 bool이어야 합니다.")
    face = None
    if include_face:
        from workflow.domains.joint_proportions.face_anchors import estimate_face_anchors
        face, _ = estimate_face_anchors(sampled, local_offset=face_local_offset)
    angle = math.radians(yaw_degrees)
    # world-space x is screen right at zero; y is vertical. This does not claim facing direction.
    xy = np.stack((sampled[:,:,0]*math.cos(angle) + sampled[:,:,2]*math.sin(angle), -sampled[:,:,1]),axis=-1)
    projected = xy[:, list(BODY18_FROM_HUMANML3D.values())]
    if face is not None:
        face_xy = np.stack((face[:,:,0]*math.cos(angle) + face[:,:,2]*math.sin(angle), -face[:,:,1]), axis=-1)
        projected = np.concatenate((projected, face_xy), axis=1)
    low_bound = projected.min(axis=(0,1)); high_bound = projected.max(axis=(0,1))
    extent = high_bound-low_bound
    if np.max(extent) <= 1e-8:
        raise ValueError('투영한 관절 영역이 비어 있습니다.')
    # margins based on available image area, with camera held constant across the full clip.
    px = min((WIDTH-64)/max(extent[0],1e-8), (HEIGHT-64)/max(extent[1],1e-8))*scale
    center = (low_bound+high_bound)/2
    output = np.zeros((n,18,3),dtype=np.float64)
    for body_index, source_index in BODY18_FROM_HUMANML3D.items():
        output[:,body_index,:2] = (xy[:,source_index]-center)*px + np.array([WIDTH/2,HEIGHT/2])
        output[:,body_index,2] = 1
    if face is not None:
        from workflow.domains.joint_proportions.face_anchors import FACE_INDICES
        output[:, FACE_INDICES, :2] = (face_xy-center)*px + np.array([WIDTH/2,HEIGHT/2])
        output[:, FACE_INDICES, 2] = 1
    return output, indices


def validate_vace_frame_count(frame_count):
    """전체 모션을 분할·절단하지 않고 VACE의 프레임 제약을 검사한다."""
    if type(frame_count) is not int or not 5 <= frame_count <= 129 or (frame_count-1)%4:
        raise ValueError('전체 포즈 영상의 프레임 수가 VACE 조건(5~129, 4n+1)에 맞지 않습니다. 모션을 자동으로 자르거나 분할하지 않습니다.')
    return frame_count


def export_vace_pose(joints_path, output_dir, source_fps, *, yaw_degrees=0, scale=.8, provenance=None, include_face=False, face_local_offset=(0.0, 0.0, 0.0)):
    """기존 출력은 덮어쓰지 않으며 영상 및 출처 JSON을 지정 디렉터리에 저장한다."""
    import imageio.v2 as imageio
    from generators.kimodo.pose_rendering import render_fun_control_body
    source=Path(joints_path); dest=Path(output_dir)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 32*1024*1024:
        raise ValueError('32MiB 이하 일반 NPY 파일이 필요합니다.')
    if dest.exists() or dest.is_symlink():
        raise ValueError('기존 출력 경로는 덮어쓰지 않습니다.')
    data=source.read_bytes()
    import io
    joints=np.load(io.BytesIO(data),allow_pickle=False)
    points, source_indices=prepare_pose_frames(joints,source_fps,yaw_degrees,scale,include_face=include_face,face_local_offset=face_local_offset)
    validate_vace_frame_count(len(points))
    segments=[(0,len(points))]
    dest.mkdir(parents=True,exist_ok=False)
    files=[]
    for number,(start,end) in enumerate(segments,1):
        filename=f'pose-{number:03d}.mp4'; path=dest/filename
        with imageio.get_writer(str(path),fps=OUTPUT_FPS,codec='libx264',quality=8,macro_block_size=1,output_params=['-pix_fmt','yuv420p']) as writer:
            for frame in points[start:end]:
                writer.append_data(np.asarray(render_fun_control_body(frame)))
        files.append({'file':filename,'frames':end-start,'output_start_frame':start,'output_end_frame_exclusive':end,
                      'source_frame_positions':source_indices[start:end].tolist(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    face_record = None
    if include_face:
        from workflow.domains.joint_proportions.face_anchors import estimate_face_anchors
        low = np.floor(source_indices).astype(int)
        high = np.minimum(low + 1, len(joints) - 1)
        fraction = (source_indices-low)[:,None,None]
        sampled = joints[low]*(1-fraction) + joints[high]*fraction
        _, face_record = estimate_face_anchors(sampled, local_offset=face_local_offset)
    record={'schema':'humanml3d-vace-body18-v1','source_file':str(source),'source_sha256':hashlib.sha256(data).hexdigest(),
            'source_frames':len(joints),'source_fps':source_fps,'output_frames_before_split':len(points),'output_fps':OUTPUT_FPS,
            'width':WIDTH,'height':HEIGHT,'yaw_degrees':yaw_degrees,'scale':scale,'skeleton':'humanml3d-22',
            'mapping':BODY18_FROM_HUMANML3D,'missing_body18':[] if include_face else [0,14,15,16,17], 'face_estimate':face_record,'provenance':provenance,
            'files':files,'limitations':'직접 투영이며 DWPose 검출 결과가 아닙니다. 얼굴점은 옵션에 따라 추정하며 가림 판정은 없습니다. 손가락·무기는 없습니다. 카메라 0도는 캐릭터 정면을 뜻하지 않습니다. VACE 품질과 접지는 미검증입니다.'}
    (dest/'pose-export.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return record
