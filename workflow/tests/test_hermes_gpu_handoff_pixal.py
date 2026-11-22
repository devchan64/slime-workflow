import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import gpu_handoff_pixal as pixal


class PixalHandoffTest(unittest.TestCase):
    def test_existing_job_is_bound_to_immutable_inputs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pixal, 'ROOT', Path(directory)):
            job = Path(directory) / ('generate-' + 'a' * 32)
            job.mkdir()
            (job / 'gpu-command.json').write_text(json.dumps({'service':'pixal-experiment'}))
            (job / 'request.json').write_text('{}')
            record = {'service':'pixal-experiment', 'input_digest':'b' * 64,
                      'target_request':{'job_id':job.name, 'fingerprint':pixal.fingerprint(job)}}
            adapter = pixal.PixalHandoffAdapter()
            self.assertEqual(adapter.submit_target(record)['job_id'], job.name)
            (job / 'request.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError):
                adapter.lookup_target(record)

    def test_rejects_untrusted_job_path(self):
        record = {'target_request':{'job_id':'../other'}}
        with self.assertRaises(ValueError):
            pixal.PixalHandoffAdapter().lookup_target(record)


if __name__ == '__main__':
    unittest.main()
