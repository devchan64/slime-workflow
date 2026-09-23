from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,shutil,subprocess,hashlib,json,time
import numpy as np
REPORT_SOURCE_ROOT=Path(__file__).resolve().parent
WORKFLOW_SOURCE_ROOT=REPORT_SOURCE_ROOT.parents[1]
argument_parser_value=argparse.ArgumentParser(description='보관 사본에서 새 실험 경로로 재생성')
argument_parser_value.add_argument('--render',action='store_true',help='모델·뷰·GLB까지 재생성')
execution_option_values=argument_parser_value.parse_args()
execution_output_root=WORKFLOW_SOURCE_ROOT/'.tmp/anny-report-replay'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
execution_output_root.mkdir(parents=True)
shutil.copytree(REPORT_SOURCE_ROOT/'snapshot/inputs',execution_output_root/'inputs')
for current_script_path in (REPORT_SOURCE_ROOT/'snapshot').glob('*.py'):
 shutil.copy2(current_script_path,execution_output_root/current_script_path.name)
shutil.copy2(REPORT_SOURCE_ROOT/'snapshot/ANNY-LICENSE.txt',execution_output_root/'ANNY-LICENSE.txt')
def run_logged_stage(stage_label_name,stage_command_values):
 print(f'{datetime.now().isoformat()}/report-replay/start {stage_label_name} output={execution_output_root}',flush=True)
 stage_log_path=execution_output_root/(stage_label_name+'.log')
 with stage_log_path.open('w') as stage_log_file:
  stage_process_value=subprocess.Popen(stage_command_values,cwd=WORKFLOW_SOURCE_ROOT,stdout=stage_log_file,stderr=subprocess.STDOUT)
  while stage_process_value.poll() is None:
   try:stage_process_value.wait(timeout=5)
   except subprocess.TimeoutExpired:
    print(f'{datetime.now().isoformat()}/report-replay/heartbeat {stage_label_name} log_bytes={stage_log_path.stat().st_size}',flush=True)
 if stage_process_value.returncode:
  print(stage_log_path.read_text()[-12000:],flush=True)
  raise RuntimeError(f'실패: {stage_command_values}')
run_logged_stage('generation',[str(WORKFLOW_SOURCE_ROOT/'.venv/bin/python'),str(execution_output_root/'generate_attributes.py')])
original_bundle_values=np.load(REPORT_SOURCE_ROOT/'snapshot/anny-rest-rig.npz',allow_pickle=False)
replayed_bundle_values=np.load(execution_output_root/'anny-rest-rig.npz',allow_pickle=False)
if set(original_bundle_values.files)!=set(replayed_bundle_values.files):raise ValueError('NPZ 필드 불일치')
comparison_result_values={}
for current_array_name in original_bundle_values.files:
 original_array_values=original_bundle_values[current_array_name]
 replayed_array_values=replayed_bundle_values[current_array_name]
 if original_array_values.shape!=replayed_array_values.shape:raise ValueError('배열 크기 불일치')
 exact_match_value=np.array_equal(original_array_values,replayed_array_values)
 maximum_error_value=float(np.max(np.abs(original_array_values-replayed_array_values))) if np.issubdtype(original_array_values.dtype,np.number) else None
 if not exact_match_value and (maximum_error_value is None or maximum_error_value>1e-6):raise ValueError(f'재현 오차: {current_array_name}')
 comparison_result_values[current_array_name]={'exact_match':exact_match_value,'max_abs_error':maximum_error_value}
if execution_option_values.render:
 for current_stage_name,current_script_name in [('build','build_preview.py'),('roundtrip','validate_roundtrip.py')]:
  run_logged_stage(current_stage_name,[str(WORKFLOW_SOURCE_ROOT/'.local/blender-runtime/bin/python'),str(execution_output_root/'run_stage.py'),str(execution_output_root/current_script_name)])
 run_logged_stage('package',[str(WORKFLOW_SOURCE_ROOT/'.venv/bin/python'),str(execution_output_root/'package_overlay.py')])
verification_result_values={'status':'passed','output':str(execution_output_root),'arrays':comparison_result_values,'gpu_generation_rerun':True,'render_rerun':execution_option_values.render,'note':'정적 모델 재현 검증. 모션 자연스러움 검증 아님.'}
(execution_output_root/'reproduction-validation.json').write_text(json.dumps(verification_result_values,ensure_ascii=False,indent=2))
print(json.dumps(verification_result_values,ensure_ascii=False),flush=True)
