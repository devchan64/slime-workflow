"""검증된 ONNX CUDA 인코더와 공식 JAX 소형 모델을 연결하는 실험 경로."""
from pathlib import Path
import gc
import hashlib
import json
import os
from generators.music.contracts import resolve_music_paths, MusicDefaultsLoader
from generators.music.runtime import calculate_music_checksum
from tools.review.common.generation_records import write_record_atomically

MAGENTA_ENDING_POLICY = Path(__file__).with_name('ending_policy.yaml')

MAGENTA_REQUIRED_FILES = ('source/checkpoints/mrt2_small.safetensors', 'source/resources/musiccoca/spm.model', 'onnx/text_encoder.onnx', 'onnx/mapper.onnx', 'onnx/pretrained_vector_quantizer.onnx')


def validate_magenta_artifacts(current_service_name):
    _, current_model_root, _ = resolve_music_paths(current_service_name)
    for current_relative_path in MAGENTA_REQUIRED_FILES:
        if not (current_model_root/current_relative_path).is_file():
            raise FileNotFoundError(f'Magenta GPU 준비 파일 누락: {current_model_root/current_relative_path}')
    return current_model_root


def prepare_magenta_model(current_service_name, current_metrics_recorder, current_download_requested):
    current_model_root = validate_magenta_artifacts(current_service_name)
    current_manifest_record = {'model_id':'google/magenta-realtime-2', 'variant':'mrt2_small', 'path':str(current_model_root), 'files':{current_relative_path:calculate_music_checksum(current_model_root/current_relative_path) for current_relative_path in MAGENTA_REQUIRED_FILES}}
    write_record_atomically(current_model_root/'prepared.json', current_manifest_record)
    print(f'Magenta 준비 완료: {current_model_root}', flush=True)
    return current_manifest_record


def require_magenta_cuda():
    os.environ['JAX_PLATFORMS'] = 'cuda'
    os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = 'false'
    import jax
    if not jax.devices() or any(current_device_value.platform != 'gpu' for current_device_value in jax.devices()):
        raise RuntimeError('Magenta JAX CUDA 장치가 필요합니다. CPU 대체는 금지합니다.')
    return jax.devices()[0].device_kind


def encode_magenta_prompt(current_model_root, current_request_record, current_attempt_root):
    import numpy
    import sentencepiece
    import onnxruntime
    onnxruntime.preload_dlls(directory='')
    current_tokenizer_model = sentencepiece.SentencePieceProcessor(model_file=str(current_model_root/'source/resources/musiccoca/spm.model'))
    current_token_values = current_tokenizer_model.encode(current_request_record['final_prompt'].lower())
    if len(current_token_values) > 127:
        raise ValueError(f'MusicCoCa 프롬프트는 127 토큰 이하여야 합니다: {len(current_token_values)}. 설명을 줄이세요.')
    current_token_values = [1]+current_token_values
    current_input_tokens = numpy.array([current_token_values+[0]*(128-len(current_token_values))], dtype=numpy.int32)
    current_input_padding = numpy.array([[0.]*len(current_token_values)+[1.]*(128-len(current_token_values))], dtype=numpy.float32)
    current_embedding_value = None
    current_provider_records = {}
    for current_model_name in ('text_encoder','mapper','pretrained_vector_quantizer'):
        current_session_options = onnxruntime.SessionOptions()
        current_session_options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        current_session_options.enable_profiling = True
        current_session_options.profile_file_prefix = str(current_attempt_root/current_model_name)
        current_model_session = onnxruntime.InferenceSession(str(current_model_root/'onnx'/(current_model_name+'.onnx')), sess_options=current_session_options, providers=['CUDAExecutionProvider'])
        current_input_values = {}
        for current_input_index, current_input_record in enumerate(current_model_session.get_inputs()):
            if current_model_name == 'text_encoder':
                current_input_value = current_input_tokens if current_input_record.type == 'tensor(int32)' else current_input_padding
            elif current_model_name == 'mapper':
                current_input_value = current_embedding_value if current_input_index == 0 else numpy.random.RandomState(current_request_record['seed']).randn(*current_embedding_value.shape).astype(numpy.float32)
            else:
                current_input_value = current_embedding_value
            current_input_values[current_input_record.name] = current_input_value.reshape(current_input_record.shape)
        current_embedding_value = current_model_session.run(None, current_input_values)[0]
        current_profile_events = json.loads(Path(current_model_session.end_profiling()).read_text())
        current_provider_names = sorted({current_event_value.get('args',{}).get('provider') for current_event_value in current_profile_events if current_event_value.get('args',{}).get('provider')})
        if current_provider_names != ['CUDAExecutionProvider'] or not numpy.isfinite(current_embedding_value).all():
            raise RuntimeError(f'GPU 인코더 계약 위반: {current_model_name} {current_provider_names}')
        current_provider_records[current_model_name] = current_provider_names
        del current_model_session
        gc.collect()
    current_style_tokens = current_embedding_value.flatten().tolist()
    if len(current_style_tokens) != 12 or not all(isinstance(current_token_value,int) and 0 <= current_token_value < 1024 for current_token_value in current_style_tokens):
        raise ValueError('Magenta 스타일 토큰 계약 위반')
    write_record_atomically(current_attempt_root/'encoder.json', {'providers':current_provider_records, 'token_count':len(current_token_values), 'style_tokens':current_style_tokens, 'mapper_seed':current_request_record['seed'], 'sampler_seed':0, 'cpu_fallback_allowed':False})
    return current_style_tokens


