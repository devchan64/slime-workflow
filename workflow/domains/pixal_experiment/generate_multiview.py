"""Experimental four-view Pixal3D with upstream alpha preprocessing."""
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
SOURCE = ROOT / '.local/trellis-experiment/masked-views-a-pose-v1'
# The canonical +X camera sees the front (-Y) pointing left in the image.
# Reference filenames describe image-facing direction, not the camera position.
NAMES = ['01_front.png', '07_left.png', '05_back.png', '03_right.png']
MODEL_NAMES = ['dinov3.gguf', 'pixal3d_naf.gguf', 'ss_dec.gguf', 'shape_dec.gguf',
               'pixal3d_ss_flow_mv.gguf', 'pixal3d_shape_flow_512_mv.gguf', 'pixal3d_shape_flow_1024_mv.gguf']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(8 * 1024 * 1024):
            h.update(data)
    return h.hexdigest()


def stage_views(job):
    from PIL import Image
    images = [Image.open(SOURCE / name).convert('RGBA') for name in NAMES]
    boxes = [image.getchannel('A').getbbox() for image in images]
    if any(box is None for box in boxes):
        raise ValueError('빈 전경 마스크')
    # A common scale keeps relative height; centre each subject on the canonical rig.
    scale = 870 / max(max(box[2]-box[0], box[3]-box[1]) for box in boxes)
    views = job / 'views'
    views.mkdir()
    for index, (image, box) in enumerate(zip(images, boxes)):
        size = tuple(round(v * scale) for v in image.size)
        image = image.resize(size, Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (1024, 1024), (255, 255, 255, 0))
        x = round(512 - (box[0] + box[2]) * scale / 2)
        y = round(512 - (box[1] + box[3]) * scale / 2)
        canvas.paste(image, (x, y))
        canvas.save(views / f'{index+1:02}.png')
    return views


def worker(job):
    reservation = os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation or not Path(reservation).is_file():
        raise RuntimeError('공용 GPU 예약 필요')
    request = json.loads((job / 'request.json').read_text())
    for path, expected in request['sha256'].items():
        if digest(Path(path)) != expected:
            raise ValueError('입력 또는 실행기 해시 불일치')
    env = dict(os.environ, LD_LIBRARY_PATH='/opt/rocm/core-10.1/lib', GGML_CUDA_DISABLE_GRAPHS='1')
    output = job / 'mesh.glb'
    subprocess.run([str(BINARY), '--views', str(job / 'views'), '--mesh-scale', '1.0',
                    '--models', str(MODELS), '--seed', '42', '--res', '1024',
                    '--require-gpu', '--no-texture', '--output', str(output)], cwd=ROOT, env=env, check=True)
    import numpy as np
    import trimesh
    mesh = trimesh.load(output, force='mesh', process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all() or np.min(mesh.faces) < 0 or np.max(mesh.faces) >= len(mesh.vertices):
        raise ValueError('유효하지 않은 메시')
    report = {'mesh_sha256':digest(output), 'vertices':len(mesh.vertices), 'faces':len(mesh.faces),
              'background':'upstream alpha-premultiplied black', 'views':NAMES, 'camera':'assumed canonical 4-view',
              'seed':42, 'resolution':1024, 'texture':False, 'rig':False}
    (job / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]).resolve(strict=True))
        return
    if len(sys.argv) != 1:
        raise ValueError('invalid arguments')
    from workflow.common.gpu_job_queue import launch_gpu_process
    paths = [BINARY] + [MODELS / name for name in MODEL_NAMES] + [SOURCE / name for name in NAMES]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    job = ROOT / '.tmp/pixal-experiment' / ('generate-' + uuid.uuid4().hex)
    job.mkdir(parents=True)
    views = stage_views(job)
    paths += sorted(views.glob('*.png'))
    (job / 'request.json').write_text(json.dumps({'sha256':{str(path):digest(path) for path in paths},
        'seed':42, 'resolution':1024, 'background':'upstream alpha-premultiplied black', 'camera':'assumed canonical, mesh_scale=1.0'}, indent=2) + '\n')
    with (job / 'worker.log').open('w') as log:
        process = launch_gpu_process([sys.executable, str(Path(__file__).resolve()), '--worker', str(job)], job,
                                     'pixal-experiment', stdout=log, stderr=log, start_new_session=True)
    print(f'job={job} queue_pid={process.pid}')


if __name__ == '__main__':
    main()
