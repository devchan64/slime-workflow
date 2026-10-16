"""회귀 실행기의 종료 출력 보존과 원래 실패 코드 전달을 검증한다."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.review.tests.run_music_regression import execute_music_regression


class RegressionRunnerContractTests(unittest.TestCase):
    def test_main_blocks_do_not_hide_test_definitions(self):
        import ast
        current_hidden_tests=[]
        for current_source_path in Path(__file__).parent.glob('test_*.py'):
            current_syntax_tree=ast.parse(current_source_path.read_text())
            for current_top_level in current_syntax_tree.body:
                if isinstance(current_top_level,ast.If) and '__name__' in ast.unparse(current_top_level.test):
                    current_hidden_tests.extend(
                        f'{current_source_path.name}:{current_definition.lineno}:{current_definition.name}'
                        for current_definition in ast.walk(current_top_level)
                        if isinstance(current_definition,(ast.FunctionDef,ast.AsyncFunctionDef)) and current_definition.name.startswith('test_')
                    )
        self.assertEqual(current_hidden_tests,[], '직접 실행 조건 안의 테스트는 unittest 수집에서 제외됩니다.')

    def test_preserves_shutdown_output_and_failure_exit(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_fixture_root = Path(current_directory_name)
            for current_failure_requested in (False, True):
                with self.subTest(failure=current_failure_requested):
                    current_module_name = 'isolated_regression_' + str(current_failure_requested).lower()
                    (current_fixture_root / (current_module_name + '.py')).write_text(
                        'import atexit,sys,unittest\n'
                        "atexit.register(lambda: print('종료 진단 보존', file=sys.stderr))\n"
                        'class FixtureTests(unittest.TestCase):\n'
                        ' def test_outcome_contract(self):\n'
                        f'  self.assertFalse({current_failure_requested!r}, "의도한 실패")\n'
                    )
                    current_console_buffer = io.StringIO()
                    with patch.dict(os.environ, {'PYTHONPATH': current_directory_name}), contextlib.redirect_stdout(current_console_buffer):
                        current_exit_code = execute_music_regression((current_module_name,), 'runner-contract-' + current_module_name)
                    current_summary_record = json.loads(current_console_buffer.getvalue())
                    self.assertEqual(current_exit_code, int(current_failure_requested))
                    self.assertEqual(current_summary_record['failed'], int(current_failure_requested))
                    current_result_root = Path(current_summary_record['result_path'])
                    self.assertIn('종료 진단 보존', (current_result_root / 'runner.log').read_text())
                    self.assertNotIn('종료 진단 보존', current_console_buffer.getvalue())
                    self.assertEqual((current_result_root / 'exit-code').read_text(), str(current_exit_code))

    def test_management_help_does_not_start_regression(self):
        import subprocess
        import sys
        current_runner_path = Path(__file__).with_name('run_management_audit.py')
        current_help_result = subprocess.run([sys.executable, str(current_runner_path), '--help'], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_help_result.returncode, 0)
        self.assertIn('usage:', current_help_result.stdout)
        self.assertNotIn('result_path', current_help_result.stdout)
        current_invalid_result = subprocess.run([sys.executable, str(current_runner_path), '--all', '--unsupported'], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_invalid_result.returncode, 2)
        self.assertIn('unrecognized arguments', current_invalid_result.stderr)
