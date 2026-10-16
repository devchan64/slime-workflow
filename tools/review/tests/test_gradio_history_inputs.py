"""결과 입력 조회의 스냅샷 검증과 초기화 계약."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from tools.review.common.gradio_history_inputs import collect_saved_input_view, describe_saved_prompt_counts, collect_saved_negative_prompt


class HistoryInputViewTests(unittest.TestCase):
    def test_reference_snapshot_and_mismatch(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory=Path(current_directory_name)
            current_reference_path=current_job_directory/'reference-1.png'
            Image.new('RGB',(2,2)).save(current_reference_path)
            current_request_record={'prompt':'Pose instruction.', 'seed':7, 'reference_snapshots':[{'path':'reference-1.png','sha256':hashlib.sha256(current_reference_path.read_bytes()).hexdigest()}]}
            current_history_record={'job_path':str(current_job_directory),'request':current_request_record}
            with patch('tools.review.common.gradio_history_inputs.GENERATION_INPUT_ROOT',current_job_directory):
                current_view_values=collect_saved_input_view(current_history_record)
                self.assertEqual(current_view_values[0],'Pose instruction.')
                self.assertEqual(current_view_values[1]['seed'],7)
                self.assertEqual(len(current_view_values[2]),1)
                current_link_view = collect_saved_input_view(current_history_record, 'http://127.0.0.1:8770', '/phantom')
                self.assertIn('/phantom/jobs/' + current_job_directory.name + '/reference-1.png', current_link_view[3])
                self.assertIn('target="_blank"', current_link_view[3])
                self.assertIn('noopener noreferrer', current_link_view[3])
                current_request_record['reference_snapshots'][0]['sha256']='wrong'
                current_view_values=collect_saved_input_view(current_history_record)
                self.assertEqual(current_view_values[2],[])
                self.assertIn('해시 불일치',current_view_values[3])
                self.assertNotIn('원본 열기', collect_saved_input_view(current_history_record, 'http://127.0.0.1:8770', '/phantom')[3])

    def test_display_uses_verified_bytes_when_file_changes(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory = Path(current_directory_name)
            current_reference_path = current_job_directory / 'reference-1.png'
            Image.new('RGB', (2, 2), 'red').save(current_reference_path)
            current_reference_bytes = current_reference_path.read_bytes()
            current_history_record = {'job_path': str(current_job_directory), 'request': {
                'reference_snapshots': [{'path': 'reference-1.png', 'sha256': hashlib.sha256(current_reference_bytes).hexdigest()}]}}

            def read_then_replace_reference(current_source_path):
                self.assertEqual(current_source_path, current_reference_path)
                Image.new('RGB', (2, 2), 'blue').save(current_reference_path)
                return current_reference_bytes

            with patch('tools.review.common.gradio_history_inputs.GENERATION_INPUT_ROOT', current_job_directory), patch.object(Path, 'read_bytes', read_then_replace_reference):
                current_view_values = collect_saved_input_view(current_history_record)
            self.assertEqual(current_view_values[2][0][0].getpixel((0, 0)), (255, 0, 0))
            with Image.open(current_reference_path) as current_changed_image:
                self.assertEqual(current_changed_image.getpixel((0, 0)), (0, 0, 255))

    def test_job_directory_link_cannot_display_other_job_reference(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root = Path(current_directory_name)
            current_other_directory = current_storage_root / 'other-job'
            current_other_directory.mkdir()
            current_reference_path = current_other_directory / 'reference-1.png'
            Image.new('RGB', (2, 2)).save(current_reference_path)
            current_reference_bytes = current_reference_path.read_bytes()
            current_selected_directory = current_storage_root / 'selected-job'
            current_selected_directory.symlink_to(current_other_directory, target_is_directory=True)
            current_history_record = {'job_path': str(current_selected_directory), 'request': {'reference_snapshots': [{'path': 'reference-1.png', 'sha256': hashlib.sha256(current_reference_bytes).hexdigest()}]}}
            with patch('tools.review.common.gradio_history_inputs.GENERATION_INPUT_ROOT', current_storage_root):
                current_view_values = collect_saved_input_view(current_history_record, 'http://127.0.0.1:8770', '/phantom')
            self.assertEqual(current_view_values[2], [])
            self.assertIn('심볼릭 링크', current_view_values[3])
            self.assertNotIn('원본 열기', current_view_values[3])
            self.assertEqual(current_reference_path.read_bytes(), current_reference_bytes)

    def test_selected_identifier_must_match_reference_directory(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root = Path(current_directory_name)
            current_other_directory = current_storage_root / 'other-job'
            current_other_directory.mkdir()
            current_reference_path = current_other_directory / 'reference-1.png'
            Image.new('RGB', (2, 2)).save(current_reference_path)
            current_history_record = {'id': 'selected-job', 'job_path': str(current_other_directory), 'request': {
                'reference_snapshots': [{'path': 'reference-1.png', 'sha256': hashlib.sha256(current_reference_path.read_bytes()).hexdigest()}]}}
            with patch('tools.review.common.gradio_history_inputs.GENERATION_INPUT_ROOT', current_storage_root):
                current_view_values = collect_saved_input_view(current_history_record, 'http://127.0.0.1:8770', '/phantom')
                self.assertEqual(current_view_values[2], [])
                self.assertIn('생성 ID', current_view_values[3])
                self.assertNotIn('<a ', current_view_values[3])
                current_history_record['id'] = 'other-job'
                self.assertEqual(len(collect_saved_input_view(current_history_record)[2]), 1)

    def test_reset_and_no_reference(self):
        self.assertEqual(collect_saved_input_view({}),('',{},[],''))
        self.assertEqual(collect_saved_input_view({'request':{'steps':40}}),('',{'steps':40},[],''))

    def test_outside_path_not_read(self):
        current_history_record={'job_path':'/etc','request':{'reference_snapshots':[{'path':'passwd','sha256':'x'}]}}
        self.assertIn('허용된',collect_saved_input_view(current_history_record)[3])

    def test_saved_final_prompt_precedes_original_without_rebuilding(self):
        current_history_record = {'request': {'prompt': 'flute', 'final_prompt': 'flute old saved suffix', 'final_prompt_words': 999}}
        self.assertEqual(collect_saved_input_view(current_history_record)[0], 'flute old saved suffix')
        self.assertEqual(describe_saved_prompt_counts(current_history_record), '저장 원문 1단어 · 저장 최종 입력 4단어')
        self.assertIn('별도 최종 문구 기록 없음', describe_saved_prompt_counts({'request': {'prompt': '  flute\n calm  '}}))
        self.assertIn('원문 2단어', describe_saved_prompt_counts({'request': {'prompt': '  flute\n calm  '}}))
        self.assertEqual(describe_saved_prompt_counts({}), '')
        self.assertIn('최종 입력 0단어', describe_saved_prompt_counts({'request': {'final_prompt': ''}}))

    def test_saved_negative_prompt_preserves_empty_runtime_value(self):
        for current_model_name in ('vace', 'phantom'):
            current_history_record = {'request': {'negative_prompt': 'outer stale text', current_model_name: {'negative_prompt': ''}}}
            self.assertEqual(collect_saved_negative_prompt(current_history_record), '')
            current_history_record['request'][current_model_name]['negative_prompt'] = 'blurred details'
            self.assertEqual(collect_saved_negative_prompt(current_history_record), 'blurred details')
        self.assertIsNone(collect_saved_negative_prompt({}))
        self.assertEqual(collect_saved_negative_prompt({'request': {'negative_prompt': 'saved text'}}), 'saved text')

    def test_negative_prompt_counts_use_saved_runtime_configuration(self):
        for current_model_name in ('vace', 'phantom'):
            current_history_record = {'request': {'prompt': 'moving figure', 'negative_prompt': 'stale outer value', current_model_name: {'negative_prompt': 'blurred details'}}}
            self.assertIn('저장 부정 입력 2단어', describe_saved_prompt_counts(current_history_record))
        self.assertIn('저장 부정 입력 0단어', describe_saved_prompt_counts({'request': {'negative_prompt': ''}}))
        self.assertNotIn('저장 부정 입력', describe_saved_prompt_counts({'request': {'prompt': 'figure'}}))

    def test_qwen_option_history_counts_original_and_saved_addition(self):
        current_history_record = {'request': {'prompt': 'figure historical style', 'qwen21': {'user_prompt': 'figure', 'additional_prompt': 'historical style'}}}
        self.assertEqual(collect_saved_input_view(current_history_record)[0], 'figure historical style')
        self.assertEqual(describe_saved_prompt_counts(current_history_record), '저장 원문 1단어 · 저장 추가 문구 2단어 · 저장 최종 입력 3단어')
        current_history_record['request']['qwen21'] = {'user_prompt': 'figure', 'additional_prompt': ''}
        current_history_record['request']['prompt'] = 'figure'
        self.assertIn('저장 추가 문구 0단어', describe_saved_prompt_counts(current_history_record))

    def test_circular_history_preserves_original_and_final_counts(self):
        from tools.review.domains.image.qwen_circular_generation import QwenCircularGenerationManager
        current_request_record = QwenCircularGenerationManager().validate_generation_request({'action': 'generate', 'images': [], 'prompt': 'grass', 'width': 512, 'height': 512, 'steps': 40, 'seed': 42, 'soft_shading': True, 'pattern_view': True})
        current_history_record = {'request': current_request_record}
        self.assertEqual(describe_saved_prompt_counts(current_history_record), '저장 원문 1단어 · 저장 최종 입력 10단어')
        self.assertEqual(collect_saved_input_view(current_history_record)[0], current_request_record['prompt'])
        current_request_record['user_prompt'] = ''
        current_request_record['prompt'] = 'historical saved pattern'
        self.assertEqual(describe_saved_prompt_counts(current_history_record), '저장 원문 0단어 · 저장 최종 입력 3단어')

class HistoryStageInputTests(unittest.TestCase):
    def test_corrupt_stage_request_is_not_presented_as_saved_prompt(self):
        from tools.review.common.gradio_history_inputs import collect_saved_stage_prompts
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory = Path(current_directory_name)
            current_stage_directory = current_job_directory / 'stage-3-horizontal'
            current_stage_directory.mkdir()
            current_history_record = {'job_path': str(current_job_directory), 'request': {'seamless_tile': {'schema_version': 7}}}
            with patch('tools.review.common.gradio_history_inputs.GENERATION_INPUT_ROOT', current_job_directory):
                for current_request_text in (
                    '{"prompt":"first","prompt":"misleading prompt"}',
                    '{"prompt":"misleading prompt","settings":{"seed":1,"seed":2}}',
                    '{"prompt":"misleading prompt","seed":NaN}',
                    '{"prompt":"misleading prompt","seed":Infinity}',
                    '{"prompt":"misleading prompt","seed":-Infinity}',
                ):
                    with self.subTest(request=current_request_text):
                        (current_stage_directory / 'request.json').write_text(current_request_text)
                        current_display_text = collect_saved_stage_prompts(current_history_record)
                        self.assertIn('3단계 · 실행 요청 읽기 실패:', current_display_text)
                        self.assertNotIn('misleading prompt', current_display_text)

    def test_stage_view_uses_execution_request_instead_of_original_plan(self):
        import json
        from tools.review.common.gradio_history_inputs import collect_saved_stage_prompts
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory = Path(current_directory_name)
            current_stage_directory = current_job_directory/'stage-3-horizontal'
            current_stage_directory.mkdir()
            (current_stage_directory/'request.json').write_text(json.dumps({'prompt':'actual saved correction'}))
            current_history_record = {'job_path':str(current_job_directory), 'request':{'seamless_tile':{'schema_version':6,'stage_prompts':['old','retired plan','old']}}}
            with patch('tools.review.common.gradio_history_inputs.GENERATION_INPUT_ROOT',current_job_directory):
                current_stage_text = collect_saved_stage_prompts(current_history_record)
                self.assertIn('3단계 · 저장 실행 입력 3단어\nactual saved correction',current_stage_text)
                current_history_record['id'] = 'different-job'
                current_rejected_text = collect_saved_stage_prompts(current_history_record)
                self.assertIn('생성 ID', current_rejected_text)
                self.assertNotIn('actual saved correction', current_rejected_text)
                current_history_record['id'] = current_job_directory.name
                self.assertEqual(collect_saved_stage_prompts(current_history_record), current_stage_text)
                self.assertIn('1단계 · 실행 요청 기록 없음',current_stage_text)
                self.assertNotIn('retired plan',current_stage_text)
                (current_stage_directory/'request.json').write_text('{}')
                self.assertIn('prompt 문자열 누락',collect_saved_stage_prompts(current_history_record))
                (current_stage_directory/'request.json').unlink()
                (current_stage_directory/'request.json').symlink_to(current_job_directory/'outside.json')
                self.assertIn('심볼릭 링크',collect_saved_stage_prompts(current_history_record))
        self.assertEqual(collect_saved_stage_prompts({}), '')
        self.assertIn('허용된 작업 폴더',collect_saved_stage_prompts({'job_path':'/etc','request':{'seamless_tile':{'schema_version':7}}}))

    def test_separation_preserves_both_saved_requests_and_counts(self):
        from tools.review.common.gradio_history_inputs import collect_saved_stage_prompts
        current_history_record = {'request':{'schema_version':2,'prompt':'saved base instruction','outfit_prompt':'saved garment instruction','outfit_prompt_word_count':999}}
        current_stage_text = collect_saved_stage_prompts(current_history_record)
        self.assertEqual(current_stage_text, '신체 베이스 · 저장 요청 3단어\nsaved base instruction\n\n복장 · 저장 요청 3단어\nsaved garment instruction')
        current_history_record['request']['outfit_prompt'] = ''
        self.assertIn('복장 · 저장 요청 0단어', collect_saved_stage_prompts(current_history_record))
        current_history_record['request']['outfit_prompt'] = None
        self.assertIn('복장 · 저장 요청 문구 없음', collect_saved_stage_prompts(current_history_record))
