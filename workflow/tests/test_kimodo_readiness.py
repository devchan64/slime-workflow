"""생성기 모델 준비 확인과 모델 관리 이동 계약."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch


class KimodoReadinessTests(unittest.TestCase):
    def run_readiness_javascript(self, checks):
        import os
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'readiness.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ModelReadiness.jsx','--bundle','--platform=node',
                            '--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={search:'?session=abc'};
              global.fetch=()=>{throw Error('render must not dispatch');};
              const assert=require('node:assert/strict'),React=require('react'),server=require('react-dom/server');
              const {default:Page,ModelReadinessMessage,modelReadinessPollDelay,modelPrepareReason,validModelReadiness}=require(process.argv[1]);
              const render=value=>server.renderToStaticMarkup(value);
              """+checks
            result=subprocess.run(['node','-e',script,str(bundle)],cwd=gui,capture_output=True,text=True,
                                  env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(result.returncode,0,result.stderr)
    def test_invalid_readiness_does_not_reach_status_rendering(self):
        self.run_readiness_javascript("""assert.equal(validModelReadiness({ready:false,message:'준비 필요',missing:['모델']}),true);
          assert.equal(validModelReadiness({ready:false,message:'준비',can_prepare:true,prepare_request:{service:'kimodo',command:'prepare',payload:{action:'prepare'}}}),true);
          for(const value of [null,{}, {ready:true,message:'준비',generation_ready:'yes'}, {ready:false,message:'준비',missing:'모델'}, {ready:false,message:'준비',missing:[{}]}, {ready:false,message:'준비',can_prepare:'yes'}, {ready:false,message:'준비',prepare_request:{}}, {ready:false,message:'준비',prepare_request:{service:'kimodo',command:'generate',payload:{}}}])
            assert.equal(validModelReadiness(value),false);""")
    def test_management_readiness_responses_match_ui_validation(self):
        import json
        from http.server import SimpleHTTPRequestHandler
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        statuses = {'ready': False, 'message': '격리된 상태', 'can_prepare': True}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = build_management_application(SimpleHTTPRequestHandler, root, root/'source.json', 8770, [])
            with patch('workflow.common.model_preparation_controls.execute_model_preparation_command', return_value=statuses), \
                 patch('workflow.common.model_preparation_controls.execute_wan13_model_command', return_value=statuses), \
                 TestClient(app) as client:
                services = ('kimodo', 'music-heartmula', 'sfx-dasheng-audiogen', 'wan22-vace', 'wan21-fun-1.3b')
                responses = []
                for service in services:
                    response = client.get('/management/assistant/model-readiness/'+service)
                    self.assertEqual(response.status_code, 200, service)
                    responses.append(response.json())
        self.run_readiness_javascript('for(const item of '+json.dumps(responses, ensure_ascii=False)+') assert.equal(validModelReadiness(item),true);')
    def test_current_readiness_message_distinguishes_assets_and_generation(self):
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'readiness.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ModelReadiness.jsx','--bundle','--platform=node',
                            '--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {ModelReadinessMessage,modelReadinessPollDelay}=require(process.argv[1]);
              const render=(status,error='')=>server.renderToStaticMarkup(React.createElement(ModelReadinessMessage,{service:'kimodo',status,error}));
              if(!render({ready:true,generation_ready:false,message:'실행 환경 필요'}).includes('모델 준비 필요'))throw Error('blocked');
              if(!render({ready:true,message:'준비됨'}).includes('생성 준비 완료'))throw Error('ready');
              if(!render(null,'연결 오류').includes('role="alert"') || !render(null,'연결 오류').includes('모델 상태 조회 실패 · 연결 오류'))throw Error('error');
              if(!render({ready:true,message:'준비됨'}).includes('role="status"'))throw Error('status');
              if(modelReadinessPollDelay({preparation_status:'running'},false)!==5000)throw Error('running');
              if(modelReadinessPollDelay({preparation_status:'queued'},true)!==5000)throw Error('queued');
              if(modelReadinessPollDelay({preparation_status:'idle'},true)!==30000)throw Error('managed');
              if(modelReadinessPollDelay({preparation_status:'idle'},false)!==null)throw Error('idle');"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)

    def test_model_status_requires_loadable_motion_correction(self):
        from generators.kimodo.contracts import inspect_kimodo_assets
        with patch('generators.kimodo.contracts.inspect_motion_correction_runtime', return_value=False):
            current_status_record = inspect_kimodo_assets()
        self.assertFalse(current_status_record['ready'])
        self.assertIn('motion_correction', current_status_record['message'])
        self.assertIn('공식 후처리 motion_correction 실행 환경', current_status_record['missing'])

    def test_missing_postprocess_runs_official_setup_without_redownload(self):
        from generators.kimodo import prepare
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_python_path = Path(current_directory_name) / 'python'
            current_python_path.touch()
            with patch.object(prepare, 'KIMODO_ENVIRONMENT_PYTHON', current_python_path), \
                 patch.object(prepare, 'KIMODO_MODEL_ROOT', Path(current_directory_name)), \
                 patch.object(prepare, 'inspect_kimodo_assets', return_value={'missing': ['공식 후처리 motion_correction 실행 환경']}), \
                 patch.object(prepare, 'install_kimodo_official_runtime') as current_install_mock, \
                 patch.object(prepare, 'download_kimodo_pinned_assets') as current_download_mock:
                prepare.prepare_kimodo_assets()
        current_install_mock.assert_called_once()
        current_download_mock.assert_not_called()

    def test_official_setup_builds_extension_without_replacing_dependencies(self):
        from types import SimpleNamespace
        from contextlib import nullcontext
        from generators.kimodo import prepare
        with patch.object(prepare, 'prepare_kimodo_source_repository'), \
             patch('workflow.common.management_setup.hold_shared_environment_reservation', return_value=nullcontext()), \
             patch.object(prepare, 'inspect_motion_correction_runtime', side_effect=[False, False, True]), \
             patch.object(prepare.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as current_run_mock, \
             patch.object(prepare.subprocess, 'check_output', return_value='/tmp/pybind11-cmake\n'):
            prepare.install_kimodo_official_runtime()
        current_install_call = current_run_mock.call_args_list[-1]
        self.assertIn('--no-deps', current_install_call.args[0])
        self.assertIn('--no-build-isolation', current_install_call.args[0])
        self.assertEqual(current_install_call.kwargs['env']['SKIP_MOTION_CORRECTION_IN_SETUP'], '0')
        self.assertTrue(current_install_call.kwargs['env']['CMAKE_PREFIX_PATH'].startswith('/tmp/pybind11-cmake'))

    def test_kimodo_runtime_setup_preserves_existing_environment(self):
        from generators.kimodo import setup_runtime
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name) / 'runtime'
            current_environment_path.mkdir()
            current_marker_path = current_environment_path / 'keep.txt'
            current_marker_path.write_text('preserve')
            with patch.object(setup_runtime, 'KIMODO_ENVIRONMENT_PYTHON', current_environment_path / 'bin/python'), \
                    patch.object(setup_runtime, 'run_logged_management_command') as current_run_mock:
                with self.assertRaisesRegex(ValueError, '자동 변경하지 않습니다'):
                    setup_runtime.prepare_kimodo_runtime_environment()
            current_run_mock.assert_not_called()
            self.assertEqual(current_marker_path.read_text(), 'preserve')

    def test_existing_kimodo_source_changes_are_not_overwritten(self):
        import subprocess
        from generators.kimodo import prepare
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_source_path = Path(temporary_directory_name) / 'source'
            current_source_path.mkdir()
            subprocess.run(['git', 'init', '-q', str(current_source_path)], check=True)
            subprocess.run(['git', '-C', str(current_source_path), 'config', 'user.email', 'test@example.invalid'], check=True)
            subprocess.run(['git', '-C', str(current_source_path), 'config', 'user.name', 'Test'], check=True)
            current_source_file = current_source_path / 'content.txt'
            current_source_file.write_text('original')
            subprocess.run(['git', '-C', str(current_source_path), 'add', 'content.txt'], check=True)
            subprocess.run(['git', '-C', str(current_source_path), 'commit', '-qm', 'test'], check=True)
            current_revision_value = subprocess.check_output(['git', '-C', str(current_source_path), 'rev-parse', 'HEAD'], text=True).strip()
            with patch.object(prepare, 'KIMODO_SOURCE_ROOT', current_source_path), \
                    patch.object(prepare, 'KIMODO_ASSET_CONFIG', {'source_revision': current_revision_value}):
                self.assertEqual(prepare.prepare_kimodo_source_repository(), current_revision_value)
                current_source_file.write_text('user change')
                with self.assertRaisesRegex(ValueError, '자동 변경하지 않습니다'):
                    prepare.prepare_kimodo_source_repository()
                self.assertEqual(current_source_file.read_text(), 'user change')

    def test_missing_model_links_to_management_without_downloading(self):
        self.run_readiness_javascript("""const html=render(React.createElement(Page,{service:'kimodo'}));
          assert.match(html,/모델 관리로 이동/);assert.match(html,/model=kimodo/);
          assert.match(render(React.createElement(ModelReadinessMessage,{service:'kimodo',status:{ready:false,message:'준비 필요'}})),/모델 준비 필요/);""")

    def test_generation_readiness_and_running_refresh_interval(self):
        self.run_readiness_javascript("""assert.equal(modelReadinessPollDelay({preparation_status:'running'},false),5000);
          assert.match(render(React.createElement(ModelReadinessMessage,{service:'kimodo',status:{ready:true,message:'완료'}})),/생성 준비 완료/);
          assert.match(render(React.createElement(ModelReadinessMessage,{service:'kimodo',status:{ready:true,generation_ready:false,message:'실행 환경 준비 필요'}})),/모델 준비 필요/);""")

    def test_status_failure_offers_navigation_and_blocks_download(self):
        self.run_readiness_javascript("""assert.match(render(React.createElement(ModelReadinessMessage,{service:'kimodo',error:'연결 오류'})),/연결 오류/);
          assert.ok(modelPrepareReason(null,'연결 오류',false));
          assert.match(render(React.createElement(Page,{service:'kimodo'})),/모델 관리로 이동/);""")

    def test_controls_only_provide_status_and_management_link(self):
        self.run_readiness_javascript("""const html=render(React.createElement(Page,{service:'kimodo'}));
          assert.match(html,/모델 준비 상태 확인/);assert.match(html,/모델 관리로 이동/);
          assert.match(html,/session=abc/);assert.doesNotMatch(html,/모델 다운로드 · 이어받기/);""")
