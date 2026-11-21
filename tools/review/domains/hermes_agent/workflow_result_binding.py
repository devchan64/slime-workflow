"""완료된 번역 시도의 텍스트를 후속 생성 요청에 고정한다."""
from hashlib import sha256


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
