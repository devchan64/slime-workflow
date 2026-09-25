"""관리도구 요청으로 고정 MoMask 프롬프트 모션을 생성한다."""
from pathlib import Path
import argparse, json, shutil, subprocess, sys
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parents[2]
ACTIONS={'walking':('walking','걷기'),'standing':('standing','대기'),'deep_breath':('deep-breath','심호흡'),'stretch':('stretch','스트레칭')}
DIRECTIONS={'down_left','down_right','up_left','up_right'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--job-dir',type=Path,required=True);p.add_argument('--action',choices=ACTIONS);p.add_argument('--directions',required=True);a=p.parse_args()
 directions=a.directions.split(',')
 if not directions or set(directions)-DIRECTIONS or len(set(directions))!=len(directions): raise ValueError('방향 선택 오류')
 config=json.loads((ROOT/'generators/momask/config/standing-loops-v1.json').read_text())
 spec=config['actions'][a.action]; folder,label=ACTIONS[a.action]
 generation_root = a.job_dir / 'motion-run'
 command=[str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/generate_motion.py'),'--output-dir',str(generation_root),'--frames',str(spec['source_frames']),'--prompt',spec['prompt']]
 subprocess.run(command,check=True)
 motion=generation_root/'motion/motion.npz'
 if a.action in ('standing','deep_breath'):
  subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/normalize_standing_arms.py'),'--motion',str(motion),'--correction-config',str(ROOT/'generators/momask/config'/('standing-corrections.yaml' if a.action=='standing' else 'deep-breath-corrections.yaml'))],check=True)
 result=a.job_dir/'result'; joints=np.load(motion)['joints']; frames=len(joints); indices=','.join(map(str,range(frames)))
 motion_quality_warnings=[]
 if a.action=='stretch':
  endpoint_wrist_offsets=joints[[0,-1]][:,[20,21],1]-joints[[0,-1]][:,[16,17],1]
  if np.any(endpoint_wrist_offsets>-.15):
   motion_quality_warnings.append('스트레칭 시작·종료 시 양손을 충분히 내리지 못했습니다. 결과 자세를 검수하세요.')
   print('품질 경고: '+motion_quality_warnings[-1],flush=True)
 if a.action in ('standing','deep_breath'):
  standing_correction_values=yaml.safe_load((motion.parent/'standing-corrections.yaml').read_text())
  upper_ratios=[]
  for shoulder,elbow in ((16,18),(17,19)):
   upper=joints[:,elbow]-joints[:,shoulder];upper_ratios.extend((np.linalg.norm(upper[:,[0,2]],axis=1)/np.maximum(-upper[:,1],1e-6)).tolist())
  if max(upper_ratios)>np.tan(np.radians(standing_correction_values['upper_arm_outward_degrees']+2)): raise ValueError('대기 팔 벌림 품질 기준 초과')
  root_travel=float(np.linalg.norm(joints[:,0,[0,2]]-joints[0,0,[0,2]],axis=1).max())
  if root_travel>.025: raise ValueError('대기 수평 이동 품질 기준 초과')
  head_vertical_range=float(np.ptp(joints[:,15,1]))
  if head_vertical_range>(.015 if a.action=='standing' else .04): raise ValueError('대기 머리 상하 움직임 과다')
  standing_correction_values=yaml.safe_load((motion.parent/'standing-corrections.yaml').read_text())
  backward_rotation_limit=standing_correction_values['chest_backward_rotation_degrees']+standing_correction_values['max_torso_pitch_degrees']
  torso_direction_values=joints[:,9]-joints[:,0]
  if np.max(np.degrees(np.arctan2(torso_direction_values[:,2],torso_direction_values[:,1])))>1.01 or np.min(np.degrees(np.arctan2(torso_direction_values[:,2],torso_direction_values[:,1]))) < -backward_rotation_limit:raise ValueError('대기 상체 전방 기울기 과다')
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_openpose_frames.py'),'--motion',str(motion),'--output-dir',str(result/'openpose'),'--sample-indices',indices],check=True)
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_anny_frames.py'),'--motion',str(motion),'--output-dir',str(result/'anny'),'--directions',','.join(directions),'--sample-indices',indices]+(['--animate-hand-closure','--arm-correction-config',str(ROOT/'generators/momask/config/stretch-arm-corrections.yaml')] if a.action=='stretch' else []),check=True)
 for direction in DIRECTIONS-set(directions):
  shutil.rmtree(result/'openpose'/direction)
 (a.job_dir/'result.json').write_text(json.dumps({'action':a.action,'label':label,'frames':frames,'anny_frames':frames,'fps':4,'directions':directions,'prompt':spec['prompt'],'sampling':'none','quality_warnings':motion_quality_warnings,'hand_pose':json.loads((result/'anny/result.json').read_text())['hand_pose'],'arm_retarget':json.loads((result/'anny/result.json').read_text())['arm_retarget'],'skinning':json.loads((result/'anny/result.json').read_text())['skinning'],'baseline_model':json.loads((result/'anny/result.json').read_text())['baseline_model'],'status':'completed'},ensure_ascii=False,indent=2)+'\n')
 sys.path.insert(0,str(ROOT/'tools/review'))
 from openpose_maps import generate_openpose_maps
 generate_openpose_maps(a.job_dir)
if __name__=='__main__':main()
