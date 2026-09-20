#!/usr/bin/env python3
"""고정 Qwen 모델로 두 이미지 참조 기반의 단일 포즈 편집을 실행한다."""
from pathlib import Path
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import logging
import subprocess
import threading
import time

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXED_MODEL_REVISION = '6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9'
FIXED_MODEL_DIRECTORY = WORKFLOW_REPO_ROOT / '.model/qwen-image-edit-2511' / FIXED_MODEL_REVISION
FIXED_IMAGE_DIMENSIONS = 512
FIXED_INFERENCE_STEPS = 4
FIXED_GENERATOR_SEED = 10107


def execute_pose_experiment():
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--output-dir', type=Path, default=WORKFLOW_REPO_ROOT / '.tmp' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S'))
    argument_value_parser.add_argument('--prompt-file', type=Path, required=True)
    argument_value_parser.add_argument('--steps', type=int, choices=(4, 10, 20), default=FIXED_INFERENCE_STEPS)
    argument_value_parser.add_argument('--reference-order', choices=('standing-first', 'pose-first'), default='standing-first')
    parsed_argument_values = argument_value_parser.parse_args()
    selected_inference_steps = parsed_argument_values.steps
    trial_output_root = parsed_argument_values.output_dir.resolve()
    if not trial_output_root.is_relative_to(WORKFLOW_REPO_ROOT / '.tmp'):
        raise ValueError('후보 에셋 출력은 저장소 .tmp 하위만 허용합니다.')
    trial_output_root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s/qwen-pose/%(message)s', handlers=[logging.FileHandler(trial_output_root/'execution.log'), logging.StreamHandler()])
    current_stage_state = {'stage':'imports', 'step':0}
    heartbeat_stop_event = threading.Event()
    qwen_pipeline_module = None
    original_reference_area = None
    run_started_time = time.monotonic()

    def emit_progress_heartbeat():
        while not heartbeat_stop_event.wait(5):
            gpu_status_result = subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader'], capture_output=True,text=True)
            logging.info('heartbeat stage=%s step=%s/%s elapsed=%.0fs gpu=%s log_bytes=%s',current_stage_state['stage'],current_stage_state['step'],selected_inference_steps,time.monotonic()-run_started_time,gpu_status_result.stdout.strip(),(trial_output_root/'execution.log').stat().st_size)

    threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
    try:
        import torch
        import diffusers
        from PIL import Image
        from diffusers import QwenImageEditPlusPipeline
        from diffusers.pipelines.qwenimage import pipeline_qwenimage_edit_plus as qwen_pipeline_module
        if diffusers.__version__ != "0.37.0" or qwen_pipeline_module.VAE_IMAGE_SIZE != 1024 * 1024:
            raise RuntimeError("참조 인코딩 크기 조정은 검증한 diffusers 0.37.0 구현에서만 지원합니다.")
        original_reference_area = qwen_pipeline_module.VAE_IMAGE_SIZE
        qwen_pipeline_module.VAE_IMAGE_SIZE = FIXED_IMAGE_DIMENSIONS * FIXED_IMAGE_DIMENSIONS
        logging.info("reference vae_size=512x512 output_size=512x512 condition_size=384x384")
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA를 사용할 수 없어 중단합니다. CPU 추론은 지원하지 않습니다.')
        if (trial_output_root/'result.png').exists():
            raise FileExistsError('기존 결과를 덮어쓸 수 없습니다. 새 실행 경로를 사용하세요.')
        prompt_text_value = parsed_argument_values.prompt_file.read_text().strip()
        if not prompt_text_value:
            raise ValueError('편집 프롬프트가 비어 있습니다.')
        (trial_output_root / 'prompt.txt').write_text(prompt_text_value + '\n')
        input_image_paths = [trial_output_root/'standing-reference.png',trial_output_root/'openpose-reference.png']
        if parsed_argument_values.reference_order == 'pose-first':
            input_image_paths.reverse()
        logging.info('reference order=%s', [input_file_path.name for input_file_path in input_image_paths])
        input_image_values = [Image.open(input_file_path).convert('RGB') for input_file_path in input_image_paths]
        if any(input_image_value.size != (512,512) for input_image_value in input_image_values):
            raise ValueError('입력 이미지는 512×512여야 합니다.')
        current_stage_state['stage']='load'
        logging.info('load model_id=Qwen/Qwen-Image-Edit-2511 model_path=%s',FIXED_MODEL_DIRECTORY)
        image_edit_pipeline = QwenImageEditPlusPipeline.from_pretrained(str(FIXED_MODEL_DIRECTORY),torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
        image_edit_pipeline.enable_sequential_cpu_offload()
        image_edit_pipeline.vae.enable_slicing()
        image_edit_pipeline.vae.enable_tiling()
        current_stage_state['stage']='inference'
        logging.info('inference size=512x512 steps=%s seed=%s device=cuda dtype=bfloat16 offload=sequential',selected_inference_steps,FIXED_GENERATOR_SEED)

        def record_denoise_progress(pipeline_instance_value, step_index_value, timestep_value, callback_value_dictionary):
            current_stage_state['step']=step_index_value+1
            logging.info('denoise step=%s/%s',step_index_value+1,selected_inference_steps)
            return callback_value_dictionary

        with torch.inference_mode():
            output_image_value = image_edit_pipeline(image=input_image_values,prompt=prompt_text_value,negative_prompt=' ',width=FIXED_IMAGE_DIMENSIONS,height=FIXED_IMAGE_DIMENSIONS,num_inference_steps=selected_inference_steps,true_cfg_scale=4.0,guidance_scale=1.0,generator=torch.Generator(device='cuda').manual_seed(FIXED_GENERATOR_SEED),num_images_per_prompt=1,callback_on_step_end=record_denoise_progress).images[0]
        if output_image_value.size != (512,512):
            raise ValueError(f'출력 크기 불일치: {output_image_value.size}')
        output_image_value.save(trial_output_root/'result.png')
        trial_result_record = {'status':'completed','model_id':'Qwen/Qwen-Image-Edit-2511','revision':FIXED_MODEL_REVISION,'size':[512,512],'reference_vae_size':[512,512],'reference_condition_size':[384,384],'steps':selected_inference_steps,'seed':FIXED_GENERATOR_SEED,'true_cfg_scale':4.0,'guidance_scale':1.0,'lightning_lora':False,'dtype':'bfloat16','execution_device':'cuda','weight_offload':'sequential_cpu_offload','torch_version':torch.__version__,'diffusers_version':diffusers.__version__,'elapsed_seconds':round(time.monotonic()-run_started_time,2),'prompt_sha256':hashlib.sha256(prompt_text_value.encode()).hexdigest(),'input_order':[input_file_path.name for input_file_path in input_image_paths],'input_sha256':{input_file_path.name:hashlib.sha256(input_file_path.read_bytes()).hexdigest() for input_file_path in input_image_paths},'quality_warnings':['실험 결과의 최종 품질 승인이 필요합니다.'],'output':'result.png'}
        (trial_output_root/'result.json').write_text(json.dumps(trial_result_record,ensure_ascii=False,indent=2)+'\n')
        current_stage_state['stage']='complete'
        logging.info('complete output=%s',trial_output_root/'result.png')
    except Exception:
        logging.exception('failed stage=%s',current_stage_state['stage'])
        print('\n'.join((trial_output_root/'execution.log').read_text().splitlines()[-25:]),flush=True)
        raise
    finally:
        if qwen_pipeline_module is not None and original_reference_area is not None:
            qwen_pipeline_module.VAE_IMAGE_SIZE = original_reference_area
        heartbeat_stop_event.set()


if __name__ == '__main__':
    execute_pose_experiment()
