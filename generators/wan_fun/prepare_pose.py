"""VideoX-Fun 포즈 검출 가중치를 고정 리비전에서 준비한다."""
import hashlib
import json
import os
import threading
import time
import traceback
from pathlib import Path

from generators.wan_fun.pose_preprocess import FUN_POSE_MODEL_DIRECTORY, FUN_POSE_MODEL_NAMES, FUN_POSE_MODEL_REVISION
from generators.kimodo.dwpose_runtime import pose_model_path


def _pose_declared_digest(current_target):
    current_record_path = current_target.parent/'prepared.json'
    if not current_record_path.exists() and not current_record_path.is_symlink():
        current_record_path = FUN_POSE_MODEL_DIRECTORY/'prepared.json'
    if current_record_path.is_symlink():
        return None
    try:
        current_record = json.loads(current_record_path.read_text(encoding='utf-8'))
        current_digest = current_record['files'][current_target.name]
        if (current_record.get('revision') != FUN_POSE_MODEL_REVISION or not isinstance(current_digest, str)
                or len(current_digest) != 64 or any(char not in '0123456789abcdef' for char in current_digest)):
            return None
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
    return current_digest


def prepared_pose_source_matches(current_target):
    """A local preparation record is a consistency check, not origin proof."""
    if current_target.is_symlink() or not current_target.is_file():
        return False
    current_digest = _pose_declared_digest(current_target)
    if current_digest is None:
        return False
    with current_target.open('rb') as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    return digest == current_digest and identity(before) == identity(after) and not current_target.is_symlink() and identity(current_target.stat()) == identity(before)


def restore_pose_source_from_backup(current_target):
    """Use an existing local preparation declaration to recover a missing source."""
    if current_target.exists() or current_target.is_symlink():
        return False
    current_digest = _pose_declared_digest(current_target)
    if current_digest is None:
        return False
    from workflow.common.model_backup_restore import restore_verified_backup
    return restore_verified_backup(current_target, current_digest)


def prepare_fun_pose_models():
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    import huggingface_hub.constants as current_hub_constants
    current_hub_constants.HF_HUB_DISABLE_XET = True
    from workflow.common.model_huggingface_download import tracked_hf_hub_download as hf_hub_download
    import onnx
    from onnxsim import simplify
    current_log_directory = Path('.tmp/test/fun-pose-prepare')
    current_log_directory.mkdir(parents=True, exist_ok=True)
    current_log_path = current_log_directory/f'{time.time_ns()}.log'
    current_stop_event = threading.Event()
    def write_prepare_message(current_message_text):
        current_log_text = time.strftime('%Y-%m-%dT%H:%M:%S')+'/fun/prepare-pose '+current_message_text
        print(current_log_text, flush=True)
        with current_log_path.open('a') as current_log_stream:
            current_log_stream.write(current_log_text+'\n')
    def report_prepare_heartbeat():
        while not current_stop_event.wait(5):
            write_prepare_message(f'다운로드 진행 중 model_root={FUN_POSE_MODEL_DIRECTORY}')
    threading.Thread(target=report_prepare_heartbeat, daemon=True).start()
    try:
        current_model_hashes = {}
        for current_model_name in FUN_POSE_MODEL_NAMES:
            write_prepare_message(f'모델 확인 model_id=yzd-v/DWPose file={current_model_name}')
            current_target = pose_model_path(current_model_name)
            if prepared_pose_source_matches(current_target):
                write_prepare_message(f'로컬 준비 기록 일치 file={current_model_name}')
                current_model_path = current_target
            elif restore_pose_source_from_backup(current_target):
                write_prepare_message(f'백업 복원 file={current_model_name}')
                current_model_path = current_target
            else:
                write_prepare_message(f'다운로드 file={current_model_name}')
                current_model_path = Path(hf_hub_download('yzd-v/DWPose', current_model_name, revision=FUN_POSE_MODEL_REVISION, local_dir=current_target.parent))
            with current_model_path.open('rb') as current_model_stream:
                current_model_hashes[current_model_name] = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
            # 입력은 단일 인체다. 형상 계산을 상수화해 CPU EP 없이 CUDA로 초기화한다.
            current_source_model = onnx.load(current_model_path)
            current_input_name = current_source_model.graph.input[0].name
            current_input_shape = [1, 3, 640, 640] if current_model_name=='yolox_l.onnx' else [1, 3, 384, 288]
            current_output_model, current_valid_result = simplify(current_source_model, overwrite_input_shapes={current_input_name: current_input_shape}, check_n=0)
            if not current_valid_result:
                raise RuntimeError('ONNX 형상 상수화 실패')
            onnx.checker.check_model(current_output_model)
            current_cuda_path = pose_model_path(Path(current_model_name).with_suffix('.cuda.onnx').name)
            current_cuda_path.parent.mkdir(parents=True, exist_ok=True)
            onnx.save(current_output_model, current_cuda_path)
            with current_cuda_path.open('rb') as current_model_stream:
                current_model_hashes[current_cuda_path.name] = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
        from workflow.common.generation_records import write_record_atomically
        current_record_groups = {}
        for current_file_name, current_digest in current_model_hashes.items():
            current_record_directory = pose_model_path(current_file_name).parent
            current_record_groups.setdefault(current_record_directory, {})[current_file_name] = current_digest
        for current_record_directory, current_hashes in current_record_groups.items():
            write_record_atomically(current_record_directory/'prepared.json', {'revision': FUN_POSE_MODEL_REVISION, 'files': current_hashes})
        write_prepare_message(f'완료 model_root={FUN_POSE_MODEL_DIRECTORY}')
    except BaseException:
        write_prepare_message(traceback.format_exc())
        raise
    finally:
        current_stop_event.set()


if __name__ == '__main__':
    prepare_fun_pose_models()
