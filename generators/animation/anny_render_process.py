"""ANNY의 외부 렌더 실행을 제한 시간 안에 종료한다."""
import subprocess

BLENDER_RENDER_TIMEOUT_SECONDS = 600


def run_blender_render(command_arguments, output_directory, timeout_seconds=BLENDER_RENDER_TIMEOUT_SECONDS):
    try:
        # subprocess.run은 제한 시간 초과 시 자식 프로세스를 kill하고 wait까지 수행한다.
        return subprocess.run(command_arguments, cwd=output_directory, check=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as timeout_error:
        raise RuntimeError(f'Blender 렌더 제한 시간 {timeout_seconds}초 초과: 렌더 프로세스를 종료했습니다. 산출물은 검수용으로 보존합니다.') from timeout_error
