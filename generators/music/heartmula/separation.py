"""HeartMuLa 원곡을 보존하고 CUDA Demucs로 MR·보컬을 분리한다."""
from pathlib import Path
import gc

from generators.music.runtime import calculate_music_checksum, require_music_cuda, attach_cuda_guards

DEMUCS_CHECKPOINT_NAME = '955717e8-8726e21a.th'
DEMUCS_CHECKPOINT_URL = 'https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/'+DEMUCS_CHECKPOINT_NAME
DEMUCS_SEGMENT_SECONDS = 7
DEMUCS_CHECKPOINT_SHA256 = '8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4'


def prepare_separation_model(current_model_root, current_download_requested):
    current_checkpoint_root = current_model_root/'demucs'
    current_checkpoint_path = current_checkpoint_root/DEMUCS_CHECKPOINT_NAME
    if not current_checkpoint_path.is_file():
        if not current_download_requested:
            raise FileNotFoundError(f'MR 분리 모델 준비 필요: {current_checkpoint_path}')
        import torch
        current_checkpoint_root.mkdir(parents=True, exist_ok=True)
        current_download_path = current_checkpoint_path.with_suffix('.download')
        torch.hub.download_url_to_file(DEMUCS_CHECKPOINT_URL, str(current_download_path), hash_prefix=DEMUCS_CHECKPOINT_SHA256)
        current_download_path.replace(current_checkpoint_path)
    current_checkpoint_hash = calculate_music_checksum(current_checkpoint_path)
    if current_checkpoint_hash != DEMUCS_CHECKPOINT_SHA256:
        raise ValueError(f'Demucs 체크포인트 해시 불일치: {current_checkpoint_path}')
    print(f'MR 분리 모델 준비 완료: {current_checkpoint_path}', flush=True)
    return {'model_id':'demucs/htdemucs', 'path':str(current_checkpoint_path), 'sha256':current_checkpoint_hash,
            'runtime_sha256':calculate_music_checksum(Path(__file__))}


def separate_heartmula_audio(current_model_root, current_attempt_root, current_metrics_recorder):
    import soundfile
    import torch
    import torchaudio
    from demucs.states import load_model
    from demucs.apply import apply_model

    require_music_cuda()
    current_model_record = prepare_separation_model(current_model_root, False)
    gc.collect()
    torch.cuda.empty_cache()
    current_metrics_recorder.update_generation_stage('separation')
    # 공식 파일 전체 해시를 검증한 뒤, 클래스가 포함된 Demucs 4 체크포인트를 로드한다.
    current_checkpoint_record = torch.load(current_model_record['path'], map_location='cpu', weights_only=False)
    current_separator_model = load_model(current_checkpoint_record, strict=True).eval().cuda()
    attach_cuda_guards(current_separator_model)
    current_audio_samples, current_sample_rate = soundfile.read(current_attempt_root/'music.wav', dtype='float32', always_2d=True)
    current_audio_tensor = torch.from_numpy(current_audio_samples.T.copy()).cuda()
    if current_sample_rate != current_separator_model.samplerate:
        current_audio_tensor = torchaudio.functional.resample(current_audio_tensor, current_sample_rate, current_separator_model.samplerate)
    current_mono_reference = current_audio_tensor.mean(0)
    current_audio_mean = current_mono_reference.mean()
    current_audio_scale = current_mono_reference.std()
    if not torch.isfinite(current_audio_scale) or current_audio_scale <= 1e-8:
        raise ValueError('MR 분리 입력이 무음이거나 유한하지 않습니다.')
    with torch.inference_mode():
        current_source_tensor = apply_model(current_separator_model, ((current_audio_tensor-current_audio_mean)/current_audio_scale)[None],
                                            device='cuda', shifts=1, split=True, overlap=0.25,
                                            segment=DEMUCS_SEGMENT_SECONDS, progress=True)[0]
    current_source_tensor = current_source_tensor*current_audio_scale+current_audio_mean
    current_vocal_index = current_separator_model.sources.index('vocals')
    current_output_tensors = {
        'vocals.wav':current_source_tensor[current_vocal_index],
        'mr.wav':sum(current_source_tensor[current_source_index] for current_source_index in range(len(current_separator_model.sources)) if current_source_index != current_vocal_index),
    }
    current_output_records = {}
    for current_output_name, current_output_tensor in current_output_tensors.items():
        if current_output_tensor.shape != current_audio_tensor.shape or not torch.isfinite(current_output_tensor).all():
            raise ValueError('분리 출력 길이·채널·유한값 계약 위반')
        current_output_path = current_attempt_root/current_output_name
        # FLOAT WAV로 저장하여 피크 클리핑·자동 음량 조절·페이드를 적용하지 않는다.
        soundfile.write(current_output_path, current_output_tensor.cpu().numpy().T, current_separator_model.samplerate, subtype='FLOAT')
        current_output_records[current_output_name] = {'sha256':calculate_music_checksum(current_output_path),
            'sample_rate':current_separator_model.samplerate, 'frames':current_output_tensor.shape[-1]}
    current_model_record.update(outputs=current_output_records, device='cuda', segment_seconds=DEMUCS_SEGMENT_SECONDS,
        method='drums+bass+other', quality_status='보컬 잔향·악기 손실 청취 검수 필요')
    return current_model_record


def encode_music_mp3(current_attempt_root):
    """WAV 원본을 유지하고 320kbps MP3를 추가 저장한다. 모델 추론은 아니다."""
    import lameenc
    import numpy
    import soundfile

    current_output_records = {}
    for current_audio_name in ('music', 'mr', 'vocals'):
        current_audio_samples, current_sample_rate = soundfile.read(current_attempt_root/(current_audio_name+'.wav'), dtype='float32', always_2d=True)
        if current_audio_samples.shape[1] != 2 or not numpy.isfinite(current_audio_samples).all():
            raise ValueError('MP3 입력의 스테레오·유한값 계약 위반')
        current_mp3_encoder = lameenc.Encoder()
        current_mp3_encoder.set_bit_rate(320)
        current_mp3_encoder.set_in_sample_rate(current_sample_rate)
        current_mp3_encoder.set_channels(2)
        current_mp3_encoder.set_quality(2)
        current_pcm_samples = numpy.rint(numpy.clip(current_audio_samples, -1, 1)*32767).astype('<i2')
        current_output_path = current_attempt_root/(current_audio_name+'.mp3')
        current_output_path.write_bytes(current_mp3_encoder.encode(current_pcm_samples.tobytes())+current_mp3_encoder.flush())
        current_output_records[current_audio_name] = {'filename':current_output_path.name, 'bitrate_kbps':320,
            'sha256':calculate_music_checksum(current_output_path)}
        print(f'MP3 저장 완료: {current_output_path} · 320kbps', flush=True)
    return current_output_records
