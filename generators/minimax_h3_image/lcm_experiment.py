"""Experimental flow-LCM update for the MiniMax image sampler."""


def lcm_noise_scale(step, total_steps, start=1.10, end=0.90):
    if type(step) is not int or type(total_steps) is not int or total_steps < 2 or not 0 <= step < total_steps:
        raise ValueError('invalid LCM step')
    return start + (end - start) * step / (total_steps - 1)


def flow_lcm_step(sample, model_output, sigma, sigma_next, noise, noise_scale):
    """Candidate flow update; caller supplies seeded noise and checks finiteness."""
    if not 0 <= sigma_next < sigma <= 1:
        raise ValueError('invalid sigma transition')
    denoised = sample + model_output * sigma
    if sigma_next == 0:
        return denoised
    return (1 - sigma_next) * denoised + sigma_next * noise * noise_scale


def make_lcm_scheduler(base_scheduler, seed):
    """Wrap an individual scheduler without changing the runtime scheduler class."""
    import torch

    class ExperimentalLCMScheduler(type(base_scheduler)):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.lcm_seed = seed
            self.lcm_generator = torch.Generator(device='cpu').manual_seed(seed)

        def step(self, model_output, timestep, sample, return_dict=False, **kwargs):
            i = self._step_index
            sigma, next_sigma = float(self.sigmas[i]), float(self.sigmas[i + 1])
            if not torch.isfinite(sample).all().item() or not torch.isfinite(model_output).all().item():
                raise ValueError('LCM 입력에 NaN 또는 무한대가 있습니다.')
            noise = (torch.randn(sample.shape, generator=self.lcm_generator, device='cpu', dtype=torch.float32).to(sample.device)
                     if next_sigma else 0)
            scale = lcm_noise_scale(i, 6)
            result = flow_lcm_step(sample.float(), model_output.float(), sigma, next_sigma, noise, scale)
            if not torch.isfinite(result).all().item():
                raise ValueError('LCM 출력에 NaN 또는 무한대가 있습니다.')
            self._step_index = i + 1
            print(f'lcm_step {i + 1} sigma={sigma} next={next_sigma} noise_scale={scale}', flush=True)
            return (result.to(sample.dtype),)

    return ExperimentalLCMScheduler(sample_sigmas=base_scheduler.head_grid)
