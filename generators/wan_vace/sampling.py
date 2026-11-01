"""공식 Euler 스케줄러에 요청 shift를 적용한다."""


def build_vace_scheduler(current_flow_shift):
    from diffusers import FlowMatchEulerDiscreteScheduler
    return FlowMatchEulerDiscreteScheduler(
        num_train_timesteps=1000, shift=current_flow_shift, use_dynamic_shifting=False,
    )
