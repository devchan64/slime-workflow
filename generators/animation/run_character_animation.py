"""고정된 제작 자산의 모든 프레임을 Qwen 포즈 편집으로 생성한다."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.character_animation_assets import hash_asset_file, resolve_asset_path
from tools.review.momask_jobs import write_record_atomically
from generators.image.worker_lock import acquire_worker_lock


def generate_character_frame(generation_job_path,current_frame_index):
    from PIL import Image
    from qwen_pose import execute_pose_generation
    generation_request_record=json.loads((generation_job_path/'request.json').read_text())
    source_frame_record=generation_request_record['frames'][current_frame_index]
    frame_output_directory=generation_job_path/source_frame_record['direction']/f"frame-{source_frame_record['frame']:04d}"
    frame_output_directory.mkdir(parents=True)
    input_reference_paths={}
    for reference_role_name in ('character','pose'):
        reference_asset_path=resolve_asset_path(source_frame_record[reference_role_name+'_path'])
        if hash_asset_file(reference_asset_path)!=source_frame_record[reference_role_name+'_sha256']:
            raise ValueError(f'생성 중 원본 변경: {reference_asset_path}')
        reference_output_path=frame_output_directory/(reference_role_name+'-reference.png')
        with Image.open(reference_asset_path) as reference_image_value:
            if reference_image_value.size!=(512,512):raise ValueError('레퍼런스는 512×512여야 합니다.')
            reference_background_image=Image.new('RGBA',(512,512),'white' if reference_role_name=='character' else 'black')
            reference_background_image.alpha_composite(reference_image_value.convert('RGBA'))
            reference_background_image.convert('RGB').save(reference_output_path)
        input_reference_paths[reference_role_name]=reference_output_path
    selected_anny_mode=generation_request_record['source']=='anny'
    execute_pose_generation(trial_output_root=frame_output_directory,prompt_text_value='\n\n'.join(generation_request_record['prompts'].values()),character_image_path=input_reference_paths['character'],pose_reference_path=input_reference_paths['pose'],pose_reference_kind='rig' if selected_anny_mode else 'openpose',selected_inference_steps=4,prompt_source_record={'kind':'registered-character-animation','motion':generation_request_record['motion'],'sha256':generation_request_record['prompt_sha256'],'words':generation_request_record['prompt_words']},enable_anypose_adapter=selected_anny_mode,enable_lightning_adapter=True,enable_standalone_lightning_adapter=not selected_anny_mode)


def generate_character_animation(generation_job_path):
    generation_request_record=json.loads((generation_job_path/'request.json').read_text())
    generation_gpu_lock_path=WORKFLOW_ROOT_DIRECTORY/'.local/image-generation-gpu.lock'
    generation_gpu_lock_path.parent.mkdir(parents=True,exist_ok=True)
    generation_result_frames={direction_name_value:[] for direction_name_value in generation_request_record['directions']}
    with generation_gpu_lock_path.open('a') as generation_gpu_lock_handle:
        acquire_worker_lock(generation_gpu_lock_handle,'waiting-gpu')
        for current_frame_index,source_frame_record in enumerate(generation_request_record['frames']):
            write_record_atomically(generation_job_path/'progress.json',{'completed':current_frame_index,'total':len(generation_request_record['frames']),'direction':source_frame_record['direction'],'frame':source_frame_record['frame']})
            # 프레임별 프로세스 종료로 모델·CUDA 메모리를 확실히 회수한다.
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'--job-dir',str(generation_job_path),'--frame-index',str(current_frame_index)],check=True)
            result_relative_path=f"{source_frame_record['direction']}/frame-{source_frame_record['frame']:04d}/result.png"
            if not (generation_job_path/result_relative_path).is_file():raise ValueError('생성 이미지 누락')
            generation_result_frames[source_frame_record['direction']].append(result_relative_path)
        write_record_atomically(generation_job_path/'result.json',{'fps':generation_request_record['fps'],'frames':generation_result_frames,'motion':generation_request_record['motion'],'source':generation_request_record['source'],'sampling':'none'})
        write_record_atomically(generation_job_path/'progress.json',{'completed':len(generation_request_record['frames']),'total':len(generation_request_record['frames'])})

if __name__=='__main__':
    execution_argument_parser=argparse.ArgumentParser()
    execution_argument_parser.add_argument('--job-dir',required=True,type=Path)
    execution_argument_parser.add_argument('--frame-index',type=int)
    execution_argument_values=execution_argument_parser.parse_args()
    if execution_argument_values.frame_index is None:generate_character_animation(execution_argument_values.job_dir)
    else:generate_character_frame(execution_argument_values.job_dir,execution_argument_values.frame_index)
