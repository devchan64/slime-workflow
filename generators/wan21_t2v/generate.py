#!/usr/bin/env python3
"""Experimental local Wan 2.1 1.3B text-to-video runner (Diffusers)."""
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='Local Diffusers-format Wan 2.1 T2V 1.3B model directory')
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--negative-prompt', default='')
    parser.add_argument('--boss-lora', type=Path, help='Local KXSR 1.3B T2V safetensors file')
    parser.add_argument('--boss-strength', type=float, default=1.0)
    parser.add_argument('--accelerator-lora', type=Path, help='Local compatible 1.3B accelerator LoRA (experimental)')
    parser.add_argument('--accelerator-strength', type=float, default=1.0)
    parser.add_argument('--width', type=int, default=832)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--frames', type=int, default=73)
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--guidance', type=float, default=3.5)
    parser.add_argument('--shift', type=float, default=4.0)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.prompt.strip(): parser.error('prompt must not be empty')
    if args.width < 16 or args.height < 16 or args.width % 16 or args.height % 16: parser.error('dimensions must be positive multiples of 16')
    if args.frames < 5 or (args.frames - 1) % 4: parser.error('frames must be 4n+1 and at least 5')
    if args.steps < 1 or args.shift <= 0 or args.guidance < 0: parser.error('invalid sampling settings')
    for path in (args.boss_lora, args.accelerator_lora):
        if path is not None and not path.is_file(): parser.error(f'LoRA file not found: {path}')
    if not Path(args.model).is_dir(): parser.error('model must be a local Diffusers model directory')
    return args


def main():
    raise SystemExit('Wan 2.1 T2V 실험은 폐기되었습니다.')
    args = parse_args()
    import torch
    from diffusers import AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, WanPipeline
    from diffusers.utils import export_to_video
    if not torch.cuda.is_available():
        raise RuntimeError('A CUDA or ROCm GPU is required')
    vae = AutoencoderKLWan.from_pretrained(args.model, subfolder='vae', torch_dtype=torch.float32, local_files_only=True)
    pipe = WanPipeline.from_pretrained(args.model, vae=vae, torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.scheduler = FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config, shift=args.shift)
    names, weights = [], []
    for name, path, weight in [('boss', args.boss_lora, args.boss_strength), ('accelerator', args.accelerator_lora, args.accelerator_strength)]:
        if path is not None:
            pipe.load_lora_weights(str(path.parent), weight_name=path.name, adapter_name=name, local_files_only=True)
            names.append(name); weights.append(weight)
    if names:
        pipe.set_adapters(names, adapter_weights=weights)
    pipe.to('cuda')
    frames = pipe(prompt=args.prompt, negative_prompt=args.negative_prompt, width=args.width, height=args.height, num_frames=args.frames, num_inference_steps=args.steps, guidance_scale=args.guidance, generator=torch.Generator(device='cuda').manual_seed(args.seed)).frames[0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(args.output), fps=16)
    print(args.output)


if __name__ == '__main__':
    main()
