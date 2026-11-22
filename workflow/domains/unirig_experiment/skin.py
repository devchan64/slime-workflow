"""Queue an experimental UniRig skin stage for the generated skeleton."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
SOURCE = ROOT/'.local/unirig-experiment/source'
PYTHON = ROOT/'.local/unirig-experiment/venv/bin/python'
MODEL = ROOT/'.local/unirig-experiment/skin-weights-only.ckpt'
ORIGINAL_MODEL = ROOT/'.model/unirig/skin/articulation-xl/model.ckpt'
INPUT = ROOT/'.tmp/unirig-experiment/generate-be0cf22c994d4108be2bcce433d4ae4f/skeleton.fbx'
EXTRACTED = INPUT.with_suffix('')/'raw_data.npz'
FILES = [INPUT,EXTRACTED,MODEL,ORIGINAL_MODEL,SOURCE/'run.py',SOURCE/'src/model/parse.py',SOURCE/'src/model/parse_encoder.py',
         SOURCE/'src/model/michelangelo/models/tsal/sal_perceiver.py',SOURCE/'configs/model/unirig_skin.yaml',
         SOURCE/'configs/task/quick_inference_unirig_skin.yaml',ROOT/'workflow/domains/unirig_experiment/rocm_skin_shims.py',
         ROOT/'workflow/domains/unirig_experiment/skin_entry.py']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def worker(job):
    reservation=os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation or not Path(reservation).is_file():
        raise RuntimeError('GPU reservation required')
    request=json.loads((job/'request.json').read_text())
    for path in FILES:
        if sha(path)!=request['sha256'][str(path)]:
            raise ValueError('Input or experiment configuration changed')
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='4',PYOPENGL_PLATFORM='egl',
             HF_HOME=str(ROOT/'.local/unirig-experiment/huggingface'),
             LD_LIBRARY_PATH=str(ROOT/'.tmp/pixal-experiment/rig-check-87edd/opengl/usr/lib/x86_64-linux-gnu'))
    args=[str(PYTHON),str(ROOT/'workflow/domains/unirig_experiment/skin_entry.py'),
          '--task=configs/task/quick_inference_unirig_skin.yaml','--seed=42',f'--input={INPUT}',
          f'--output={job / "skinned.fbx"}',f'--npz_dir={job}','--data_name=raw_data.npz']
    subprocess.run(args,cwd=SOURCE,env=env,check=True)
    target=job/'skinned.fbx'
    if not target.is_file() or not target.stat().st_size:
        raise RuntimeError('Skinned output was not produced')
    (job/'result.json').write_text(json.dumps({'skinned_fbx':str(target),'sha256':sha(target)},indent=2)+'\n')


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        worker(Path(sys.argv[2]).resolve(strict=True)); return
    raise RuntimeError('폐기된 Pixal3D 리그를 입력으로 사용하는 실험입니다. 새 TRELLIS.2 모델용 리깅 입력을 먼저 준비하세요.')


if __name__ == '__main__':
    main()
