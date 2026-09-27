import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.review.domains.anny import anny_attributes


class AnnyHistoryTest(unittest.TestCase):
    def create_history_job(self, jobs_directory_path, identifier_value, state_value):
        job_directory_path=jobs_directory_path/identifier_value
        job_directory_path.mkdir(parents=True)
        (job_directory_path/'history.json').write_text(json.dumps({'id':identifier_value,'request':{'attributes':{}}}))
        (job_directory_path/'status.json').write_text(json.dumps({'status':state_value}))
        (job_directory_path/'result.png').write_bytes(b'image')
        return job_directory_path

    def test_delete_history_preserves_completed_job_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(anny_attributes,'JOBS',Path(temporary_directory_name)):
            job_directory_path=self.create_history_job(Path(temporary_directory_name),'1234abcd','completed')

            self.assertEqual(anny_attributes.delete_anny_history_record('1234abcd'),{'deleted':'1234abcd','files_preserved':True})
            self.assertFalse((job_directory_path/'history.json').exists())
            self.assertTrue((job_directory_path/'result.png').exists())

    def test_clear_history_rejects_active_job(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(anny_attributes,'JOBS',Path(temporary_directory_name)):
            job_directory_path=self.create_history_job(Path(temporary_directory_name),'1234abcd','running')

            with self.assertRaisesRegex(ValueError,'먼저 중지'):
                anny_attributes.clear_anny_history_records()
            self.assertTrue((job_directory_path/'history.json').exists())

    def test_clear_history_preserves_completed_job_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(anny_attributes,'JOBS',Path(temporary_directory_name)):
            job_directory_path=self.create_history_job(Path(temporary_directory_name),'1234abcd','completed')

            self.assertEqual(anny_attributes.clear_anny_history_records(),{'cleared':1,'files_preserved':True})
            self.assertFalse((job_directory_path/'history.json').exists())
            self.assertTrue((job_directory_path/'result.png').exists())
