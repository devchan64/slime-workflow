"""검증된 공식 파이프라인에 인코딩 완료 입력의 CPU 보관만 추가한다."""
import hashlib
import importlib.util

VACE_PIPELINE_RELATIVE_PATH = 'videox_fun/pipeline/pipeline_wan2_2_vace_fun.py'
VACE_PIPELINE_OFFLOAD_ANCHOR = '        vace_context = self.vace_latent(vace_latents, mask_latents)\n'
VACE_PIPELINE_OFFLOAD_INSERT = '''
        # 인코딩 완료 입력은 값·dtype을 보존하여 CPU에 보관한다.
        input_video = input_video.to("cpu")
        mask_condition = mask_condition.to("cpu")
        if control_video is None and video is not None:
            init_video = init_video.to("cpu")
        vace_latents = [current_latent_tensor.to("cpu") for current_latent_tensor in vace_latents]
        mask_latents = [current_latent_tensor.to("cpu") for current_latent_tensor in mask_latents]
'''

VACE_BRANCH_OFFLOAD_REPLACEMENTS = (
    ('            c = self.before_proj(c) + x\n', '            c = self.before_proj(c) + x.to(c.device)\n'),
    ('            c = c.to(x.device)\n', '            c = c.to(kwargs["e"].device)\n'),
    ('        hints = self.forward_vace(x, vace_context, seq_len, kwargs)\n',
     '        x = x.to("cpu")\n        hints = self.forward_vace(x, vace_context, seq_len, kwargs)\n        x = x.to(device)\n'),
)


def load_branch_offload_model(current_source_root, current_attempt_root):
    """VACE 분기 계산 동안 본체 입력을 CPU에 보관하고 복귀시킨다."""
    from tools.review.common.generation_records import write_record_atomically
    current_source_text = (current_source_root / 'videox_fun/models/wan_transformer3d_vace.py').read_text()
    current_patched_text = current_source_text
    for current_original_text, current_replacement_text in VACE_BRANCH_OFFLOAD_REPLACEMENTS:
        if current_patched_text.count(current_original_text) != 1:
            raise ValueError('공식 VACE 분기 오프로드 위치가 일치하지 않습니다.')
        current_patched_text = current_patched_text.replace(current_original_text, current_replacement_text)
    current_output_path = current_attempt_root / 'model-branch-offload.py'
    current_output_path.write_text(current_patched_text)
    write_record_atomically(current_attempt_root / 'branch-offload-source.json', {
        'upstream_sha256': hashlib.sha256(current_source_text.encode()).hexdigest(),
        'execution_sha256': hashlib.sha256(current_patched_text.encode()).hexdigest(),
        'replacements': VACE_BRANCH_OFFLOAD_REPLACEMENTS,
        'policy': '공식 연산식 유지, VACE 분기 대기 입력 CPU 보관 및 CUDA 복귀',
    })
    current_module_spec = importlib.util.spec_from_file_location('videox_fun.models.model_branch_offload', current_output_path)
    current_module_object = importlib.util.module_from_spec(current_module_spec)
    current_module_spec.loader.exec_module(current_module_object)
    return current_module_object.VaceWanTransformer3DModel


def load_input_offload_pipeline(current_source_root, current_attempt_root):
    """공식 파일을 수정하지 않고 이동문만 포함한 실행 사본을 기록·로딩한다."""
    from tools.review.common.generation_records import write_record_atomically
    current_source_text = (current_source_root / VACE_PIPELINE_RELATIVE_PATH).read_text()
    if current_source_text.count(VACE_PIPELINE_OFFLOAD_ANCHOR) != 1:
        raise ValueError('공식 VACE 입력 오프로드 위치가 일치하지 않습니다.')
    current_patched_text = current_source_text.replace(VACE_PIPELINE_OFFLOAD_ANCHOR, VACE_PIPELINE_OFFLOAD_ANCHOR + VACE_PIPELINE_OFFLOAD_INSERT)
    current_output_path = current_attempt_root / 'pipeline-input-offload.py'
    current_output_path.write_text(current_patched_text)
    write_record_atomically(current_attempt_root / 'input-offload-source.json', {
        'upstream_sha256': hashlib.sha256(current_source_text.encode()).hexdigest(),
        'execution_sha256': hashlib.sha256(current_patched_text.encode()).hexdigest(),
        'insertion': VACE_PIPELINE_OFFLOAD_INSERT,
        'policy': '공식 연산식 유지, 인코딩 완료 입력 CPU 보관',
    })
    current_module_spec = importlib.util.spec_from_file_location('videox_fun.pipeline.pipeline_input_offload', current_output_path)
    current_module_object = importlib.util.module_from_spec(current_module_spec)
    current_module_spec.loader.exec_module(current_module_object)
    return current_module_object.Wan2_2VaceFunPipeline
