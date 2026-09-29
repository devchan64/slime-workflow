"""시스템 Python 변경과 의존성 누락을 접수 전에 거절한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
from tools.review.domains.image.image_runtime import validate_image_runtime


class ImageRuntimeValidationTests(unittest.TestCase):
    def verify_runtime_probe(self, current_python_version, missing_module_names):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            environment_root_path = Path(temporary_root_name)
            (environment_root_path/'pyvenv.cfg').write_text('version = 3.12.3\n')
            with patch('tools.review.domains.image.image_runtime.subprocess.run', return_value=CompletedProcess([], 0, json.dumps({'version':current_python_version,'missing':missing_module_names}))):
                validate_image_runtime(environment_root_path)

    def test_reject_changed_interpreter(self):
        with self.assertRaisesRegex(ValueError, '필요 Python 3.12, 현재 3.14'):
            self.verify_runtime_probe('3.14', ['torch'])

    def test_reject_missing_dependency(self):
        with self.assertRaisesRegex(ValueError, '의존성 누락.*torch'):
            self.verify_runtime_probe('3.12', ['torch'])

    def test_accept_compatible_runtime(self):
        self.verify_runtime_probe('3.12', [])
