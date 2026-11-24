"""Wan 2.1 I2V 저장 입력 계약."""
from generators.wan21_video_contracts import validate_request
from workflow.common.video_input_restore import load_video_saved_input


def load_saved_input(root, job):
    allowed = {'action','prompt','negative_prompt','width','height','frames','steps','seed','flow_shift','guidance_scale','acceleration','action_lora','action_variant','action_strength'}
    return load_video_saved_input(root, job, 'wan21-i2v', allowed, lambda request: validate_request(request, 'i2v'))
