"""UniRig 신규 접수를 차단하고 기존 작업 기록은 보존한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common.gpu_job_queue import launch_gpu_process
from workflow.domains.unirig_experiment import trellis2_candidates
from workflow.domains.hermes_agent import unirig_handoff_cli


class UniRigRetirementTests(unittest.TestCase):
    def test_queue_rejects_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '폐기'):
                launch_gpu_process(['worker'], directory, 'unirig-experiment')
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_candidate_submission_and_handoff_are_rejected(self):
        with patch('sys.argv', ['trellis2_candidates.py']):
            with self.assertRaisesRegex(RuntimeError, '폐기'):
                trellis2_candidates.main()
        with self.assertRaisesRegex(RuntimeError, '폐기'):
            unirig_handoff_cli.main()
