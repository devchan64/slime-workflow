"""Queue a TRELLIS.2 geometry-only run with official-derived GGUF weights."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
BASE = ROOT / '.local/trellis2-experiment'
BINARY = BASE / 'build-rocm101/trellis-cli'
MODELS = BASE / 'model-gguf'
IMAGE = ROOT / '.local/trellis-experiment/masked-views-a-pose-v1/01_front.png'
MODEL_FILES = ('dinov3.gguf', 'ss_dec.gguf', 'shape_dec.gguf', 'ss_flow.gguf',
               'shape_flow_512.gguf', 'shape_flow_1024.gguf')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def worker(job):
    reservation = os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation or not Path(reservation).is_file():
        raise RuntimeError('공용 GPU 예약 필요')
    request = json.loads((job / 'request.json').read_text())
    for path, expected in request['sha256'].items():
        if digest(Path(path)) != expected:
            raise ValueError('TRELLIS.2 입력 또는 가중치가 변경되었습니다')
    # Existing queued requests remain bound to the executable they recorded.
    recorded_binaries = [Path(path) for path in request['sha256'] if Path(path).name == 'trellis-cli']
    if len(recorded_binaries) != 1:
        raise ValueError('TRELLIS.2 실행기 지문이 없습니다')
    job_binary = recorded_binaries[0]
    env = dict(os.environ, LD_LIBRARY_PATH='/opt/rocm/core-10.1/lib',
               GGML_CUDA_DISABLE_GRAPHS='1', GGML_FA_DEBUG='1')
    # Avoid inherited experimental kernel overrides changing the recorded path.
    for key in ('TRELLIS_FA_FAST', 'TRELLIS_FA_NOMASK', 'TRELLIS_NOFA'):
        env.pop(key, None)
    output = job / 'mesh.glb'
    subprocess.run([str(job_binary), str(IMAGE), '--models', str(MODELS), '--seed', '42',
                    '--res', '1024', '--require-gpu', '--no-texture', '--output', str(output)],
                   cwd=ROOT, env=env, check=True)
    import numpy as np
    import trimesh
    mesh = trimesh.load(output, force='mesh', process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('TRELLIS.2 메시가 비어 있거나 비유한 좌표를 포함합니다')
    if np.min(mesh.faces) < 0 or np.max(mesh.faces) >= len(mesh.vertices):
        raise ValueError('TRELLIS.2 메시 면 인덱스 오류')
    result = {'model':'microsoft/TRELLIS.2-4B', 'input':str(IMAGE), 'views':1,
              'seed':42, 'resolution':1024, 'texture':False, 'rig':False,
              'mesh_sha256':digest(output), 'vertices':len(mesh.vertices), 'faces':len(mesh.faces),
              'limitations':'Raw geometry only; GGML port and converted weights; GPU numerical parity, commercial dependency review and rig suitability not verified.'}
    (job / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        worker(Path(sys.argv[2]).resolve(strict=True)); return
    if sys.argv[1:] not in ([], ['--foreground']):
        raise ValueError('invalid arguments')
    from workflow.common.gpu_job_queue import launch_gpu_process
    paths = [BINARY, IMAGE] + [MODELS / name for name in MODEL_FILES]
    for path in paths:
        if not path.is_file(): raise FileNotFoundError(path)
    job = ROOT / '.tmp/trellis2-experiment' / ('generate-' + uuid.uuid4().hex)
    job.mkdir(parents=True)
    request = {'model':'microsoft/TRELLIS.2-4B', 'sha256':{str(p):digest(p) for p in paths},
               'seed':42, 'resolution':1024, 'input_views':1, 'texture':False,
               'backend':'GGML HIP', 'attention':'default GGML; log selected kernel'}
    (job / 'request.json').write_text(json.dumps(request, indent=2)+'\n')
    with (job / 'worker.log').open('w') as log:
        proc = launch_gpu_process([sys.executable, str(Path(__file__).resolve()), '--worker', str(job)],
                                  job, 'trellis-experiment', stdout=log, stderr=log, start_new_session=True)
    print(f'job={job} queue_pid={proc.pid}', flush=True)
    if sys.argv[1:] == ['--foreground']:
        raise SystemExit(proc.wait())


if __name__=='__main__': main()
