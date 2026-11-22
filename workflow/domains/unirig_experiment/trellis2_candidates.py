"""Queue UniRig skeleton and skin trials on three repaired TRELLIS.2 candidates."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
SOURCE=ROOT/'.local/unirig-experiment/source'
PYTHON=ROOT/'.local/unirig-experiment/venv/bin/python'
INPUTS={n:ROOT/f'.tmp/trellis2-experiment/rig-candidates-v3/repair-{n}/candidate.glb' for n in (20000,50000,100000)}
INPUTS[3000]=ROOT/'.tmp/trellis2-experiment/rig-candidate-3000/candidate.glb'
MODEL=ROOT/'.model/unirig/skeleton/articulation-xl_quantization_256/model.ckpt'
SKIN=ROOT/'.local/unirig-experiment/skin-weights-only.ckpt'


def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def worker(job):
    reservation=os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation or not Path(reservation).is_file(): raise RuntimeError('GPU reservation required')
    request=json.loads((job/'request.json').read_text())
    for p,expected in request['sha256'].items():
        if sha(Path(p))!=expected: raise ValueError('input or model changed')
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='4',PYOPENGL_PLATFORM='egl',
             HF_HOME=str(ROOT/'.local/unirig-experiment/huggingface'),
             LD_LIBRARY_PATH=str(ROOT/'.tmp/pixal-experiment/rig-check-87edd/opengl/usr/lib/x86_64-linux-gnu'))
    results=[]
    for n in request.get('targets',[20000,50000,100000]):
        source=INPUTS[n]
        out=job/str(n);out.mkdir()
        skeleton=out/'skeleton.fbx'; skinned=out/'skinned.fbx'
        print(f'candidate {n}: skeleton',flush=True)
        subprocess.run([str(PYTHON),str(ROOT/'workflow/domains/unirig_experiment/skin_entry.py'),
                        '--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml',
                        '--seed=42',f'--input={source}',f'--output={skeleton}',f'--npz_dir={out}'],cwd=SOURCE,env=env,check=True)
        if not skeleton.is_file() or not skeleton.stat().st_size: raise RuntimeError('skeleton missing')
        print(f'candidate {n}: extract skeleton',flush=True)
        subprocess.run([str(PYTHON),'-m','src.data.extract','--config=configs/data/quick_inference.yaml',
                        '--require_suffix=fbx','--force_override=false','--num_runs=1','--id=0',f'--time=trellis2_skin_{n}',
                        f'--faces_target_count={n}',f'--input={skeleton}',f'--output_dir={out}'],cwd=SOURCE,env=env,check=True)
        if not (skeleton.with_suffix('')/'raw_data.npz').is_file(): raise RuntimeError('skeleton extraction missing')
        print(f'candidate {n}: skin',flush=True)
        subprocess.run([str(PYTHON),str(ROOT/'workflow/domains/unirig_experiment/skin_entry.py'),
                        '--task=configs/task/quick_inference_unirig_skin.yaml','--seed=42',f'--input={skeleton}',
                        f'--output={skinned}',f'--npz_dir={out}','--data_name=raw_data.npz'],cwd=SOURCE,env=env,check=True)
        if not skinned.is_file() or not skinned.stat().st_size: raise RuntimeError('skinned model missing')
        results.append({'target_triangles':n,'skeleton':str(skeleton),'skinned':str(skinned),'skinned_sha256':sha(skinned)})
    (job/'result.json').write_text(json.dumps({'candidates':results,'limitations':'Experimental ROCm fallbacks; no deform validation until independently checked.'},indent=2)+'\n')


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker': worker(Path(sys.argv[2]).resolve(strict=True));return
    args=sys.argv[1:]
    if any(arg not in ('--foreground','--target=3000') for arg in args) or len(args)!=len(set(args)):
        raise ValueError('invalid arguments')
    targets=[3000] if '--target=3000' in args else [20000,50000,100000]
    from workflow.common.gpu_job_queue import launch_gpu_process
    paths=[MODEL,SKIN,Path(__file__).resolve(),ROOT/'workflow/domains/unirig_experiment/skin_entry.py',
           ROOT/'workflow/domains/unirig_experiment/rocm_skin_shims.py']
    for n in targets:
        source=INPUTS[n];paths += [source,source.with_suffix('')/'raw_data.npz']
    for path in paths:
        if not path.is_file(): raise FileNotFoundError(path)
    job=ROOT/'.tmp/unirig-experiment'/('generate-'+uuid.uuid4().hex);job.mkdir(parents=True)
    (job/'request.json').write_text(json.dumps({'purpose':'TRELLIS.2 candidate rigging validation',
        'sha256':{str(p):sha(p) for p in paths},'seed':42,'targets':targets},indent=2)+'\n')
    with (job/'worker.log').open('w') as log:
        proc=launch_gpu_process([str(PYTHON),str(Path(__file__).resolve()),'--worker',str(job)],job,
                                'unirig-experiment',stdout=log,stderr=log,start_new_session=True)
    print(f'job={job} queue_pid={proc.pid}',flush=True)
    if '--foreground' in args: raise SystemExit(proc.wait())


if __name__=='__main__': main()
