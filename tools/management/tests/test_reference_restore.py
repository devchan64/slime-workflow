"""공유 참조 이미지 복원 시 저장 데이터와 파일 경계를 검증한다."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from tools.management.common.reference_restore import HistoryInputError, restore_reference_inputs


class ReferenceRestoreTests(unittest.TestCase):
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
            with self.assertRaisesRegex(HistoryInputError, '선택한 작업 폴더 밖'):
                restore_reference_inputs(current_reference_record, current_storage_directory)
            current_selected_reference.unlink()
            current_selected_directory.rmdir()
            current_selected_directory.symlink_to(current_other_directory, target_is_directory=True)
            with self.assertRaisesRegex(HistoryInputError, '작업 폴더는 심볼릭 링크'):
                restore_reference_inputs(current_reference_record, current_storage_directory)
            self.assertTrue(current_other_reference.is_file())

    def test_restore_rejects_incomplete_reference_metadata(self):
        current_reference_names = ['reference-1.png', 'reference-2.png']
        for current_snapshot_records in ([], None, [{'path': 'reference-1.png'}], [{'path': 'reference-2.png'}, {'path': 'reference-1.png'}], ['invalid']):
            with self.subTest(snapshots=current_snapshot_records):
                with self.assertRaises(HistoryInputError):
                    restore_reference_inputs({'request': {
                        'references': current_reference_names,
                        'reference_snapshots': current_snapshot_records,
                    }})

    def test_restore_rejects_malformed_records_before_file_read(self):
        from unittest.mock import patch
        current_invalid_records=[None,[],{'request':None},{'request':[]},
            {'request':{'references':'reference-1.png'}},
            {'request':{'references':[None]}},
            {'request':{'reference_snapshots':{}}},
            {'request':{'reference_snapshots':['invalid']}},
            {'request':{'reference_snapshots':[{}]}},
            {'request':{'reference_snapshots':[{'path':'reference-1.png','sha256':123}]}},
            {'request':{'reference_snapshots':[{'path':'reference-1.png','sha256':'bad'}]}},
            {'id':[], 'request':{'reference_snapshots':[{'path':'reference-1.png','sha256':'a'*64}]}}]
        with patch.object(Path,'read_bytes') as current_read_mock:
            for current_history_record in current_invalid_records:
                with self.subTest(record=current_history_record), self.assertRaises(HistoryInputError):
                    restore_reference_inputs(current_history_record)
            current_read_mock.assert_not_called()

    def test_restore_rejects_invalid_setting_types_before_file_read(self):
        from copy import deepcopy
        from unittest.mock import patch
        for current_setting_name, current_invalid_values in (
            ('prompt', (None, [], 42)), ('tag', (None, {}, True)),
            *((current_setting_name, (None, '512', True, 1.5, float('nan'))) for current_setting_name in ('width', 'height', 'steps', 'seed')),
        ):
            for current_invalid_value in current_invalid_values:
                with self.subTest(setting=current_setting_name, value=current_invalid_value):
                    current_history_record = {'request': {current_setting_name: current_invalid_value}}
                    current_original_record = deepcopy(current_history_record)
                    with patch.object(Path, 'read_bytes') as current_file_reader, self.assertRaisesRegex(HistoryInputError, current_setting_name):
                        restore_reference_inputs(current_history_record)
                    current_file_reader.assert_not_called()
                    self.assertEqual(current_history_record, current_original_record)

    def test_restore_reference_inputs_uses_saved_settings_without_files(self):
        restored_input_values=restore_reference_inputs({'request':{'prompt':'마을 입구','tag':'돌온재','width':512,'height':768,'steps':30,'seed':42}})
        self.assertEqual(restored_input_values[:6],('마을 입구','돌온재',512,768,30,42))
        self.assertIn('참조 이미지',restored_input_values[-1])
