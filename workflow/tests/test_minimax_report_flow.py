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
                self.assertEqual([entry.get('job_id') for entry in messages],[proposal,None,report_job])
                self.assertIn(result['evidence']['result_url'],messages[-1]['text'])
