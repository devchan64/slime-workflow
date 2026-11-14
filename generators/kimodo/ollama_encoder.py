"""Ollama의 고정 FP16 GGUF를 Kimodo용 safetensors로 변환한다."""
import hashlib
import subprocess
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

OLLAMA_ENCODER_TAG = 'llama3:8b-instruct-fp16'
OLLAMA_ENCODER_SHA256 = 'f2296999531d6120801529a45b1d103f7370c5970be939ebfc2ba5d0833e9e1e'
OLLAMA_ENCODER_BYTES = 16068890912


def download_ollama_encoder(current_blob_path):
    from tools.review.common.model_download_records import track_model_download
    current_blob_path.parent.mkdir(parents=True, exist_ok=True)
    current_resume_bytes = current_blob_path.stat().st_size if current_blob_path.exists() else 0
    with track_model_download('ollama/llama3:8b-instruct-fp16') as current_download_record:
        current_download_record.update(stage='다운로드', bytes=current_resume_bytes, total_bytes=OLLAMA_ENCODER_BYTES, resumed_bytes=current_resume_bytes)
        current_stop_event = threading.Event()
        def report_encoder_progress():
            while not current_stop_event.wait(1):
                current_received_bytes = current_blob_path.stat().st_size if current_blob_path.exists() else 0
                current_download_record.update(bytes=current_received_bytes)
        current_progress_thread = threading.Thread(target=report_encoder_progress, daemon=True)
        current_progress_thread.start()
        try:
            if current_resume_bytes != OLLAMA_ENCODER_BYTES:
                subprocess.run([
                    'curl', '--fail', '--location', '--silent', '--show-error', '--retry', '2',
                    '--continue-at', '-', '--output', str(current_blob_path),
                    f'https://registry.ollama.ai/v2/library/llama3/blobs/sha256:{OLLAMA_ENCODER_SHA256}',
                ], check=True)
        finally:
            current_stop_event.set()
            current_progress_thread.join()
        current_download_record.update(stage='SHA-256 검증', bytes=current_blob_path.stat().st_size)
        with current_blob_path.open('rb') as current_blob_file:
            if hashlib.file_digest(current_blob_file, 'sha256').hexdigest() != OLLAMA_ENCODER_SHA256:
                raise ValueError('Ollama FP16 GGUF SHA-256 불일치')


def convert_ollama_encoder(current_blob_path, current_output_root):
    import torch
    from gguf import GGMLQuantizationType, GGUFReader
    from transformers import AutoModelForCausalLM

    current_reader = GGUFReader(str(current_blob_path))
    if any(current_tensor.tensor_type not in (GGMLQuantizationType.F16, GGMLQuantizationType.F32)
           for current_tensor in current_reader.tensors):
        raise ValueError('FP16/FP32 텐서만 있는 GGUF가 필요합니다.')
    del current_reader
    with TemporaryDirectory(dir=current_output_root.parent) as current_model_directory:
        current_encoder_model, current_loading_info = AutoModelForCausalLM.from_pretrained(
            current_model_directory, gguf_file=str(current_blob_path.resolve()), dtype=torch.float16,
            local_files_only=True, output_loading_info=True,
        )
        for current_loading_field in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs'):
            if current_loading_info.get(current_loading_field):
                raise ValueError(f'GGUF 가중치 로딩 불일치: {current_loading_field}: {current_loading_info[current_loading_field]}')
        current_encoder_model.config._name_or_path = "meta-llama/Meta-Llama-3-8B-Instruct"
        current_encoder_model.save_pretrained(current_output_root, max_shard_size='5GB')


def publish_converted_encoder(current_blob_path, current_output_root):
    from tools.review.common.generation_records import write_record_atomically

    with TemporaryDirectory(dir=current_output_root.parent) as current_staging_directory:
        current_staging_root = Path(current_staging_directory)/'converted'
        convert_ollama_encoder(current_blob_path, current_staging_root)
        current_file_records = {}
        for current_file_path in current_staging_root.iterdir():
            if current_file_path.suffix not in ('.safetensors', '.json') or current_file_path.name == 'generation_config.json':
                continue
            with current_file_path.open('rb') as current_file_stream:
                current_file_records[current_file_path.name] = {
                    'size': current_file_path.stat().st_size,
                    'sha256': hashlib.file_digest(current_file_stream, 'sha256').hexdigest(),
                }
        current_output_root.mkdir(exist_ok=True)
        for current_file_name in current_file_records:
            (current_staging_root/current_file_name).replace(current_output_root/current_file_name)
        write_record_atomically(current_output_root/'conversion.json', {
            'source_sha256': OLLAMA_ENCODER_SHA256, 'tag': OLLAMA_ENCODER_TAG, 'files': current_file_records,
        })


if __name__ == '__main__':
    import argparse

    current_parser = argparse.ArgumentParser(description=__doc__)
    current_parser.add_argument('blob', type=Path)
    current_parser.add_argument('output', type=Path)
    current_arguments = current_parser.parse_args()
    download_ollama_encoder(current_arguments.blob)
    publish_converted_encoder(current_arguments.blob, current_arguments.output)
