"""격리된 워크플로우 목록과 GUI 응답 계약을 연결한다."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
from workflow.domains.hermes_agent.workflow_run_store import WorkflowRunStore


class SessionQueueUiContractTests(unittest.TestCase):
    def test_filter_inputs_reference_the_shared_search_help(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'queue.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'QueuePanel.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Queue=require(process.argv[1]).default;
              const html=server.renderToStaticMarkup(React.createElement(Queue,{session:'session',call:()=>{throw Error('unexpected request')}}));
              const help=html.match(/<small id="([^"]+)">날짜 기준/);assert.ok(help);
              const fields=[...html.matchAll(/<input[^>]*aria-describedby="([^"]+)"[^>]*>/g)];
              assert.equal(fields.length,5);for(const [,describedBy] of fields)assert.ok(describedBy.split(' ').includes(help[1]));"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def assert_ui_accepts(self,result):
        gui=Path(__file__).resolve().parents[2]/'gui'
        script="""import {validSessionQueueResult} from './sessionQueueValidation.mjs';
          const value=JSON.parse(process.argv[1]);if(!validSessionQueueResult(value))throw Error('actual workflow list was rejected');"""
        subprocess.run(['node','--input-type=module','-e',script,json.dumps(result)],cwd=gui,check=True,capture_output=True,text=True)

    def test_actual_workflow_list_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            store=WorkflowRunStore(Path(directory)/'workflow.sqlite3')
            step=create_workflow_step_draft('motion','kimodo',{'prompt':'Walk forward.'})
            store.register_workflow_run('run','session',[step])
            result=store.find_session_workflow_steps('session','','')
            self.assertEqual(len(result['steps']),1)
            self.assert_ui_accepts(result)

    def test_actual_direct_writer_receipt_is_accepted(self):
        from workflow.domains.hermes_agent.session_queue import append_session_writer_proposals
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.gpu_handoff_kimodo import _derived_id
        session='a'*32;job='2026-11-18_00-00-00-12345678'
        request_id='writer_'+hashlib.sha256(json.dumps([session,job],separators=(',',':')).encode()).hexdigest()
        answer='HERMES_WRITER_PROPOSAL\n{"mode":"write","prompt":"test"}\nEND_HERMES_WRITER_PROPOSAL'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','test');sessions.attach_session_job(session,'request_12345678',job)
            receipts=HermesDelegationStore(root/'receipts');handoffs=GpuHandoffStore(root/'handoffs')
            bound={'request':{'mode':'write','prompt':'test'},'workspace_fingerprint':'b'*64}
            receipts.execute_service_delegation_once(_derived_id('handoff_',request_id),'writer-agent',bound,lambda _: {'id':'20261122-130000-abcdef12'},lambda _:None)
            record={'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False}
            payload={'session_id':session,'category':'','state':'','search_filters':{}}
            with patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore',return_value=receipts),patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=handoffs),patch('workflow.domains.hermes_agent.writer_operations.read_writer_job_review',return_value={'stage':'review'}):
                result=append_session_writer_proposals({'steps':[]},payload,lambda _:record,root/'sessions')
            self.assertEqual(len(result['direct_jobs']),1)
            self.assert_ui_accepts(result)
