#!/usr/bin/env python3
"""고정 Qwen 모델로 두 이미지 참조 기반의 단일 포즈 편집을 실행한다."""
from pathlib import Path
import hashlib
import math
import json
import logging
import subprocess
import threading
import time

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[3]
FIXED_MODEL_REVISION = '6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9'
FIXED_MODEL_DIRECTORY = WORKFLOW_REPO_ROOT / '.model/qwen-image-edit-2511' / FIXED_MODEL_REVISION
FIXED_IMAGE_DIMENSIONS = 512
FIXED_INFERENCE_STEPS = 10
FIXED_GENERATOR_SEED = 10107


PIPELINE_EXECUTION_LOCK = threading.Lock()


def execute_pose_generation(*, trial_output_root, prompt_text_value,
                            character_image_path, pose_reference_path,
                            pose_reference_kind, selected_reference_order='standing-first',
                            selected_inference_steps=FIXED_INFERENCE_STEPS,
                            prompt_source_record=None, enable_anypose_adapter=False, enable_lightning_adapter=True,
                            selected_base_strength=0.7, selected_helper_strength=0.7):
    """준비된 512px 참조로 포즈를 변경한다. GPU 실행은 샌드박스 밖에서 호출한다."""
    from PIL import Image
    from .prompts import validate_reference_options
    validate_reference_options(pose_reference_kind, selected_reference_order)
    if type(enable_anypose_adapter) is not bool:
        raise ValueError('AnyPose 활성화는 bool이어야 합니다.')
    if type(enable_lightning_adapter) is not bool:
        raise ValueError('Lightning 활성화는 bool이어야 합니다.')
    for selected_adapter_strength in (selected_base_strength, selected_helper_strength):
        if type(selected_adapter_strength) not in (int, float) or not math.isfinite(selected_adapter_strength) or not 0 <= selected_adapter_strength <= 1.5:
            raise ValueError('AnyPose strength는 0~1.5의 유한 숫자여야 합니다.')
    if not enable_anypose_adapter and (selected_base_strength != 0.7 or selected_helper_strength != 0.7):
        raise ValueError('AnyPose 비활성 상태에서는 strength를 변경할 수 없습니다.')
    active_lightning_adapter = enable_anypose_adapter and enable_lightning_adapter
    required_anypose_steps = 4 if active_lightning_adapter else 10
    if enable_anypose_adapter and (pose_reference_kind != 'rig' or selected_reference_order != 'standing-first' or selected_inference_steps != required_anypose_steps):
        raise ValueError('AnyPose는 리그·캐릭터 우선, Lightning=4스텝 또는 비Lightning=10스텝이어야 합니다.')
    selected_true_cfg_scale = 1.0 if active_lightning_adapter else 4.0
    resolved_adapter_records = []
    if type(selected_inference_steps) is not int or selected_inference_steps not in (4, 10, 20):
        raise ValueError('steps는 4, 10, 20만 허용합니다.')
    if not isinstance(prompt_text_value, str) or not prompt_text_value.strip():
        raise ValueError('편집 프롬프트가 비어 있습니다.')
    prompt_text_value = prompt_text_value.strip()
    trial_output_root = Path(trial_output_root).resolve()
    if not trial_output_root.is_relative_to((WORKFLOW_REPO_ROOT / '.tmp').resolve()):
        raise ValueError('후보 에셋 출력은 저장소 .tmp 하위만 허용합니다.')
    if any((trial_output_root / output_file_name).exists() for output_file_name in ('result.png', 'result.json', 'execution.log')):
        raise FileExistsError('기존 실행을 덮어쓸 수 없습니다. 새 실행 경로를 사용하세요.')
    input_image_paths = [Path(character_image_path).resolve(), Path(pose_reference_path).resolve()]
    input_image_roles = ['character', pose_reference_kind]
    if selected_reference_order == 'pose-first':
        input_image_paths.reverse()
        input_image_roles.reverse()
    input_image_values = []
    for input_file_path in input_image_paths:
        with Image.open(input_file_path) as input_image_value:
            if input_image_value.format != 'PNG' or input_image_value.size != (512, 512):
                raise ValueError('입력은 512×512 PNG여야 합니다.')
            if input_image_value.mode not in ('RGB', 'RGBA'):
                raise ValueError('입력은 RGB/RGBA여야 합니다.')
            if input_image_value.mode == 'RGBA' and input_image_value.getextrema()[3] != (255, 255):
                raise ValueError('투명 참조는 먼저 캐릭터=흰색, 포즈=해당 배경으로 합성하세요.')
            input_image_values.append(input_image_value.convert('RGB'))
    if not PIPELINE_EXECUTION_LOCK.acquire(blocking=False):
        raise RuntimeError('참조 VAE 설정 충돌 방지를 위해 동시 추론을 허용하지 않습니다.')
    try:
        trial_output_root.mkdir(parents=True, exist_ok=True)
        run_output_logger = logging.getLogger(f'qwen-pose.{trial_output_root.name}')
        run_output_logger.setLevel(logging.INFO)
        run_output_logger.propagate = False
        for output_log_handler in (logging.FileHandler(trial_output_root/'execution.log'), logging.StreamHandler()):
            output_log_handler.setFormatter(logging.Formatter('%(asctime)s/qwen-pose/%(message)s'))
            run_output_logger.addHandler(output_log_handler)
    except Exception:
        PIPELINE_EXECUTION_LOCK.release()
        raise
    current_stage_state = {'stage':'imports', 'step':0}
    heartbeat_stop_event = threading.Event()
    qwen_pipeline_module = None
    original_reference_area = None
    run_started_time = time.monotonic()

    def emit_progress_heartbeat():
        while not heartbeat_stop_event.wait(5):
            try:
                gpu_status_result = subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader'], capture_output=True,text=True,timeout=3,check=True)
            except (OSError, subprocess.SubprocessError):
                run_output_logger.exception('heartbeat GPU 상태 조회 실패')
                continue
            run_output_logger.info('heartbeat stage=%s step=%s/%s elapsed=%.0fs gpu=%s log_bytes=%s',current_stage_state['stage'],current_stage_state['step'],selected_inference_steps,time.monotonic()-run_started_time,gpu_status_result.stdout.strip(),(trial_output_root/'execution.log').stat().st_size)

    heartbeat_worker_thread = threading.Thread(target=emit_progress_heartbeat,daemon=True)
    heartbeat_worker_thread.start()
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
        run_output_logger.info("reference vae_size=512x512 output_size=512x512 condition_size=384x384")
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA를 사용할 수 없어 중단합니다. CPU 추론은 지원하지 않습니다.')
        if (trial_output_root/'result.png').exists():
            raise FileExistsError('기존 결과를 덮어쓸 수 없습니다. 새 실행 경로를 사용하세요.')
        (trial_output_root / 'prompt.txt').write_text(prompt_text_value + '\n')
        run_output_logger.info('reference order=%s kind=%s', input_image_roles, pose_reference_kind)
        if not (FIXED_MODEL_DIRECTORY/'model_index.json').is_file():
            raise FileNotFoundError(f'모델 준비 필요: model_id=Qwen/Qwen-Image-Edit-2511 model_path={FIXED_MODEL_DIRECTORY}')
        if enable_anypose_adapter:
            from .anypose import validate_adapter_files
            resolved_adapter_records = validate_adapter_files(include_lightning_adapter=active_lightning_adapter)
            for adapter_record_values in resolved_adapter_records:
                if adapter_record_values['name'] == 'anypose_base':
                    adapter_record_values['strength'] = selected_base_strength
                elif adapter_record_values['name'] == 'anypose_helper':
                    adapter_record_values['strength'] = selected_helper_strength
        current_stage_state['stage']='load' 
        run_output_logger.info('load model_id=Qwen/Qwen-Image-Edit-2511 model_path=%s',FIXED_MODEL_DIRECTORY)
        image_edit_pipeline = QwenImageEditPlusPipeline.from_pretrained(str(FIXED_MODEL_DIRECTORY),torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
        if enable_anypose_adapter:
            current_stage_state['stage'] = 'adapters'
            for adapter_record_values in resolved_adapter_records:
                adapter_file_path = Path(adapter_record_values['path'])
                run_output_logger.info('adapter name=%s strength=%s path=%s', adapter_record_values['name'], adapter_record_values['strength'], adapter_file_path)
                image_edit_pipeline.load_lora_weights(str(adapter_file_path.parent), weight_name=adapter_file_path.name, adapter_name=adapter_record_values['name'], local_files_only=True)
            image_edit_pipeline.set_adapters([adapter_record_values['name'] for adapter_record_values in resolved_adapter_records], adapter_weights=[adapter_record_values['strength'] for adapter_record_values in resolved_adapter_records])
        image_edit_pipeline.enable_sequential_cpu_offload()
        image_edit_pipeline.vae.enable_slicing()
        image_edit_pipeline.vae.enable_tiling()
        current_stage_state['stage']='inference'
        run_output_logger.info('inference size=512x512 steps=%s seed=%s device=cuda dtype=bfloat16 offload=sequential',selected_inference_steps,FIXED_GENERATOR_SEED)

        def record_denoise_progress(pipeline_instance_value, step_index_value, timestep_value, callback_value_dictionary):
            current_stage_state['step']=step_index_value+1
            run_output_logger.info('denoise step=%s/%s',step_index_value+1,selected_inference_steps)
            return callback_value_dictionary

        with torch.inference_mode():
            output_image_value = image_edit_pipeline(image=input_image_values,prompt=prompt_text_value,negative_prompt=' ',width=FIXED_IMAGE_DIMENSIONS,height=FIXED_IMAGE_DIMENSIONS,num_inference_steps=selected_inference_steps,true_cfg_scale=selected_true_cfg_scale,guidance_scale=1.0,generator=torch.Generator(device='cuda').manual_seed(FIXED_GENERATOR_SEED),num_images_per_prompt=1,callback_on_step_end=record_denoise_progress).images[0]
        if output_image_value.size != (512,512):
            raise ValueError(f'출력 크기 불일치: {output_image_value.size}')
        output_image_value.save(trial_output_root/'result.png')
        trial_result_record = {'status':'completed','model_id':'Qwen/Qwen-Image-Edit-2511','revision':FIXED_MODEL_REVISION,'size':[512,512],'reference_vae_size':[512,512],'reference_condition_size':[384,384],'steps':selected_inference_steps,'seed':FIXED_GENERATOR_SEED,'true_cfg_scale':selected_true_cfg_scale,'guidance_scale':1.0,'lightning_lora':active_lightning_adapter,'dtype':'bfloat16','execution_device':'cuda','weight_offload':'sequential_cpu_offload','torch_version':torch.__version__,'diffusers_version':diffusers.__version__,'elapsed_seconds':round(time.monotonic()-run_started_time,2),'prompt_sha256':hashlib.sha256(prompt_text_value.encode()).hexdigest(),'input_order':[input_file_path.name for input_file_path in input_image_paths],'input_sha256':{input_file_path.name:hashlib.sha256(input_file_path.read_bytes()).hexdigest() for input_file_path in input_image_paths},'quality_warnings':['실험 결과의 최종 품질 승인이 필요합니다.'],'output':'result.png'}
        trial_result_record.update({'pose_reference_kind': pose_reference_kind, 'reference_order': selected_reference_order, 'prompt_source': prompt_source_record, 'adapters': resolved_adapter_records, 'execution_preset': ('anypose-lightning-v1' if active_lightning_adapter else 'anypose-standard-v1') if enable_anypose_adapter else 'base-v1', 'input_references': [{'role': input_image_role, 'path': str(input_file_path), 'sha256': hashlib.sha256(input_file_path.read_bytes()).hexdigest()} for input_image_role, input_file_path in zip(input_image_roles, input_image_paths)]})
        (trial_output_root/'result.json').write_text(json.dumps(trial_result_record,ensure_ascii=False,indent=2)+'\n')
        current_stage_state['stage']='complete'
        run_output_logger.info('complete output=%s',trial_output_root/'result.png')
        return trial_result_record
    except Exception:
        run_output_logger.exception('failed stage=%s',current_stage_state['stage'])
        print('\n'.join((trial_output_root/'execution.log').read_text().splitlines()[-25:]),flush=True)
        raise
    finally:
        if qwen_pipeline_module is not None and original_reference_area is not None:
            qwen_pipeline_module.VAE_IMAGE_SIZE = original_reference_area
        heartbeat_stop_event.set()
        heartbeat_worker_thread.join(timeout=4)
        for output_log_handler in list(run_output_logger.handlers):
            output_log_handler.close()
            run_output_logger.removeHandler(output_log_handler)
        PIPELINE_EXECUTION_LOCK.release()
