"""보관된 입력·런타임과 별도 승인 프롬프트로 재현한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import importlib.util
import json
import sys

REPORT_ROOT_PATH = Path(__file__).resolve().parent
DIRECTION_NAME_VALUES = ('down_left', 'down_right', 'up_left', 'up_right')


def execute_report_reproduction():
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--workflow-root', type=Path, required=True)
    argument_parser_value.add_argument('--base-prompt', type=Path, required=True)
    argument_parser_value.add_argument('--rear-prompt', type=Path, required=True)
    argument_parser_value.add_argument('--verify-only', action='store_true')
    parsed_argument_values = argument_parser_value.parse_args()
    workflow_root_path = parsed_argument_values.workflow_root.resolve()
    base_prompt_text = parsed_argument_values.base_prompt.read_text().strip()
    rear_prompt_text = parsed_argument_values.rear_prompt.read_text().strip()
    selected_frame_records = []
    for current_direction_name in DIRECTION_NAME_VALUES:
        current_prompt_text = base_prompt_text + ('\n\n' + rear_prompt_text if current_direction_name in ('up_left', 'up_right') else '')
        for current_frame_number in range(1, 9):
            source_frame_root = REPORT_ROOT_PATH / 'snapshot' / current_direction_name / f'frame-{current_frame_number:02d}'
            source_result_record = json.loads((source_frame_root / 'result.json').read_text())
            if hashlib.sha256(current_prompt_text.encode()).hexdigest() != source_result_record['prompt_sha256']:
                raise ValueError(f'승인 프롬프트 해시 불일치: {current_direction_name}')
            selected_frame_records.append((current_direction_name, current_frame_number, source_frame_root, current_prompt_text))
    if parsed_argument_values.verify_only:
        print('32프레임 프롬프트 해시 검증 통과. GPU 추론 미실행.')
        return
    package_source_root = REPORT_ROOT_PATH / 'snapshot/runtime-source'
    package_module_spec = importlib.util.spec_from_file_location('report_qwen_pose', package_source_root / '__init__.py', submodule_search_locations=[str(package_source_root)])
    package_module_value = importlib.util.module_from_spec(package_module_spec)
    sys.modules['report_qwen_pose'] = package_module_value
    package_module_spec.loader.exec_module(package_module_value)
    import report_qwen_pose.runtime as runtime_module_value
    import report_qwen_pose.anypose as adapter_module_value
    runtime_module_value.WORKFLOW_REPO_ROOT = workflow_root_path
    runtime_module_value.FIXED_MODEL_DIRECTORY = workflow_root_path / '.model/qwen-image-edit-2511' / runtime_module_value.FIXED_MODEL_REVISION
    adapter_module_value.WORKFLOW_REPO_ROOT = workflow_root_path
    experiment_output_root = workflow_root_path / '.tmp/test/anypose-report-replay' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    experiment_output_root.mkdir(parents=True, exist_ok=False)
    for current_direction_name, current_frame_number, source_frame_root, current_prompt_text in selected_frame_records:
        runtime_module_value.execute_pose_generation(
            trial_output_root=experiment_output_root / current_direction_name / f'frame-{current_frame_number:02d}',
            prompt_text_value=current_prompt_text,
            character_image_path=REPORT_ROOT_PATH / 'inputs/character-baseline-v2' / f'{current_direction_name}.png',
            pose_reference_path=source_frame_root / 'rig-reference.png',
            pose_reference_kind='rig', selected_reference_order='standing-first',
            selected_inference_steps=4, enable_anypose_adapter=True, enable_lightning_adapter=True)
    print(f'재현 완료: {experiment_output_root}')


if __name__ == '__main__':
    execute_report_reproduction()
