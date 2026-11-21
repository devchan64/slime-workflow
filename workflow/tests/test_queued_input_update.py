import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common.queued_input_update import request_revision, update_waiting_request


class QueuedInputUpdateTests(unittest.TestCase):
    def test_revision_and_reservation_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, queue = root/'job', root/'queue'
            job.mkdir(); queue.mkdir(); (queue/'active').mkdir(); (queue/'execution.lock').touch()
            (job/'status.json').write_text('{"status":"queued"}')
            (job/'request.json').write_text('{"seed":42}')
            (queue/'ticket.json').write_text(json.dumps({'path':str(job.resolve()), 'pid':123}))
            before = request_revision({'seed':42})
            with patch('workflow.common.queued_input_update.inspect_gpu_ticket_executor_identity', return_value='verified'):
                after = update_waiting_request(job, queue, before, lambda old: {**old, 'seed':43})
                self.assertEqual(after, request_revision({'seed':43}))
                with self.assertRaisesRegex(ValueError, '변경'):
                    update_waiting_request(job, queue, before, lambda old: old)
                (queue/'active'/'reserved.json').write_text(json.dumps({'path':str(job.resolve())}))
                with self.assertRaisesRegex(ValueError, '예약'):
                    update_waiting_request(job, queue, after, lambda old: old)
                (queue/'active'/'reserved.json').unlink()
                (job/'status.json').write_text('{"status":"running"}')
                with self.assertRaisesRegex(ValueError, '대기 중'):
                    update_waiting_request(job, queue, after, lambda old: old)
                self.assertEqual(json.loads((job/'request.json').read_text()), {'seed':43})
