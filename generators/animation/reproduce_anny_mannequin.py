"""등록된 ANNY v3/v4 입력과 코드로 새 실행 경로에서 전체 제작 과정을 재현한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import shutil
import subprocess
import numpy as np

WORKFLOW_SOURCE_ROOT = Path(__file__).resolve().parents[2]
argument_parser_value = argparse.ArgumentParser(description='ANNY 등록 버전 전체 재현')
argument_parser_value.add_argument('--asset-version', type=int, choices=[3, 4], default=4)
execution_option_values = argument_parser_value.parse_args()
REGISTERED_ASSET_ROOT = WORKFLOW_SOURCE_ROOT / f'assets/motion-sheet/mannequin-walk-v{execution_option_values.asset_version}'
EXECUTION_OUTPUT_ROOT = WORKFLOW_SOURCE_ROOT / '.tmp/anny-mannequin-replay' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
PYTHON_RUNTIME_PATH = WORKFLOW_SOURCE_ROOT / '.venv/bin/python'
BLENDER_RUNTIME_PATH = WORKFLOW_SOURCE_ROOT / '.local/blender-runtime/bin/python'


def run_logged_stage(stage_label_name, stage_command_values):
    stage_log_path = EXECUTION_OUTPUT_ROOT / f'{stage_label_name}.log'
    print(f'{datetime.now().isoformat()}/anny-replay/start {stage_label_name} command={stage_command_values}', flush=True)
    with stage_log_path.open('w') as stage_log_file:
        stage_process_value = subprocess.Popen(stage_command_values, cwd=WORKFLOW_SOURCE_ROOT, stdout=stage_log_file, stderr=subprocess.STDOUT)
        while stage_process_value.poll() is None:
            try:
                stage_process_value.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f'{datetime.now().isoformat()}/anny-replay/heartbeat {stage_label_name} log_bytes={stage_log_path.stat().st_size} tail={stage_log_path.read_text()[-300:]}', flush=True)
    if stage_process_value.returncode:
        print(stage_log_path.read_text()[-10000:], flush=True)
        raise RuntimeError(f'단계 실패: {stage_command_values}')


def reproduce_registered_model():
    asset_manifest_record = json.loads((REGISTERED_ASSET_ROOT / 'artifact.json').read_text())
    for relative_file_name, expected_digest_value in asset_manifest_record['files'].items():
        if hashlib.sha256((REGISTERED_ASSET_ROOT / relative_file_name).read_bytes()).hexdigest() != expected_digest_value:
            raise ValueError(f'등록 파일 해시 불일치: {relative_file_name}')
    EXECUTION_OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    print(f'{datetime.now().isoformat()}/anny-replay/inputs source={REGISTERED_ASSET_ROOT} output={EXECUTION_OUTPUT_ROOT}', flush=True)
    shutil.copytree(REGISTERED_ASSET_ROOT / 'inputs', EXECUTION_OUTPUT_ROOT / 'inputs')
    for source_script_path in REGISTERED_ASSET_ROOT.glob('*.py'):
        shutil.copy2(source_script_path, EXECUTION_OUTPUT_ROOT / source_script_path.name)
    try:
        run_logged_stage('generation', [str(PYTHON_RUNTIME_PATH), str(EXECUTION_OUTPUT_ROOT / 'generate_attributes.py')])
        original_model_data = np.load(REGISTERED_ASSET_ROOT / 'inputs/anny-rest-rig.npz', allow_pickle=False)
        replayed_model_data = np.load(EXECUTION_OUTPUT_ROOT / 'anny-rest-rig.npz', allow_pickle=False)
        if set(original_model_data.files) != set(replayed_model_data.files):
            raise ValueError('재현 모델 NPZ 필드 불일치')
        comparison_result_values = {}
        for current_array_name in original_model_data.files:
            original_array_values = original_model_data[current_array_name]
            replayed_array_values = replayed_model_data[current_array_name]
            if not np.array_equal(original_array_values, replayed_array_values):
                raise ValueError(f'재현 모델 배열 불일치: {current_array_name}')
            comparison_result_values[current_array_name] = 'exact_match'
        run_logged_stage('build', [str(BLENDER_RUNTIME_PATH), str(EXECUTION_OUTPUT_ROOT / 'run_stage.py'), str(EXECUTION_OUTPUT_ROOT / 'build_preview.py')])
        shutil.copy2(EXECUTION_OUTPUT_ROOT / 'anny-raw-rig.blend', EXECUTION_OUTPUT_ROOT / 'inputs/anny-reference-fit-rig.blend')
        for current_stage_name in ['retarget_loop', 'render_asset', 'validate_roundtrip']:
            run_logged_stage(current_stage_name, [str(BLENDER_RUNTIME_PATH), str(EXECUTION_OUTPUT_ROOT / 'run_stage.py'), str(EXECUTION_OUTPUT_ROOT / f'{current_stage_name}.py')])
        run_logged_stage('package', [str(PYTHON_RUNTIME_PATH), str(EXECUTION_OUTPUT_ROOT / 'package_asset.py')])
        replayed_motion_data = np.load(EXECUTION_OUTPUT_ROOT / 'mannequin-motion.npz', allow_pickle=False)
        original_motion_data = np.load(REGISTERED_ASSET_ROOT / 'mannequin-motion.npz', allow_pickle=False)
        if set(replayed_motion_data.files) != set(original_motion_data.files):
            raise ValueError('모션 NPZ 필드 불일치')
        for current_array_name in original_motion_data.files:
            if not np.allclose(original_motion_data[current_array_name], replayed_motion_data[current_array_name], atol=1e-6, rtol=0):
                raise ValueError(f'재현 모션 오차: {current_array_name}')
        if not np.allclose(replayed_motion_data['joints'][0], replayed_motion_data['joints'][-1], atol=1e-6, rtol=0):
            raise ValueError('루프 끝점 불일치')
        if len(list(EXECUTION_OUTPUT_ROOT.glob('*/preview-*.png'))) != 32:
            raise ValueError('리그 프레임 수 불일치')
        execution_result_record = {'status': 'passed', 'asset': f'mannequin-walk/v{execution_option_values.asset_version}', 'model_arrays': comparison_result_values, 'motion_tolerance': 1e-6, 'rendered_frames': 32, 'output': str(EXECUTION_OUTPUT_ROOT)}
    except Exception as execution_error_value:
        (EXECUTION_OUTPUT_ROOT / 'reproduction-validation.json').write_text(json.dumps({'status': 'failed', 'error': str(execution_error_value)}, ensure_ascii=False, indent=2))
        raise
    (EXECUTION_OUTPUT_ROOT / 'reproduction-validation.json').write_text(json.dumps(execution_result_record, ensure_ascii=False, indent=2))
    print(f'{datetime.now().isoformat()}/anny-replay/complete {execution_result_record}', flush=True)


if __name__ == '__main__':
    reproduce_registered_model()
