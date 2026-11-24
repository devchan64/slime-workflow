"""보고 재시도는 완료된 원 결과와 조회한 리비전에만 적용된다."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
from workflow.domains.hermes_agent.flux_reports import proposal_request_id
from workflow.domains.hermes_agent.minimax_submission import read_report_status, retry_report
from workflow.domains.hermes_agent.minimax_report_lifecycle import advance_minimax_report


class MiniMaxReportRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.storage=Path(self.temp.name)/'jobs';self.storage.mkdir()
        self.service='minimax-h3-image';self.session='a'*32;self.proposal='2026-11-24_10-00-00-12345678';self.job='2026-11-24_10-05-00-12345678'
        self.request_id=proposal_request_id(self.session,self.proposal,self.service)
        self.origin={'session_id':self.session,'proposal_job_id':self.proposal,'request_id':self.request_id}
        self.base={**self.origin,'service':self.service};self.path=self.storage/self.job;self.path.mkdir()
        (self.path/'status.json').write_text(json.dumps({'status':'completed'}))
        (self.path/'request.json').write_text(json.dumps({'prompt':'house'}))
        Image.new('RGB',(16,16)).save(self.path/'result.png')
        (self.path/'result.json').write_text(json.dumps({'image_sha256':hashlib.sha256((self.path/'result.png').read_bytes()).hexdigest()}))
        self.sessions=Mock();self.sessions.read_session_record.return_value={'messages':[{'job_id':self.proposal}]}
        self.receipts=Mock();self.receipts.read_service_delegation.return_value={'state':'accepted','job_id':self.job,'service':self.service,'request_id':self.request_id}
        self.storage_patch=patch('generators.minimax_h3_image.contracts.STORAGE',self.storage);self.storage_patch.start();self.addCleanup(self.storage_patch.stop)

    def record(self, state, **kwargs):
        (self.path/'hermes-report.json').write_text(json.dumps({'state':state,'origin':self.origin,**kwargs}))

    def test_failed_report_retries_once_and_does_not_regenerate(self):
        original_id='report_'+hashlib.sha256((self.service+'/'+self.job+'/image').encode()).hexdigest()
        self.record('failed',error='writer failed',report_request_id=original_id,hermes_job_id='2026-11-24_11-00-00-12345678')
        before=read_report_status(self.base,sessions=self.sessions,store=self.receipts)
        self.assertTrue(before['report']['retry_available']);self.assertEqual(before['report']['retry_revision'],0)
        result=retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)
        self.assertEqual(result['retry_revision'],1)
        saved=json.loads((self.path/'hermes-report.json').read_text());self.assertEqual(saved['state'],'waiting');self.assertEqual(saved['retry_history'][0]['error'],'writer failed')
        self.assertNotIn('hermes_job_id',saved)
        with self.assertRaises(ValueError):retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)
        self.assertEqual(json.loads((self.path/'status.json').read_text())['status'],'completed')
        writer='2026-11-24_12-00-00-12345678';calls=[];stored={}
        def dispatch(command,payload):
            calls.append(command)
            if command=='hermes-submit':stored.update(payload);return {'id':writer}
            return {'id':writer,'request':{'request_id':stored['request_id']},'status':{'status':'completed'},'final_response':'재분석 보고'}
        result=advance_minimax_report(self.path,self.service,dispatch,self.sessions,observe=Mock(return_value=[]),receipts=self.receipts)
        self.assertEqual(result['state'],'completed');self.assertNotEqual(result['report_request_id'],original_id);self.assertEqual(calls.count('hermes-submit'),1)

    def test_unavailable_observation_can_retry_but_generation_failure_cannot(self):
        self.record('completed',observations=[{'unavailable':'모델 없음'}])
        self.assertTrue(read_report_status(self.base,sessions=self.sessions,store=self.receipts)['report']['retry_available'])
        (self.path/'status.json').write_text(json.dumps({'status':'failed'}))
        self.assertFalse(read_report_status(self.base,sessions=self.sessions,store=self.receipts)['report']['retry_available'])
        with self.assertRaises(ValueError):retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)

    def test_failed_and_cancelled_generation_are_reported_without_retry(self):
        self.record('failed',error='생성 작업이 완료되지 않았습니다.')
        for state in ('failed','cancelled'):
            (self.path/'status.json').write_text(json.dumps({'status':state}))
            report=read_report_status(self.base,sessions=self.sessions,store=self.receipts)['report']
            self.assertEqual(report['generation_state'],state)
            self.assertFalse(report['retry_available'])

    def test_unreadable_generation_status_is_unknown_and_not_retryable(self):
        self.record('failed',error='보고 상태 확인 필요')
        (self.path/'status.json').unlink()
        report=read_report_status(self.base,sessions=self.sessions,store=self.receipts)['report']
        self.assertEqual(report['generation_state'],'unknown')
        self.assertFalse(report['retry_available'])

    def test_lock_and_wrong_session_are_rejected(self):
        import fcntl
        self.record('failed',error='failed')
        with (self.path/'execution.lock').open('w') as held:
            fcntl.flock(held,fcntl.LOCK_EX)
            with self.assertRaises(ValueError):retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)
        self.sessions.read_session_record.return_value={'messages':[]}
        with self.assertRaises(ValueError):retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)

    def test_missing_result_is_not_advertised_as_retryable(self):
        self.record('failed',error='분석 실패')
        (self.path/'result.png').unlink()
        report=read_report_status(self.base,sessions=self.sessions,store=self.receipts)['report']
        self.assertFalse(report['retry_available']);self.assertIn('무결성',report['retry_unavailable_reason'])
        with self.assertRaises(ValueError):retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)

    def test_capability_schema_matches_first_revision_and_minimax_services(self):
        from jsonschema import Draft202012Validator
        from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog
        by_name={item['command']:item for item in list_hermes_capability_catalog()['records']}
        retry=by_name['hermes-minimax-report-retry']['payload_schema']
        payload={**self.base,'expected_revision':0}
        self.assertFalse(list(Draft202012Validator(retry).iter_errors(payload)))
        self.assertTrue(list(Draft202012Validator(retry).iter_errors({**payload,'expected_revision':10})))
        self.assertTrue(list(Draft202012Validator(retry).iter_errors({**payload,'service':'kimodo'})))
        submit=by_name['hermes-minimax-submit']['payload_schema']
        self.assertNotIn('kimodo',submit['properties']['request'].get('validation','').lower())

    def test_concurrent_retry_clicks_schedule_only_one_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        self.record('failed',error='writer failed')
        barrier=threading.Barrier(2)
        def retry_once():
            barrier.wait()
            try:return retry_report({**self.base,'expected_revision':0},sessions=self.sessions,store=self.receipts)
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:retry_once(),range(2)))
        self.assertEqual(sum(result is not None for result in results),1)
        saved=json.loads((self.path/'hermes-report.json').read_text())
        self.assertEqual(saved['state'],'waiting');self.assertEqual(saved['retry_revision'],1);self.assertEqual(len(saved['retry_history']),1)

    def test_status_and_retry_use_the_same_gateway_contract(self):
        import io
        from types import SimpleNamespace
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        sessions_root=Path(self.temp.name)/'sessions';sessions=HermesSessionStore(sessions_root);sessions.create_session_record(self.session)
        sessions.append_session_request(self.session,'user_request','이미지');sessions.attach_session_job(self.session,'user_request',self.proposal)
        self.record('failed',error='writer failed')
        manager=HermesServiceManager(Path(self.temp.name)/'hermes-jobs',sessions_root)
        def command(name,payload):
            body=json.dumps({'service':'hermes-agent','command':name,'payload':payload}).encode()
            handler=SimpleNamespace(path='/management/command',command='POST',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(body))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(body),wfile=io.BytesIO(),responses=[])
            handler.send_response=handler.responses.append;handler.send_header=lambda *args:None;handler.end_headers=lambda:None
            ManagementCommandGateway({'hermes-agent':manager.handle_hermes_request}).handle(handler)
            return handler.responses[0],json.loads(handler.wfile.getvalue())
        with patch('workflow.domains.hermes_agent.minimax_submission.HermesDelegationStore',return_value=self.receipts):
            code,status=command('hermes-minimax-report-status',self.base)
            self.assertEqual(code,200);self.assertTrue(status['report']['retry_available'])
            code,result=command('hermes-minimax-report-retry',{**self.base,'expected_revision':0})
            self.assertEqual(code,200);self.assertEqual(result['retry_revision'],1)
            code,_=command('hermes-minimax-report-retry',{**self.base,'expected_revision':0})
            self.assertEqual(code,400)
