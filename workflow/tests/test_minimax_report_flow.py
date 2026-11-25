"""격리된 실제 서비스·접수·세션 기록의 MiniMax 보고 연결을 검증한다."""
import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image
from workflow.common.management_gateway import ManagementCommandGateway
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.flux_reports import proposal_request_id
from workflow.domains.hermes_agent.minimax_form_commands import execute_minimax_form_command
from workflow.domains.hermes_agent.minimax_submission import submit_from_proposal, read_report_status
from workflow.domains.hermes_agent.minimax_report_lifecycle import advance_minimax_report
from workflow.domains.hermes_agent.session_store import HermesSessionStore


def write(path, value): path.write_text(json.dumps(value), encoding='utf-8')


def run_generation(manager, service, request):
    body=json.dumps({'service':service,'command':'generate','payload':request}).encode()
    handler=SimpleNamespace(path='/management/command',command='POST',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(body))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(body),wfile=io.BytesIO(),responses=[])
    handler.send_response=handler.responses.append;handler.send_header=lambda *args:None;handler.end_headers=lambda:None
    ManagementCommandGateway({service:manager.handle_image_request}).handle(handler)
    if handler.responses != [202]: raise AssertionError((handler.responses,handler.wfile.getvalue()))
    return json.loads(handler.wfile.getvalue())


