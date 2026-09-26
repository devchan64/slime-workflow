import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.domains.momask import momask_jobs as jobs

class MoMaskResumeTests(unittest.TestCase):
    def test_resume_keeps_id_and_appends_log(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path=Path(temporary_directory_name)
            job_directory_path=temporary_root_path/'sample';job_directory_path.mkdir()
            for relative_file_path in ('result/anny/mannequin.blend','result/anny/render_asset.py','result/anny/run_stage.py','result/anny/baseline-model.json','result/anny/arm-corrections.json','motion-run/motion/motion.npz','motion-run/prompt.txt'):
                output_file_path=job_directory_path/relative_file_path;output_file_path.parent.mkdir(parents=True,exist_ok=True);output_file_path.touch()
            (job_directory_path/'status.json').write_text(json.dumps({'status':'cancelled'}))
            (job_directory_path/'worker.log').write_text('previous log\n')
            (job_directory_path/'cancel.request').touch()
            with patch.object(jobs,'resolve_generation_directory',return_value=job_directory_path),patch.object(jobs,'GENERATION_LOCK_FILE',temporary_root_path/'lock'),patch.object(jobs,'GENERATION_HISTORY_DIRECTORY',temporary_root_path/'history'),patch.object(jobs.subprocess,'Popen') as launch_process_mock:
                self.assertEqual(jobs.resume_generation_job('sample')['id'],'sample')
                self.assertTrue((job_directory_path/'resume.request').exists())
                self.assertFalse((job_directory_path/'cancel.request').exists())
                self.assertIn('previous log',(job_directory_path/'worker.log').read_text())
                launch_process_mock.assert_called_once()
                with self.assertRaisesRegex(ValueError,'취소·실패'):jobs.resume_generation_job('sample')
