"""원본 생성과 같은 시도 폴더에 ANNY·OpenPose 출력을 저장한다."""
from generators.hy_motion.vnccs_contract import calculate_file_digest
from generators.hy_motion.vnccs_export import export_vnccs_package


def generate_automatic_renders(current_job_directory, current_attempt_path, current_request_record, current_render_config, current_progress_callback):
    current_motion_path = current_attempt_path / 'motion.npz'
    current_source_frames = round(current_request_record['duration_seconds'] * 30)
    current_source_record = {
        'source_id': current_job_directory.parent.name + '-' + current_job_directory.name,
        'motion_path': str(current_motion_path), 'motion_sha256': calculate_file_digest(current_motion_path),
        'request': current_request_record, 'frames': current_source_frames,
    }
    current_export_request = {
        'source_id': current_source_record['source_id'], 'start_frame': 1,
        'end_frame': current_source_frames, 'frame_step': 1,
        'directions': current_request_record['directions'], 'tag': current_request_record.get('tag', ''),
    }
    current_render_directory = current_attempt_path / 'anny'
    current_render_directory.mkdir()
    current_result_record = export_vnccs_package(
        current_job_directory, current_render_directory, current_export_request,
        current_render_config, current_progress_callback, current_source_record=current_source_record)
    return {**current_result_record, 'relative_path': 'anny', 'automatic': True}
