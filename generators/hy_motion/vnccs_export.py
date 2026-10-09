"""HY-Motion 원본→ANNY→VNCCS 포즈 PNG 패키지의 독립 작업 파이프라인."""
from pathlib import Path
import json
import shutil
import subprocess
import zipfile
import numpy as np
import yaml
from PIL import Image
from generators.hy_motion.contracts import WORKFLOW_ROOT_DIRECTORY, UniqueConfigLoader
from generators.hy_motion.preview import validate_motion_output
from generators.hy_motion.vnccs_contract import calculate_file_digest, validate_vnccs_request
from tools.review.common.generation_records import write_record_atomically

BLENDER_RUNTIME_PYTHON = WORKFLOW_ROOT_DIRECTORY / '.local/blender-runtime/bin/python'
BLENDER_STAGE_RUNNER = WORKFLOW_ROOT_DIRECTORY / 'generators/momask/templates/run_stage.py'
VNCCS_STAGE_TEMPLATE = Path(__file__).parent / 'templates/vnccs_stage.py'
POSE_REFERENCE_BACKGROUND = (255, 255, 255, 255)
SOURCE_ALIGNED_SEGMENT_IDS = frozenset(('lower_spine', 'middle_spine', 'upper_spine', 'lower_neck', 'upper_neck', 'collar_l', 'shoulder_l', 'collar_r', 'shoulder_r'))


def write_pose_reference(current_source_path, current_target_path, expected_image_resolution):
    """투명 픽셀의 검은 RGB가 섞이지 않도록 흰 배경 모델 입력을 저장한다."""
    with Image.open(current_source_path) as current_source_image:
        current_source_image.load()
        if current_source_image.mode != 'RGBA' or current_source_image.size != (expected_image_resolution,) * 2 or current_source_image.getchannel('A').getextrema()[1] == 0:
            raise ValueError('VNCCS PNG 크기·RGBA·빈 이미지 검증 실패')
        current_background_image = Image.new('RGBA', current_source_image.size, POSE_REFERENCE_BACKGROUND)
        Image.alpha_composite(current_background_image, current_source_image).convert('RGB').save(current_target_path)


