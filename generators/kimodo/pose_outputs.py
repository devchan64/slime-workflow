"""직접 포즈는 필수로 생성하고 DWPose 실패는 별도 경고로 보존한다."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON


def export_kimodo_pose_outputs(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    current_metrics_recorder.update_generation_stage('direct-pose-export')
    current_workspace_root = Path(__file__).resolve().parents[2]
    current_direct_command=[str(KIMODO_ENVIRONMENT_PYTHON),'-m','generators.kimodo.direct_pose_export',str(current_attempt_root),str(current_attempt_root),*current_request_record.get('directions',['front_left'])]
    current_direct_command.extend(['--scale-percent',str(current_request_record.get('openpose_scale_percent',80.0))])
    if 'proportion_face_anchor_calibration' in current_request_record:
        current_direct_command.extend(['--request-json',str(current_job_root/'request.json')])
    subprocess.run(current_direct_command,cwd=current_workspace_root,check=True)
    current_direct_record = json.loads((current_attempt_root/'soma-direct-pose.json').read_text())
    current_metrics_recorder.update_generation_stage('dwpose-export')
    current_workspace_root = Path(__file__).resolve().parents[2]
    current_quality_warnings = []
    try:
        current_process_environment = os.environ.copy()
        current_library_paths = []
        for current_module_name, current_library_directory in (('onnxruntime', 'capi'), ('migraphx_libs', '')):
            current_module_spec = importlib.util.find_spec(current_module_name)
            if current_module_spec and current_module_spec.submodule_search_locations:
                current_module_root = Path(next(iter(current_module_spec.submodule_search_locations)))
                current_library_paths.append(str(current_module_root/current_library_directory))
        if current_process_environment.get('LD_LIBRARY_PATH'):
            current_library_paths.append(current_process_environment['LD_LIBRARY_PATH'])
        current_process_environment['LD_LIBRARY_PATH'] = os.pathsep.join(current_library_paths)
        subprocess.run([str(KIMODO_ENVIRONMENT_PYTHON),str(Path(__file__).with_name('dwpose_export.py')),str(current_job_root),str(current_attempt_root)],cwd=current_workspace_root,env=current_process_environment,check=True)
        current_dwpose_record = json.loads((current_attempt_root/'dwpose-export.json').read_text())
        for current_direction_name, current_axis_record in current_dwpose_record.get('body_axis', {}).items():
            current_completed_count = len(current_axis_record.get('joint_completion', {}).get('frames', []))
            current_remaining_count = len(current_axis_record.get('remaining_partial_joint_frames', current_axis_record.get('partial_joint_frames', [])))
            if current_completed_count:
                current_quality_warnings.append(f'DWPose {current_direction_name}: {current_completed_count}프레임의 미검출 관절은 같은 프레임 SOMA 투영으로 추정했습니다. DWPose 검출값이 아니며 상세 프레임은 dwpose-export.json을 확인하세요.')
            if current_remaining_count:
                current_quality_warnings.append(f'DWPose {current_direction_name}: {current_remaining_count}프레임에 검출·보완되지 않은 관절이 남아 있습니다. 상세 프레임은 dwpose-export.json을 확인하세요.')
    except (subprocess.CalledProcessError,OSError,ValueError) as current_export_error:
        current_warning_text = f'DWPose 생성 오류: {current_export_error}. 직접 포즈 결과는 유지합니다. 상세 원인은 실행 로그를 확인하세요.'
        current_quality_warnings.append(current_warning_text)
        current_dwpose_record = {'status':'warning','videos':{},'quality_warnings':current_quality_warnings}
        (current_attempt_root/'dwpose-export.json').write_text(json.dumps(current_dwpose_record,ensure_ascii=False))
        print(f'{datetime.now().astimezone().isoformat()}/kimodo/dwpose-export WARN {current_warning_text}',flush=True)
    return current_direct_record,current_dwpose_record,current_quality_warnings
