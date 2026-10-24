"""HeartMuLa NF4 생성·FP32 디코더를 순차 CUDA 실행한다."""
from pathlib import Path
import json
import os
from generators.music.contracts import resolve_music_paths
from generators.music.runtime import calculate_music_checksum, require_music_cuda, attach_cuda_guards
from tools.review.common.generation_records import write_record_atomically

HEARTMULA_SOURCE_REVISIONS = (
    ('HeartMuLa/HeartMuLaGen','2e18e01702011f4f7dc8642b6260967df62417ea','bundle'),
    ('HeartMuLa/HeartMuLa-oss-3B-happy-new-year','41f6fc68490e11dc43fdabaa6b5767946408c903','bundle/HeartMuLa-oss-3B'),
    ('HeartMuLa/HeartCodec-oss-20260123','f889dab0532cfa4bf459f2a3367eb6d346b8eeda','bundle/HeartCodec-oss'),
)
HEARTMULA_LIBRARY_REVISION = '5858ca8f1ffe58d62be7c007ea55f1033c5ca456'
HEARTMULA_DECODE_WINDOW_SECONDS = 7.44
HEARTMULA_SAMPLING_SETTINGS = {'topk':50,'temperature':1.0,'cfg_scale':3.0}


def validate_heartmula_artifacts(current_service_name):
    _,current_model_root,current_python_path = resolve_music_paths(current_service_name)
    if not current_python_path.is_file():
        raise FileNotFoundError(f'HeartMuLa 실행 환경 누락: {current_python_path}')
    current_bundle_root = current_model_root/'bundle'
    for current_relative_path in ('tokenizer.json','gen_config.json','HeartMuLa-oss-3B/config.json','HeartCodec-oss/config.json'):
        if not (current_bundle_root/current_relative_path).is_file():
            raise FileNotFoundError(f'모델 파일 누락: {current_bundle_root/current_relative_path}')
    for current_model_name in ('HeartMuLa-oss-3B','HeartCodec-oss'):
        current_index_path = current_bundle_root/current_model_name/'model.safetensors.index.json'
        current_index_record = json.loads(current_index_path.read_text())
        for current_shard_name in set(current_index_record['weight_map'].values()):
            current_shard_path = current_index_path.parent/current_shard_name
            if not current_shard_path.resolve().is_relative_to(current_index_path.parent.resolve()) or not current_shard_path.is_file():
                raise ValueError(f'가중치 파일 누락·경로 오류: {current_shard_path}')
    return current_model_root


def prepare_heartmula_model(current_service_name,current_metrics_recorder,current_download_requested):
    current_model_root = validate_heartmula_artifacts(current_service_name)
    current_metrics_recorder.update_generation_stage('prepare')
    current_manifest_path = current_model_root/'prepared.json'
    current_model_files = sorted(current_model_root.glob('bundle/**/*.safetensors'))+sorted(current_model_root.glob('bundle/**/*.json'))
    current_model_files = [current_model_path for current_model_path in current_model_files if '.cache' not in current_model_path.parts]
    current_manifest_record = {'model_id':HEARTMULA_SOURCE_REVISIONS[1][0],'sources':HEARTMULA_SOURCE_REVISIONS,'library_revision':HEARTMULA_LIBRARY_REVISION,'runtime_sha256':calculate_music_checksum(Path(__file__)),'files':[{'path':str(current_model_path.relative_to(current_model_root)),'size':current_model_path.stat().st_size,'sha256':calculate_music_checksum(current_model_path)} for current_model_path in current_model_files]}
    write_record_atomically(current_manifest_path,current_manifest_record)
    print(f'HeartMuLa 모델 준비 완료: {current_model_root}/bundle',flush=True)
    return current_manifest_record


