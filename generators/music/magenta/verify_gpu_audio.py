"""검증된 스타일 토큰으로 JAX CUDA 음악·디코더의 짧은 출력만 검증한다."""
from pathlib import Path
import os
import sys
os.environ['JAX_PLATFORMS']='cuda'
os.environ['XLA_PYTHON_CLIENT_PREALLOCATE']='false'
WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


def verify_magenta_audio():
    import numpy
    import jax
    from magenta_rt import MagentaRT2Jax, paths
    from magenta_rt.config import MUSICCOCA
    current_output_directory=WORKFLOW_ROOT_DIRECTORY/'.tmp/test/magenta-gpu-audio/queued-validation'
    current_output_directory.mkdir(parents=True,exist_ok=True)
    current_metrics_recorder=GenerationTelemetryRecorder(current_output_directory,5,[])
    current_metrics_recorder.start_generation_telemetry()
    current_final_status='failed'
    try:
        if not jax.devices() or any(current_device_value.platform!='gpu' for current_device_value in jax.devices()):
            raise RuntimeError('JAX CUDA 장치가 필요합니다.')
        print('CUDA devices='+str(jax.devices()),flush=True)
        current_style_tokens=numpy.load(WORKFLOW_ROOT_DIRECTORY/'.tmp/test/magenta-gpu-encoder/pretrained_vector_quantizer-outputs.npz')['arr_0'].flatten().tolist()
        if len(current_style_tokens)!=12 or not all(0<=current_token_value<1024 for current_token_value in current_style_tokens):
            raise ValueError('스타일 토큰 계약 오류')
        paths.set_magenta_home(WORKFLOW_ROOT_DIRECTORY/'.model/music/music-magenta/source')
        current_metrics_recorder.update_generation_stage('load')
        current_music_model=MagentaRT2Jax(size='mrt2_small')
        current_audio_state=None
        current_audio_chunks=[]
        current_metrics_recorder.update_generation_stage('inference')
        for current_step_number in range(5):
            current_audio_wave,current_audio_state=current_music_model.generate(conditioning={MUSICCOCA.key:current_style_tokens},frames=25,state=current_audio_state)
            current_audio_chunks.append(current_audio_wave.samples)
            current_metrics_recorder.record_generation_step(current_step_number+1)
        import soundfile
        current_output_samples=numpy.concatenate(current_audio_chunks,axis=0)
        if current_output_samples.shape!=(240000,2) or not numpy.isfinite(current_output_samples).all():
            raise ValueError(f'WAV 출력 계약 위반: {current_output_samples.shape}')
        soundfile.write(current_output_directory/'music.wav',current_output_samples,48000,subtype='PCM_16')
        current_final_status='completed'
        print('완료: '+str(current_output_directory/'music.wav'),flush=True)
    finally:
        current_metrics_recorder.finish_generation_telemetry(current_final_status)


if __name__=='__main__':
    verify_magenta_audio()
