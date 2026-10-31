"""VideoX-Fun 포즈 검출 가중치를 고정 리비전에서 준비한다."""
import hashlib
import json
import threading
import time
import traceback
from pathlib import Path

from generators.wan_fun.pose_preprocess import FUN_POSE_MODEL_DIRECTORY, FUN_POSE_MODEL_NAMES, FUN_POSE_MODEL_REVISION


def prepare_fun_pose_models():
    from huggingface_hub import hf_hub_download
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
            write_prepare_message(f'다운로드 model_id=yzd-v/DWPose file={current_model_name}')
            current_model_path = Path(hf_hub_download('yzd-v/DWPose', current_model_name, revision=FUN_POSE_MODEL_REVISION, local_dir=FUN_POSE_MODEL_DIRECTORY))
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
            current_cuda_path = current_model_path.with_suffix('.cuda.onnx')
            onnx.save(current_output_model, current_cuda_path)
            with current_cuda_path.open('rb') as current_model_stream:
                current_model_hashes[current_cuda_path.name] = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
        (FUN_POSE_MODEL_DIRECTORY/'prepared.json').write_text(json.dumps({'revision': FUN_POSE_MODEL_REVISION, 'files': current_model_hashes}))
        write_prepare_message(f'완료 model_root={FUN_POSE_MODEL_DIRECTORY}')
    except BaseException:
        write_prepare_message(traceback.format_exc())
        raise
    finally:
        current_stop_event.set()


if __name__ == '__main__':
    prepare_fun_pose_models()
