"""오프로드 훅과 분리하여 공식 Flex Attention만 전체 그래프로 컴파일한다."""
import torch
from torch.nn.attention import flex_attention as flex_attention_module


def build_compiled_attention(current_attention_function):
    """밀집 eager 실행을 거절하는 독립 CUDA attention 경계를 만든다."""
    def execute_compiled_attention(*current_attention_arguments, **current_attention_keywords):
        if not torch.compiler.is_compiling():
            raise RuntimeError('Flex Attention 컴파일이 해제되었습니다. 밀집 연산을 실행하지 않습니다.')
        return current_attention_function(*current_attention_arguments, **current_attention_keywords)

    current_compiled_function = torch.compile(execute_compiled_attention, backend='inductor', fullgraph=True)

    @torch.compiler.disable
    def dispatch_compiled_attention(*current_attention_arguments, **current_attention_keywords):
        return current_compiled_function(*current_attention_arguments, **current_attention_keywords)

    return dispatch_compiled_attention


def enable_compiled_attention():
    """현재 생성 작업 프로세스의 공식 Flex 진입점만 감싼다."""
    flex_attention_module.flex_attention = build_compiled_attention(flex_attention_module.flex_attention)
