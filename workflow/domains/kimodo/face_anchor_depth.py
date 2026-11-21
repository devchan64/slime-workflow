"""Kimodo 얼굴 앵커 깊이 기록을 읽기 전용으로 요약한다."""
import json
import math
import statistics
from functools import lru_cache
from pathlib import Path

FACE_DEPTH_JOINT_NAMES = {0:'코',14:'오른쪽 눈',15:'왼쪽 눈',16:'오른쪽 귀',17:'왼쪽 귀'}
FACE_DEPTH_MAXIMUM_BYTES = 16*1024*1024


def summarize_face_anchor_depth(current_depth_record,current_expected_frames,current_expected_directions):
    """검증 가능한 깊이 차이만 방향과 얼굴 관절별로 요약한다."""
    if not isinstance(current_depth_record,dict):
        raise ValueError('얼굴 앵커 깊이 기록 형식 오류')
    if current_depth_record.get('schema')=='kimodo-face-anchor-depth-v1':
        return {'status':'invalid','message':'v1은 직교 카메라 깊이 변환 오류가 있어 사용할 수 없습니다.'}
    if current_depth_record.get('schema')!='kimodo-face-anchor-depth-v2':
        raise ValueError('알 수 없는 얼굴 앵커 깊이 기록 버전')
    current_views=current_depth_record.get('directions')
    if type(current_expected_frames) is not int or current_expected_frames<=0 or not isinstance(current_views,dict) or set(current_views)!=set(current_expected_directions):
        raise ValueError('깊이 기록의 방향 또는 프레임 정보가 다릅니다.')
    current_output=[]
    for current_direction,current_frames in current_views.items():
        if not isinstance(current_frames,list) or len(current_frames)!=current_expected_frames:
            raise ValueError('깊이 기록의 방향별 프레임 수가 다릅니다.')
        current_samples={current_joint:[] for current_joint in FACE_DEPTH_JOINT_NAMES}
        for current_frame in current_frames:
            if not isinstance(current_frame,list) or len(current_frame)!=5 or [current_point.get('joint') if isinstance(current_point,dict) else None for current_point in current_frame]!=list(FACE_DEPTH_JOINT_NAMES):
                raise ValueError('깊이 기록의 얼굴 관절 순서 오류')
            for current_point in current_frame:
                current_anchor=current_point.get('anchor_depth')
                current_surface=current_point.get('surface_depth')
                current_gap=current_point.get('depth_gap')
                current_pixel=current_point.get('pixel_xy')
                if not isinstance(current_pixel,list) or len(current_pixel)!=2 or any(type(current_value) not in (int,float) or not math.isfinite(current_value) for current_value in current_pixel) or type(current_anchor) not in (int,float) or not math.isfinite(current_anchor) or current_anchor<=0:
                    raise ValueError('얼굴 앵커 좌표 또는 깊이 값 오류')
                if current_surface is None and current_gap is None:
                    continue
                if type(current_surface) not in (int,float) or not math.isfinite(current_surface) or current_surface<=0 or type(current_gap) not in (int,float) or not math.isfinite(current_gap) or not math.isclose(current_gap,current_anchor-current_surface,rel_tol=1e-9,abs_tol=1e-9):
                    raise ValueError('얼굴 앵커 깊이 차이 값 오류')
                current_samples[current_point['joint']].append(float(current_gap))
        for current_joint,current_values in current_samples.items():
            current_output.append({'direction':current_direction,'joint':current_joint,'label':FACE_DEPTH_JOINT_NAMES[current_joint],'measured':len(current_values),'total':current_expected_frames,'median_gap':statistics.median(current_values) if current_values else None,'min_gap':min(current_values) if current_values else None,'max_gap':max(current_values) if current_values else None})
    return {'status':'valid','unit':'SOMA 좌표 단위','rows':current_output,'message':'앵커 깊이 − 같은 픽셀의 가장 앞 표면 깊이. 양수는 앵커가 표면보다 뒤에 있음을 뜻하지만, 앵커가 실제 얼굴 표면인지와 가림 부위는 판정하지 않습니다. 미측정은 배경 또는 화면 밖입니다.'}


@lru_cache(maxsize=32)
def read_face_anchor_depth_summary(current_path_text,current_modified_ns,current_file_size,current_frame_count,current_direction_names):
    """파일 변경 시에만 다시 읽어 잦은 상태 조회의 부담을 줄인다."""
    current_path=Path(current_path_text)
    if current_file_size>FACE_DEPTH_MAXIMUM_BYTES:
        raise ValueError('얼굴 앵커 깊이 기록이 16MiB를 초과합니다.')
    return summarize_face_anchor_depth(json.loads(current_path.read_text()),current_frame_count,current_direction_names)
