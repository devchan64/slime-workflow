import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from workflow.domains.hermes_agent.minimax_report_lifecycle import advance_minimax_report


class MiniMaxReportLifecycleTests(unittest.TestCase):
    def test_completed_result_is_reported_once_to_original_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
            origin = {'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
            (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}))
            (root/'status.json').write_text(json.dumps({'status':'completed'}))
            receipts = Mock();receipts.read_service_delegation.return_value={'state':'accepted','job_id':root.name}
            sessions = Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
            job='2026-11-24_12-01-00-12345678'
            def dispatch(command, payload):
                if command=='hermes-submit':
                    dispatch.request=payload['request_id'];return {'id':job}
                return {'id':job,'request':{'request_id':dispatch.request},'status':{'status':'completed'},'final_response':'보고서','final_response_truncated':False}
            inspect=Mock(return_value={'service':'minimax-h3-image','job_id':root.name,'result_url':'/minimax-h3-image/jobs/example/result.png'})
            observe=Mock(return_value=[{'observation':'house'}])
            value=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            self.assertEqual(value['state'],'completed')
            self.assertEqual(sessions.append_session_request.call_count,1)
            advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            self.assertEqual(sessions.append_session_request.call_count,1)
            self.assertEqual(observe.call_count,1)

    def test_wrong_receipt_does_not_deliver(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':{'session_id':'a'*32,'proposal_job_id':'x','request_id':'y'}}))
            receipts=Mock();receipts.read_service_delegation.return_value={'state':'unknown'}
            sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':'x'}]}
            with self.assertRaises(ValueError):advance_minimax_report(root,'minimax-h3-image',Mock(),sessions,receipts=receipts)
            sessions.append_session_request.assert_not_called()

    def test_resume_after_restart_keeps_single_writer_and_detects_changed_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
            origin={'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
            (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}))
            (root/'status.json').write_text(json.dumps({'status':'completed'}))
            receipts=Mock();receipts.read_service_delegation.return_value={'state':'accepted','job_id':root.name}
            sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
            hermes_job='2026-11-24_12-01-00-12345678';calls=[];saved={}
            def dispatch(command,payload):
                calls.append(command)
                if command=='hermes-submit':saved.update(payload);return {'id':hermes_job}
                return {'id':hermes_job,'request':{'request_id':saved['request_id']},'status':{'status':'running'}}
            inspect=Mock(return_value={'service':'minimax-h3-image','job_id':root.name,'digest':'original'})
            observe=Mock(return_value=[{'observation':'house'}])
            first=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            self.assertEqual(first['state'],'writing')
            advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            self.assertEqual(calls.count('hermes-submit'),1)
            self.assertEqual(observe.call_count,1)
            inspect.return_value={'service':'minimax-h3-image','job_id':root.name,'digest':'modified'}
            final=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            self.assertEqual(final['state'],'failed')
            sessions.append_session_request.assert_not_called()

    def test_long_prompt_is_bounded_and_truncation_is_disclosed(self):
        from workflow.domains.hermes_agent.minimax_report_lifecycle import build_report_prompt
        prompt=build_report_prompt({'user_prompt':'x'*8000,'generation_prompt':'y'*10000},[{'observation':'z'*2000} for _ in range(4)],'원래 요청 '*2000)
        self.assertLess(len(prompt),12000)
        self.assertIn('truncated_fields',prompt)
        self.assertIn('user_prompt',prompt)
        self.assertIn('original_user_request',prompt)
        clipped=json.loads(prompt.split('\n',1)[1])['truncated_fields']
        self.assertTrue({'original_user_request','user_prompt','generation_prompt','observation'}.issubset(clipped))

    def test_missing_original_request_is_not_invented(self):
        from workflow.domains.hermes_agent.minimax_report_lifecycle import build_report_prompt
        prompt=build_report_prompt({'user_prompt':'house','generation_prompt':'house'},[])
        data=json.loads(prompt.split('\n',1)[1])
        self.assertNotIn('original_user_request',data['evidence'])
        self.assertIn('원 요청은 확인 불가',prompt)

    def test_followup_instructions_are_context_not_proof_of_submission(self):
        from workflow.domains.hermes_agent.minimax_report_lifecycle import build_report_prompt
        prompt = build_report_prompt({'user_prompt':'성당'}, [], '아직 접수하지 마세요', ['이제 대기열에 접수해줘'])
        data = json.loads(prompt.split('\n', 1)[1])
        self.assertEqual(data['evidence']['subsequent_user_messages'], ['이제 대기열에 접수해줘'])
        self.assertIn('독립적으로 증명하지 않습니다', prompt)

    def test_result_changed_during_writer_detail_is_not_delivered(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
            origin={'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
            (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}))
            (root/'status.json').write_text(json.dumps({'status':'completed'}))
            receipts=Mock();receipts.read_service_delegation.return_value={'state':'accepted','job_id':root.name}
            sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
            inspect=Mock(side_effect=[{'digest':'old'},{'digest':'old'},{'digest':'new'}])
            job='2026-11-24_12-01-00-12345678';saved={}
            def dispatch(command,payload):
                if command=='hermes-submit':saved.update(payload);return {'id':job}
                return {'id':job,'request':{'request_id':saved['request_id']},'status':{'status':'completed'},'final_response':'보고서'}
            record=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=Mock(return_value=[]),receipts=receipts)
            self.assertEqual(record['state'],'failed');sessions.append_session_request.assert_not_called()

    def test_real_session_record_receives_report_once_after_writer_restart(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.flux_reports import proposal_request_id
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);service='minimax-h3-i2v';job='2026-11-24_12-00-00-12345678';proposal='2026-11-24_11-00-00-12345678';session='b'*32
            directory=root/job;directory.mkdir();sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_original','영상 생성');sessions.attach_session_job(session,'request_original',proposal)
            request_id=proposal_request_id(session,proposal,service);origin={'session_id':session,'proposal_job_id':proposal,'request_id':request_id}
            receipts=HermesDelegationStore(root/'receipts');receipts.execute_service_delegation_once(request_id,service,{},lambda _: {'id':job},lambda _:None)
            (directory/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}));(directory/'status.json').write_text(json.dumps({'status':'completed'}))
            hermes_job='2026-11-24_12-01-00-12345678';saved={};calls=[]
            def dispatch(command,payload):
                calls.append(command)
                if command=='hermes-submit':saved.update(payload);return {'id':hermes_job}
                return {'id':hermes_job,'request':{'request_id':saved['request_id']},'status':{'status':'completed'},'final_response':'보고서 내용','final_response_truncated':False}
            inspect=Mock(return_value={'service':service,'job_id':job,'attempt':'a'*32,'result_url':'/minimax-h3-i2v/jobs/example/preview.mp4'});observe=Mock(return_value=[{'seconds':0,'observation':'person'}])
            advance_minimax_report(directory,service,dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            # Simulate a crash after the session append but before the report
            # file records completion; replay must reuse the same message.
            report_path=directory/'hermes-report.json'
            record=json.loads(report_path.read_text());record['state']='writing';record.pop('body',None)
            report_path.write_text(json.dumps(record))
            advance_minimax_report(directory,service,dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            session_record=sessions.read_session_record(session)
            self.assertEqual([entry['job_id'] for entry in session_record['messages']],[proposal,hermes_job])
            self.assertEqual(calls.count('hermes-submit'),1)

    def test_scheduler_discovers_valid_image_and_video_reports_after_restart(self):
        from unittest.mock import patch
        from workflow.domains.hermes_agent.minimax_report_lifecycle import watch_minimax_reports
        class OnePass:
            stopped=False
            def is_set(self): return self.stopped
            def wait(self, _): self.stopped=True
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);job='2026-11-24_12-00-00-12345678'
            for service in ('minimax-h3-image','minimax-h3-i2v'):
                directory=root/'.tmp/test'/service/job;directory.mkdir(parents=True)
                (directory/'hermes-report.json').write_text(json.dumps({'state':'waiting'}))
            invalid=root/'.tmp/test/minimax-h3-image/not-a-job';invalid.mkdir()
            (invalid/'hermes-report.json').write_text(json.dumps({'state':'waiting'}))
            with patch('workflow.domains.hermes_agent.minimax_report_lifecycle.advance_minimax_report') as advance:
                watch_minimax_reports(root,OnePass(),Mock(),sessions=Mock(),interval=0.01)
            self.assertEqual({call.args[1] for call in advance.call_args_list},{'minimax-h3-image','minimax-h3-i2v'})
            self.assertEqual(advance.call_count,2)

    def test_failed_or_cancelled_generation_does_not_start_analysis_or_report(self):
        for state in ('failed','cancelled'):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
                origin={'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
                (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}))
                (root/'status.json').write_text(json.dumps({'status':state}))
                (root/'worker.log').write_text('LLVM ERROR: Disk quota exceeded')
                receipts=Mock();receipts.read_service_delegation.return_value={'state':'accepted','job_id':root.name}
                sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
                inspect=Mock();observe=Mock();dispatch=Mock()
                result=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
                self.assertEqual(result['state'],'failed');inspect.assert_not_called();observe.assert_not_called();dispatch.assert_not_called()
                notice=sessions.append_result_notice.call_args.args[2]
                self.assertIn(root.name,notice)
                self.assertIn('할당량 초과' if state=='failed' else '취소',notice)

    def test_writer_timeout_reuses_identical_request_identifier(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
            origin={'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
            (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}));(root/'status.json').write_text(json.dumps({'status':'completed'}))
            receipts=Mock();receipts.read_service_delegation.return_value={'state':'accepted','job_id':root.name}
            sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
            inspect=Mock(return_value={'service':'minimax-h3-image','job_id':root.name,'result_url':'/minimax-h3-image/jobs/example/result.png'});observe=Mock(return_value=[])
            dispatch=Mock(side_effect=TimeoutError('response lost'))
            for _ in range(2):
                with self.assertRaises(TimeoutError):advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=inspect,observe=observe,receipts=receipts)
            self.assertEqual(dispatch.call_args_list[0].args[1]['request_id'],dispatch.call_args_list[1].args[1]['request_id'])
            self.assertEqual(observe.call_count,1);sessions.append_session_request.assert_not_called()

    def test_scheduler_does_not_analyze_while_generation_or_cleanup_holds_execution_lock(self):
        import fcntl
        from unittest.mock import patch
        from workflow.domains.hermes_agent.minimax_report_lifecycle import watch_minimax_reports
        class OnePass:
            stopped=False
            def is_set(self): return self.stopped
            def wait(self, _): self.stopped=True
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);directory=root/'.tmp/test/minimax-h3-image/2026-11-24_12-00-00-12345678';directory.mkdir(parents=True)
            (directory/'hermes-report.json').write_text(json.dumps({'state':'waiting'}))
            with (directory/'execution.lock').open('w') as held:
                fcntl.flock(held,fcntl.LOCK_EX)
                with patch('workflow.domains.hermes_agent.minimax_report_lifecycle.advance_minimax_report') as advance:
                    watch_minimax_reports(root,OnePass(),Mock(),sessions=Mock(),interval=0.01)
                    advance.assert_not_called()
                fcntl.flock(held,fcntl.LOCK_UN)
            with patch('workflow.domains.hermes_agent.minimax_report_lifecycle.advance_minimax_report') as advance:
                watch_minimax_reports(root,OnePass(),Mock(),sessions=Mock(),interval=0.01)
                advance.assert_called_once()

    def test_unknown_receipt_recovers_before_reporting(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
            origin={'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
            (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin,'submission_sha256':'a'*64}))
            (root/'status.json').write_text(json.dumps({'status':'completed'}))
            receipts=Mock();receipts.read_service_delegation.side_effect=[{'state':'unknown'},{'state':'accepted','job_id':root.name}]
            sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
            job='2026-11-24_12-01-00-12345678';saved={}
            def dispatch(command,payload):
                if command=='hermes-submit':saved.update(payload);return {'id':job}
                return {'id':job,'request':{'request_id':saved['request_id']},'status':{'status':'completed'},'final_response':'보고'}
            with patch('workflow.domains.hermes_agent.minimax_submission.recover_completed_submission',return_value=True) as recover:
                result=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=Mock(return_value={'result_url':'/result'}),observe=Mock(return_value=[]),receipts=receipts)
            self.assertEqual(result['state'],'completed');recover.assert_called_once();sessions.append_session_request.assert_called_once()

    def test_writer_queue_state_is_persisted_for_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'2026-11-24_12-00-00-12345678';root.mkdir()
            origin={'session_id':'a'*32,'proposal_job_id':'2026-11-24_11-00-00-12345678','request_id':'r'*16}
            (root/'hermes-report.json').write_text(json.dumps({'state':'waiting','origin':origin}))
            (root/'status.json').write_text(json.dumps({'status':'completed'}))
            receipts=Mock();receipts.read_service_delegation.return_value={'state':'accepted','job_id':root.name}
            sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':origin['proposal_job_id']}]}
            job='2026-11-24_12-01-00-12345678';saved={}
            def dispatch(command,payload):
                if command=='hermes-submit':saved.update(payload);return {'id':job}
                return {'id':job,'request':{'request_id':saved['request_id']},'status':{'status':'queued'}}
            result=advance_minimax_report(root,'minimax-h3-image',dispatch,sessions,inspect=Mock(return_value={'result_url':'/result'}),observe=Mock(return_value=[]),receipts=receipts)
            self.assertEqual(result['writer_status'],'queued')
            self.assertEqual(json.loads((root/'hermes-report.json').read_text())['writer_status'],'queued')
