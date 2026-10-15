"""Qwen 2511 Gradio 입력·이력 복원 계약을 검증한다."""
import unittest
import io
import hashlib
from pathlib import Path
import tempfile
import gradio as gr
from PIL import Image

from tools.review.ui.gradio import qwen_2511_app


class Qwen2511GradioTests(unittest.TestCase):
    def test_restore_rejects_cross_job_reference_links(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_storage_directory = Path(current_temporary_directory)
            current_generation_identifier = '2026-10-15_13-00-00-1234abcd'
            current_selected_directory = current_storage_directory/current_generation_identifier
            current_selected_directory.mkdir()
            current_other_directory = current_storage_directory/'other-job'
            current_other_directory.mkdir()
            current_other_reference = current_other_directory/'reference-1.png'
            Image.new('RGB', (8, 8), 'red').save(current_other_reference)
            current_reference_record = {'id': current_generation_identifier, 'request': {'reference_snapshots': [
                {'path': 'reference-1.png', 'sha256': hashlib.sha256(current_other_reference.read_bytes()).hexdigest()}
            ]}}
            current_selected_reference = current_selected_directory/'reference-1.png'
            current_selected_reference.symlink_to(current_other_reference)
            with self.assertRaisesRegex(gr.Error, '선택한 작업 폴더 밖'):
                qwen_2511_app.restore_reference_inputs(current_reference_record, current_storage_directory)
            current_selected_reference.unlink()
            current_selected_directory.rmdir()
            current_selected_directory.symlink_to(current_other_directory, target_is_directory=True)
            with self.assertRaisesRegex(gr.Error, '작업 폴더는 심볼릭 링크'):
                qwen_2511_app.restore_reference_inputs(current_reference_record, current_storage_directory)
            self.assertTrue(current_other_reference.is_file())

    def test_reference_request_trims_history_tag(self):
        request_payload_value=qwen_2511_app.build_reference_request('마을 입구',' 돌온재 ',[],512,768,4,10107)
        self.assertEqual(request_payload_value['tag'],'돌온재')

    def test_restore_reference_inputs_uses_saved_settings_without_files(self):
        restored_input_values=qwen_2511_app.restore_reference_inputs({'request':{'prompt':'마을 입구','tag':'돌온재','width':512,'height':768,'steps':30,'seed':42}})
        self.assertEqual(restored_input_values[:6],('마을 입구','돌온재',512,768,30,42))
        self.assertIn('참조 이미지',restored_input_values[-1])

    def test_invalid_reference_reports_slot_and_actual_dimensions(self):
        with self.assertRaisesRegex(gr.Error,'참조 이미지 2: 1024×768'):
            qwen_2511_app.prepare_reference_image_bytes((None,Image.new('L',(1024,768)),None))

    def test_transparent_reference_reports_actionable_error(self):
        with self.assertRaisesRegex(gr.Error,'투명 이미지는 배경을 합성'):
            qwen_2511_app.prepare_reference_image_bytes((Image.new('RGBA',(512,512),(0,0,0,0)),))

    def test_valid_reference_preserves_pixels_and_order(self):
        reference_bytes_values=qwen_2511_app.prepare_reference_image_bytes((Image.new('RGB',(464,455),'red'),None,Image.new('RGB',(512,512),'blue')))
        self.assertEqual(len(reference_bytes_values),2)
        self.assertEqual([Image.open(io.BytesIO(current_image_bytes)).getpixel((0,0)) for current_image_bytes in reference_bytes_values],[(255,0,0),(0,0,255)])
