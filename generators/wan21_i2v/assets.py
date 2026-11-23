"""Pinned files for Wan 2.1 I2V 480p and an experimental fight adapter."""
from pathlib import Path
from generators.wan21_video_assets import inspect_files, prepare_files

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / '.model/wan21-i2v'
FILES = (
    ('base/model.safetensors', 'Comfy-Org/Wan-2.1', '8ddd6780aaba11a2a8eeb1039d8c6d54600ef9f1', 'split_files/diffusion_models/wan2.1_i2v_480p_14B_bf16.safetensors', 32789894024, 'c058a4ac5363c35d1ab4dd3bdec788c23b267fa42a0d7c68aba599f2f74600c9'),
    ('clip_vision/clip_vision_h.safetensors', 'Comfy-Org/Wan-2.1', '55dc69dfdb9c8806600cce6c26a619e1734999e0', 'split_files/clip_vision/clip_vision_h.safetensors', 1264219396, '64a7ef761bfccbadbaa3da77366aac4185a6c58fa5de5f589b42a65bcc21f161'),
    ('acceleration/lightx2v.safetensors', 'lightx2v/Wan2.1-Distill-Loras', '95cdc36649282bd91741d2af8bb0528bb2aa9814', 'wan2.1_i2v_lora_rank64_lightx2v_4step.safetensors', 739472104, '8833bd4fd7c8eabebf0bc8ee5cfaf47f4f310ce116928a02c1adf8941dd4b0f1'),
    ('action/fight.safetensors', 'joyfox/Wan2.1-Fight-LoRA', 'd6f72527e49e967d47324716471df4dc043ebef3', 'wan2.1-fight.safetensors', 359257680, '2e30a338b898f8efb11a9b26ebe5cdf69445c11170c30311fe0b86b2cab28e37'),
)

def inspect_assets():
    return inspect_files(DIRECTORY, FILES)

def prepare_assets():
    prepare_files(DIRECTORY, FILES, 'wan21-i2v-assets')
