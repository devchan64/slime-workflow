"""ComfyUI의 discrete-flow simple 스케줄과 LCM 갱신을 재현한다."""
import torch
from diffusers import FlowMatchEulerDiscreteScheduler
from diffusers.utils.torch_utils import randn_tensor


class AnimateLightX2VScheduler(FlowMatchEulerDiscreteScheduler):
    def __init__(self):
        super().__init__(num_train_timesteps=1000, shift=5.0)

    def set_timesteps(self, num_inference_steps, device=None, **kwargs):
        if type(num_inference_steps) is not int or not 2 <= num_inference_steps <= 50:
            raise ValueError('LightX2V 스텝은 2~50이어야 합니다.')
        # ComfyUI simple_scheduler: 1000개의 shift된 이산 sigma를 역순 선택.
        ts = torch.arange(1, 1001, dtype=torch.float32) / 1000
        sigmas = 5 * ts / (1 + 4 * ts)
        indices = [999 - int(i * 1000 / num_inference_steps) for i in range(num_inference_steps)]
        self.sigmas = torch.cat((sigmas[indices], torch.zeros(1))).to(device=device)
        self.timesteps = self.sigmas[:-1] * 1000
        self._step_index = 0
        self.num_inference_steps = num_inference_steps

    def step(self, model_output, timestep, sample, generator=None, return_dict=True, **kwargs):
        if self._step_index is None or self._step_index >= self.num_inference_steps:
            raise ValueError('LightX2V 스케줄러를 먼저 초기화해야 합니다.')
        sigma = self.sigmas[self._step_index]
        next_sigma = self.sigmas[self._step_index + 1]
        if not torch.isclose(timestep.to(sigma.device), self.timesteps[self._step_index]):
            raise ValueError('LightX2V 스케줄러 스텝 순서가 일치하지 않습니다.')
        denoised = sample.float() - sigma * model_output.float()
        if self._step_index + 1 < self.num_inference_steps:
            noise = randn_tensor(sample.shape, generator=generator, device=sample.device, dtype=torch.float32)
            denoised = next_sigma * noise + (1 - next_sigma) * denoised
        self._step_index += 1
        output = denoised.to(sample.dtype)
        if return_dict:
            from diffusers.schedulers.scheduling_flow_match_euler_discrete import FlowMatchEulerDiscreteSchedulerOutput
            return FlowMatchEulerDiscreteSchedulerOutput(prev_sample=output)
        return (output,)
