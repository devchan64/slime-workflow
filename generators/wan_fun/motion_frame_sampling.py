"""처리된 포즈 영상에서 앉기·일어서기 32+32 구간을 구성한다."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def select_fun_motion_segment(current_motion_values, current_start_index, current_end_index, current_frame_total):
    """시간 순서를 유지하며 움직임이 큰 구간에 프레임을 더 배분한다."""
    if current_end_index - current_start_index + 1 < current_frame_total:
        raise ValueError('각 동작 구간에 서로 다른 원본 프레임이 33개 이상 필요합니다.')
    current_segment_motion = np.asarray(current_motion_values[current_start_index + 1:current_end_index + 1], dtype=np.float64)
    current_scale_value = max(float(np.percentile(current_segment_motion, 90)), 1e-6)
    current_segment_weights = 0.35 + np.clip(current_segment_motion / current_scale_value, 0.0, 2.0)
    current_cumulative_values = np.concatenate(([0.0], np.cumsum(current_segment_weights)))
    current_targets = np.linspace(0.0, current_cumulative_values[-1], current_frame_total)
    current_selected_indices = [current_start_index]
    for current_output_index in range(1, current_frame_total - 1):
        current_candidate_index = current_start_index + int(np.searchsorted(current_cumulative_values, current_targets[current_output_index]))
        current_minimum_index = current_selected_indices[-1] + 1
        current_maximum_index = current_end_index - (current_frame_total - 1 - current_output_index)
        current_selected_indices.append(max(current_minimum_index, min(current_candidate_index, current_maximum_index)))
    current_selected_indices.append(current_end_index)
    return current_selected_indices


def analyze_fun_pose_frames(current_video_frames):
    """검은 배경 포즈 선의 상단과 변화량으로 앉은 구간을 찾는다."""
    current_frame_count = len(current_video_frames)
    if current_frame_count < 65:
        raise ValueError('65개의 서로 다른 포즈 프레임이 필요합니다.')
    current_pose_masks = []
    current_head_positions = []
    for current_frame_image in current_video_frames:
        current_pose_mask = np.max(current_frame_image, axis=2) > 45
        current_pose_rows = np.flatnonzero(current_pose_mask.any(axis=1))
        if len(current_pose_rows) < 20:
            raise ValueError('포즈 선을 확인할 수 없는 프레임이 있습니다. 검은 배경의 DWPose 영상을 사용하세요.')
        current_head_positions.append(float(current_pose_rows[0]))
        current_pose_masks.append(cv2.resize(current_pose_mask.astype(np.float32), (208, 120), interpolation=cv2.INTER_AREA))
    current_smoothed_heads = np.convolve(np.pad(current_head_positions, (2, 2), mode='edge'), np.ones(5)/5, mode='valid')
    current_head_range = float(np.max(current_smoothed_heads) - np.min(current_smoothed_heads))
    if current_head_range < 30:
        raise ValueError('서기와 앉기의 충분한 높이 변화를 찾지 못했습니다.')
    current_sitting_mask = current_smoothed_heads >= np.min(current_smoothed_heads) + current_head_range * 0.7
    current_sitting_runs = []
    current_run_start = None
    for current_frame_index, current_is_sitting in enumerate([*current_sitting_mask, False]):
        if current_is_sitting and current_run_start is None:
            current_run_start = current_frame_index
        elif not current_is_sitting and current_run_start is not None:
            current_sitting_runs.append((current_run_start, current_frame_index - 1))
            current_run_start = None
    current_sitting_start, current_sitting_end = max(current_sitting_runs, key=lambda current_run_value: current_run_value[1] - current_run_value[0])
    current_lower_pivot = max(32, current_sitting_start)
    current_upper_pivot = min(current_frame_count - 33, current_sitting_end)
    if current_lower_pivot > current_upper_pivot:
        raise ValueError('앉은 구간 양쪽에 32개 이상의 프레임이 필요합니다.')
    current_pivot_index = (current_lower_pivot + current_upper_pivot) // 2
    current_motion_values = [0.0] + [float(np.mean(np.abs(current_pose_masks[current_frame_index] - current_pose_masks[current_frame_index - 1]))) for current_frame_index in range(1, current_frame_count)]
    current_down_indices = select_fun_motion_segment(current_motion_values, 0, current_pivot_index, 33)
    current_up_indices = select_fun_motion_segment(current_motion_values, current_pivot_index, current_frame_count - 1, 33)
    return {'source_frames': current_frame_count, 'sitting_range': [current_sitting_start, current_sitting_end], 'sitting_pivot': current_pivot_index, 'selected_indices': current_down_indices + current_up_indices[1:], 'first_transition_intervals': 32, 'second_transition_intervals': 32}


def prepare_fun_motion_video(current_source_path, current_output_path, current_record_path):
    current_source_path = Path(current_source_path)
    current_output_path = Path(current_output_path)
    current_record_path = Path(current_record_path)
    if current_source_path.resolve() in (current_output_path.resolve(), current_record_path.resolve()) or current_output_path.resolve() == current_record_path.resolve():
        raise ValueError('입력과 출력 경로는 서로 달라야 합니다.')
    if current_output_path.exists() or current_record_path.exists():
        raise FileExistsError('기존 출력 파일을 덮어쓰지 않습니다.')
    current_video_capture = cv2.VideoCapture(str(current_source_path))
    try:
        if not current_video_capture.isOpened() or abs(current_video_capture.get(cv2.CAP_PROP_FPS) - 16) > 0.01:
            raise ValueError('16fps 포즈 MP4가 필요합니다.')
        current_video_frames = []
        while True:
            current_frame_ready, current_frame_image = current_video_capture.read()
            if not current_frame_ready:
                break
            if current_frame_image.shape[:2] != (480, 832):
                raise ValueError('832×480 포즈 MP4가 필요합니다.')
            current_video_frames.append(current_frame_image)
            if len(current_video_frames) > 512:
                raise ValueError('포즈 영상은 512프레임 이하여야 합니다.')
    finally:
        current_video_capture.release()
    current_motion_record = analyze_fun_pose_frames(current_video_frames)
    current_output_path.parent.mkdir(parents=True, exist_ok=True)
    current_record_path.parent.mkdir(parents=True, exist_ok=True)
    current_video_writer = cv2.VideoWriter(str(current_output_path), cv2.VideoWriter_fourcc(*'mp4v'), 16, (832, 480))
    if not current_video_writer.isOpened():
        raise RuntimeError('MP4 인코더를 열 수 없습니다.')
    try:
        for current_frame_index in current_motion_record['selected_indices']:
            current_video_writer.write(current_video_frames[current_frame_index])
    finally:
        current_video_writer.release()
    current_motion_record.update({'source_sha256': hashlib.sha256(current_source_path.read_bytes()).hexdigest(), 'output_sha256': hashlib.sha256(current_output_path.read_bytes()).hexdigest(), 'output_frames': 65, 'output_fps': 16, 'source_index_base': 0, 'selection': 'pose-height-pivot-and-motion-weighted'})
    current_record_path.write_text(json.dumps(current_motion_record, ensure_ascii=False, indent=2) + '\n')
    return current_motion_record


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('source', type=Path)
    current_argument_parser.add_argument('output', type=Path)
    current_argument_parser.add_argument('--record', type=Path, required=True)
    current_arguments = current_argument_parser.parse_args()
    print(json.dumps(prepare_fun_motion_video(current_arguments.source, current_arguments.output, current_arguments.record), ensure_ascii=False))
