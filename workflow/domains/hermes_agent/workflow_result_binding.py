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


def read_workflow_effect_audio(source_storage_root, source_job_identifier, observed_job_record):
    from .delegation_store import read_bounded_delegation_record, validate_service_job_identifier
    from .media_result_paths import validate_hermes_audio_result_path
    import os
    import stat

    source_service_name = "sfx-dasheng-audiogen"
    if not validate_service_job_identifier(source_service_name, source_job_identifier):
        raise ValueError("효과음 원 작업 ID가 잘못되었습니다.")
    source_audio_path = validate_hermes_audio_result_path(source_service_name, source_job_identifier, observed_job_record)
    if source_audio_path is None:
        raise ValueError("완료된 효과음 시도의 결과 경로가 필요합니다.")
    source_attempt_identifier = source_audio_path.split("/")[-2]
    source_job_directory = source_storage_root / source_job_identifier
    local_audio_path = source_job_directory / "attempts" / source_attempt_identifier / "sound.wav"
    if local_audio_path.resolve(strict=True) != local_audio_path.absolute():
        raise ValueError("효과음 원본 경로를 확인하세요.")
    status_record_path = source_job_directory / "status.json"
    result_record_path = source_job_directory / "result.json"
    source_status_record = read_bounded_delegation_record(status_record_path)
    source_result_record = read_bounded_delegation_record(result_record_path)
    if not isinstance(source_status_record, dict) or source_status_record.get("status") != "completed" or not isinstance(source_result_record, dict):
        raise ValueError("효과음 원 서비스의 완료 기록이 필요합니다.")
    with os.fdopen(os.open(local_audio_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as audio_file_handle:
        if not stat.S_ISREG(os.fstat(audio_file_handle.fileno()).st_mode):
            raise ValueError("효과음 결과는 일반 파일이어야 합니다.")
        maximum_audio_bytes = 4 * 1024 * 1024
        audio_content_bytes = audio_file_handle.read(maximum_audio_bytes + 1)
    if len(audio_content_bytes) > maximum_audio_bytes:
        raise ValueError("워크플로우 효과음 보존 한도는 파일당 4 MiB입니다.")
    validate_workflow_effect_audio(audio_content_bytes, source_result_record, source_attempt_identifier)
    if (read_bounded_delegation_record(status_record_path) != source_status_record
            or read_bounded_delegation_record(result_record_path) != source_result_record):
        raise ValueError("효과음 검증 중 원 서비스의 시도 기록이 변경되었습니다.")
    return audio_content_bytes
