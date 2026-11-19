"""진단 불가와 기존 증거 보존의 사용자 계약을 검증한다."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROBE_SCRIPT_PATH = Path(__file__).with_name('check_vmm_remap.py')


class DriverProbeContractTests(unittest.TestCase):
    def test_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            report_file_path = Path(temporary_directory_value) / 'report.json'
            report_file_path.write_text('existing evidence')
            process_result_value = subprocess.run([sys.executable, str(PROBE_SCRIPT_PATH), '--output', str(report_file_path)], capture_output=True, text=True)
            self.assertNotEqual(process_result_value.returncode, 0)
            self.assertEqual(report_file_path.read_text(), 'existing evidence')

    def test_missing_dependencies_are_incomplete_not_pass(self):
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            report_file_path = Path(temporary_directory_value) / 'report.json'
            environment_values = dict(os.environ, PATH=temporary_directory_value)
            process_result_value = subprocess.run([sys.executable, str(PROBE_SCRIPT_PATH), '--output', str(report_file_path)], capture_output=True, text=True, env=environment_values)
            self.assertEqual(process_result_value.returncode, 2)
            self.assertEqual(json.loads(report_file_path.read_text())['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
