"""SOMA 렌더를 검출하고 3D 원본 길이 기준 고정 배율로 포즈 MP4를 만든다."""
from pathlib import Path
import sys
import json
import hashlib
import shutil
import threading
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS
from generators.kimodo.soma_pose import SOMA_BODY_JOINT_NAMES
from generators.kimodo.dwpose_runtime import prepare_fun_pose_frames


def calculate_soma_segment_gains(current_attempt_root, current_ratio_record):
    """2D 단축을 실제 뼈 길이로 오인하지 않도록 SOMA 3D 길이로 보정 배율을 정한다."""
    current_skeleton_record = json.loads((current_attempt_root/'skeleton.json').read_text())
    current_motion_path = current_attempt_root/('motion-in-place.npz' if (current_attempt_root/'motion-in-place.npz').exists() else 'motion.npz')
    with np.load(current_motion_path, allow_pickle=False) as current_motion_archive:
        current_joint_positions = current_motion_archive['posed_joints']
    current_body_positions = np.zeros((len(current_joint_positions),18,3))
    for current_joint_index, current_joint_name in enumerate(SOMA_BODY_JOINT_NAMES):
        if current_joint_name:
            current_body_positions[:,current_joint_index] = current_joint_positions[:,current_skeleton_record['joint_names'].index(current_joint_name)]
    current_torso_length = np.median(np.linalg.norm(current_body_positions[:,[2,5]].mean(1)-current_body_positions[:,[8,11]].mean(1),axis=-1))
    current_segment_gains = {}
    for current_group_name, current_joint_pairs in REFERENCE_SEGMENT_GROUPS.items():
        current_source_length = np.median([np.linalg.norm(current_body_positions[:,current_child_index]-current_body_positions[:,current_parent_index],axis=-1) for current_parent_index,current_child_index in current_joint_pairs])
        current_target_ratio = current_ratio_record['ratios'][current_group_name]
        if not np.isfinite(current_target_ratio) or current_target_ratio <= 0 or current_source_length <= 0 or current_torso_length <= 0:
            raise ValueError('관절 길이 보정 기준 오류')
        current_segment_gains[current_group_name] = float(current_target_ratio*current_torso_length/current_source_length)
    return current_segment_gains


def adjust_detected_pose_frames(current_detected_frames, current_image_shape, current_segment_gains, current_scale_percent):
    """검출된 2D 벡터에 클립 전체 고정 배율을 적용하여 투영 단축과 동작을 보존한다."""
    current_output_frames = []
    current_center_point = np.array([current_image_shape[1]/2,current_image_shape[0]/2])
    for current_frame_records in current_detected_frames:
        current_pose_record = current_frame_records[0]
        current_body_points = current_pose_record.body.keypoints
        current_original_points = np.array([[current_point.x,current_point.y] if current_point else [np.nan,np.nan] for current_point in current_body_points])
        current_adjusted_points = current_original_points.copy()
        if current_segment_gains:
            if not np.isfinite(current_original_points[1:14]).all():
                raise ValueError('관절 길이 보정에 필요한 몸 관절 검출 누락')
            for current_group_name in ('shoulder_width','hip_width'):
                current_left_index,current_right_index = REFERENCE_SEGMENT_GROUPS[current_group_name][0]
                current_pair_center = current_original_points[[current_left_index,current_right_index]].mean(0)
                current_adjusted_points[[current_left_index,current_right_index]] = current_pair_center+(current_original_points[[current_left_index,current_right_index]]-current_pair_center)*current_segment_gains[current_group_name]
            for current_group_name in ('upper_arm','forearm','thigh','shin'):
                for current_parent_index,current_child_index in REFERENCE_SEGMENT_GROUPS[current_group_name]:
                    current_adjusted_points[current_child_index] = current_adjusted_points[current_parent_index]+(current_original_points[current_child_index]-current_original_points[current_parent_index])*current_segment_gains[current_group_name]
        def transform_pose_points(current_point_list, current_translation_vector):
            if current_point_list is None:
                return None
            return [current_point._replace(x=float((current_point.x+current_translation_vector[0]-current_center_point[0])*current_scale_percent/100+current_center_point[0]), y=float((current_point.y+current_translation_vector[1]-current_center_point[1])*current_scale_percent/100+current_center_point[1])) if current_point else None for current_point in current_point_list]
        current_updated_body = [current_point._replace(x=float(current_adjusted_points[current_point_index,0]),y=float(current_adjusted_points[current_point_index,1])) if current_point else None for current_point_index,current_point in enumerate(current_body_points)]
        current_output_frames.append([current_pose_record._replace(body=current_pose_record.body._replace(keypoints=transform_pose_points(current_updated_body,[0,0])),left_hand=transform_pose_points(current_pose_record.left_hand,current_adjusted_points[7]-current_original_points[7] if current_body_points[7] else [0,0]),right_hand=transform_pose_points(current_pose_record.right_hand,current_adjusted_points[4]-current_original_points[4] if current_body_points[4] else [0,0]),face=transform_pose_points(current_pose_record.face,[0,0]))])
    return current_output_frames


