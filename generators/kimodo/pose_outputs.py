"""직접 포즈는 필수로 생성하고 DWPose 실패는 별도 경고로 보존한다."""
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime


def export_kimodo_pose_outputs(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    current_metrics_recorder.update_generation_stage('direct-pose-export')
    current_workspace_root = Path(__file__).resolve().parents[2]
    current_direct_command=[str(current_workspace_root/'.venv/bin/python'),'-m','generators.kimodo.direct_pose_export',str(current_attempt_root),str(current_attempt_root),*current_request_record.get('directions',['front_left'])]
    current_direct_command.extend(['--scale-percent',str(current_request_record.get('openpose_scale_percent',85.0))])
    if 'proportion_face_anchor_calibration' in current_request_record:
        current_direct_command.extend(['--request-json',str(current_job_root/'request.json')])
    subprocess.run(current_direct_command,cwd=current_workspace_root,check=True)
    current_direct_record = json.loads((current_attempt_root/'soma-direct-pose.json').read_text())
    current_metrics_recorder.update_generation_stage('dwpose-export')
    current_workspace_root = Path(__file__).resolve().parents[2]
    current_quality_warnings = []
    try:
        subprocess.run([str(current_workspace_root/'.venv/bin/python'),str(Path(__file__).with_name('dwpose_export.py')),str(current_job_root),str(current_attempt_root)],env={**os.environ,'PYTHONPATH':str(current_workspace_root/'.local/wan22-animate/preprocess-deps')},check=True)
        current_dwpose_record = json.loads((current_attempt_root/'dwpose-export.json').read_text())
    except (subprocess.CalledProcessError,OSError,ValueError) as current_export_error:
        current_warning_text = f'DWPose 생성 오류: {current_export_error}. 직접 포즈 결과는 유지합니다. 상세 원인은 실행 로그를 확인하세요.'
        current_quality_warnings.append(current_warning_text)
        current_dwpose_record = {'status':'warning','videos':{},'quality_warnings':current_quality_warnings}
        (current_attempt_root/'dwpose-export.json').write_text(json.dumps(current_dwpose_record,ensure_ascii=False))
        print(f'{datetime.now().astimezone().isoformat()}/kimodo/dwpose-export WARN {current_warning_text}',flush=True)
    return current_direct_record,current_dwpose_record,current_quality_warnings
