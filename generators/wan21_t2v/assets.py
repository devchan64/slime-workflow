"""Pinned files for Wan 2.1 T2V 1.3B and its 4-step adapter."""
import hashlib
from pathlib import Path
from generators.wan21_video_assets import inspect_files, prepare_files

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / '.model/wan21-t2v'
BOSS_LORA = DIRECTORY / 'action/kxsr.safetensors'
BOSS_SHA256 = 'be4273230a772e8132cb2b24258fc6f06ab59361e405a7e694e3b4a2299846c4'
FILES = (
    ('base/model.safetensors', 'Comfy-Org/Wan-2.1', 'dfcea77bcf258496e20c69cd84e8e8e41909bb3b', 'split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors', 2838104528, '6f999b0d6cb9a72b3d98ac386ed96f57f8cecae13994a69232514ea4974ad5fd'),
    ('acceleration/self-forcing.safetensors', 'Kijai/WanVideo_comfy', 'b04f12a71005567610c4565c3ac5e5ee93824eef', 'LoRAs/Wan2_1_self_forcing_1_3B/Wan2_1_self_forcing_dmd_1_3B_lora_rank_32_fp16.safetensors', 91233416, 'c873cfe2f60d77d6e7fb787ce3ba728e19fbb958f21bf5d5da0ddfe7c37649db'),
)

def inspect_assets():
    return inspect_files(DIRECTORY, FILES)

def inspect_boss_lora(path=None):
    path = BOSS_LORA if path is None else path
    try:
        if path.is_symlink() or not path.is_file(): return False
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest() == BOSS_SHA256
    except OSError:
        return False

def prepare_assets():
    raise ValueError('Wan 2.1 T2V 모델 준비 기능은 폐기되었습니다.')
