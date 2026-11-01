"""공식 forward를 변경하지 않고 가중치의 CPU·CUDA 이동만 수행한다."""

def install_expert_block_offload(current_model_object):
    def load_block_cuda(current_block_module,current_input_values):
        current_block_module.to('cuda')
    def release_block_cpu(current_block_module,current_input_values,current_output_values):
        current_block_module.to('cpu')
    for current_block_list in (current_model_object.blocks,current_model_object.vace_blocks):
        for current_block_module in current_block_list:
            current_block_module.register_forward_pre_hook(load_block_cuda)
            current_block_module.register_forward_hook(release_block_cpu)
