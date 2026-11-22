"""UniRig 신규 접수를 차단하고 기존 작업 기록은 보존한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common.gpu_job_queue import launch_gpu_process


class UniRigRetirementTests(unittest.TestCase):
    def test_queue_rejects_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '폐기'):
                launch_gpu_process(['worker'], directory, 'unirig-experiment')
            self.assertEqual(list(Path(directory).iterdir()), [])
