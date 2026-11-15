import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.review.domains.translation import service
from tools.review.common.management_gateway import resolve_management_command, identify_management_command


class TranslationServiceTests(unittest.TestCase):
    def test_gateway_round_trip(self):
        for translation_command_name, translation_payload_record in [('translation-submit', {'text': '나무', 'target_language': 'en'}), ('translation-status', {'id': '2026-11-15_12-00-00-12345678'}), ('translation-history', {})]:
            translation_method_value, translation_route_value = resolve_management_command('prompt-translation', translation_command_name, translation_payload_record)
            self.assertEqual(identify_management_command(translation_route_value, translation_method_value, translation_payload_record), ('prompt-translation', translation_command_name, translation_payload_record))

    def test_queue_preserves_original_and_checks_input(self):
        with tempfile.TemporaryDirectory() as translation_temp_directory:
            translation_temp_path = Path(translation_temp_directory)
            translation_manager_value = service.TranslationServiceManager()
            translation_manager_value.job_storage_root = translation_temp_path / 'jobs'
            (translation_temp_path / 'model').mkdir()
            (translation_temp_path / 'model' / 'manifest.json').write_text('{}')
            (translation_temp_path / 'python').touch()
            with patch.object(service, 'TRANSLATION_MODEL_ROOT', translation_temp_path / 'model'), patch.object(service, 'TRANSLATION_PYTHON_PATH', translation_temp_path / 'python'), patch.object(service, 'launch_gpu_process') as translation_launch_mock:
                for translation_bad_payload in ({'text': '', 'target_language': 'en'}, {'text': '나무', 'target_language': 'ja'}, {'text': '나무', 'target_language': 'en', 'extra': 1}):
                    with self.assertRaises(ValueError):
                        translation_manager_value.execute_translation_command('translation-submit', translation_bad_payload)
                translation_submission_value = translation_manager_value.execute_translation_command('translation-submit', {'text': '나무', 'target_language': 'zh-CN'})
                translation_job_path = translation_manager_value.job_storage_root / translation_submission_value['id']
                self.assertEqual(json.loads((translation_job_path / 'request.json').read_text())['text'], '나무')
                self.assertEqual(translation_launch_mock.call_args.args[2], 'prompt-translation')
                (translation_job_path / 'status.json').write_text('{"status":"completed"}')
                (translation_job_path / 'result.json').write_text('{"text":"树"}')
                self.assertEqual(translation_manager_value.execute_translation_command('translation-status', {'id': translation_submission_value['id']})['result']['text'], '树')
                self.assertEqual(len(translation_manager_value.execute_translation_command('translation-history', {})['records']), 1)
                with self.assertRaises(ValueError):
                    translation_manager_value.execute_translation_command('translation-status', {'id': '../outside'})


if __name__ == '__main__':
    unittest.main()
