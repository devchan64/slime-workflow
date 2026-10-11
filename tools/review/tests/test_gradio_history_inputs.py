"""결과 입력 조회의 스냅샷 검증과 초기화 계약."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from tools.review.common.gradio_history_inputs import collect_saved_input_view


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
                current_request_record['reference_snapshots'][0]['sha256']='wrong'
                current_view_values=collect_saved_input_view(current_history_record)
                self.assertEqual(current_view_values[2],[])
                self.assertIn('해시 불일치',current_view_values[3])

    def test_reset_and_no_reference(self):
        self.assertEqual(collect_saved_input_view({}),('',{},[],''))
        self.assertEqual(collect_saved_input_view({'request':{'steps':40}}),('',{'steps':40},[],''))

    def test_outside_path_not_read(self):
        current_history_record={'job_path':'/etc','request':{'reference_snapshots':[{'path':'passwd','sha256':'x'}]}}
        self.assertIn('허용된',collect_saved_input_view(current_history_record)[3])
