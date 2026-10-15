"""결과 입력 조회의 스냅샷 검증과 초기화 계약."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from tools.review.common.gradio_history_inputs import collect_saved_input_view, describe_saved_prompt_counts


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
