#!/usr/bin/env python3
"""Experimental local Wan 2.1 14B image-to-video runner (Diffusers)."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True, help='Local Wan 2.1 I2V Diffusers model directory')
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--negative-prompt', default='')
    parser.add_argument('--lora', type=Path, help='Compatible Wan 2.1 I2V LoRA')
    parser.add_argument('--lora-strength', type=float, default=1.0)
    parser.add_argument('--width', type=int, default=832)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--frames', type=int, default=81)
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--guidance', type=float, default=5.0)
    parser.add_argument('--shift', type=float, default=5.0)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.model.is_dir(): parser.error('model must be a local Diffusers model directory')
    if not args.image.is_file(): parser.error('input image not found')
    if args.lora is not None and not args.lora.is_file(): parser.error('LoRA file not found')
    if not args.prompt.strip(): parser.error('prompt must not be empty')
    if args.width < 16 or args.height < 16 or args.width % 16 or args.height % 16: parser.error('dimensions must be positive multiples of 16')
    if args.frames < 5 or (args.frames - 1) % 4: parser.error('frames must be 4n+1 and at least 5')
    if args.steps < 1 or args.shift <= 0 or args.guidance < 0: parser.error('invalid sampling settings')
    import torch
    from diffusers import AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, WanImageToVideoPipeline
    from diffusers.utils import export_to_video, load_image
    if not torch.cuda.is_available(): raise RuntimeError('A CUDA or ROCm GPU is required')
    vae = AutoencoderKLWan.from_pretrained(args.model, subfolder='vae', torch_dtype=torch.float32, local_files_only=True)
    pipe = WanImageToVideoPipeline.from_pretrained(args.model, vae=vae, torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.scheduler = FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config, shift=args.shift)
    if args.lora:
        pipe.load_lora_weights(str(args.lora.parent), weight_name=args.lora.name, adapter_name='action', local_files_only=True)
        pipe.set_adapters(['action'], adapter_weights=[args.lora_strength])
    pipe.to('cuda')
    image = load_image(str(args.image)).convert('RGB').resize((args.width, args.height))
    frames = pipe(image=image, prompt=args.prompt, negative_prompt=args.negative_prompt, width=args.width, height=args.height, num_frames=args.frames, num_inference_steps=args.steps, guidance_scale=args.guidance, generator=torch.Generator(device='cuda').manual_seed(args.seed)).frames[0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(args.output), fps=16)
    print(args.output)


if __name__ == '__main__': main()
