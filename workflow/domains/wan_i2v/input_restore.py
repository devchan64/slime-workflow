"""Wan 2.2 I2V 저장 입력 계약."""
from generators.wan_i2v.contracts import validate_request
from workflow.common.video_input_restore import load_video_saved_input


def load_saved_input(root, job):
    allowed = {'action','prompt','negative_prompt','width','height','frames','steps','seed','flow_shift','guidance_scale','lora_mode','kungfu_strength'}
    return load_video_saved_input(root, job, 'wan22-i2v', allowed, validate_request)
