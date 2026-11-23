"""고정된 Wan 2.2 I2V 및 Lightning·KungFu 파일 준비."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / '.model/wan22-i2v'
FILES = (
    ('base/high.safetensors', 'Comfy-Org/Wan-2.2', '5df3a4a3ed0628002308022198249dbbbd045d09', 'split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp16.safetensors', 28577914792, 'c21c21efa368d529a982a7d89dd11d86608b5937cae9a125d0ffe5491918a100'),
    ('base/low.safetensors', 'Comfy-Org/Wan-2.2', '5df3a4a3ed0628002308022198249dbbbd045d09', 'split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors', 28577914792, 'edb89340c8a6fbf1a70e76a839ae01eaf7d289f05ea1ebd6b1a3fc6f533826e9'),
    ('lightning/high.safetensors', 'lightx2v/Wan2.2-Lightning', '18bccf8884ec0a078eed79785eb4ef13ea16ce1e', 'Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors', 1226977424, 'd176c808d6fc461999b68e321efcb7501b20b8c3797523ed0df14f7d1deff11e'),
    ('lightning/low.safetensors', 'lightx2v/Wan2.2-Lightning', '18bccf8884ec0a078eed79785eb4ef13ea16ce1e', 'Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/low_noise_model.safetensors', 1226977424, '024f21de095bc8fad9809ded3e9e49a2e170dcf27075da8145ba7d60d8aab7f9'),
    ('kungfu/high.safetensors', 'starsfriday/Wan2.2-I2V-KungFu', 'ba38b9bc97e6b1c2dfb461b3cc95ce20ee9c0d75', 'wan2.2_wugong_i2v_high.safetensors', 306807976, '6a2eb34a83ebb9b76fb09f2ae66e1ecdeba1dd4cbb0143574bbe9ae87652b9f8'),
    ('kungfu/low.safetensors', 'starsfriday/Wan2.2-I2V-KungFu', 'ba38b9bc97e6b1c2dfb461b3cc95ce20ee9c0d75', 'wan2.2_wugong_i2v_low.safetensors', 306807976, 'a62c61cb866a85433bc07d64e4d344fe278fff1c9352829ad5e873b0c87261a8'),
)


def inspect_assets():
    for relative, _, _, _, size, digest in FILES:
        path = DIRECTORY / relative
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                return False
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    return False
        except OSError:
            return False
    return True


def prepare_assets():
    from workflow.common.model_http_download import download_verified_http
    for relative, repo, revision, remote, size, digest in FILES:
        url = f'https://huggingface.co/{repo}/resolve/{revision}/{remote}'
        download_verified_http(url, DIRECTORY / relative, digest, 'wan22-i2v-assets/' + relative, expected_total_bytes=size)
    if not inspect_assets():
        raise ValueError('I2V 모델 또는 LoRA 파일 검증 실패')
