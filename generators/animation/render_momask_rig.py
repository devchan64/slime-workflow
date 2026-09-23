#!/usr/bin/env python3
"""채택된 리그의 고정 렌더 코드를 새 실험 폴더에서 실행한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import shutil
import subprocess
import time
from resolve_default_rig import resolve_default_walk_rig

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
BLENDER_PYTHON_PATH = WORKFLOW_ROOT_PATH / '.local/blender-runtime/bin/python'
PACKAGE_PYTHON_PATH = WORKFLOW_ROOT_PATH / '.venv/bin/python'
REPRODUCTION_FILE_NAMES = ('mannequin.blend', 'render_asset.py', 'run_stage.py', 'package_asset.py', 'build_review.py', 'artifact.json')


def execute_baseline_rig_render():
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--output-dir', type=Path)
    parsed_argument_values = argument_parser_value.parse_args()
    source_asset_root = resolve_default_walk_rig()
    experiment_output_root = (parsed_argument_values.output_dir or WORKFLOW_ROOT_PATH / '.tmp' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')).resolve()
    if not experiment_output_root.is_relative_to(WORKFLOW_ROOT_PATH / '.tmp'):
        raise ValueError('출력은 저장소 .tmp 안에 있어야 합니다.')
    for runtime_python_path in (BLENDER_PYTHON_PATH, PACKAGE_PYTHON_PATH):
        if not runtime_python_path.is_file():
            raise FileNotFoundError(runtime_python_path)
    experiment_output_root.mkdir(parents=True, exist_ok=False)
    for current_file_name in REPRODUCTION_FILE_NAMES:
        shutil.copy2(source_asset_root / current_file_name, experiment_output_root / current_file_name)
    shutil.copytree(source_asset_root / 'inputs', experiment_output_root / 'inputs')
    render_stage_commands = [
        [str(BLENDER_PYTHON_PATH), str(experiment_output_root / 'run_stage.py'), str(experiment_output_root / 'render_asset.py')],
        [str(PACKAGE_PYTHON_PATH), str(experiment_output_root / 'package_asset.py')],
        [str(PACKAGE_PYTHON_PATH), str(experiment_output_root / 'build_review.py')],
    ]
    current_log_path = experiment_output_root / 'execution.log'
    with current_log_path.open('w') as current_log_handle:
        for current_stage_index, current_stage_command in enumerate(render_stage_commands, 1):
            current_log_handle.write(f'{datetime.now().isoformat()}/momask-render/stage {current_stage_index} {current_stage_command}\n')
            current_log_handle.flush()
            current_stage_process = subprocess.Popen(current_stage_command, stdout=current_log_handle, stderr=subprocess.STDOUT)
            while current_stage_process.poll() is None:
                print(f'{datetime.now().isoformat()}/momask-render/heartbeat stage={current_stage_index} log_bytes={current_log_path.stat().st_size}', flush=True)
                time.sleep(5)
            if current_stage_process.returncode:
                print('\n'.join(current_log_path.read_text().splitlines()[-25:]), flush=True)
                raise RuntimeError(f'실행 실패: {current_stage_command}, exit={current_stage_process.returncode}')
    print(f'{datetime.now().isoformat()}/momask-render/complete {experiment_output_root}', flush=True)


if __name__ == '__main__':
    execute_baseline_rig_render()