def export_kimodo_dwpose(current_job_root,current_attempt_root):
    current_request_record = json.loads((current_job_root/'request.json').read_text())
    current_ratio_path = current_attempt_root/'reference-proportions.json'
    current_segment_gains = calculate_soma_segment_gains(current_attempt_root,json.loads(current_ratio_path.read_text())) if current_ratio_path.exists() else {}
    current_output_videos = {}
    for current_direction_name in current_request_record.get('directions',['front_left']):
        current_source_path = current_attempt_root/f'soma-render-{current_direction_name}.mp4'
        current_work_directory = current_attempt_root/f'dwpose-{current_direction_name}'
        current_work_directory.mkdir()
        shutil.copy2(current_source_path,current_work_directory/'driving.mp4')
        current_pose_request = {'driving_video_file':'driving.mp4','driving_video_sha256':hashlib.sha256(current_source_path.read_bytes()).hexdigest(),'frames':int((current_request_record['frames']-1)*16/30)+1,'pose_include_hands':current_request_record.get('pose_include_hands',False),'pose_include_face':current_request_record.get('pose_include_face',False)}
        prepare_fun_pose_frames(current_work_directory,current_work_directory,current_pose_request,lambda current_frames,current_shape:adjust_detected_pose_frames(current_frames,current_shape,current_segment_gains,current_request_record.get('openpose_scale_percent',85)))
        current_output_name = f'dwpose-{current_direction_name}.mp4'
        shutil.copy2(current_work_directory/'pose.mp4',current_attempt_root/current_output_name)
        current_output_videos[current_direction_name] = current_output_name
    (current_attempt_root/'dwpose-export.json').write_text(json.dumps({'videos':current_output_videos,'fps':16,'width':832,'height':480,'segment_gains':current_segment_gains,'length_basis':'SOMA 3D 기준 고정 배율 · 2D 투영 단축 유지','scale_percent':current_request_record.get('openpose_scale_percent',85),'pose_include_hands':current_request_record.get('pose_include_hands',False),'pose_include_face':current_request_record.get('pose_include_face',False)},ensure_ascii=False))


if __name__ == '__main__':
    current_stop_event = threading.Event()
    def report_export_heartbeat():
        while not current_stop_event.wait(5):
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+'/kimodo/dwpose-heartbeat 포즈 영상 생성 중',flush=True)
    threading.Thread(target=report_export_heartbeat,daemon=True).start()
    try:
        export_kimodo_dwpose(Path(sys.argv[1]),Path(sys.argv[2]))
    except Exception as current_export_error:
        (Path(sys.argv[2])/'dwpose-error.json').write_text(json.dumps({'error':str(current_export_error)},ensure_ascii=False))
        raise
    finally:
        current_stop_event.set()
