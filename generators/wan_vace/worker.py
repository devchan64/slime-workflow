"""VACE-Fun Q4 고·저노이즈 전문가를 CUDA에서 순차 실행한다."""
from pathlib import Path
import sys
import os
VACE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VACE_WORKSPACE_ROOT))
from generators.wan_vace.contracts import VACE_JOB_STORAGE, verify_vace_weights
from generators.common.reference_video_worker import run_reference_video_worker


def build_vace_conditions(current_request_record, current_reference_tensor):
    """외형 참조는 별도 잠재 슬롯, 첫 프레임은 비편집 마스크로 전달한다."""
    import torch
    current_frame_count = current_request_record['frames']
    if current_request_record['mode'] == 'reference':
        return {'reference_image': current_reference_tensor}
    if current_request_record['mode'] == 'first_frame':
        current_video_tensor = torch.full((current_frame_count, 480, 832, 3), 0.5)
        current_video_tensor[:1] = current_reference_tensor
        current_mask_tensor = torch.ones((current_frame_count, 480, 832))
        current_mask_tensor[:1] = 0
        return {'control_video': current_video_tensor, 'control_masks': current_mask_tensor}
    return {}


def execute_vace_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    """공식 파이프라인과 고정 GGUF 어댑터로 실행한다."""
    os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:True'
    from generators.wan_vace.official_runtime import execute_official_inference
    return execute_official_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder)


if __name__ == '__main__':
    run_reference_video_worker(VACE_JOB_STORAGE, Path(__file__), verify_vace_weights, execute_vace_inference)