class MiniMaxReportFlowTests(unittest.TestCase):
    def test_image_and_video_flow(self):
        from workflow.domains.minimax_h3_image.generation import MiniMaxH3ImageManager
        from workflow.domains.minimax_h3.generation import MiniMaxH3GenerationManager
        for service in ('minimax-h3-image','minimax-h3-i2v'):
            with self.subTest(service=service), tempfile.TemporaryDirectory() as temp:
                root=Path(temp);sessions=HermesSessionStore(root/'sessions');session='a'*32;sessions.create_session_record(session)
                proposal='2026-11-24_10-00-00-12345678';sessions.append_session_request(session,'original_request','원래 대화의 요청');sessions.attach_session_job(session,'original_request',proposal)
                if service=='minimax-h3-image':
                    manager=MiniMaxH3ImageManager();manager_path='workflow.domains.minimax_h3_image.generation.MiniMaxH3ImageManager'
                    proposal_data={'service':'flux-image','prompt':'house','width':1024,'height':1024,'seed':42,'explicit_service':False}
                    answer='HERMES_FLUX_PROPOSAL\n'+json.dumps(proposal_data)+'\nEND_HERMES_FLUX_PROPOSAL'
                    job_request={'prompt':'house','minimax_preferred':True,'image_selection_version':1}
                    generation={'action':'generate','prompt':'house','images':[],'width':1024,'height':1024,'steps':6,'seed':42}
                else:
                    manager=MiniMaxH3GenerationManager();manager_path='workflow.domains.minimax_h3.generation.MiniMaxH3GenerationManager'
                    proposal_data={'service':'wan22-i2v','mode':'first_frame','prompt':'walk','explicit_service':False}
                    answer='HERMES_VIDEO_PROPOSAL\n'+json.dumps(proposal_data)+'\nEND_HERMES_VIDEO_PROPOSAL'
                    job_request={'prompt':'animate this image','minimax_preferred':True}
                    image=io.BytesIO();Image.new('RGB',(832,480)).save(image,format='PNG')
                    generation={'action':'generate','prompt':'walk','images':[base64.b64encode(image.getvalue()).decode()],'width':832,'height':480,'frames':124,'steps':8,'seed':42}
                manager.job_storage_root=root/'jobs';manager.job_storage_root.mkdir()
                detail={'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False,'request':job_request}
                request_id=proposal_request_id(session,proposal,service);payload={'session_id':session,'proposal_job_id':proposal,'request_id':request_id,'service':service,'request':generation}
                store=HermesDelegationStore(root/'receipts');calls=[]
                def dispatch(target,command,request):
                    calls.append(command);return run_generation(manager,target,request)
                with patch(manager_path,return_value=manager),patch.object(manager,'history_storage_path',return_value=root/'history'),patch.object(manager,'validate_generation_runtime'),patch.object(manager,'launch_generation_worker',return_value=Mock()),patch('workflow.domains.image.image_generation.threading.Thread'):
                    if service == 'minimax-h3-image':
                        def form_command(action, **fields):
                            return execute_minimax_form_command(
                                'hermes-minimax-form-' + action, {'session_id': session, **fields},
                                sessions=sessions, read_job=lambda _: detail, dispatch=dispatch, receipts=store)
                        form = form_command('prepare', service=service, proposal_job_id=proposal)
                        panel_input = {**form['request'], 'prompt': 'house in a rainy forest'}
                        edited = form_command('save', form_id=form['form_id'], revision=form['revision'], request=panel_input)
                        final = form_command('update', form_id=form['form_id'], revision=edited['revision'], request={'seed': 73})
                        generation = final['request']
                        self.assertEqual((generation['prompt'], generation['seed']), ('house in a rainy forest', 73))
                        payload['request'] = generation
                        accepted = form_command('submit', form_id=form['form_id'], revision=final['revision'])
                    else:
                        accepted=submit_from_proposal(payload,sessions=sessions,read_job=lambda _:detail,dispatch=dispatch,store=store)
                    duplicate=submit_from_proposal(payload,sessions=sessions,read_job=lambda _:detail,dispatch=dispatch,store=store)
                self.assertEqual(calls,['generate']);self.assertTrue(duplicate['duplicate'])
                directory=manager.job_storage_root/accepted['job_id']
                if service=='minimax-h3-image':
                    Image.new('RGB',(16,16)).save(directory/'result.png')
                    write(directory/'result.json',{'image_sha256':hashlib.sha256((directory/'result.png').read_bytes()).hexdigest()})
                    write(directory/'status.json',{'status':'completed'})
                    storage_patch='generators.minimax_h3_image.contracts.STORAGE'
                else:
                    attempt='a'*32;folder=directory/'attempts'/attempt;folder.mkdir(parents=True)
                    write(directory/'status.json',{'status':'completed','attempt':attempt});write(directory/'current-attempt.json',{'id':attempt})
                    hashes=[]
                    for index in range(3):
                        file=folder/f'output-{index:03d}.png';Image.new('RGB',(8,8),(index,0,0)).save(file);hashes.append(hashlib.sha256(file.read_bytes()).hexdigest())
                    (folder/'preview.mp4').write_bytes(b'video')
                    write(folder/'result.json',{'frames':3,'fps':24,'output_sha256':hashes,'video_sha256':hashlib.sha256(b'video').hexdigest()})
                    storage_patch='generators.minimax_h3.contracts.JOB_STORAGE'
                report_job='2026-11-24_12-00-00-12345678';saved={}
                def report_dispatch(command,record):
                    if command=='hermes-submit':saved.update(record);return {'id':report_job}
                    return {'id':report_job,'request':{'request_id':saved['request_id']},'status':{'status':'completed'},'final_response':'분석 보고서','final_response_truncated':False}
                sessions.append_session_request(session,'request_followup','수정한 폼을 대기열에 접수해줘')
                observed=Mock(return_value=[{'observation':'sample'}])
                result=advance_minimax_report(directory,service,report_dispatch,sessions,observe=observed,receipts=store)
                self.assertEqual(result['state'],'completed')
                instructions = saved['prompt'].split('\n', 1)[0]
                self.assertEqual('최종 MP4 표본' in instructions, service == 'minimax-h3-i2v')
                self.assertEqual('결과 PNG를 비교' in instructions, service == 'minimax-h3-image')
                report_input=json.loads(saved['prompt'].split('\n',1)[1])
                self.assertEqual(report_input['evidence']['original_user_request'],'원래 대화의 요청')
                self.assertEqual(report_input['evidence']['subsequent_user_messages'],['수정한 폼을 대기열에 접수해줘'])
                self.assertEqual(report_input['evidence']['user_prompt'],generation['prompt'])
                self.assertIn(generation['prompt'],report_input['evidence']['generation_prompt'])
                with patch(storage_patch,manager.job_storage_root):
                    status=read_report_status({key:payload[key] for key in ('session_id','proposal_job_id','request_id','service')},sessions=sessions,store=store)
                self.assertEqual(status['report']['state'],'completed')
                self.assertEqual(status['report']['generation_state'],'completed')
                messages=sessions.read_session_record(session)['messages']
                self.assertEqual([entry.get('job_id') for entry in messages if not entry.get('result_notice')],[proposal,None,report_job])
                if service == 'minimax-h3-image':
                    self.assertIn(result['evidence']['result_url'], messages[-3]['text'])
                    self.assertIn('작성을 시작', messages[-2]['text'])
                    self.assertEqual([item['role'] for item in messages[-3:-1]], ['assistant', 'assistant'])
                self.assertIn(result['evidence']['result_url'],messages[-1]['text'])

    def test_report_reuses_session_resident_without_injecting_chat_history(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        session = 'b' * 32
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sessions = HermesSessionStore(root / 'sessions')
            sessions.create_session_record(session)
            jobs = root / 'jobs'
            jobs.mkdir()
            manager = HermesServiceManager(jobs, root / 'sessions')
            payload = {'request_id': 'report_' + 'a' * 64, 'report_session_id': session, 'prompt': '비교 보고서'}
            with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident',
                       return_value={'state': 'accepted', 'id': 'resident_test'}) as ensure, \
                 patch('workflow.domains.hermes_agent.resident_chat_executor.launch_resident_chat') as launch:
                job = manager.submit_hermes_job_locked(payload)
                duplicate = manager.submit_hermes_job_locked(payload)
            ensure.assert_called_once_with(session, payload['request_id'])
            self.assertEqual(launch.call_args.args, (jobs / job['id'], 'resident_test', session))
            self.assertEqual(duplicate, {'id':job['id'], 'duplicate':True})
            saved = json.loads((jobs / job['id'] / 'request.json').read_text())
            self.assertEqual(saved['report_session_id'], session)
            self.assertNotIn('context', saved)
