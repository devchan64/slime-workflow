import unittest
import hashlib
import json
import sqlite3
from contextlib import closing
import tempfile
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent.session_queue import append_session_video_jobs, append_session_flux_proposals, append_session_writer_proposals


class SessionQueueTests(unittest.TestCase):
    def test_writer_proposal_receipt_is_visible_in_session_jobs(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.gpu_handoff_kimodo import _derived_id
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        session='a'*32;job='2026-11-18_00-00-00-12345678';writer_job='20261122-130000-abcdef12'
        request_id='writer_'+hashlib.sha256(json.dumps([session,job],separators=(',',':')).encode()).hexdigest()
        answer='HERMES_WRITER_PROPOSAL\n{"mode":"write","prompt":"test"}\nEND_HERMES_WRITER_PROPOSAL'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','test');sessions.attach_session_job(session,'request_12345678',job)
            receipts=HermesDelegationStore(root/'receipts');handoffs=GpuHandoffStore(root/'handoffs')
            bound={'request':{'mode':'write','prompt':'test'},'workspace_fingerprint':'b'*64}
            receipts.execute_service_delegation_once(_derived_id('handoff_',request_id),'writer-agent',bound,lambda _: {'id':writer_job},lambda _:None)
            payload={'session_id':session,'category':'','state':'','search_filters':{}}
            record={'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False}
            with patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore',return_value=receipts),patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=handoffs),patch('workflow.domains.hermes_agent.writer_operations.read_writer_job_review',return_value={'stage':'review'}):
                result=append_session_writer_proposals({'steps':[]},payload,lambda _:record,root/'sessions')
                self.assertEqual(len(result['direct_jobs']),1)
                row=result['direct_jobs'][0]
                self.assertEqual((row['source_kind'],row['source_job_id'],row['state']),('writer_proposal',writer_job,'completed'))
                self.assertEqual(row['proposal_job_id'],job)
                self.assertEqual(append_session_writer_proposals({'steps':[]},{**payload,'category':'image'},lambda _:record,root/'sessions')['direct_jobs'],[])

    def test_writer_unaccepted_withdrawal_and_unreadable_receipt_are_visible(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        session='a'*32;job='2026-11-18_00-00-00-12345678'
        request_id='writer_'+hashlib.sha256(json.dumps([session,job],separators=(',',':')).encode()).hexdigest()
        answer='HERMES_WRITER_PROPOSAL\n{"mode":"write","prompt":"test"}\nEND_HERMES_WRITER_PROPOSAL'
        record={'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False}
        payload={'session_id':session,'category':'','state':'','search_filters':{}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','test');sessions.attach_session_job(session,'request_12345678',job)
            receipts=HermesDelegationStore(root/'receipts');handoffs=GpuHandoffStore(root/'handoffs')
            with patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore',return_value=receipts),patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=handoffs):
                handoffs.withdraw_if_unaccepted(request_id,session,'writer-agent')
                row=append_session_writer_proposals({'steps':[]},payload,lambda _:record,root/'sessions')['direct_jobs'][0]
                self.assertEqual((row['state'],row['handoff_state'],row['source_job_id']),('cancelled','withdrawn',None))
                with patch.object(receipts,'read_service_delegation',side_effect=ValueError('broken')):
                    result=append_session_writer_proposals({'steps':[]},payload,lambda _:record,root/'sessions')
                self.assertEqual(result['direct_jobs'],[]);self.assertEqual(result['writer_proposal_unreadable_count'],1)

    def test_recent_kimodo_result_uses_kimodo_frame_view(self):
        import os,subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'recent.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'RecentGeneratorJobs.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');const {RecentJobResult,validRecentHistorySource:valid}=require(process.argv[1]);
              const source={service:'flux-image',command:'hermes-generator-source-history',result_kind:'flux',video_result:false,result_path:'/management/frame/flux-image/'};
              assert.equal(valid(source),true);for(const bad of [{...source,result_kind:{}},{...source,result_path:'//example.com/'},{...source,result_path:'javascript:alert(1)'},{...source,video_result:'yes'}])assert.equal(valid(bad),false);
              const render=source=>server.renderToStaticMarkup(React.createElement(RecentJobResult,{source,id:'2026-11-18_00-00-00-12345678',choose:()=>{}}));
              process.stdout.write(JSON.stringify([render({service:'kimodo'}),render({service:'flux-image',result_kind:'flux'})]));"""
            kimodo,flux=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}))
        self.assertIn('Kimodo 원본 프레임',kimodo);self.assertIn('작업 결과',flux)

    def test_real_session_handoff_is_visible_until_it_is_cancelled(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore, _canonical_input
        session='a'*32
        proposal_job='2026-11-22_00-00-00-12345678'
        request_id='flux_'+hashlib.sha256(json.dumps([session,proposal_job,'flux-image'],separators=(',',':')).encode()).hexdigest()
        answer='HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        request={'action':'generate','prompt':'blue sky','width':512,'height':512,'seed':42,'steps':16,'images':[],'tag':''}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sessions=HermesSessionStore(root/'sessions')
            sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','이미지 생성')
            sessions.attach_session_job(session,'request_12345678',proposal_job)
            handoffs=GpuHandoffStore(root/'handoffs')
            handoffs.approve(request_id,session,'flux-image',hashlib.sha256(_canonical_input(request)).hexdigest(),
                             target_request=request,resident_id='resident_123',confirmed=True)
            payload={'session_id':session,'category':'image','state':'','search_filters':{}}
            record={'status':{'status':'completed'},'final_response':answer}
            with patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore',return_value=HermesDelegationStore(root/'receipts')), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=handoffs):
                row=append_session_flux_proposals({'steps':[]},payload,lambda _:record,root/'sessions')['direct_jobs'][0]
                self.assertEqual((row['request_id'],row['handoff_state'],row['state']),(request_id,'approved','queued'))
                handoffs.transition(request_id,1,'cancelled')
                row=append_session_flux_proposals({'steps':[]},payload,lambda _:record,root/'sessions')['direct_jobs'][0]
                self.assertEqual((row['handoff_state'],row['state']),('cancelled','cancelled'))

    def test_real_rejected_receipt_and_handoff_recovery_are_visible(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore, _canonical_input
        from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter
        session='a'*32;job='2026-11-22_00-00-00-12345678'
        request_id='flux_'+hashlib.sha256(json.dumps([session,job,'flux-image'],separators=(',',':')).encode()).hexdigest()
        answer='HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        request={'action':'generate','prompt':'blue sky','width':512,'height':512,'seed':42,'steps':16,'images':[],'tag':''}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','이미지 생성');sessions.attach_session_job(session,'request_12345678',job)
            receipts=HermesDelegationStore(root/'receipts');handoffs=GpuHandoffStore(root/'handoffs')
            handoffs.approve(request_id,session,'flux-image',hashlib.sha256(_canonical_input(request)).hexdigest(),target_request=request,resident_id='resident_123',confirmed=True)
            handoffs.transition(request_id,1,'waiting_release');handoffs.transition(request_id,2,'submitting')
            record=handoffs.read(request_id)
            self.assertTrue(FluxHandoffAdapter(delegation_store=receipts).seal_unsubmitted_target(record))
            handoffs.transition(request_id,3,'rejected_reload_queued')
            payload={'session_id':session,'category':'image','state':'','search_filters':{}}
            with patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore',return_value=receipts),patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=handoffs):
                read=lambda:append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer},root/'sessions')['direct_jobs'][0]
                self.assertEqual((read()['handoff_state'],read()['state']),('rejected_reload_queued','running'))
                handoffs.transition(request_id,4,'rejected_reloading')
                self.assertEqual((read()['handoff_state'],read()['state']),('rejected_reloading','running'))
                handoffs.transition(request_id,5,'rejected')
                row=read();self.assertEqual((row['handoff_state'],row['state'],row['source_job_id']),('rejected','failed',None))
                payload['state']='failed';self.assertEqual(read()['request_id'],request_id)

    def test_flux_handoff_is_visible_before_target_receipt_exists(self):
        session='a'*32
        proposal_job='2026-11-22_00-00-00-12345678'
        answer='HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        payload={'session_id':session,'category':'image','state':'queued','search_filters':{}}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore') as handoffs:
            sessions.return_value.read_session_record.return_value={'messages':[{'job_id':proposal_job}]}
            receipts.return_value.read_service_delegation.return_value={'state':'not_found'}
            handoffs.return_value.read.return_value={'session_id':session,'service':'flux-image','state':'waiting_release'}
            result=append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})
            self.assertEqual([(row['proposal_job_id'],row['state']) for row in result['direct_jobs']],[(proposal_job,'queued')])
            self.assertEqual(result['direct_jobs'][0]['handoff_state'],'waiting_release')
            self.assertIsNotNone(result['direct_jobs'][0]['observed_at'])
            payload['search_filters']={'generator':'FLUX','job_id':'12345678'}
            self.assertEqual(len(append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs']),1)
            payload['search_filters']={'job_id':'absent'}
            self.assertEqual(append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'],[])
            payload['search_filters']={}
            payload['state']=''
            for handoff_state, state in [('cancel_reloading','running'),('cancelled','cancelled'),('withdrawn','cancelled'),('rejected_reload_queued','running'),('rejected_reloading','running'),('rejected','failed')]:
                handoffs.return_value.read.return_value={'session_id':session,'service':'flux-image','state':handoff_state}
                row=append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'][0]
                self.assertEqual((row['handoff_state'],row['state']),(handoff_state,state))
            receipts.return_value.read_service_delegation.return_value={'state':'rejected'}
            handoffs.return_value.read.return_value={'session_id':session,'service':'flux-image','state':'rejected_reloading'}
            row=append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'][0]
            self.assertEqual((row['handoff_state'],row['state']),('rejected_reloading','running'))
            handoffs.return_value.read.return_value=None
            row=append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'][0]
            self.assertEqual((row['handoff_state'],row['state']),('rejected','failed'))
            self.assertIsNotNone(row['observed_at'])
            handoffs.return_value.read.side_effect=OSError('unavailable')
            row=append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'][0]
            self.assertEqual((row['receipt_state'],row['handoff_state'],row['state']),('rejected','unknown','failed'))
            handoffs.return_value.read.side_effect=None
            receipts.return_value.read_service_delegation.return_value={'state':'not_found'}
            handoffs.return_value.read.return_value=None
            self.assertEqual(append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'],[])
            handoffs.return_value.read.return_value={'session_id':'b'*32,'service':'flux-image','state':'waiting_release'}
            payload['state']=''
            row=append_session_flux_proposals({'steps':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'][0]
            self.assertEqual(row['state'],'unknown')
            self.assertIsNone(row['observed_at'])

    def test_date_filters_use_korean_day_for_direct_and_workflow_jobs(self):
        from workflow.domains.hermes_agent.session_queue import _matches_created_dates
        from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
        from workflow.domains.hermes_agent.workflow_run_store import WorkflowRunStore
        day = {'created_from':'2026-11-22', 'created_through':'2026-11-22'}
        self.assertTrue(_matches_created_dates('2026-11-21T15:00:00+00:00', day))
        self.assertFalse(_matches_created_dates('2026-11-21T14:59:59+00:00', day))
        self.assertFalse(_matches_created_dates('', day))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workflow.sqlite3'
            store = WorkflowRunStore(path)
            store.register_workflow_run('run', 'session', [create_workflow_step_draft('motion', 'kimodo', {'prompt':'Walk.'})])
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE workflow_step_time SET created_at='2026-11-21 15:00:00'")
            self.assertEqual(len(store.find_session_workflow_steps('session', '', '', day)['steps']), 1)
            self.assertEqual(len(store.find_session_workflow_steps('session', '', '', {'generator':'MODO','job_id':'MOTION'})['steps']), 1)
            self.assertEqual(store.find_session_workflow_steps('session', '', '', {'generator':'absent'})['steps'], [])
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE workflow_step_time SET created_at='2026-11-21 14:59:59'")
            self.assertEqual(store.find_session_workflow_steps('session', '', '', day)['steps'], [])

    def test_date_filter_applies_to_both_direct_receipt_paths(self):
        payload={'session_id':'a'*32,'category':'','state':'',
                 'search_filters':{'created_from':'2026-11-22','created_through':'2026-11-22'}}
        messages=[{'form_id':'b'*32,'created_at':'2026-11-21T15:00:00+00:00'},
                  {'job_id':'2026-11-22_00-00-00-12345678','created_at':'2026-11-21T15:00:00+00:00'}]
        answer='HERMES_FLUX_PROPOSAL\n{"service":"flux-image","prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.session_queue.read_hermes_video_source_job',return_value={'status':'completed'}), \
             patch('workflow.domains.hermes_agent.flux_profile_operations.read_hermes_flux_source_job',return_value={'status':'completed'}):
            sessions.return_value.read_session_record.return_value={'messages':messages}
            receipts.return_value.read_service_delegation.return_value={'state':'accepted','job_id':'job-id'}
            videos=append_session_video_jobs({'steps':[]},payload)
            flux=append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})
            self.assertEqual(len(videos['direct_jobs']),1)
            self.assertEqual(len(flux['direct_jobs']),1)
            payload['search_filters']={'created_from':'2026-11-21','created_through':'2026-11-21'}
            self.assertEqual(append_session_video_jobs({'steps':[]},payload)['direct_jobs'],[])
            self.assertEqual(append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})['direct_jobs'],[])

    def test_real_session_and_receipt_storage_join_through_service(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.flux_profile_operations import submit_hermes_flux_profile
        session='a'*32; other='b'*32
        proposal_job='2026-11-22_00-00-00-12345678'; generated='2026-11-22_09-33-14-f9df6f1e'
        request_id='flux_'+hashlib.sha256(json.dumps([session,proposal_job,'flux-image'],separators=(',',':')).encode()).hexdigest()
        answer='HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        request={'action':'generate','prompt':'blue sky','width':512,'height':512,'seed':42,'steps':16,'images':[],'tag':''}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); sessions=HermesSessionStore(root/'sessions'); receipts=HermesDelegationStore(root/'receipts')
            for session_id in (session,other):
                sessions.create_session_record(session_id)
                sessions.append_session_request(session_id,'request_12345678','이미지 생성')
                sessions.attach_session_job(session_id,'request_12345678',proposal_job)
            job_path=root/'jobs'/proposal_job; job_path.mkdir(parents=True)
            (job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':answer})+'\n')
            manager=HermesServiceManager(hermes_storage_root=root/'jobs',hermes_session_root=root/'sessions')
            with patch('workflow.domains.hermes_agent.flux_profile_operations.HermesDelegationStore',return_value=receipts), \
                 patch('workflow.domains.hermes_agent.flux_profile_operations.call_hermes_flux_profile',return_value={'id':generated}) as dispatch, \
                 patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore',return_value=receipts), \
                 patch('workflow.domains.hermes_agent.flux_profile_operations.read_hermes_flux_source_job',return_value={'status':'completed'}), \
                 patch('workflow.domains.hermes_agent.workflow_commands.execute_workflow_command',return_value={'steps':[],'truncated':False}):
                self.assertEqual(submit_hermes_flux_profile(request_id,'flux-image',request)['job_id'],generated)
                self.assertTrue(submit_hermes_flux_profile(request_id,'flux-image',request)['duplicate'])
                dispatch.assert_called_once()
                def list_session(sid):
                    return manager.execute_hermes_command('hermes-workflow-list',{'session_id':sid,'category':'','state':'','search_filters':{}})
                rows=list_session(session)['direct_jobs']
                self.assertEqual([(row['generator'],row['source_job_id'],row['state']) for row in rows],[('flux-image',generated,'completed')])
                self.assertEqual(list_session(other)['direct_jobs'],[])

    def test_proposal_reader_ignores_unrelated_logs_and_diff(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        job='2026-11-22_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); path=root/job; path.mkdir()
            (path/'status.json').write_text(json.dumps({'status':'completed'}))
            (path/'worker.log').symlink_to('/does/not/exist')
            (path/'change.diff').symlink_to('/does/not/exist')
            with patch('workflow.domains.hermes_agent.service.read_hermes_final_response',return_value=('answer',False)) as answer:
                record=HermesServiceManager(hermes_storage_root=root).read_hermes_proposal_record(job)
            self.assertEqual(record['final_response'],'answer')
            answer.assert_called_once_with(path)
            (path/'status.json').unlink()
            with self.assertRaises(OSError):
                HermesServiceManager(hermes_storage_root=root).read_hermes_proposal_record(job)

    def test_flux_proposal_receipt_belongs_to_session_and_respects_filters(self):
        session='a'*32
        proposal_job='2026-11-22_00-00-00-12345678'
        source_job='2026-11-22_09-33-14-f9df6f1e'
        message={'job_id':proposal_job,'created_at':'2026-11-22T00:00:00+00:00'}
        answer='HERMES_FLUX_PROPOSAL\n{"service":"flux-image","prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        record={'status':{'status':'completed'},'final_response':answer}
        payload={'session_id':session,'category':'image','state':'completed','search_filters':{}}
        expected='flux_'+hashlib.sha256(json.dumps([session,proposal_job,'flux-image'],separators=(',',':')).encode()).hexdigest()
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.flux_profile_operations.read_hermes_flux_source_job',return_value={'status':'completed'}):
            sessions.return_value.read_session_record.return_value={'messages':[message]}
            receipts.return_value.read_service_delegation.return_value={'state':'accepted','job_id':source_job}
            result=append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:record)
            receipts.return_value.read_service_delegation.assert_called_once_with(expected,'flux-image')
            self.assertEqual(result['direct_jobs'][0]['source_job_id'],source_job)
            self.assertEqual(result['direct_jobs'][0]['proposal_job_id'],proposal_job)
            payload['category']='motion'
            self.assertEqual(append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:record)['direct_jobs'],[])

    def test_flux_unreadable_receipt_is_not_treated_as_absent(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        message={'job_id':'2026-11-22_00-00-00-12345678'}
        answer='HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts:
            sessions.return_value.read_session_record.return_value={'messages':[message]}
            receipts.return_value.read_service_delegation.side_effect=OSError('unavailable')
            result=append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:{'status':{'status':'completed'},'final_response':answer})
            self.assertEqual(result['direct_jobs'][0]['state'],'unknown')
            self.assertIsNone(result['direct_jobs'][0]['source_job_id'])

    def test_flux_deduplicates_by_service_and_job_id(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        message={'job_id':'2026-11-22_00-00-00-12345678'}
        job='2026-11-22_09-33-14-f9df6f1e'
        answer='HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.flux_profile_operations.read_hermes_flux_source_job',return_value={'status':'completed'}):
            sessions.return_value.read_session_record.return_value={'messages':[message]}
            receipts.return_value.read_service_delegation.return_value={'state':'accepted','job_id':job}
            read=lambda _:{'status':{'status':'completed'},'final_response':answer}
            other={'steps':[{'generator':'wan22-fun-control','source_job_id':job}],'direct_jobs':[]}
            self.assertEqual(len(append_session_flux_proposals(other,payload,read)['direct_jobs']),1)
            same={'steps':[{'generator':'flux-image','source_job_id':job}],'direct_jobs':[]}
            self.assertEqual(append_session_flux_proposals(same,payload,read)['direct_jobs'],[])

    def test_unreadable_or_truncated_conversation_jobs_are_reported(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        messages=[{'job_id':f'2026-11-22_00-00-0{i}-12345678'} for i in range(3)]
        def read(job):
            if job==messages[0]['job_id']: raise OSError('unavailable')
            if job==messages[1]['job_id']: return {'status':{'status':'completed'},'final_response_truncated':True,'final_response':'cut'}
            return {'status':{'status':'completed'},'final_response':'일반 대화 응답'}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions:
            sessions.return_value.read_session_record.return_value={'messages':messages}
            result=append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,read)
        self.assertEqual(result['flux_proposal_unreadable_count'],2)
        self.assertEqual(result['direct_jobs'],[])

    def test_unknown_job_status_is_not_treated_as_no_proposal(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        message={'job_id':'2026-11-22_00-00-00-12345678'}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions:
            sessions.return_value.read_session_record.return_value={'messages':[message]}
            for status in ('unknown', None, 'unexpected'):
                with self.subTest(status=status):
                    result=append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:{'status':{'status':status}})
                    self.assertEqual(result['flux_proposal_unreadable_count'],1)

    def test_duplicate_conversation_job_is_not_linked_to_wrong_message(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        message={'job_id':'2026-11-22_00-00-00-12345678'}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions:
            sessions.return_value.read_session_record.return_value={'messages':[message,message]}
            result=append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:self.fail('중복 작업 조회 금지'))
        self.assertEqual(result['flux_proposal_unreadable_count'],1)
        self.assertEqual(result['direct_jobs'],[])

    def test_changed_session_snapshot_is_rejected(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions:
            sessions.return_value.read_session_record.return_value={'messages':[]}
            with self.assertRaisesRegex(ValueError,'세션 이력'):
                append_session_flux_proposals({'steps':[],'direct_jobs':[],'session_message_snapshot':'old'},payload,lambda _:None)

    def test_session_changed_during_proposal_scan_is_rejected(self):
        payload={'session_id':'a'*32,'category':'','state':'','search_filters':{}}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions:
            sessions.return_value.read_session_record.side_effect=[{'messages':[]},{'messages':[{'job_id':'2026-11-22_00-00-00-12345678'}]}]
            with self.assertRaisesRegex(ValueError,'세션 이력'):
                append_session_flux_proposals({'steps':[],'direct_jobs':[]},payload,lambda _:None)

    def test_direct_receipts_and_workflow_deduplication(self):
        session = 'a' * 32
        forms = [{'form_id':c * 32,'created_at':'2026-11-21T09:00:00+00:00'} for c in '1234']
        payload = {'session_id':session,'category':'','state':'','search_filters':{}}
        result = {'steps':[{'source_job_id':'job-duplicate'}], 'truncated':False}
        # Forms are examined newest first.
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.session_queue.read_hermes_video_source_job',return_value={'status':'running','queried_at':'now'}):
            sessions.return_value.read_session_record.return_value={'messages':forms}
            receipts.return_value.read_service_delegation.side_effect=[{'state':'accepted','job_id':'job-live'}, {'state':'accepted','job_id':'job-duplicate'}, {'state':'unknown'}, {'state':'not_found'}]
            response=append_session_video_jobs(result,payload)
        self.assertEqual([(row['source_job_id'],row['state']) for row in response['direct_jobs']], [('job-live','running'),(None,'unknown')])
        self.assertEqual(response['steps'],result['steps'])
        self.assertEqual([row['message_offset'] for row in response['direct_jobs']], [0, 2])
        self.assertEqual(response['direct_jobs'][0]['message_snapshot'], hashlib.sha256(json.dumps(forms,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest())
        self.assertEqual(response['direct_jobs'][0]['message_snapshot'], response['direct_jobs'][1]['message_snapshot'])

    def test_filters_and_failed_status_are_not_reported_as_running(self):
        payload={'session_id':'a'*32,'category':'motion','state':'unknown','search_filters':{}}
        result={'steps':[],'truncated':False}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.session_queue.read_hermes_video_source_job',side_effect=OSError('unavailable')):
            sessions.return_value.read_session_record.return_value={'messages':[{'form_id':'b'*32,'created_at':'2026-11-21T09:00:00+00:00'}]}
            receipts.return_value.read_service_delegation.return_value={'state':'accepted','job_id':'job-live'}
            response=append_session_video_jobs(result,payload)
            self.assertEqual(response['direct_jobs'][0]['state'],'unknown')
            payload['search_filters']={'generator':'FUN-CONTROL','job_id':'LIVE'}
            self.assertEqual(len(append_session_video_jobs(result,payload)['direct_jobs']),1)
            payload['search_filters']={'job_id':'absent'}
            self.assertEqual(append_session_video_jobs(result,payload)['direct_jobs'],[])
            payload['search_filters']={}
            payload['category']='image'
            self.assertEqual(append_session_video_jobs(result,payload)['direct_jobs'],[])