def execute_heartmula_inference(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder):
    import torch
    import soundfile
    import numpy
    from transformers import BitsAndBytesConfig
    from heartlib import HeartMuLaGenPipeline
    from heartlib.heartmula.modeling_heartmula import HeartMuLa
    from heartlib.heartcodec.modeling_heartcodec import HeartCodec
    current_model_root = validate_heartmula_artifacts(current_service_name)
    os.environ['HF_HUB_OFFLINE']='1'
    require_music_cuda()
    torch.manual_seed(current_request_record['seed'])
    torch.cuda.manual_seed_all(current_request_record['seed'])
    current_frame_limit = int(current_request_record['duration_seconds']*1000)//80
    current_metrics_recorder.current_step_total = current_frame_limit+1
    current_metrics_recorder.current_run_state['step_total'] = current_frame_limit+1

    class CudaSequentialPipeline(HeartMuLaGenPipeline):
        @property
        def mula(self):
            if self._mula is None:
                current_metrics_recorder.update_generation_stage('load')
                self._mula = HeartMuLa.from_pretrained(self.mula_path,local_files_only=True,device_map={'':'cuda:0'},dtype=torch.bfloat16,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16,llm_int8_skip_modules=['audio_head','text_embeddings','audio_embeddings','projection','muq_linear']))
                self._mula.backbone.max_seq_len = current_cache_length
                attach_cuda_guards(self._mula)
                current_metrics_recorder.update_generation_stage('inference')
            return self._mula
        @property
        def codec(self):
            if self._codec is None:
                current_metrics_recorder.update_generation_stage('decoding')
                self._codec = HeartCodec.from_pretrained(self.codec_path,local_files_only=True,device_map={'':'cuda:0'},dtype=torch.float32)
                attach_cuda_guards(self._codec)
            return self._codec

    current_music_pipeline = CudaSequentialPipeline.from_pretrained(str(current_model_root/'bundle'),device={'mula':torch.device('cuda:0'),'codec':torch.device('cuda:0')},dtype={'mula':torch.bfloat16,'codec':torch.float32},version='3B',lazy_load=True)
    current_lyrics_text = current_request_record['lyrics']
    current_tags_path = current_attempt_root/'tags.txt'
    current_lyrics_path = current_attempt_root/'lyrics.txt'
    current_tags_path.write_text(current_request_record['final_prompt'])
    current_lyrics_path.write_text(current_lyrics_text)
    current_model_inputs = current_music_pipeline.preprocess({'tags':str(current_tags_path),'lyrics':str(current_lyrics_path)},cfg_scale=HEARTMULA_SAMPLING_SETTINGS['cfg_scale'])
    current_cache_length = current_model_inputs['tokens'].shape[1]+current_frame_limit+2
    if current_cache_length > 8192:
        raise ValueError(f'HeartMuLa 컨텍스트 상한 초과: {current_cache_length}')
    current_original_generate = HeartMuLa.generate_frame
    current_generated_count = 0
    current_eos_observed = False
    def record_heartmula_frame(current_model_instance,*current_frame_arguments,**current_frame_keywords):
        nonlocal current_generated_count,current_eos_observed
        current_frame_output = current_original_generate(current_model_instance,*current_frame_arguments,**current_frame_keywords)
        current_generated_count += 1
        current_eos_observed = bool(torch.any(current_frame_output[0:1] >= current_music_pipeline.config.audio_eos_id))
        current_metrics_recorder.record_generation_step(current_generated_count)
        return current_frame_output
    HeartMuLa.generate_frame = record_heartmula_frame
    try:
        with torch.inference_mode():
            current_model_outputs = current_music_pipeline._forward(current_model_inputs,max_audio_length_ms=int(current_request_record['duration_seconds']*1000),**HEARTMULA_SAMPLING_SETTINGS)
            current_termination_record = {'reason':'audio_eos' if current_eos_observed else 'max_audio_length_ms','audio_eos_id':current_music_pipeline.config.audio_eos_id,'frames':current_model_outputs['frames'].shape[-1],'cache_length':current_cache_length}
            write_record_atomically(current_attempt_root/'termination.json',current_termination_record)
            current_audio_wave = current_music_pipeline.codec.detokenize(current_model_outputs['frames'].to('cuda:0'),duration=HEARTMULA_DECODE_WINDOW_SECONDS)
            current_audio_samples = current_audio_wave.float().cpu().numpy().T
            current_music_pipeline._unload()
    finally:
        HeartMuLa.generate_frame = current_original_generate
    if current_audio_samples.ndim != 2 or current_audio_samples.shape[1] != 2 or not len(current_audio_samples) or not numpy.isfinite(current_audio_samples).all():
        raise ValueError('HeartMuLa stereo WAV 유한값 계약 위반')
    current_metrics_recorder.update_generation_stage('saving')
    current_audio_path = current_attempt_root/'music.wav'
    soundfile.write(current_audio_path,current_audio_samples,48000,subtype='PCM_16')
    current_result_record = {'attempt':current_attempt_root.name,'model_id':HEARTMULA_SOURCE_REVISIONS[1][0],'format':'wav','channels':2,'sample_rate':48000,'duration_seconds':len(current_audio_samples)/48000,'output_sha256':calculate_music_checksum(current_audio_path),'runtime_sha256':calculate_music_checksum(Path(__file__)),'prompt_sha256':current_request_record['prompt_sha256'],'model_compute_device':'cuda','quantization':'NF4 double quant, BF16 compute','codec_dtype':'float32','codec_window_seconds':HEARTMULA_DECODE_WINDOW_SECONDS,'sampling':HEARTMULA_SAMPLING_SETTINGS,'seed':current_request_record['seed'],'torch_peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20,'torch_peak_reserved_mib':torch.cuda.max_memory_reserved()/2**20,'quality_warnings':['4비트 생성 모델의 품질·보컬 유입·끝맺음은 청취 검수가 필요합니다.'],'quality_status':'사용자 청취 검수 대기','seamless_loop_guaranteed':False}
    current_result_record['termination'] = current_termination_record
    if not current_eos_observed:
        current_result_record['quality_warnings'].append('최대 출력 시간에 도달해 종료했습니다. 음악적 끝맺음이 완료되었다는 의미가 아닙니다.')
    write_record_atomically(current_model_root/'gpu-validation.json',{'generation_id':current_attempt_root.parent.parent.name,'attempt':current_attempt_root.name,'runtime_sha256':current_result_record['runtime_sha256'],'status':'passed'})
    return current_result_record
