"""고정 Qwen 2511 4스텝 Lightning / 30스텝 표준 3참조 작업자."""
from pathlib import Path
import argparse
from worker_lock import acquire_worker_lock
import json
import sys
import traceback

WORKFLOW_ROOT_PATH=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKFLOW_ROOT_PATH/'generators/animation'))
from qwen_pose import execute_pose_generation
sys.path.insert(0,str(WORKFLOW_ROOT_PATH))
from tools.review.domains.image.three_reference_generation import resolve_reference_settings, validate_three_reference_job_path, verify_reference_snapshots


def execute_three_reference_worker():
    argument_parser_value=argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--job-dir',type=Path,required=True)
    parsed_argument_values=argument_parser_value.parse_args()
    current_job_root=validate_three_reference_job_path(parsed_argument_values.job_dir)
    current_lock_path=WORKFLOW_ROOT_PATH/'.local/image-generation-gpu.lock'
    current_lock_path.parent.mkdir(parents=True,exist_ok=True)
    with current_lock_path.open('a') as current_lock_handle:
        try:
            acquire_worker_lock(current_lock_handle,'waiting-gpu')
            current_request_record=json.loads((current_job_root/'request.json').read_text())
            verify_reference_snapshots(current_job_root,current_request_record)
            execute_pose_generation(selected_generator_seed=current_request_record.get('seed',10107),enable_text_only_generation=not current_request_record['references'],trial_output_root=current_job_root,prompt_text_value=current_request_record['prompt'],character_image_path=current_job_root/'reference-1.png',pose_reference_path=current_job_root/'reference-2.png' if (current_job_root/'reference-2.png').exists() else None,additional_reference_paths=tuple(current_job_root/f'reference-{current_reference_index}.png' for current_reference_index in range(3,4) if (current_job_root/f'reference-{current_reference_index}.png').exists()),pose_reference_kind='rig',selected_reference_order='standing-first',selected_output_width=current_request_record['width'],selected_output_height=current_request_record['height'],**resolve_reference_settings(current_request_record['steps']),prompt_source_record={'kind':'management-three-reference','reference_order':list(range(1, len(current_request_record['references']) + 1))})
            (current_job_root/'status.json').write_text('{"status":"completed"}')
        except Exception as current_error_value:
            traceback.print_exc()
            (current_job_root/'status.json').write_text(json.dumps({'status':'failed','error':str(current_error_value)},ensure_ascii=False))
            raise


if __name__=='__main__':
    execute_three_reference_worker()
