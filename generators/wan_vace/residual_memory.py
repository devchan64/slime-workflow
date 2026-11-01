"""고정 공식 블록의 잔차 임시 텐서 절감과 블록 단위 CUDA 오프로드."""
import ast
import inspect
import textwrap
import torch
from generators.wan_vace.rotary_memory import ROTARY_TOKEN_CHUNK_SIZE


def add_chunked_residual(current_base_tensor, current_delta_tensor, current_scale_tensor=None):
    current_output_dtype = torch.promote_types(current_base_tensor.dtype,current_delta_tensor.dtype)
    if current_scale_tensor is not None:
        current_output_dtype = torch.promote_types(current_output_dtype,current_scale_tensor.dtype)
    current_output_tensor = torch.empty_like(current_base_tensor,dtype=current_output_dtype)
    for current_chunk_start in range(0,current_base_tensor.shape[-2],ROTARY_TOKEN_CHUNK_SIZE):
        current_chunk_end = min(current_chunk_start+ROTARY_TOKEN_CHUNK_SIZE,current_base_tensor.shape[-2])
        current_delta_chunk = current_delta_tensor[...,current_chunk_start:current_chunk_end,:]
        if current_scale_tensor is not None:
            current_scale_chunk = current_scale_tensor if current_scale_tensor.shape[-2]==1 else current_scale_tensor[...,current_chunk_start:current_chunk_end,:]
            current_delta_chunk = current_delta_chunk*current_scale_chunk
        current_output_tensor[...,current_chunk_start:current_chunk_end,:] = current_base_tensor[...,current_chunk_start:current_chunk_end,:]+current_delta_chunk
    return current_output_tensor


def install_residual_memory(current_attention_class):
    current_original_function = current_attention_class.forward
    current_source_tree = ast.parse(textwrap.dedent(inspect.getsource(current_original_function)))
    current_replace_count = 0
    class ResidualMemoryTransformer(ast.NodeTransformer):
        def visit_Assign(self, current_assign_node):
            nonlocal current_replace_count
            current_target_name = current_assign_node.targets[0]
            current_value_node = current_assign_node.value
            if isinstance(current_target_name,ast.Name) and current_target_name.id=='x' and isinstance(current_value_node,ast.BinOp) and isinstance(current_value_node.op,ast.Add) and isinstance(current_value_node.left,ast.Name) and current_value_node.left.id=='x':
                current_right_node = current_value_node.right
                current_arguments_list = [current_value_node.left]
                if isinstance(current_right_node,ast.BinOp) and isinstance(current_right_node.op,ast.Mult):
                    current_arguments_list.extend([current_right_node.left,current_right_node.right])
                else:
                    current_arguments_list.append(current_right_node)
                current_assign_node.value = ast.Call(func=ast.Name(id='add_chunked_residual',ctx=ast.Load()),args=current_arguments_list,keywords=[])
                current_replace_count += 1
            if isinstance(current_target_name,ast.Name) and current_target_name.id=='y' and isinstance(current_value_node,ast.Call):
                return [current_assign_node,ast.Delete(targets=[ast.Name(id='temp_x',ctx=ast.Del())])]
            return current_assign_node
    current_source_tree = ResidualMemoryTransformer().visit(current_source_tree)
    if current_replace_count != 3:
        raise ValueError('공식 잔차 구조 불일치: 3개 잔차 연산 필요')
    current_global_values = dict(current_original_function.__globals__,add_chunked_residual=add_chunked_residual)
    exec(compile(ast.fix_missing_locations(current_source_tree),'<vace-residual-memory>','exec'),current_global_values)
    current_attention_class.forward = current_global_values['forward']


def install_expert_block_offload(current_model_object):
    def load_block_cuda(current_block_module,current_input_values):
        current_block_module.to('cuda')
    def release_block_cpu(current_block_module,current_input_values,current_output_values):
        current_block_module.to('cpu')
    for current_block_list in (current_model_object.blocks,current_model_object.vace_blocks):
        for current_block_module in current_block_list:
            current_block_module.register_forward_pre_hook(load_block_cuda)
            current_block_module.register_forward_hook(release_block_cpu)
