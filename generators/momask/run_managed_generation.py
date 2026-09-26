"""관리도구 요청으로 고정 MoMask 프롬프트 모션을 생성한다."""
from pathlib import Path
import argparse, json, shutil, subprocess, sys
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parents[2]
ACTIONS={'walking':('walking','걷기'),'standing':('standing','대기')}
DIRECTIONS={'down_left','down_right','up_left','up_right'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--job-dir',type=Path,required=True);p.add_argument('--action',choices=ACTIONS);p.add_argument('--directions',required=True);a=p.parse_args()
 directions=a.directions.split(',')
 if not directions or set(directions)-DIRECTIONS or len(set(directions))!=len(directions): raise ValueError('방향 선택 오류')
 config=json.loads((ROOT/'generators/momask/config/standing-loops-v1.json').read_text())
 camera_angle_values=yaml.safe_load((ROOT/'generators/momask/config/camera-angles.yaml').read_text())
 spec=config['actions'][a.action]; folder,label=ACTIONS[a.action]
 generation_root = a.job_dir / 'motion-run'
 command=[str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/generate_motion.py'),'--output-dir',str(generation_root),'--frames',str(spec['source_frames']),'--prompt',spec['prompt']]
 subprocess.run(command,check=True)
 motion=generation_root/'motion/motion.npz'
 result=a.job_dir/'result'; joints=np.load(motion)['joints']; frames=len(joints); indices=','.join(map(str,range(frames)))
 motion_quality_warnings=[]
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_openpose_frames.py'),'--motion',str(motion),'--output-dir',str(result/'openpose'),'--sample-indices',indices,'--camera-azimuth-degrees',str(camera_angle_values[a.action])],check=True)
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_anny_frames.py'),'--motion',str(motion),'--output-dir',str(result/'anny'),'--directions',','.join(directions),'--sample-indices',indices,'--camera-azimuth-degrees',str(camera_angle_values[a.action])],check=True)
 for direction in DIRECTIONS-set(directions):
  shutil.rmtree(result/'openpose'/direction)
 (a.job_dir/'result.json').write_text(json.dumps({'action':a.action,'label':label,'frames':frames,'anny_frames':frames,'fps':4,'directions':directions,'prompt':spec['prompt'],'sampling':'none','quality_warnings':motion_quality_warnings,'hand_pose':json.loads((result/'anny/result.json').read_text())['hand_pose'],'arm_retarget':json.loads((result/'anny/result.json').read_text())['arm_retarget'],'skinning':json.loads((result/'anny/result.json').read_text())['skinning'],'baseline_model':json.loads((result/'anny/result.json').read_text())['baseline_model'],'status':'completed'},ensure_ascii=False,indent=2)+'\n')
 sys.path.insert(0,str(ROOT))
 from tools.review.domains.momask.openpose_maps import generate_openpose_maps
 generate_openpose_maps(a.job_dir,json.loads((a.job_dir/'request.json').read_text()).get('face',False))
if __name__=='__main__':main()
