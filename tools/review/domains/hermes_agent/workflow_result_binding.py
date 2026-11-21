"""완료된 번역 시도의 텍스트를 후속 생성 요청에 고정한다."""
from hashlib import sha256
from io import BytesIO
import wave


def bind_translation_prompt_input(translation_status_record, expected_job_identifier, consumer_request_record):
    receipt_status_record = translation_status_record.get("receipt", {})
    source_job_record = translation_status_record.get("job", {})
    if (not expected_job_identifier or receipt_status_record.get("job_id") != expected_job_identifier
            or source_job_record.get("id", expected_job_identifier) != expected_job_identifier):
        raise ValueError("번역 작업 식별자가 일치하지 않습니다.")
    if receipt_status_record.get("state") != "accepted" or source_job_record.get("status") != "completed":
        raise ValueError("번역 완료 확인이 필요합니다.")
    source_result_record = source_job_record.get("result")
    translated_prompt_text = source_result_record.get("text") if isinstance(source_result_record, dict) else None
    if not isinstance(translated_prompt_text, str) or not translated_prompt_text.strip():
        raise ValueError("연결할 번역 결과가 없습니다.")
    if "prompt" in consumer_request_record:
        raise ValueError("프롬프트 고정값과 결과 연결을 동시에 지정했습니다.")
    return {
        "request": {**consumer_request_record, "prompt": translated_prompt_text},
        "source": {
            "service": "prompt-translation",
            "job_id": expected_job_identifier,
            "output": "text",
            "sha256": sha256(translated_prompt_text.encode("utf-8")).hexdigest(),
        },
    }


def validate_workflow_effect_audio(audio_content_bytes, source_result_record, expected_attempt_identifier):
    """Dasheng 결과 원장의 시도·파일 지문과 실제 모노 PCM16 프레임을 대조한다."""
    if (source_result_record.get("attempt") != expected_attempt_identifier or source_result_record.get("format") != "wav"
            or source_result_record.get("output_sha256") != sha256(audio_content_bytes).hexdigest()):
        raise ValueError("효과음 생성 시도 또는 WAV 해시가 일치하지 않습니다.")
    try:
        with wave.open(BytesIO(audio_content_bytes), "rb") as current_audio_stream:
            audio_frame_count = current_audio_stream.getnframes()
            if (current_audio_stream.getnchannels() != 1 or current_audio_stream.getsampwidth() != 2
                    or current_audio_stream.getframerate() != 16000 or current_audio_stream.getcomptype() != "NONE"
                    or source_result_record.get("channels") != 1 or source_result_record.get("sample_rate") != 16000
                    or audio_frame_count < 1 or len(current_audio_stream.readframes(audio_frame_count)) != audio_frame_count * 2):
                raise ValueError("효과음 결과는 16 kHz 모노 PCM16 WAV여야 합니다.")
    except (EOFError, wave.Error) as invalid_audio_error:
        raise ValueError("효과음 WAV 헤더 또는 데이터가 손상되었습니다.") from invalid_audio_error
