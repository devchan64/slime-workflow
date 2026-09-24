"""관리도구 요청으로 고정 MoMask 프롬프트 모션을 생성한다."""
from pathlib import Path
import argparse, json, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
ACTIONS={'standing':('standing','대기',4),'deep_breath':('deep-breath','심호흡',8),'stretch':('stretch','스트레칭',20)}
DIRECTIONS={'down_left','down_right','up_left','up_right'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--job-dir',type=Path,required=True);p.add_argument('--action',choices=ACTIONS);p.add_argument('--directions',required=True);a=p.parse_args()
 directions=a.directions.split(',')
 if not directions or set(directions)-DIRECTIONS or len(set(directions))!=len(directions): raise ValueError('방향 선택 오류')
 config=json.loads((ROOT/'generators/momask/config/standing-loops-v1.json').read_text())
 spec=config['actions'][a.action]; folder,label,frames=ACTIONS[a.action]
 command=[str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/generate_motion.py'),'--output-dir',str(a.job_dir),'--frames',str(spec['source_frames']),'--prompt',spec['prompt']]
 subprocess.run(command,check=True)
 motion=a.job_dir/'motion/motion.npz'; result=a.job_dir/'result'; indices=','.join(map(str,spec['sample_indices']))
 subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/render_openpose_frames.py'),'--motion',str(motion),'--output-dir',str(result),'--sample-indices',indices],check=True)
 for direction in DIRECTIONS-set(directions): shutil.rmtree(result/direction)
 (a.job_dir/'result.json').write_text(json.dumps({'action':a.action,'label':label,'frames':frames,'fps':4,'directions':directions,'prompt':spec['prompt'],'status':'completed'},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
