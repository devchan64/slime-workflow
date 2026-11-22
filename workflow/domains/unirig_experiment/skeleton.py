"""Queue the experimental ROCm UniRig skeleton stage with pinned input hashes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / '.local/unirig-experiment/source'
PYTHON = ROOT / '.local/unirig-experiment/venv/bin/python'
MODEL = ROOT / '.model/unirig/skeleton/articulation-xl_quantization_256/model.ckpt'
INPUT = ROOT / '.tmp/pixal-experiment/rig-check-87edd/remesh-300k/meshfix/candidate.glb'
EXTRACTED = INPUT.with_suffix('') / 'raw_data.npz'
FILES = [INPUT, EXTRACTED, MODEL, SOURCE/'run.py', SOURCE/'src/model/parse.py',
         SOURCE/'src/model/parse_encoder.py', SOURCE/'src/model/michelangelo/models/tsal/sal_perceiver.py',
         SOURCE/'configs/model/unirig_ar_350m_1024_81920_float32.yaml',
         SOURCE/'configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def worker(job):
    reservation = os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation or not Path(reservation).is_file():
        raise RuntimeError('GPU reservation required')
    request = json.loads((job/'request.json').read_text())
    for path in FILES:
        if sha(path) != request['sha256'][str(path)]:
            raise ValueError('Input or experiment configuration changed')
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='4',
               HF_HOME=str(ROOT/'.local/unirig-experiment/huggingface'),
               LD_LIBRARY_PATH=str(ROOT/'.tmp/pixal-experiment/rig-check-87edd/opengl/usr/lib/x86_64-linux-gnu'))
    args = [str(PYTHON), 'run.py', '--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml',
            '--seed=42', f'--input={INPUT}', f'--output={job / "skeleton.fbx"}', f'--npz_dir={job}']
    subprocess.run(args, cwd=SOURCE, env=env, check=True)
    result = job/'skeleton.fbx'
    if not result.is_file() or not result.stat().st_size:
        raise RuntimeError('Skeleton output was not produced')
    (job/'result.json').write_text(json.dumps({'skeleton_fbx':str(result),'sha256':sha(result),'skin':False},indent=2)+'\n')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]).resolve(strict=True))
        return
    raise RuntimeError('UniRig 실험은 폐기되어 새 리깅 작업을 접수할 수 없습니다.')


if __name__ == '__main__':
    main()
