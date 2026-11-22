"""Queue a single-view, mesh-only Pixal3D experiment on the shared ROCm GPU."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
BASE = ROOT / '.local/pixal3d-experiment'
BINARY = BASE / 'build-rocm101/trellis-cli'
MODELS = BASE / 'model-gguf'
SOURCE = ROOT / '.local/trellis-experiment/masked-views-a-pose-v1/01_front.png'
MODEL_FILES = ['dinov3.gguf', 'pixal3d_naf.gguf', 'ss_dec.gguf', 'shape_dec.gguf',
               'pixal3d_ss_flow_sv.gguf', 'pixal3d_shape_flow_512_sv.gguf', 'pixal3d_shape_flow_1024_sv.gguf']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def worker(job):
    reservation = os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation or not Path(reservation).is_file():
        raise RuntimeError('공용 GPU 예약 필요')
    expected = json.loads((job / 'request.json').read_text())
    paths = [BINARY, SOURCE] + [MODELS / x for x in MODEL_FILES]
    for path in paths:
        if not path.is_file() or sha(path) != expected['sha256'][str(path)]:
            raise ValueError(f'입력 또는 실행기 해시 불일치: {path}')
    env = dict(os.environ, LD_LIBRARY_PATH='/opt/rocm/core-10.1/lib', GGML_CUDA_DISABLE_GRAPHS='1')
    output = job / 'mesh.glb'
    args = [str(BINARY), '--sv-image', str(SOURCE), '--models', str(MODELS), '--seed', '42',
            '--res', '1024', '--require-gpu', '--no-texture', '--output', str(output)]
    result = subprocess.run(args, cwd=ROOT, env=env, check=False)
    if result.returncode:
        raise RuntimeError(f'Pixal3D 프로세스 실패: {result.returncode}')
    import numpy as np
    import trimesh
    mesh = trimesh.load(output, force='mesh', process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('유효하지 않은 출력 메시')
    if np.min(mesh.faces) < 0 or np.max(mesh.faces) >= len(mesh.vertices):
        raise ValueError('메시 면 인덱스 오류')
    report = {'input_sha256': expected['sha256'][str(SOURCE)], 'mesh_sha256': sha(output),
              'vertices': len(mesh.vertices), 'faces': len(mesh.faces), 'seed': 42,
              'resolution': 1024, 'texture': False, 'rig': False,
              'limitations': 'experimental f16 conversion; output is geometry only; not assessed for commercial use or rigging'}
    (job / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]).resolve(strict=True))
        return
    if len(sys.argv) != 1:
        raise ValueError('invalid arguments')
    from workflow.common.gpu_job_queue import launch_gpu_process
    paths = [BINARY, SOURCE] + [MODELS / x for x in MODEL_FILES]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    hashes = {str(path): sha(path) for path in paths}
    job = ROOT / '.tmp/pixal-experiment' / ('generate-' + uuid.uuid4().hex)
    job.mkdir(parents=True, exist_ok=False)
    (job / 'request.json').write_text(json.dumps({'sha256': hashes, 'seed': 42, 'resolution': 1024}, indent=2) + '\n')
    with (job / 'worker.log').open('w') as log:
        process = launch_gpu_process([sys.executable, str(Path(__file__).resolve()), '--worker', str(job)], job,
                                     'pixal-experiment', stdout=log, stderr=log, start_new_session=True)
    print(f'job={job} queue_pid={process.pid}')


if __name__ == '__main__':
    main()
