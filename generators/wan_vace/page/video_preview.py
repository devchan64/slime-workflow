"""브라우저에서 재생할 수 있는 입력 영상 사본을 준비한다."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT


def prepare_vace_browser_video(current_video_path):
    if not current_video_path:
        return None
    import imageio_ffmpeg
    current_source_path = Path(current_video_path)
    if not current_source_path.is_file() or current_source_path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('영상 파일을 확인하세요. MP4는 32MiB 이하여야 합니다.')
    current_source_digest = hashlib.sha256(current_source_path.read_bytes()).hexdigest()
    current_cache_root = VACE_WORKSPACE_ROOT / '.tmp' / 'wan-vace-browser-video'
    current_cache_root.mkdir(parents=True, exist_ok=True)
    current_output_path = current_cache_root / (current_source_digest + '.mp4')
    if current_output_path.is_file():
        return str(current_output_path)
    current_file_descriptor, current_temp_name = tempfile.mkstemp(suffix='.mp4', dir=current_cache_root)
    os.close(current_file_descriptor)
    current_temp_path = Path(current_temp_name)
    try:
        current_command_args = [imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-y', '-i', str(current_source_path),
                                '-map', '0:v:0', '-an', '-c:v', 'libx264', '-crf', '0', '-pix_fmt', 'yuv420p',
                                '-fps_mode', 'passthrough', '-movflags', '+faststart', str(current_temp_path)]
        subprocess.run(current_command_args, check=True, capture_output=True, timeout=180)
        if current_temp_path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('재생용 변환 결과가 32MiB를 초과합니다. 더 작은 MP4를 사용하세요.')
        os.replace(current_temp_path, current_output_path)
    except (OSError, subprocess.SubprocessError) as current_video_error:
        raise ValueError('영상 변환에 실패했습니다. H.264 MP4를 다시 첨부하세요.') from current_video_error
    finally:
        current_temp_path.unlink(missing_ok=True)
    return str(current_output_path)
