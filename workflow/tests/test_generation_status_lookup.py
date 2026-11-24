"""상태 자동 갱신은 삭제된 작업 추적만 해제하고 실제 오류를 보존한다."""
import unittest
from unittest.mock import Mock, patch
from workflow.common.generation_status_lookup import read_existing_generation_status


class GenerationStatusLookupTests(unittest.TestCase):
    def test_malformed_history_never_marks_job_deleted(self):
        for current_history_response in (None, {}, {'records':{}}, {'records':''}, {'records':None}, {'records':[None]}, {'records':[{}]}, {'records':[{'id':42}]}, {'records':[{'id':' '}]}, {'records':[{'id':'existing'},{}]}):
            with self.subTest(response=current_history_response):
                current_status_error = ValueError('상태 조회 실패')
                current_command_mock = Mock(side_effect=[current_status_error,current_history_response])
                with self.assertRaisesRegex(ValueError,'이력 조회 응답') as current_raised_error:
                    read_existing_generation_status(current_command_mock,'existing')
                self.assertIs(current_raised_error.exception.__cause__,current_status_error)

    def test_success_does_not_read_history(self):
        current_status_record = {'status':'running'}
        current_command_mock = Mock(return_value=current_status_record)
        self.assertIs(read_existing_generation_status(current_command_mock,'existing'),current_status_record)
        current_command_mock.assert_called_once_with('status',{'id':'existing'})

    def test_missing_job_and_service_errors_remain_distinct(self):
        current_command_mock = Mock(side_effect=[ValueError('missing'),{'records':[]}])
        self.assertIsNone(read_existing_generation_status(current_command_mock,'removed'))
        for current_failure_responses in ([ValueError('corrupt'),{'records':[{'id':'existing'}]}], [ValueError('status failed'),RuntimeError('gateway unavailable')]):
            with self.subTest(responses=current_failure_responses):
                with self.assertRaises((ValueError,RuntimeError)):
                    read_existing_generation_status(Mock(side_effect=current_failure_responses),'existing')

    def test_current_media_result_distinguishes_stale_and_missing(self):
        import subprocess,tempfile,json
        from pathlib import Path
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'media.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MediaJobResult.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');const {MediaResultError,default:MediaJobResult}=require(process.argv[1]);
              const key=props=>MediaJobResult(props).key;
              assert.equal(key({service:'one',id:'job'}),key({service:'one',id:'job',kind:'video'}));
              assert.notEqual(key({service:'one',id:'job'}),key({service:'one',id:'other'}));
              assert.notEqual(key({service:'one',id:'job'}),key({service:'two',id:'job'}));
              assert.notEqual(key({service:'one',id:'job'}),key({service:'one',id:'job',kind:'audio'}));
              const render=(error,stale)=>server.renderToStaticMarkup(React.createElement(MediaResultError,{error,stale}));
              process.stdout.write(JSON.stringify([render('영상 원본 작업 경로 오류',true),render('접속 오류',true),render('접속 오류',false)]));"""
            missing,stale,empty=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True))
        self.assertIn('작업을 찾지 못했습니다',missing);self.assertIn('마지막으로 조회한 결과',missing)
        self.assertIn('마지막으로 조회한 결과',stale);self.assertNotIn('마지막으로 조회한 결과',empty)

    def test_current_flux_pages_retain_distinct_services(self):
        from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        from workflow.common.management_catalog import REACT_REVIEW_PATHS
        self.assertIn('flux-seamless',FLUX_IMAGE_PROFILE_RECORDS)
        self.assertEqual(len({REACT_REVIEW_PATHS[service+'-generator'] for service in FLUX_IMAGE_PROFILE_RECORDS}),len(FLUX_IMAGE_PROFILE_RECORDS))

    def test_cleanup_and_controls_explain_unavailable_state(self):
        import os, subprocess, tempfile
        from pathlib import Path
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            for name in ('HistoryCleanup','GeneratorJobControls','KimodoFrames','SelectedHistoryDeletion','RecordFolder','JobIdentifier'):
                subprocess.run([str(gui/'node_modules/.bin/esbuild'),name+'.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(Path(directory)/(name+'.cjs'))],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),path=require('node:path');
              const component=name=>require(path.join(process.argv[1],name+'.cjs')).default;
              const cleanup=component('HistoryCleanup'),controls=component('GeneratorJobControls'),kimodo=component('KimodoFrames'),selected=component('SelectedHistoryDeletion'),folder=component('RecordFolder'),identifier=component('JobIdentifier');
              const render=value=>server.renderToStaticMarkup(value);
              const html=render(React.createElement(React.Fragment,null,...[1,2].map(i=>React.createElement(cleanup,{key:i,job:'j',service:'kimodo',state:null}))));
              assert.match(html,/삭제하려면 작업 상태를 다시 확인하세요/);
              const ids=[...html.matchAll(/aria-describedby="([^"]+)"/g)].map(match=>match[1]);
              assert.equal(ids.length,2);assert.notEqual(ids[0],ids[1]);
              const action=render(React.createElement(controls,{service:'kimodo',id:'j',state:'running',disabled:true,refresh:()=>{}}));
              assert.match(action,/<button[^>]*disabled[^>]*>작업 중지 검토<\\/button>/);
              assert.notEqual(kimodo({id:'one'}).key,kimodo({id:'two'}).key);
              assert.notEqual(selected({service:'kimodo',id:'one'}).key,selected({service:'kimodo',id:'two'}).key);
              assert.notEqual(folder({service:'kimodo',id:'one'}).key,folder({service:'kimodo',id:'two'}).key);
              assert.notEqual(folder({service:'kimodo',id:'one'}).key,folder({service:'kimodo',id:'one',direct:true}).key);
              assert.notEqual(identifier({id:'one'}).key,identifier({id:'two'}).key);
              assert.notEqual(identifier({id:'one'}).key,identifier({id:'one',label:'실행 ID'}).key);
              const list=render(React.createElement(React.Fragment,null,...['one','two'].map(id=>React.createElement(selected,{key:id,id,service:'kimodo',allowPriority:true}))));
              const allIds=[...list.matchAll(/ id="([^"]+)"/g)].map(match=>match[1]);
              assert.equal(new Set(allIds).size,allIds.length);
              for(const [,id] of list.matchAll(/aria-describedby="([^"]+)"/g))assert.ok(allIds.includes(id));"""
            subprocess.run(['node','-e',script,directory],cwd=gui,check=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_direct_gui_entrypoint_initializes_repository_imports(self):
        import os
        from pathlib import Path
        import subprocess
        import sys
        current_repository_root=Path(__file__).resolve().parents[2]
        current_process_environment=dict(os.environ)
        current_process_environment.pop('PYTHONPATH',None)
        for current_script_name in ('serve.py',):
            with self.subTest(script=current_script_name):
                current_process_result=subprocess.run([sys.executable,str(current_repository_root/'gui'/current_script_name),'--help'],cwd='/tmp',env=current_process_environment,capture_output=True,text=True,timeout=15)
                self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)
                self.assertIn('--port',current_process_result.stdout)
