"""SOMA 원본을 고정 ANNY 리그에 전달하고 공용 CUDA 렌더러를 실행한다."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
import yaml
from PIL import Image
from generators.kimodo.contracts import KIMODO_WORKSPACE_ROOT, KIMODO_CONFIG_ROOT, UniqueConfigLoader
from tools.review.common.generation_records import write_record_atomically

ANNY_RUNTIME_PYTHON = KIMODO_WORKSPACE_ROOT/'.local/blender-runtime/bin/python'
ANNY_STAGE_RUNNER = KIMODO_WORKSPACE_ROOT/'generators/momask/templates/run_stage.py'
ANNY_STAGE_TEMPLATE = Path(__file__).with_name('anny_stage.py')


def load_anny_configuration():
    current_config_record=yaml.load((KIMODO_CONFIG_ROOT/'anny-render.yaml').read_text(),Loader=UniqueConfigLoader)
    current_required_fields={'schema_version','source_joint_names','target_profile','retarget_profile','resolution','samples','projections','camera_elevation','camera_angles','framing_margin'}
    if not isinstance(current_config_record,dict) or set(current_config_record)!=current_required_fields or current_config_record['schema_version']!=1:
        raise ValueError('ANNY 렌더 설정 계약 오류')
    if len(current_config_record['source_joint_names'])!=22 or len(set(current_config_record['source_joint_names']))!=22:
        raise ValueError('SOMA 대응 관절은 고유한 22개여야 합니다.')
    if current_config_record['target_profile']!='generators/animation/config/anny_profiles/neutral.yaml' or current_config_record['retarget_profile']!='generators/kimodo/config/anny-retarget.yaml':
        raise ValueError('ANNY 고정 프로필 경로 오류')
    if current_config_record['resolution']!=512 or current_config_record['samples']!=16 or current_config_record['projections']!=['orthographic'] or current_config_record['camera_angles']!={'front_left':45} or current_config_record['camera_elevation']!=17 or current_config_record['framing_margin']!=1.12:
        raise ValueError('ANNY 고정 렌더 기준값 오류')
    return current_config_record


def verify_anny_resources():
    current_config_record=load_anny_configuration()
    current_profile_record=yaml.load((KIMODO_WORKSPACE_ROOT/current_config_record['target_profile']).read_text(),Loader=UniqueConfigLoader)
    current_manifest_record=yaml.load((KIMODO_WORKSPACE_ROOT/current_profile_record['manifest_path']).read_text(),Loader=UniqueConfigLoader)
    current_baseline_path=KIMODO_WORKSPACE_ROOT/current_profile_record['blend_path']
    if hashlib.sha256(current_baseline_path.read_bytes()).hexdigest()!=current_manifest_record['files'][current_baseline_path.name]['sha256']:
        raise ValueError('ANNY 기준 리그 해시 불일치')
    if not ANNY_RUNTIME_PYTHON.is_file():
        raise FileNotFoundError(f'ANNY Blender 실행 환경 누락: {ANNY_RUNTIME_PYTHON}')
    return current_config_record,current_baseline_path


def prepare_anny_channels(current_motion_path,current_skeleton_record,current_config_record):
    current_joint_names=current_skeleton_record['joint_names']
    if current_skeleton_record['skeleton']!='somaskel77' or current_skeleton_record['fps']!=30 or len(current_joint_names)!=77 or len(set(current_joint_names))!=77:
        raise ValueError('SOMA77 골격 계약 오류')
    current_source_indices=[current_joint_names.index(current_joint_name) for current_joint_name in current_config_record['source_joint_names']]
    with np.load(current_motion_path,allow_pickle=False) as current_motion_archive:
        current_joint_positions=current_motion_archive['posed_joints']
    if current_joint_positions.ndim!=3 or current_joint_positions.shape[1:]!=(77,3) or not len(current_joint_positions) or not np.isfinite(current_joint_positions).all():
        raise ValueError('SOMA 관절 크기·유한값 오류')
    return current_joint_positions[:,current_source_indices].copy()


def generate_anny_outputs(current_attempt_root,current_metrics_recorder):
    current_config_record,current_baseline_path=verify_anny_resources()
    from generators.kimodo.anny_rotation import prepare_neck_rotation_channels
    prepare_neck_rotation_channels(current_attempt_root)
    current_retarget_root=current_attempt_root/'anny'
    current_input_root=current_retarget_root/'inputs'
    current_input_root.mkdir(parents=True,exist_ok=False)
    current_motion_path=current_attempt_root/'motion.npz'
    current_skeleton_record=json.loads((current_attempt_root/'skeleton.json').read_text())
    current_joint_positions=prepare_anny_channels(current_motion_path,current_skeleton_record,current_config_record)
    current_profile_path=KIMODO_WORKSPACE_ROOT/current_config_record['retarget_profile']
    current_profile_record=yaml.load(current_profile_path.read_text(),Loader=UniqueConfigLoader)
    current_adapted_path=current_input_root/'mannequin-motion.npz'
    np.savez_compressed(current_adapted_path,joints=current_joint_positions,rest=np.asarray(current_profile_record['source_reference']['joint_positions']),contacts=np.zeros((len(current_joint_positions),2)),sample_indices=np.arange(len(current_joint_positions)))
    shutil.copy2(current_profile_path,current_retarget_root/'retarget-profile.yaml')
    shutil.copy2(KIMODO_WORKSPACE_ROOT/'generators/momask/position_retarget.py',current_retarget_root/'position_retarget.py')
    shutil.copy2(current_baseline_path,current_input_root/'anny-reference-fit-rig.blend')
    write_record_atomically(current_input_root/'artifact.json',{'generator':'Kimodo','fps':30,'source_motion':str(current_motion_path),'source_motion_sha256':hashlib.sha256(current_motion_path.read_bytes()).hexdigest(),'files':{'mannequin-motion.npz':hashlib.sha256(current_adapted_path.read_bytes()).hexdigest()}})
    current_stage_record={'output_directory':str(current_retarget_root),'export_directory':str(current_retarget_root),'config':current_config_record,'request':{'start_frame':1,'end_frame':len(current_joint_positions),'frame_step':1,'directions':['front_left']}}
    current_stage_path=current_retarget_root/'stage-request.json'
    write_record_atomically(current_stage_path,current_stage_record)
    for current_stage_name in ('retarget','render'):
        current_metrics_recorder.update_generation_stage(current_stage_name)
        current_log_path=current_retarget_root/(current_stage_name+'.log')
        with current_log_path.open('w') as current_log_stream:
            current_stage_process=subprocess.Popen([str(ANNY_RUNTIME_PYTHON),str(ANNY_STAGE_RUNNER),str(ANNY_STAGE_TEMPLATE),str(current_stage_path),current_stage_name],stdout=current_log_stream,stderr=subprocess.STDOUT)
            try:
                current_exit_code=current_stage_process.wait()
            except BaseException:
                current_stage_process.terminate()
                try:current_stage_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    current_stage_process.kill();current_stage_process.wait()
                raise
        if current_exit_code:
            raise RuntimeError(f'ANNY {current_stage_name} 실패: '+current_log_path.read_text(errors='replace')[-4000:])
    current_render_record=json.loads((current_retarget_root/'render-manifest.json').read_text())
    if len(current_render_record['images'])!=len(current_joint_positions):
        raise ValueError('ANNY 렌더 프레임 수 불일치')
    current_preview_frames=[]
    for current_frame_index,current_image_record in enumerate(current_render_record['images'],1):
        if current_image_record['source_frame']!=current_frame_index:
            raise ValueError('ANNY 렌더 원본 프레임 순서 오류')
        current_image_path=current_retarget_root/current_image_record['path']
        if not current_image_path.resolve().is_relative_to(current_retarget_root.resolve()):
            raise ValueError('ANNY 결과 경로 이탈')
        with Image.open(current_image_path) as current_image_value:
            if current_image_value.mode!='RGBA' or current_image_value.size!=(512,512) or current_image_value.getchannel('A').getextrema()[1]==0:
                raise ValueError('ANNY 렌더 이미지 계약 오류')
            current_background_image=Image.new('RGBA',(512,512),'white')
            current_preview_frames.append(np.asarray(Image.alpha_composite(current_background_image,current_image_value).convert('RGB')))
    current_quality_record=json.loads((current_retarget_root/'review-metrics.json').read_text())
    return current_preview_frames,{'automatic':True,'rig':'anny-neutral-v4','method':current_quality_record['retarget_method'],'neck_rotation':current_quality_record['neck_rotation'],'quality_approved':False,'quality_warnings':current_quality_record['quality_warnings'],'frames':len(current_preview_frames),'fps':30,'target_sha256':hashlib.sha256(current_baseline_path.read_bytes()).hexdigest(),'profile_sha256':hashlib.sha256(current_profile_path.read_bytes()).hexdigest()}
