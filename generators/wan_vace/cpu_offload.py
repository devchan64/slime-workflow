"""공식 forward를 변경하지 않고 가중치의 CPU·CUDA 이동만 수행한다."""

VACE_TRANSIENT_MODULE_NAMES = frozenset((
    'text_embedding', 'time_embedding', 'time_projection',
    'vace_patch_embedding', 'head',
))

def install_expert_block_offload(current_model_object):
    def load_block_cuda(current_block_module,current_input_values):
        current_block_module.to('cuda')
    def release_block_cpu(current_block_module,current_input_values,current_output_values):
        current_block_module.to('cpu')
    for current_block_list in (current_model_object.blocks,current_model_object.vace_blocks):
        for current_block_module in current_block_list:
            current_block_module.register_forward_pre_hook(load_block_cuda)
            current_block_module.register_forward_hook(release_block_cpu)
    # patch_embedding은 공식 forward가 실행 장치를 조회하므로 GPU에 유지한다.
    # 나머지는 출력 텐서를 이동하지 않고 사용이 끝난 가중치만 내려보낸다.
    for current_module_name in VACE_TRANSIENT_MODULE_NAMES:
        current_module_object = getattr(current_model_object, current_module_name)
        current_module_object.register_forward_pre_hook(load_block_cuda)
        current_module_object.register_forward_hook(release_block_cpu)