def execute_magenta_inference(current_service_name, current_request_record, current_attempt_root, current_metrics_recorder):
    import numpy
    import soundfile
    from magenta_rt import MagentaRT2Jax, paths
    from magenta_rt.config import MUSICCOCA
    current_model_root = validate_magenta_artifacts(current_service_name)
    current_metrics_recorder.update_generation_stage('encoding')
    current_style_tokens = encode_magenta_prompt(current_model_root, current_request_record, current_attempt_root)
    import yaml
    current_ending_policy = yaml.load(MAGENTA_ENDING_POLICY.read_text(),Loader=MusicDefaultsLoader)
    if not isinstance(current_ending_policy,dict) or set(current_ending_policy) != {'version','ending_seconds','prompt_suffix'} or current_ending_policy['version'] != 1 or type(current_ending_policy['ending_seconds']) is not int or not 1 <= current_ending_policy['ending_seconds'] <= 30 or not isinstance(current_ending_policy['prompt_suffix'],str) or not current_ending_policy['prompt_suffix'].strip():
        raise ValueError('Magenta 마무리 정책 계약 오류')
    current_ending_request = dict(current_request_record,final_prompt=current_request_record['final_prompt']+' '+current_ending_policy['prompt_suffix'])
    current_ending_directory = current_attempt_root/'ending'
    current_ending_directory.mkdir()
    current_ending_tokens = encode_magenta_prompt(current_model_root,current_ending_request,current_ending_directory)
    current_ending_start = max(current_request_record['duration_seconds']/2,current_request_record['duration_seconds']-current_ending_policy['ending_seconds'])
    write_record_atomically(current_attempt_root/'conditioning.json',{'body_prompt':current_request_record['final_prompt'],'ending_prompt':current_ending_request['final_prompt'],'body_words':len(current_request_record['final_prompt'].split()),'ending_words':len(current_ending_request['final_prompt'].split()),'ending_prompt_sha256':hashlib.sha256(current_ending_request['final_prompt'].encode()).hexdigest(),'ending_start_seconds':current_ending_start,'ending_policy_sha256':calculate_music_checksum(MAGENTA_ENDING_POLICY),'volume_processing':False})
    paths.set_magenta_home(current_model_root/'source')
    current_metrics_recorder.update_generation_stage('load')
    current_music_model = MagentaRT2Jax(size='mrt2_small')
    current_frame_total = round(current_request_record['duration_seconds']*25)
    current_chunk_total = (current_frame_total+24)//25
    current_metrics_recorder.current_step_total = current_chunk_total
    current_metrics_recorder.current_run_state['step_total'] = current_chunk_total
    current_audio_state = None
    current_audio_chunks = []
    current_metrics_recorder.update_generation_stage('inference')
    for current_chunk_index in range(current_chunk_total):
        current_audio_wave, current_audio_state = current_music_model.generate(conditioning={MUSICCOCA.key:current_ending_tokens if current_chunk_index >= current_ending_start else current_style_tokens}, frames=min(25,current_frame_total-current_chunk_index*25), state=current_audio_state)
        current_audio_chunks.append(current_audio_wave.samples)
        current_metrics_recorder.record_generation_step(current_chunk_index+1)
    current_output_samples = numpy.concatenate(current_audio_chunks,axis=0)
    if current_output_samples.shape != (current_frame_total*1920,2) or not numpy.isfinite(current_output_samples).all():
        raise ValueError(f'Magenta WAV 계약 위반: {current_output_samples.shape}')
    current_metrics_recorder.update_generation_stage('saving')
    current_audio_path = current_attempt_root/'music.wav'
    soundfile.write(current_audio_path,current_output_samples,48000,subtype='PCM_16')
    return {'attempt':current_attempt_root.name,'model_id':'google/magenta-realtime-2','variant':'mrt2_small','format':'wav','channels':2,'sample_rate':48000,'duration_seconds':len(current_output_samples)/48000,'output_sha256':calculate_music_checksum(current_audio_path),'prompt_sha256':current_request_record['prompt_sha256'],'runtime_sha256':calculate_music_checksum(Path(__file__)),'model_compute_device':'cuda','mapper_seed':current_request_record['seed'],'sampler_seed':0,'quality_status':'사용자 청취 검수 대기','quality_warnings':['스트리밍 모델을 지정 길이에서 종료합니다. 자연스러운 종결·보컬 미포함은 청취 검수가 필요합니다.'],'seamless_loop_guaranteed':False}
