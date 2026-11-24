import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.flux_reports import proposal_request_id
from workflow.domains.hermes_agent.minimax_submission import submit_from_proposal


class MiniMaxSubmissionTests(unittest.TestCase):
    def test_concurrent_different_inputs_never_share_receipt(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        with tempfile.TemporaryDirectory() as temporary:
            store = HermesDelegationStore(Path(temporary))
            dispatch = Mock(return_value={'id':'2026-11-24_10-05-00-12345678'})
            barrier = threading.Barrier(2)
            def submit(prompt):
                barrier.wait()
                try:
                    return store.execute_service_delegation_once('request_123','minimax-h3-image',{'prompt':prompt},dispatch,lambda _:None)
                except ValueError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                first,second = [future.result() for future in (pool.submit(submit,'red roof'),pool.submit(submit,'blue roof'))]
            self.assertNotEqual(first is None,second is None)
            self.assertEqual(dispatch.call_count,1)

    def test_concurrent_submissions_dispatch_once(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        session, job, service = 'a'*32, '2026-11-24_10-00-00-12345678', 'minimax-h3-image'
        proposal = {'service':'flux-image','prompt':'house','width':512,'height':512,'seed':42,'explicit_service':False}
        detail = {'status':{'status':'completed'},'final_response':'HERMES_FLUX_PROPOSAL\n'+json.dumps(proposal)+'\nEND_HERMES_FLUX_PROPOSAL',
                  'final_response_truncated':False,'request':{'image_selection_version':1,'minimax_preferred':True,'prompt':'house'}}
        sessions = Mock();sessions.read_session_record.return_value={'messages':[{'job_id':job}]}
        dispatch = Mock(return_value={'id':'2026-11-24_10-05-00-12345678'})
        payload = {'session_id':session,'proposal_job_id':job,'request_id':proposal_request_id(session,job,service),
                   'service':service,'request':{'action':'generate','prompt':'house'}}
        with tempfile.TemporaryDirectory() as temporary, patch('workflow.domains.minimax_h3_image.generation.MiniMaxH3ImageManager',return_value=Mock()):
            store = HermesDelegationStore(Path(temporary));barrier = threading.Barrier(2)
            def submit():
                barrier.wait()
                return submit_from_proposal(payload,sessions=sessions,read_job=lambda _:detail,dispatch=dispatch,store=store)
            with ThreadPoolExecutor(max_workers=2) as pool:
                first,second = [future.result() for future in (pool.submit(submit),pool.submit(submit))]
            self.assertEqual({first['duplicate'],second['duplicate']},{True,False})
            self.assertEqual(first['job_id'],second['job_id'])
            self.assertEqual(dispatch.call_count,1)

    def test_image_proposal_duplicate_and_mismatch(self):
        session='a'*32; job='2026-11-24_10-00-00-12345678'; service='minimax-h3-image'
        request_id=proposal_request_id(session,job,service)
        proposal={'service':'flux-image','prompt':'house','width':1024,'height':1024,'seed':42,'explicit_service':False}
        answer='HERMES_FLUX_PROPOSAL\n'+json.dumps(proposal)+'\nEND_HERMES_FLUX_PROPOSAL'
        detail={'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False,'request':{'image_selection_version':1,'minimax_preferred':True,'prompt':'house image'}}
        sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':job}]}
        manager=Mock(); manager.validate_generation_request.return_value={}
        dispatch=Mock(return_value={'id':'2026-11-24_10-05-00-12345678'})
        payload={'session_id':session,'proposal_job_id':job,'request_id':request_id,'service':service,'request':{'action':'generate','prompt':'house'}}
        with tempfile.TemporaryDirectory() as temporary, patch('workflow.domains.minimax_h3_image.generation.MiniMaxH3ImageManager', return_value=manager):
            store=HermesDelegationStore(Path(temporary))
            args={'sessions':sessions,'read_job':lambda _:detail,'dispatch':dispatch,'store':store}
            first=submit_from_proposal(payload,**args)
            second=submit_from_proposal(payload,**args)
            self.assertFalse(first['duplicate']);self.assertTrue(second['duplicate']);self.assertEqual(dispatch.call_count,1)
            self.assertEqual(dispatch.call_args.args[2]['_minimax_report_origin']['session_id'],session)
            with self.assertRaises(ValueError):submit_from_proposal({**payload,'request_id':'wrong-id'},**args)
            sessions.read_session_record.return_value={'messages':[]}
            with self.assertRaises(ValueError):submit_from_proposal(payload,**args)

    def test_video_request_is_bound_to_its_own_proposal(self):
        session='b'*32;job='2026-11-24_10-00-00-12345678';service='minimax-h3-i2v'
        proposal={'service':'wan22-i2v','mode':'first_frame','prompt':'walk','explicit_service':False}
        answer='HERMES_VIDEO_PROPOSAL\n'+json.dumps(proposal)+'\nEND_HERMES_VIDEO_PROPOSAL'
        detail={'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False,'request':{'minimax_preferred':True,'prompt':'image to video'}}
        sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':job}]}
        manager=Mock();manager.validate_generation_request.return_value={}
        dispatch=Mock(return_value={'id':'2026-11-24_10-05-00-12345678'})
        payload={'session_id':session,'proposal_job_id':job,'request_id':proposal_request_id(session,job,service),'service':service,'request':{'action':'generate','prompt':'walk'}}
        with tempfile.TemporaryDirectory() as temp, patch('workflow.domains.minimax_h3.generation.MiniMaxH3GenerationManager',return_value=manager):
            result=submit_from_proposal(payload,sessions=sessions,read_job=lambda _:detail,dispatch=dispatch,store=HermesDelegationStore(Path(temp)))
            self.assertEqual(result['state'],'accepted')
            self.assertEqual(dispatch.call_args.args[:2],(service,'generate'))

    def test_generator_persists_origin_before_launch_without_saving_it_in_prompt(self):
        import io
        from types import SimpleNamespace
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.domains.minimax_h3_image.generation import MiniMaxH3ImageManager
        session='c'*32;proposal='2026-11-24_10-00-00-12345678';service='minimax-h3-image'
        origin={'session_id':session,'proposal_job_id':proposal,'request_id':proposal_request_id(session,proposal,service)}
        request={'action':'generate','prompt':'a house','images':[],'width':1024,'height':1024,'steps':6,'seed':42,'_minimax_report_origin':origin}
        body=json.dumps({'service':service,'command':'generate','payload':request}).encode()
        handler=SimpleNamespace(path='/management/command',command='POST',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(body))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(body),wfile=io.BytesIO(),responses=[])
        handler.send_response=handler.responses.append;handler.send_header=lambda *args:None;handler.end_headers=lambda:None
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manager=MiniMaxH3ImageManager();manager.job_storage_root=root/'jobs';manager.job_storage_root.mkdir()
            with patch.object(manager,'history_storage_path',return_value=root/'history'),patch.object(manager,'validate_generation_runtime'),patch.object(manager,'launch_generation_worker',return_value=Mock()),patch('workflow.domains.image.image_generation.threading.Thread'):
                ManagementCommandGateway({service:manager.handle_image_request}).handle(handler)
            self.assertEqual(handler.responses,[202])
            job=json.loads(handler.wfile.getvalue())['id'];directory=manager.job_storage_root/job
            self.assertEqual(json.loads((directory/'hermes-report.json').read_text())['origin'],origin)
            self.assertNotIn('_minimax_report_origin',json.loads((directory/'request.json').read_text()))

    def test_report_status_checks_session_receipt_and_origin(self):
        from workflow.domains.hermes_agent.minimax_submission import read_report_status
        session='d'*32;proposal='2026-11-24_10-00-00-12345678';service='minimax-h3-image';job='2026-11-24_10-05-00-12345678'
        origin={'session_id':session,'proposal_job_id':proposal,'request_id':proposal_request_id(session,proposal,service)}
        payload={**origin,'service':service};sessions=Mock();sessions.read_session_record.return_value={'messages':[{'job_id':proposal}]}
        store=Mock();store.read_service_delegation.return_value={'state':'accepted','job_id':job,'request_id':origin['request_id'],'service':service}
        with tempfile.TemporaryDirectory() as temp:
            storage=Path(temp);directory=storage/job;directory.mkdir();path=directory/'hermes-report.json'
            path.write_text(json.dumps({'origin':origin,'state':'writing','hermes_job_id':'2026-11-24_11-00-00-abcdef12','report_prompt':'private'}))
            with patch('generators.minimax_h3_image.contracts.STORAGE',storage):
                result=read_report_status(payload,sessions=sessions,store=store)
                self.assertEqual(result['report']['state'],'writing')
                self.assertNotIn('report_prompt',result['report'])
                path.unlink()
                missing=read_report_status(payload,sessions=sessions,store=store)
                self.assertEqual(missing['receipt']['state'],'accepted')
                self.assertEqual(missing['report']['state'],'unknown')
                self.assertFalse(missing['report']['retry_available'])
                path.write_text(json.dumps({'origin':{**origin,'session_id':'e'*32},'state':'completed'}))
                with self.assertRaises(ValueError):read_report_status(payload,sessions=sessions,store=store)

    def test_response_loss_recovers_only_one_matching_completed_job(self):
        import hashlib
        from PIL import Image
        from workflow.domains.hermes_agent.minimax_submission import recover_completed_submission, submission_digest
        from workflow.domains.hermes_agent.minimax_report_lifecycle import register_minimax_report
        service='minimax-h3-image';session='f'*32;proposal='2026-11-24_10-00-00-12345678';job='2026-11-24_10-05-00-12345678'
        origin={'session_id':session,'proposal_job_id':proposal,'request_id':proposal_request_id(session,proposal,service)}
        request={'action':'generate','prompt':'house','images':[],'width':1024,'height':1024,'steps':6,'seed':42}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);storage=root/'jobs';storage.mkdir();directory=storage/job;directory.mkdir();store=HermesDelegationStore(root/'receipts')
            def lost(_):
                register_minimax_report(directory,service,origin,submission_digest(service,request))
                (directory/'request.json').write_text(json.dumps(request));(directory/'status.json').write_text(json.dumps({'status':'completed'}))
                Image.new('RGB',(16,16)).save(directory/'result.png')
                (directory/'result.json').write_text(json.dumps({'image_sha256':hashlib.sha256((directory/'result.png').read_bytes()).hexdigest()}))
                runner=Path(__file__).resolve().parents[2]/'generators/minimax_h3_image/worker.py'
                (directory/'gpu-command.json').write_text(json.dumps({'service':service,'command':['python',str(runner),'--job-dir',str(directory)]}))
                raise TimeoutError('response lost')
            with self.assertRaises(TimeoutError):store.execute_service_delegation_once(origin['request_id'],service,request,lost,lambda _:None)
            self.assertEqual(store.read_service_delegation(origin['request_id'],service)['state'],'unknown')
            self.assertTrue(recover_completed_submission(directory,service,origin,store=store))
            self.assertEqual(store.read_service_delegation(origin['request_id'],service)['job_id'],job)
            self.assertFalse(recover_completed_submission(directory,service,origin,store=store))

    def test_response_loss_does_not_recover_ambiguous_or_unfinished_job(self):
        from workflow.domains.hermes_agent.minimax_submission import recover_completed_submission, submission_digest
        from workflow.domains.hermes_agent.minimax_report_lifecycle import register_minimax_report
        service='minimax-h3-image';session='f'*32;proposal='2026-11-24_10-00-00-12345678';origin={'session_id':session,'proposal_job_id':proposal,'request_id':proposal_request_id(session,proposal,service)}
        request={'prompt':'x'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);storage=root/'jobs';storage.mkdir();one=storage/'2026-11-24_10-05-00-12345678';one.mkdir();store=HermesDelegationStore(root/'receipts')
            def lost(_):
                register_minimax_report(one,service,origin,submission_digest(service,request))
                raise TimeoutError('lost')
            with self.assertRaises(TimeoutError):store.execute_service_delegation_once(origin['request_id'],service,request,lost,lambda _:None)
            two=storage/'2026-11-24_10-06-00-12345678';two.mkdir();register_minimax_report(two,service,origin,submission_digest(service,request))
            self.assertFalse(recover_completed_submission(one,service,origin,store=store))
            self.assertEqual(store.read_service_delegation(origin['request_id'],service)['state'],'unknown')

    def test_response_loss_recovery_refuses_running_or_forged_command(self):
        from workflow.domains.hermes_agent.minimax_submission import recover_completed_submission, submission_digest
        from workflow.domains.hermes_agent.minimax_report_lifecycle import register_minimax_report
        service='minimax-h3-image';session='f'*32;proposal='2026-11-24_10-00-00-12345678';origin={'session_id':session,'proposal_job_id':proposal,'request_id':proposal_request_id(session,proposal,service)}
        request={'prompt':'x'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);directory=root/'jobs'/'2026-11-24_10-05-00-12345678';directory.mkdir(parents=True);store=HermesDelegationStore(root/'receipts')
            def lost(_):
                register_minimax_report(directory,service,origin,submission_digest(service,request))
                (directory/'status.json').write_text(json.dumps({'status':'running'}))
                (directory/'gpu-command.json').write_text(json.dumps({'service':service,'command':['python','/untrusted/worker.py','--job-dir',str(directory)]}))
                raise TimeoutError('lost')
            with self.assertRaises(TimeoutError):store.execute_service_delegation_once(origin['request_id'],service,request,lost,lambda _:None)
            self.assertFalse(recover_completed_submission(directory,service,origin,store=store))
            self.assertEqual(store.read_service_delegation(origin['request_id'],service)['state'],'unknown')

    def test_service_dispatch_validates_bad_payload_without_local_environment_error(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manager=HermesServiceManager(root/'jobs',root/'sessions')
            with self.assertRaisesRegex(ValueError,'대화·제안'):
                manager.execute_hermes_command('hermes-minimax-submit',{})

    def test_service_dispatch_uses_configured_gateway_for_submit_callback(self):
        import os
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manager=HermesServiceManager(root/'jobs',root/'sessions')
            def exercise(payload, *, sessions, read_job, dispatch):
                return dispatch('minimax-h3-image','status',{'id':'fixture'})
            with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:9876'}),patch('workflow.domains.hermes_agent.minimax_submission.submit_from_proposal',side_effect=exercise),patch('workflow.common.management_gateway.execute_management_command',return_value={'ok':True}) as gateway:
                self.assertEqual(manager.execute_hermes_command('hermes-minimax-submit',{}),{'ok':True})
            gateway.assert_called_once_with('minimax-h3-image','status',{'id':'fixture'},'http://127.0.0.1:9876')
