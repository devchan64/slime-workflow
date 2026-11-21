"""방향 가중치와 영상 DWPose 얼굴 관측의 차이를 진단한다."""
import hashlib
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_body_face_experiment import FACE_LANDMARK_INDICES
from generators.kimodo.reference_proportions import REFERENCE_CONFIDENCE_THRESHOLD

VISIBILITY_ZERO_WEIGHT_TOLERANCE = 1e-8


def compare_direction_detector_evidence(current_weight_record,current_raw_frames,current_direct_record,current_direction_name):
    """0 가중치 관절의 높은 DWPose 점수와 3D 투영 거리 기록."""
    current_weights=current_weight_record.get('frames')
    current_views=current_direct_record.get('directions',{})
    if current_weight_record.get('direction')!=current_direction_name or current_direction_name not in current_views:
        raise ValueError('가중치와 직접 포즈의 출력 방향이 다릅니다.')
    current_direct=current_views[current_direction_name]
    current_direct_frames=np.asarray(current_direct['body_points_832x480'],dtype=float)
    if not isinstance(current_weights,list) or not isinstance(current_raw_frames,list) or current_direct_frames.ndim!=3 or current_direct_frames.shape[1:]!=(18,3) or len(current_weights)!=len(current_raw_frames) or len(current_weights)!=len(current_direct_frames) or not len(current_weights) or not np.isfinite(current_direct_frames).all():
        raise ValueError('가중치·DWPose·직접 포즈 프레임이 일치하지 않습니다.')
    if current_direct.get('source_frames')!=list(range(len(current_weights))):
        raise ValueError('직접 포즈의 원본 프레임 순서가 일치하지 않습니다.')
    current_rows=[]
    for current_index,(current_weight_frame,current_raw_frame) in enumerate(zip(current_weights,current_raw_frames)):
        current_weight_values=np.asarray(current_weight_frame.get('weights'),dtype=float)
        if current_weight_frame.get('frame')!=current_index or current_weight_values.shape!=(18,) or not np.isfinite(current_weight_values).all() or np.any((current_weight_values<0)|(current_weight_values>1)):
            raise ValueError('프레임별 관절 가중치 형식 오류')
        try:
            current_body=current_raw_frame[0][0][0]
        except (IndexError,TypeError) as current_error:
            raise ValueError('단일 인물 DWPose 검출 형식 오류') from current_error
        if not isinstance(current_body,list) or len(current_body)!=18:
            raise ValueError('단일 인물 BODY18 검출이 필요합니다.')
        for current_joint_index in FACE_LANDMARK_INDICES:
            current_detection=current_body[current_joint_index]
            if current_detection is None:
                continue
            if not isinstance(current_detection,list) or len(current_detection)<3 or not all(type(current_value) in (int,float) and np.isfinite(current_value) for current_value in current_detection[:3]):
                raise ValueError('DWPose 관절 좌표 또는 점수 형식 오류')
            current_score=float(current_detection[2])
            current_weight=float(current_weight_values[current_joint_index])
            if current_weight<=VISIBILITY_ZERO_WEIGHT_TOLERANCE and current_score>=REFERENCE_CONFIDENCE_THRESHOLD:
                current_distance=float(np.linalg.norm(np.asarray(current_detection[:2])-current_direct_frames[current_index,current_joint_index,:2]))
                current_rows.append({'frame':current_index,'joint':current_joint_index,'weight':current_weight,'detector_score':current_score,'projected_distance_px':current_distance,'detected_xy':current_detection[:2],'projected_xy':current_direct_frames[current_index,current_joint_index,:2].tolist()})
    return {'schema':'kimodo-visibility-disagreement-v1','direction':current_direction_name,'frames':len(current_weights),'score_threshold':REFERENCE_CONFIDENCE_THRESHOLD,'zero_weight_tolerance':VISIBILITY_ZERO_WEIGHT_TOLERANCE,'rows':current_rows,'limitations':['방향 가중치는 참조 시점의 사람 판단을 보간한 값이며 실제 가림 판정이 아님','DWPose 점수는 가시성 확률이 아니며 높은 점수도 가림이나 오검출을 배제하지 않음','3D 앵커 투영과 DWPose의 좌표 차이는 양쪽의 오차를 모두 포함','카메라 방향과 영점 정합이 가정이며 동일 프레임의 후처리 전 검출만 비교']}


