"""AnimationGPT 관절 생성과 VACE 포즈 출력의 단일 작업 실행기.

호출자는 이 함수를 격리된 작업 프로세스에서 실행하고 작업 경로를 관리한다.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path

from workflow.domains.animationgpt.inference import MOTIONGPT_REVISION


def validate_request(request):
    if not isinstance(request, dict) or set(request) - {'prompt', 'seed', 'yaw_degrees', 'scale', 'include_face'}:
        raise ValueError('지원하지 않는 생성 입력입니다.')
    prompt = request.get('prompt')
    seed = request.get('seed')
    yaw = request.get('yaw_degrees', 0)
    scale = request.get('scale', .8)
    face = request.get('include_face', False)
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        raise ValueError('프롬프트는 1~2000자여야 합니다.')
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError('시드는 0~2147483647의 정수여야 합니다.')
    for value, low, high, label in ((yaw, -180, 180, '카메라 각도'), (scale, .1, 1, '화면 크기')):
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{label} 범위 오류')
    if type(face) is not bool:
        raise ValueError('얼굴 추정은 참 또는 거짓이어야 합니다.')
    return {'prompt': prompt.strip(), 'seed': seed, 'yaw_degrees': yaw, 'scale': scale, 'include_face': face}


def validate_upstream(source_root):
    source = Path(source_root)
    def git(*arguments):
        return subprocess.run(['git', '-C', str(source), *arguments], check=True, capture_output=True, text=True).stdout.strip()
    try:
        if git('rev-parse', 'HEAD') != MOTIONGPT_REVISION or git('status', '--porcelain', '--untracked-files=no'):
            raise ValueError('MotionGPT 소스 리비전 또는 추적 파일 변경을 확인하세요.')
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError('MotionGPT 소스 리비전을 확인할 수 없습니다.') from error


def run_pipeline(request, output_dir, source_root, model_root):
    """새 디렉터리에 관절 NPY와 VACE 제어 영상 및 출처를 기록한다."""
    from workflow.common.animationgpt_model_download import ANIMATIONGPT_MODEL_DIRECTORY, inspect_animationgpt_model_files
    from workflow.domains.joint_proportions.vace_pose_export import export_vace_pose, prepare_pose_frames, validate_vace_frame_count
    import numpy as np

    values = validate_request(request)
    validate_upstream(source_root)
    if Path(model_root).resolve() != ANIMATIONGPT_MODEL_DIRECTORY.resolve() or not inspect_animationgpt_model_files():
        raise ValueError('모델 관리에서 AnimationGPT 파일을 준비하고 검증하세요.')
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise ValueError('기존 출력은 덮어쓰지 않습니다.')
    destination.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[3]
    python = root / '.local/animationgpt-legacy/venv/bin/python'
    if not python.is_file():
        raise FileNotFoundError('AnimationGPT Python 3.10 실행 환경이 준비되지 않았습니다.')
    payload = {'prompt': values['prompt'], 'seed': values['seed'], 'source_root': str(Path(source_root).resolve()),
               'model_root': str(Path(model_root).resolve()), 'output': str(destination.resolve())}
    process = subprocess.run([str(python), '-m', 'workflow.domains.animationgpt.worker'], input=json.dumps(payload),
                             cwd=str(root), text=True, capture_output=True)
    if process.returncode:
        raise RuntimeError('AnimationGPT 추론 실패: ' + process.stderr[-4000:])
    path = destination / 'joints.npy'
    metadata = json.loads((destination / 'motion.json').read_text(encoding='utf-8'))
    joints = np.load(path, allow_pickle=False)
    projected, _ = prepare_pose_frames(joints, metadata['fps'], values['yaw_degrees'], values['scale'], include_face=values['include_face'])
    try:
        validate_vace_frame_count(len(projected))
    except ValueError as error:
        pose, pose_error = None, str(error)
    else:
        pose = export_vace_pose(path, destination / 'vace-pose', metadata['fps'], yaw_degrees=values['yaw_degrees'],
                                scale=values['scale'], include_face=values['include_face'], provenance=metadata)
        pose_error = None
    record = {'schema': 'animationgpt-pose-pipeline-v1', 'request': values, 'motion': metadata,
              'joints_file': path.name, 'joints_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'pose_manifest': 'vace-pose/pose-export.json' if pose else None,
              'pose_segments': len(pose['files']) if pose else 0, 'pose_unavailable_reason': pose_error,
              'limitations': '관절과 투영 포즈만 생성합니다. 무기 궤적·가림·접지와 영상 품질은 보장하지 않습니다.'}
    (destination / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return record
