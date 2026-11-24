"""워크플로우 결과의 실행별 상태 분리 계약."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class WorkflowResultScopeUiTests(unittest.TestCase):
    def test_writer_result_is_keyed_by_job(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'writer.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'WriterResult.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const component=require(process.argv[1]).default;
              if(component({id:'one'}).key===component({id:'two'}).key)process.exit(1);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_choice_views_match_gui_contract(self):
        from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
        from workflow.domains.hermes_agent.workflow_run_store import WorkflowRunStore
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            store = WorkflowRunStore(Path(directory)/'workflow.sqlite3')
            first = create_workflow_step_draft('translation','prompt-translation',{'text':'안녕','target_language':'en'})
            second = create_workflow_step_draft('sound','sfx-dasheng-audiogen',{'prompt':'placeholder'})
            del second['inputs']['prompt']
            second['bindings']['prompt']={'from_step':'translation','output':'text','selection':'user_choice'}
            store.register_workflow_run('run','session',[first,second])
            request = store.claim_ready_step('run','translation')
            store.record_translation_completion('run','translation','job',{'receipt':{'request_id':request['request_id'],'job_id':'job','state':'accepted'},'job':{'id':'job','status':'completed','result':{'text':'hello'}}})
            self.assertIsNone(store.claim_ready_step('run','sound'))
            waiting = store.read_session_run_view('run','session')
            choice = waiting['choices'][0]
            store.select_workflow_output('run','session',choice['step_id'],choice['input_field'],choice['source_request'],choice['digest'])
            selected = store.read_session_run_view('run','session')
            self.assertEqual(selected['choices'][0]['selected'],1)
            script = """import {validWorkflowView} from './workflowViewValidation.mjs';
              if(!JSON.parse(process.argv[1]).every(view=>validWorkflowView(view,'run')))process.exit(1);"""
            subprocess.run(['node','--input-type=module','-e',script,json.dumps([waiting,selected])],cwd=gui,check=True,capture_output=True,text=True)

    def test_retry_history_views_match_gui_contract(self):
        from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
        from workflow.domains.hermes_agent.workflow_run_store import WorkflowRunStore
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            store = WorkflowRunStore(Path(directory)/'workflow.sqlite3')
            step = create_workflow_step_draft('translation','prompt-translation',{'text':'안녕','target_language':'en'})
            store.register_workflow_run('run','session',[step])
            request = store.claim_ready_step('run','translation')
            store.close_unsuccessful_step('run',{'step_id':'translation','request_id':request['request_id']},'failed')
            retry_run = store.retry_failed_step('run','session','translation',request['request_id'])
            views = [store.read_session_run_view(value,'session') for value in ('run',retry_run)]
            self.assertEqual(len(views[0]['retries']),1)
            script = """import {validWorkflowView} from './workflowViewValidation.mjs';
              if(!JSON.parse(process.argv[1]).every(view=>validWorkflowView(view,view.run_id)))process.exit(1);"""
            subprocess.run(['node','--input-type=module','-e',script,json.dumps(views)],cwd=gui,check=True,capture_output=True,text=True)

    def test_completed_translation_view_matches_gui_contract(self):
        from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
        from workflow.domains.hermes_agent.workflow_run_store import WorkflowRunStore
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            store = WorkflowRunStore(Path(directory)/'workflow.sqlite3')
            step = create_workflow_step_draft('translation','prompt-translation',{'text':'안녕','target_language':'en'})
            store.register_workflow_run('run','session',[step])
            request = store.claim_ready_step('run','translation')
            job = 'test-job'
            store.record_translation_completion('run','translation',job,{'receipt':{'request_id':request['request_id'],'job_id':job,'state':'accepted'},'job':{'id':job,'status':'completed','result':{'text':'hello'}}})
            view = store.read_session_run_view('run','session')
            self.assertEqual(view['results'][0]['outputs']['text'],'hello')
            script = """import {validWorkflowView} from './workflowViewValidation.mjs';
              if(!validWorkflowView(JSON.parse(process.argv[1]),'run'))process.exit(1);"""
            subprocess.run(['node','--input-type=module','-e',script,json.dumps(view)],cwd=gui,check=True,capture_output=True,text=True)

    def test_actual_catalog_is_accepted_by_result_screen(self):
        from workflow.domains.hermes_agent.workflow_catalog import read_workflow_generator_catalog
        gui = Path(__file__).resolve().parents[2] / 'gui'
        script = """import {readFileSync} from 'node:fs';
          import vm from 'node:vm';import {untilAborted} from './managementCommand.js';
          const source=readFileSync('./WorkflowResults.jsx','utf8');
          const start=source.indexOf('  useEffect(()=>{\\n    let active=true,timedOut=false;const controller=');
          const marker='  },[call,catalogRevision]);';
          const effect=source.slice(start,source.indexOf(marker,start)+marker.length);
          let accepted=null,error='';const generators=JSON.parse(process.argv[1]);
          const context=vm.createContext({AbortController,untilAborted,useEffect:fn=>fn(),call:async()=>({generators}),
            setTimeout:()=>1,clearTimeout:()=>{},setCatalogError:value=>error=value,setCatalog:value=>accepted=value,
            setCatalogLoading:()=>{},setCatalogReady:()=>{},catalogRevision:0});
          vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));
          if(error || accepted!==generators)throw Error(error || 'catalog rejected');"""
        subprocess.run(['node','--input-type=module','-e',script,json.dumps(read_workflow_generator_catalog())],cwd=gui,check=True,capture_output=True,text=True)

    def test_isolated_store_view_matches_gui_contract(self):
        from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
        from workflow.domains.hermes_agent.workflow_run_store import WorkflowRunStore
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            store = WorkflowRunStore(Path(directory)/'workflow.sqlite3')
            store.register_workflow_run('run','session',[create_workflow_step_draft('motion','kimodo',{'prompt':'Walk forward.'})])
            initial = store.read_session_run_view('run','session')
            store.request_workflow_cancellation('run','session')
            cancelled = store.read_session_run_view('run','session')
            script = """import {validWorkflowView} from './workflowViewValidation.mjs';
              if(!JSON.parse(process.argv[1]).every(view=>validWorkflowView(view,'run')))process.exit(1);"""
            subprocess.run(['node','--input-type=module','-e',script,json.dumps([initial,cancelled])],cwd=gui,check=True,capture_output=True,text=True)

    def test_result_component_is_keyed_by_session_and_run(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'result.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'WorkflowResults.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const component=require(process.argv[1]).default;
              const key=(session,run)=>component({session,run}).key;
              if(key('one','run')===key('two','run') || key('one','run')===key('one','other'))process.exit(1);
              if(key('one','run')!==key('one','run'))process.exit(2);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})


if __name__ == '__main__':
    unittest.main()