def calculate_local_white_fraction(current_image_array,current_image_point):
    """검수용 흰 배경 렌더에서 관절 주변 5×5 밝은 픽셀 비율을 기록한다."""
    current_image_array=np.asarray(current_image_array)
    current_image_point=np.asarray(current_image_point,dtype=float)
    if current_image_array.ndim!=3 or current_image_array.shape[2]!=3 or current_image_array.dtype!=np.uint8 or current_image_point.shape!=(2,) or not np.isfinite(current_image_point).all():
        raise ValueError('렌더 이미지 또는 관절 좌표 형식 오류')
    current_horizontal,current_vertical=np.rint(current_image_point).astype(int)
    if current_horizontal<2 or current_vertical<2 or current_horizontal>=current_image_array.shape[1]-2 or current_vertical>=current_image_array.shape[0]-2:
        raise ValueError('관절점 주변 검수 영역이 영상 범위를 벗어났습니다.')
    current_patch=current_image_array[current_vertical-2:current_vertical+3,current_horizontal-2:current_horizontal+3]
    return float(np.mean(np.min(current_patch,axis=2)>=245))


def inspect_disagreement_render(current_report,current_video_path):
    """불일치 프레임의 두 좌표 주변 백색 비율을 영상에서 측정한다."""
    import cv2
    current_capture=cv2.VideoCapture(str(current_video_path))
    if not current_capture.isOpened():
        raise ValueError('검수 렌더 영상을 열 수 없습니다.')
    try:
        if int(current_capture.get(cv2.CAP_PROP_FRAME_COUNT))!=current_report['frames']:
            raise ValueError('검수 렌더와 관절 기록의 프레임 수가 다릅니다.')
        current_rows=[]
        for current_row in current_report['rows']:
            current_capture.set(cv2.CAP_PROP_POS_FRAMES,current_row['frame'])
            current_ok,current_image=current_capture.read()
            if not current_ok:
                raise ValueError('검수 렌더 프레임을 읽지 못했습니다.')
            current_rows.append({**current_row,'detected_white_fraction_5x5':calculate_local_white_fraction(current_image,current_row['detected_xy']),'projected_white_fraction_5x5':calculate_local_white_fraction(current_image,current_row['projected_xy'])})
    finally:
        current_capture.release()
    return {**current_report,'rows':current_rows,'render_check':'5×5 픽셀의 RGB 각 채널 245 이상인 비율. 흰 배경 렌더에서만 해석; 메시 부위와 깊이·가림을 판정하지 않음.'}


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='방향 가중치와 DWPose 관측 차이 검수')
    for current_name in ('weights','raw','direct'):
        current_parser.add_argument(current_name,type=Path)
    current_parser.add_argument('direction')
    current_parser.add_argument('output',type=Path)
    current_parser.add_argument('--render-video',type=Path,help='동일 방향 흰 배경 SOMA 렌더의 검수')
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 관측 차이 기록을 덮어쓰지 않습니다.')
    current_inputs={current_name:json.loads(getattr(current_arguments,current_name).read_text()) for current_name in ('weights','raw','direct')}
    current_result=compare_direction_detector_evidence(current_inputs['weights'],current_inputs['raw'],current_inputs['direct'],current_arguments.direction)
    if current_arguments.render_video is not None:
        current_result=inspect_disagreement_render(current_result,current_arguments.render_video)
        current_result['render_sha256']=hashlib.sha256(current_arguments.render_video.read_bytes()).hexdigest()
    current_result['inputs']={current_name:{'path':str(getattr(current_arguments,current_name)),'sha256':hashlib.sha256(getattr(current_arguments,current_name).read_bytes()).hexdigest()} for current_name in current_inputs}
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
    print(f'방향 가중치·검출 차이 저장: {current_arguments.output}',flush=True)