def export_vnccs_package(current_job_directory, current_attempt_path, current_request_record, current_config_record, current_progress_callback, current_source_record=None):
    if current_config_record.get('rig_backend') != 'anny':
        raise ValueError('MakeHuman 출력은 폐기되었습니다. ANNY 설정으로 새 작업을 생성하세요.')
    if current_source_record is None:
        current_source_record = json.loads((current_job_directory / 'export-source.json').read_text())
    current_motion_path = Path(current_source_record['motion_path'])
    if calculate_file_digest(current_motion_path) != current_source_record['motion_sha256']:
        raise ValueError('접수 이후 HY-Motion 원본 해시 변경')
    current_source_frames = current_source_record['frames']
    validate_vnccs_request({current_field_name: current_field_value for current_field_name, current_field_value in current_request_record.items() if current_field_name != 'action'}, current_source_frames)
    with np.load(current_motion_path, allow_pickle=False) as current_motion_archive:
        if 'fps' not in current_motion_archive or current_motion_archive['fps'].shape != () or float(current_motion_archive['fps']) != 30:
            raise ValueError('VNCCS 입력은 30 FPS 원본이어야 합니다.')
        current_motion_arrays = {current_field_name: current_motion_archive[current_field_name] for current_field_name in current_motion_archive.files if current_field_name != 'fps'}
        validate_motion_output(current_motion_arrays, current_source_frames)
    current_source_directory = current_attempt_path / 'source-motion'
    current_source_directory.mkdir()
    shutil.copy2(current_motion_path, current_source_directory / 'motion.npz')
    write_record_atomically(current_source_directory / 'result.json', {'relative_path': '.'})
    write_record_atomically(current_source_directory / 'request.json', current_source_record['request'])
    current_retarget_directory = current_attempt_path / 'retarget'
    current_input_directory = current_retarget_directory / 'inputs'
    current_input_directory.mkdir(parents=True)
    # 기존 위치 변환기의 실행 출처 검증에 필요한 계산기 사본을 시도 안에 보존한다.
    shutil.copy2(WORKFLOW_ROOT_DIRECTORY / 'generators/momask/position_retarget.py', current_retarget_directory / 'position_retarget.py')
    current_template_path = WORKFLOW_ROOT_DIRECTORY / '.model/hy-motion/upstream/scripts/gradio/static/assets/dump_wooden/j_template.bin'
    current_reference_joints = np.frombuffer(current_template_path.read_bytes(), dtype=np.float32).reshape(52, 3)[:22]
    current_profile_record = yaml.load((WORKFLOW_ROOT_DIRECTORY / 'generators/momask/config/humanml22-anny-retarget.yaml').read_text(), Loader=UniqueConfigLoader)
    current_profile_record['profile_id'] = 'hymotion22-anny-vnccs-v3'
    current_profile_segments = {current_segment_record['segment_id'] for current_segment_record in current_profile_record['segments']}
    if not SOURCE_ALIGNED_SEGMENT_IDS <= current_profile_segments:
        raise ValueError('원본 방향 대응에 필요한 척추·쇄골·어깨 세그먼트 누락')
    for current_segment_record in current_profile_record['segments']:
        if current_segment_record['segment_id'] in SOURCE_ALIGNED_SEGMENT_IDS:
            current_segment_record['transfer_mode'] = 'absolute_direction'
    current_profile_record['source_reference'] = {'id': 'HY-Motion Wooden body22', 'source_url': 'https://github.com/Tencent-Hunyuan/HY-Motion-1.0', 'source_sha256': calculate_file_digest(current_template_path), 'joint_positions': current_reference_joints.tolist()}
    (current_retarget_directory / 'retarget-profile.yaml').write_text(yaml.safe_dump(current_profile_record, allow_unicode=True, sort_keys=False))
    current_adapted_path = current_input_directory / 'mannequin-motion.npz'
    np.savez_compressed(current_adapted_path, joints=current_motion_arrays['world_joints'][:, :22], rest=current_reference_joints, contacts=np.zeros((current_source_frames, 2)), sample_indices=np.arange(current_source_frames))
    write_record_atomically(current_input_directory / 'artifact.json', {'files': {'mannequin-motion.npz': calculate_file_digest(current_adapted_path)}, 'generator': 'HY-Motion', 'fps': 30, 'source_motion': current_source_record['source_id'], 'source_motion_sha256': current_source_record['motion_sha256']})
    current_baseline_profile = yaml.load((WORKFLOW_ROOT_DIRECTORY / current_config_record['target_profile']).read_text(), Loader=UniqueConfigLoader)
    current_baseline_path = WORKFLOW_ROOT_DIRECTORY / current_baseline_profile['blend_path']
    current_baseline_manifest = yaml.load((WORKFLOW_ROOT_DIRECTORY / current_baseline_profile['manifest_path']).read_text(), Loader=UniqueConfigLoader)
    if calculate_file_digest(current_baseline_path) != current_baseline_manifest['files'][current_baseline_path.name]['sha256']:
        raise ValueError('ANNY 기준 리그 해시 불일치')
    shutil.copy2(current_baseline_path, current_input_directory / 'anny-reference-fit-rig.blend')
    write_record_atomically(current_retarget_directory / 'baseline-model.json', current_baseline_profile)
    current_stage_record = {'output_directory': str(current_retarget_directory), 'source_directory': str(current_source_directory), 'skin_profile_path': str(WORKFLOW_ROOT_DIRECTORY / current_config_record['skin_profile']), 'export_directory': str(current_attempt_path), 'request': current_request_record, 'config': current_config_record}
    current_stage_path = current_attempt_path / 'stage-request.json'
    write_record_atomically(current_stage_path, current_stage_record)
    for current_stage_name in ('position', 'rotation', 'skin', 'render'):
        current_progress_callback(current_stage_name, 'ANNY→VNCCS 출력 단계: ' + current_stage_name)
        current_log_path = current_attempt_path / (current_stage_name + '.log')
        with current_log_path.open('w') as current_log_stream:
            current_process_result = subprocess.run([str(BLENDER_RUNTIME_PYTHON), str(BLENDER_STAGE_RUNNER), str(VNCCS_STAGE_TEMPLATE), str(current_stage_path), current_stage_name], stdout=current_log_stream, stderr=subprocess.STDOUT)
        if current_process_result.returncode:
            raise RuntimeError(f'ANNY {current_stage_name} 단계 실패 (exit={current_process_result.returncode}): ' + current_log_path.read_text(errors='replace')[-4000:])
    current_skin_record = json.loads((current_retarget_directory / 'final/comparison.json').read_text())
    current_render_record = json.loads((current_attempt_path / 'render-manifest.json').read_text())
    current_comparison_directory = current_attempt_path / 'unconstrained'
    current_comparison_directory.mkdir()
    current_comparison_stage = {**current_stage_record, 'export_directory': str(current_comparison_directory), 'constraint_comparison_disabled': True, 'config': {**current_config_record, 'projections': ['orthographic']}}
    current_comparison_path = current_comparison_directory / 'stage-request.json'
    write_record_atomically(current_comparison_path, current_comparison_stage)
    current_progress_callback('render-comparison', '제약 끔 정사영 비교 렌더')
    with (current_comparison_directory / 'render.log').open('w') as current_log_stream:
        current_process_result = subprocess.run([str(BLENDER_RUNTIME_PYTHON), str(BLENDER_STAGE_RUNNER), str(VNCCS_STAGE_TEMPLATE), str(current_comparison_path), 'render'], stdout=current_log_stream, stderr=subprocess.STDOUT)
    if current_process_result.returncode:
        raise RuntimeError('제약 끔 비교 렌더 실패: ' + (current_comparison_directory / 'render.log').read_text(errors='replace')[-4000:])
    current_comparison_record = json.loads((current_comparison_directory / 'render-manifest.json').read_text())
    for current_image_record in current_render_record['images']:
        current_image_record['skin_constraints_enabled'] = True
    current_render_record['images'].extend({**current_image_record, 'path': 'unconstrained/' + current_image_record['path'], 'skin_constraints_enabled': False} for current_image_record in current_comparison_record['images'])
    current_file_records = []
    for current_image_record in current_render_record['images']:
        current_image_path = current_attempt_path / current_image_record['path']
        current_reference_path = current_image_path.with_name(current_image_path.stem + '-rgb.png')
        write_pose_reference(current_image_path, current_reference_path, current_config_record['resolution'])
        from generators.hy_motion.openpose_export import write_projected_openpose
        current_openpose_path = current_image_path.with_name(current_image_path.stem + '-openpose.png')
        write_projected_openpose(current_image_record, current_openpose_path, current_config_record['resolution'])
        current_file_records.append({**current_image_record, 'openpose_path': str(current_openpose_path.relative_to(current_attempt_path)), 'openpose_sha256': calculate_file_digest(current_openpose_path), 'openpose_json_path': str(current_openpose_path.with_suffix('.json').relative_to(current_attempt_path)), 'sha256': calculate_file_digest(current_image_path), 'model_input_path': str(current_reference_path.relative_to(current_attempt_path)), 'model_input_sha256': calculate_file_digest(current_reference_path), 'model_input_mode': 'RGB', 'model_input_background': list(POSE_REFERENCE_BACKGROUND[:3])})
    current_skin_record['quality_warnings'] = [*current_skin_record['quality_warnings'], 'ANNY 렌더의 VNCCS 학습 마네킹 호환성·포즈 추종·체형 보존은 미검증']
    current_manifest_record = {'schema_version': 1, 'kind': 'vnccs-posestudio-pose-images', 'source': current_source_record, 'rig': {**current_baseline_profile, 'blend_sha256': calculate_file_digest(current_baseline_path)}, 'config': current_config_record, 'camera': current_render_record['camera'], 'projection_cameras': current_render_record['projection_cameras'], 'source_fps': 30, 'source_frames': current_source_frames, 'request': current_request_record, 'images': current_file_records, 'skin_profile': current_skin_record['profile'], 'quality_summary': current_skin_record['summary'], 'quality_warnings': current_skin_record['quality_warnings'], 'automatic_adoption': False, 'usage': '각 PNG를 VNCCS PoseStudio의 image1 포즈 입력으로 사용하고 image2에 캐릭터 참조를 별도로 제공한다. LoRA·Qwen 추론과 게임 자산 등록은 수행하지 않는다.'}
    current_manifest_record['constraints'] = {'skin_collision': True, 'rotation_barrier': True, 'profile_sha256': current_skin_record['profile_sha256']}
    current_manifest_record['conditioning_status'] = 'unverified-anny-render'
    current_manifest_record['usage'] = 'image1에는 images[].model_input_path의 흰 배경 RGB PNG, image2에는 단일 캐릭터 참조를 사용한다. RGBA 원본은 검수용이다. ANNY와 VNCCS의 호환성·생성 품질은 미검증이며 Qwen 추론은 수행하지 않는다.'
    write_record_atomically(current_attempt_path / 'vnccs-manifest.json', current_manifest_record)
    shutil.copy2(current_retarget_directory / 'final/comparison.json', current_attempt_path / 'retarget-quality.json')
    with zipfile.ZipFile(current_attempt_path / 'vnccs-package.zip', 'w', compression=zipfile.ZIP_DEFLATED) as current_archive_file:
        for current_relative_path in ['vnccs-manifest.json', 'retarget-quality.json', *[current_file_record['path'] for current_file_record in current_file_records]]:
            current_archive_file.write(current_attempt_path / current_relative_path, current_relative_path)
        for current_file_record in current_file_records:
            for current_field_name in ('model_input_path', 'openpose_path', 'openpose_json_path'):
                current_relative_path = current_file_record[current_field_name]
                current_archive_file.write(current_attempt_path / current_relative_path, current_relative_path)
        current_archive_file.write(current_retarget_directory / 'final/barrier/mannequin.blend', 'anny-rig.blend')
    current_source_indices = list(range(current_request_record['start_frame'], current_request_record['end_frame'] + 1, current_request_record['frame_step']))
    return {'kind': 'vnccs', 'constraint_comparison': True, 'rig_backend': 'anny', 'openpose': True, 'projections': current_render_record['projections'], 'frames': len(current_source_indices), 'source_indices': current_source_indices, 'source_frames': current_source_frames, 'source_fps': 30, 'preview_fps': 30 / current_request_record['frame_step'], 'directions': current_request_record['directions'], 'quality_warnings': current_skin_record['quality_warnings'], 'quality_summary': current_skin_record['summary'], 'downloads': ['vnccs-package.zip', 'vnccs-manifest.json', 'retarget-quality.json']}
