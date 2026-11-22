import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import gpu_handoff_trellis2 as trellis2
from workflow.domains.hermes_agent.gpu_handoff_pixal import fingerprint


class Trellis2HandoffTest(unittest.TestCase):
    def test_job_and_input_are_bound_to_the_trellis_queue(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(trellis2, 'ROOT', Path(directory)):
            job = Path(directory) / ('generate-' + 'a' * 32)
            job.mkdir()
            (job / 'gpu-command.json').write_text(json.dumps({'service':'trellis-experiment'}))
            (job / 'request.json').write_text('{}')
            record = {'service':'trellis-experiment', 'input_digest':'b' * 64,
                      'target_request':{'job_id':job.name, 'fingerprint':fingerprint(job)}}
            adapter = trellis2.Trellis2HandoffAdapter()
            self.assertEqual(adapter.submit_target(record)['job_id'], job.name)
            (job / 'request.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError): adapter.lookup_target(record)

    def test_rejects_untrusted_path(self):
        with self.assertRaises(ValueError):
            trellis2.Trellis2HandoffAdapter().lookup_target({'target_request':{'job_id':'../other'}})


if __name__ == '__main__': unittest.main()
