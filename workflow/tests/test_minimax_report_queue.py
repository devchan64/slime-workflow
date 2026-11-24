"""검증된 MiniMax 보고서 작성만 상주 모델 반환 후보가 된다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.common.gpu_job_queue import is_registered_minimax_report


class MiniMaxReportQueueTests(unittest.TestCase):
    def test_only_exact_recorded_minimax_report_is_eligible(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);service='minimax-h3-image';source_id='2026-11-24_10-00-00-12345678';report_id='2026-11-24_11-00-00-12345678'
            source=root/'.tmp/test'/service/source_id;source.mkdir(parents=True)
            job=root/'.tmp/test/hermes-agent/jobs'/report_id;job.mkdir(parents=True)
            request_id='report_'+'a'*64;prompt='보고서\n'+json.dumps({'evidence':{'service':service,'job_id':source_id},'observations':[]})
            (job/'request.json').write_text(json.dumps({'request_id':request_id,'prompt':prompt}))
            record={'state':'writing','hermes_job_id':report_id,'report_request_id':request_id,'report_prompt':prompt}
            (source/'hermes-report.json').write_text(json.dumps(record))
            with patch('workflow.common.gpu_job_queue.WORKFLOW_ROOT_DIRECTORY',root):
                self.assertTrue(is_registered_minimax_report(job))
                (source/'hermes-report.json').write_text(json.dumps({**record,'report_prompt':'changed'}))
                self.assertFalse(is_registered_minimax_report(job))
                (source/'hermes-report.json').write_text(json.dumps({**record,'state':'completed'}))
                self.assertFalse(is_registered_minimax_report(job))
