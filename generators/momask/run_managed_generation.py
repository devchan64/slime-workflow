"""관리도구 요청으로 고정 MoMask 프롬프트 모션을 생성한다."""
from pathlib import Path
import argparse, json, shutil, subprocess, sys
import numpy as np
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
 if a.action=='standing':
  subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/normalize_standing_arms.py'),'--motion',str(motion)],check=True)
 result=a.job_dir/'result'; joints=np.load(motion)['joints']; frames=len(joints); indices=','.join(map(str,range(frames)))
 if a.action=='standing':
  upper_ratios=[]
  for shoulder,elbow in ((16,18),(17,19)):
   upper=joints[:,elbow]-joints[:,shoulder];upper_ratios.extend((np.linalg.norm(upper[:,[0,2]],axis=1)/np.maximum(-upper[:,1],1e-6)).tolist())
  if max(upper_ratios)>.05: raise ValueError('대기 팔 벌림 품질 기준 초과')
  root_travel=float(np.linalg.norm(joints[:,0,[0,2]]-joints[0,0,[0,2]],axis=1).max())
  if root_travel>.05: raise ValueError('대기 수평 이동 품질 기준 초과')
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_openpose_frames.py'),'--motion',str(motion),'--output-dir',str(result/'openpose'),'--sample-indices',indices],check=True)
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_anny_frames.py'),'--motion',str(motion),'--output-dir',str(result/'anny'),'--directions',','.join(directions),'--sample-indices',indices],check=True)
 for direction in DIRECTIONS-set(directions):
  shutil.rmtree(result/'openpose'/direction)
 (a.job_dir/'result.json').write_text(json.dumps({'action':a.action,'label':label,'frames':frames,'anny_frames':frames,'fps':4,'directions':directions,'prompt':spec['prompt'],'sampling':'none','status':'completed'},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
