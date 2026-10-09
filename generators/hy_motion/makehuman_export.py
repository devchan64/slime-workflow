"""공용 HY-Motion 작업에서 MakeHuman 포즈 패키지를 출력한다."""
import json
import subprocess
import zipfile
from pathlib import Path
import yaml
from generators.hy_motion.contracts import WORKFLOW_ROOT_DIRECTORY, UniqueConfigLoader
from generators.hy_motion.vnccs_contract import calculate_file_digest
from tools.review.common.generation_records import write_record_atomically

MAKEHUMAN_ASSET_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / 'assets/animation-models/vnccs-makehuman-base-v1'


def export_makehuman_package(current_source_record, current_attempt_path, current_request_record, current_config_record, current_progress_callback):
    from generators.hy_motion.vnccs_export import BLENDER_RUNTIME_PYTHON, BLENDER_STAGE_RUNNER, write_pose_reference
    current_asset_path = MAKEHUMAN_ASSET_DIRECTORY / 'rig.npz'
    current_asset_manifest = yaml.load((MAKEHUMAN_ASSET_DIRECTORY / 'manifest.yaml').read_text(), Loader=UniqueConfigLoader)
    if calculate_file_digest(current_asset_path) != current_asset_manifest['sha256']:
        raise ValueError('MakeHuman 고정 리그 해시 불일치')
    current_stage_record = {'export_directory': str(current_attempt_path), 'asset_path': str(current_asset_path), 'motion_path': current_source_record['motion_path'], 'request': current_request_record, 'config': current_config_record}
    current_stage_path = current_attempt_path / 'stage-request.json'
    write_record_atomically(current_stage_path, current_stage_record)
    current_progress_callback('makehuman', 'MakeHuman 관절 방향 전달·고정 체형 스키닝·CUDA 렌더')
    current_log_path = current_attempt_path / 'makehuman.log'
    with current_log_path.open('w') as current_log_stream:
        current_process_result = subprocess.run([str(BLENDER_RUNTIME_PYTHON), str(BLENDER_STAGE_RUNNER), str(Path(__file__).parent / 'templates/makehuman_stage.py'), str(current_stage_path)], stdout=current_log_stream, stderr=subprocess.STDOUT)
    if current_process_result.returncode:
        raise RuntimeError('MakeHuman 단계 실패: ' + current_log_path.read_text(errors='replace')[-4000:])
    current_render_record = json.loads((current_attempt_path / 'render-manifest.json').read_text())
    current_quality_record = json.loads((current_attempt_path / 'retarget-quality.json').read_text())
    current_file_records = []
    for current_image_record in current_render_record['images']:
        current_image_path = current_attempt_path / current_image_record['path']
        current_reference_path = current_image_path.with_name(current_image_path.stem + '-rgb.png')
        write_pose_reference(current_image_path, current_reference_path, current_config_record['resolution'])
        current_file_records.append({**current_image_record, 'sha256': calculate_file_digest(current_image_path), 'model_input_path': str(current_reference_path.relative_to(current_attempt_path)), 'model_input_sha256': calculate_file_digest(current_reference_path)})
    current_manifest_record = {'schema_version': 2, 'kind': 'vnccs-posestudio-pose-images', 'conditioning_status': 'makehuman-base-retarget-candidate', 'source': current_source_record, 'rig': current_asset_manifest, 'config': current_config_record, 'request': current_request_record, 'camera': current_render_record['camera'], 'projection_cameras': current_render_record['projection_cameras'], 'images': current_file_records, 'quality_summary': current_quality_record, 'quality_warnings': current_quality_record['quality_warnings'], 'automatic_adoption': False, 'usage': 'image1에는 model_input_path RGB, image2에는 단일 캐릭터 참조. 공식 기본 메쉬·가중치를 사용하나 morph·텍스처·조명·생성 품질 동등성은 미검증.'}
    write_record_atomically(current_attempt_path / 'vnccs-manifest.json', current_manifest_record)
    with zipfile.ZipFile(current_attempt_path / 'vnccs-package.zip', 'w', compression=zipfile.ZIP_DEFLATED) as current_archive_file:
        for current_relative_path in ['vnccs-manifest.json', 'retarget-quality.json', 'makehuman-motion.npz', *[current_image_record[current_field_name] for current_image_record in current_file_records for current_field_name in ('path', 'model_input_path')]]:
            current_archive_file.write(current_attempt_path / current_relative_path, current_relative_path)
    current_source_indices = list(range(current_request_record['start_frame'], current_request_record['end_frame'] + 1, current_request_record['frame_step']))
    return {'kind': 'vnccs', 'projections': current_render_record['projections'], 'rig_backend': 'makehuman', 'frames': len(current_source_indices), 'source_indices': current_source_indices, 'source_frames': current_source_record['frames'], 'source_fps': 30, 'preview_fps': 30 / current_request_record['frame_step'], 'directions': current_request_record['directions'], 'quality_warnings': current_quality_record['quality_warnings'], 'quality_summary': current_quality_record, 'downloads': ['vnccs-package.zip', 'vnccs-manifest.json', 'retarget-quality.json']}
