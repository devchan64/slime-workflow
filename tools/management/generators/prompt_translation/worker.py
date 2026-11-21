"""공용 대기열의 ROCm 작업자로 TranslateGemma를 실행한다."""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import sys
import traceback

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.prompt_translation.prepare import calculate_file_sha256, resolve_translation_snapshot
from generators.prompt_translation.terms import compare_translation_terms
from generators.prompt_translation.quality_checks import inspect_translation_quality
from generators.prompt_translation.semantic_review import find_negated_source_clauses
from tools.management.common.generation_records import write_record_atomically
from tools.management.domains.translation.service import TRANSLATION_JOB_ROOT, TRANSLATION_MODEL_ROOT, TRANSLATION_JOB_PATTERN


def resolve_translation_target_code(translation_target_language):
    return {'en': 'en', 'zh-CN': 'zh-Hans'}[translation_target_language]


def execute_translation_worker(translation_job_path):
    if translation_job_path.is_symlink() or translation_job_path.resolve().parent != TRANSLATION_JOB_ROOT.resolve() or not TRANSLATION_JOB_PATTERN.fullmatch(translation_job_path.name):
        raise ValueError('번역 작업 경로 오류')
    try:
        translation_request_record = json.loads((translation_job_path / 'request.json').read_text(encoding='utf-8'))
        translation_manifest_record = json.loads((TRANSLATION_MODEL_ROOT / 'manifest.json').read_text(encoding='utf-8'))
        if translation_manifest_record['model_id'] != 'google/translategemma-4b-it':
            raise ValueError('번역 모델 ID 오류')
        translation_snapshot_path = resolve_translation_snapshot(TRANSLATION_MODEL_ROOT, translation_manifest_record)
        for translation_relative_path, translation_expected_hash in translation_manifest_record['files'].items():
            translation_file_path = translation_snapshot_path / translation_relative_path
            if Path(translation_relative_path).is_absolute() or '..' in Path(translation_relative_path).parts or calculate_file_sha256(translation_file_path) != translation_expected_hash:
                raise ValueError('모델 파일 해시 검증 실패: ' + translation_relative_path)
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        if not torch.version.hip or not torch.cuda.is_available():
            raise RuntimeError('ROCm GPU를 사용할 수 없습니다.')
        translation_processor_value = AutoProcessor.from_pretrained(translation_snapshot_path, local_files_only=True)
        translation_model_value = AutoModelForImageTextToText.from_pretrained(translation_snapshot_path, local_files_only=True, torch_dtype=torch.bfloat16).to('cuda').eval()
        translation_target_code = resolve_translation_target_code(translation_request_record['target_language'])
        translation_message_values = [{'role': 'user', 'content': [{'type': 'text', 'source_lang_code': 'ko', 'target_lang_code': translation_target_code, 'text': translation_request_record['text']}]}]
        translation_input_values = translation_processor_value.apply_chat_template(translation_message_values, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors='pt').to('cuda')
        translation_input_length = translation_input_values['input_ids'].shape[-1]
        if translation_input_length > 1536:
            raise ValueError('입력 토큰이 1536개를 초과했습니다. 원문을 줄여 주세요.')
        with torch.inference_mode():
            translation_output_values = translation_model_value.generate(**translation_input_values, max_new_tokens=min(512, 2048-translation_input_length), do_sample=False)
        translation_generated_tokens = translation_output_values[0][translation_input_length:]
        translation_output_limit = min(512, 2048-translation_input_length)
        translation_eos_value = translation_model_value.generation_config.eos_token_id
        translation_eos_values = translation_eos_value if isinstance(translation_eos_value, list) else [translation_eos_value]
        if len(translation_generated_tokens) >= translation_output_limit and int(translation_generated_tokens[-1]) not in translation_eos_values:
            raise ValueError('출력 토큰 제한에 도달했습니다. 원문을 줄여 주세요.')
        translation_result_text = translation_processor_value.decode(translation_generated_tokens, skip_special_tokens=True).strip()
        if not translation_result_text:
            raise ValueError('번역 결과가 비어 있습니다.')
        translation_check_values = compare_translation_terms(translation_request_record['text'], translation_result_text, translation_request_record.get('check_terms', []))
        translation_quality_values = inspect_translation_quality(translation_request_record['text'], translation_result_text, translation_request_record['target_language'])
        del translation_model_value, translation_input_values, translation_output_values, translation_generated_tokens
        gc.collect()
        torch.cuda.empty_cache()
        if find_negated_source_clauses(translation_request_record['text']):
            try:
                translation_review_process = subprocess.Popen([str(WORKFLOW_ROOT_DIRECTORY / '.venv/bin/python'), str(WORKFLOW_ROOT_DIRECTORY / 'generators/prompt_translation/semantic_review.py'), str(translation_job_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=WORKFLOW_ROOT_DIRECTORY)
                try:
                    translation_review_output, translation_review_errors = translation_review_process.communicate(json.dumps({'source': translation_request_record['text'], 'translation': translation_result_text, 'language': translation_request_record['target_language']}, ensure_ascii=False), timeout=240)
                except subprocess.TimeoutExpired:
                    translation_review_process.terminate()
                    translation_review_process.communicate(timeout=20)
                    raise RuntimeError('의미 검토 시간 초과')
                if translation_review_process.returncode:
                    raise RuntimeError('작가 AI 의미 검토 실행 실패: ' + translation_review_errors[-500:])
                translation_quality_values.extend(json.loads(translation_review_output))
            except Exception as translation_review_error:
                translation_quality_values.append({'source': '부정 표현 의미 검토', 'target': '검토 미완료: ' + str(translation_review_error), 'status': 'review', 'source_ref': '작가 AI 의미 검토'})
        write_record_atomically(translation_job_path / 'result.json', {'text': translation_result_text, 'model_id': translation_manifest_record['model_id'], 'revision': translation_manifest_record['revision'], 'files': translation_manifest_record['files'], 'dtype': 'bfloat16', 'term_checks': translation_check_values, 'quality_checks': translation_quality_values})
        write_record_atomically(translation_job_path / 'status.json', {'status': 'completed'})
    except Exception as translation_worker_error:
        traceback.print_exc()
        write_record_atomically(translation_job_path / 'status.json', {'status': 'failed', 'error': str(translation_worker_error)})
        raise


if __name__ == '__main__':
    translation_argument_parser = argparse.ArgumentParser(description=__doc__)
    translation_argument_parser.add_argument('--job-dir', type=Path, required=True)
    execute_translation_worker(translation_argument_parser.parse_args().job_dir)
