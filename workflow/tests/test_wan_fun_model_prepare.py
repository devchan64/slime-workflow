"""Wan Fun 모델 준비 명령과 상태 표시 계약."""
import unittest
from unittest.mock import Mock

from workflow.common.management_gateway import resolve_management_command


class FunModelPrepareTests(unittest.TestCase):
    def test_rocm_install_applies_shared_constraints_to_each_pip_step(self):
        import os
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from generators.wan_fun import setup_rocm
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_python_path = current_root_path / 'env/bin/python'
            current_python_path.parent.mkdir(parents=True)
            current_python_path.touch()
            (current_root_path / 'env/pyvenv.cfg').touch()
            current_site_path = current_root_path / 'site'
            (current_site_path / 'onnxruntime/capi').mkdir(parents=True)
            (current_site_path / 'onnxruntime/capi/libonnxruntime.so.1').touch()
            with patch.object(setup_rocm, 'FUN_WORKSPACE_DIRECTORY', current_root_path), \
                    patch.object(setup_rocm, 'FUN_ENVIRONMENT_DIRECTORY', current_root_path / 'env'), \
                    patch.object(setup_rocm, 'FUN_PYTHON_EXECUTABLE', current_python_path), \
                    patch.object(setup_rocm, 'ManagementLaunchLogger'), \
                    patch.object(setup_rocm, 'run_logged_management_command') as current_run_mock, \
                    patch.object(setup_rocm.subprocess, 'check_output', return_value=str(current_site_path)), \
                    patch.dict(os.environ, {}, clear=True):
                setup_rocm.setup_fun_rocm_environment()
            current_pip_commands = [current_call.args[0] for current_call in current_run_mock.call_args_list if 'pip' in current_call.args[0]]
            current_telemetry = [command for command in current_pip_commands if '--target' in command]
            self.assertEqual(len(current_telemetry), 1)
            self.assertEqual(current_telemetry[0][current_telemetry[0].index('--target') + 1], str(current_root_path / '.local/otel/wan-fun'))
            current_runtime_commands = [command for command in current_pip_commands if '--target' not in command]
            self.assertEqual(len(current_runtime_commands), 3)
            for current_pip_command in current_runtime_commands:
                self.assertEqual(current_pip_command[current_pip_command.index('-c') + 1], str(setup_rocm.FUN_ROCM_CONSTRAINTS_PATH))
                self.assertEqual(current_pip_command.count('-c'), 2)
                self.assertIn(str(setup_rocm.FUN_MIGRAPHX_CONSTRAINTS_PATH), current_pip_command)

    def test_incomplete_rocm_environment_is_preserved(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from generators.wan_fun import setup_rocm
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_environment_path = current_root_path / 'env'
            current_environment_path.mkdir()
            current_marker_path = current_environment_path / 'keep.txt'
            current_marker_path.write_text('keep')
            with patch.object(setup_rocm, 'FUN_WORKSPACE_DIRECTORY', current_root_path), \
                    patch.object(setup_rocm, 'FUN_ENVIRONMENT_DIRECTORY', current_environment_path), \
                    patch.object(setup_rocm, 'FUN_PYTHON_EXECUTABLE', current_environment_path / 'bin/python'), \
                    patch.object(setup_rocm, 'ManagementLaunchLogger'), \
                    patch.object(setup_rocm, 'run_logged_management_command') as current_run_mock:
                with self.assertRaisesRegex(ValueError, '불완전'):
                    setup_rocm.setup_fun_rocm_environment(prepare_model_assets=False)
            current_run_mock.assert_not_called()
            self.assertEqual(current_marker_path.read_text(), 'keep')

    def test_runtime_only_skips_model_downloads_and_keeps_gpu_validation(self):
        import os
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from generators.wan_fun import setup_rocm
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_python_path = current_root_path / 'env/bin/python'
            current_python_path.parent.mkdir(parents=True)
            current_python_path.touch()
            (current_root_path / 'env/pyvenv.cfg').touch()
            current_site_path = current_root_path / 'site'
            (current_site_path / 'onnxruntime/capi').mkdir(parents=True)
            (current_site_path / 'onnxruntime/capi/libonnxruntime.so.1').touch()
            with patch.object(setup_rocm, 'FUN_WORKSPACE_DIRECTORY', current_root_path), \
                    patch.object(setup_rocm, 'FUN_ENVIRONMENT_DIRECTORY', current_root_path / 'env'), \
                    patch.object(setup_rocm, 'FUN_PYTHON_EXECUTABLE', current_python_path), \
                    patch.object(setup_rocm, 'ManagementLaunchLogger'), \
                    patch.object(setup_rocm, 'run_logged_management_command') as current_run_mock, \
                    patch.object(setup_rocm.subprocess, 'check_output', return_value=str(current_site_path)), \
                    patch.dict(os.environ, {}, clear=True):
                setup_rocm.setup_fun_rocm_environment(prepare_model_assets=False)
            current_command_values = [current_call.args[0] for current_call in current_run_mock.call_args_list]
            self.assertTrue(any(setup_rocm.build_fun_gpu_validation() in current_command for current_command in current_command_values))
            self.assertFalse(any('generators.wan_fun.prepare' in current_command or 'generators.wan_fun.prepare_pose' in current_command for current_command in current_command_values))

    def test_gpu_validation_rejects_non_rocm_even_with_optimization(self):
        import subprocess
        import sys
        from generators.wan_fun.setup_rocm import build_fun_gpu_validation
        current_fake_code = "import sys,types; sys.modules['torch']=types.SimpleNamespace(version=types.SimpleNamespace(hip=None)); sys.modules['migraphx']=types.ModuleType('migraphx'); sys.modules['onnxruntime']=types.ModuleType('onnxruntime'); sys.modules['onnxruntime_ep_migraphx']=types.ModuleType('onnxruntime_ep_migraphx')\n"
        current_check_result = subprocess.run([sys.executable, '-O', '-c', current_fake_code + build_fun_gpu_validation()], capture_output=True, text=True)
        self.assertNotEqual(current_check_result.returncode, 0)
        self.assertIn('ROCm GPU', current_check_result.stderr)

    def test_incompatible_rocm_packages_are_not_replaced_even_with_optimization(self):
        import subprocess
        import sys
        from generators.wan_fun.setup_rocm import build_fun_package_preflight
        current_fake_metadata = "import importlib.metadata as package_metadata; package_metadata.version=lambda current_name: '0.0'\n"
        current_check_result = subprocess.run([sys.executable, '-O', '-c', current_fake_metadata + build_fun_package_preflight()], capture_output=True, text=True)
        self.assertNotEqual(current_check_result.returncode, 0)
        self.assertIn('교체하지 않습니다', current_check_result.stderr)

    def test_prepare_reserves_exclusive_shared_environment(self):
        from workflow.domains.wan_fun.generation import FunControlGenerationManager
        current_manager_value = FunControlGenerationManager()
        self.assertEqual(current_manager_value.select_generation_service({'action': 'prepare'}), 'wan-fun-prepare')
        self.assertEqual(current_manager_value.select_generation_service({'action': 'generate'}), 'wan-fun')

    def test_prepare_uses_shared_job_route(self):
        self.assertEqual(resolve_management_command('wan22-fun-control', 'prepare', {'action': 'prepare'}),
                         ('POST', '/wan22-fun-control/jobs'))
        with self.assertRaises(ValueError):
            resolve_management_command('wan22-fun-control', 'prepare', {'action': 'generate'})

    def test_queued_prepare_disables_duplicate_and_reports_errors(self):
        import subprocess,tempfile
        from pathlib import Path
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'readiness.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ModelReadiness.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const {modelPrepareReason}=require(process.argv[1]);
              if(!modelPrepareReason({ready:false,preparation_status:'queued',prepare_request:{}},'',false).includes('진행 중'))throw Error('queued');
              if(!modelPrepareReason(null,'연결 실패',false).includes('다시 확인'))throw Error('error');"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True)

    def test_completed_single_file_keeps_recovered_byte_count(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace
        from unittest.mock import patch
        from workflow.common import model_huggingface_download
        from workflow.common.model_download_records import list_model_download_records, track_model_download
        with TemporaryDirectory() as current_temporary_root:
            current_root_path = Path(current_temporary_root)
            current_probe_value = SimpleNamespace(filename='vae.bin', file_size=100, is_cached=False,
                                                  will_download=True, commit_hash='a'*40,
                                                  local_path=str(current_root_path/'vae.bin'))
            def fake_hub_download(repo_id, filename, *, local_dir=None, revision=None, dry_run=False, tqdm_class=None):
                return current_probe_value if dry_run else str(current_root_path/'vae.bin')
            def fake_partial_recovery(*current_args, resume_report_callback=None, **current_kwargs):
                resume_report_callback(40)
                current_progress_record = list_model_download_records(current_root_path/'records')[0]
                self.assertEqual((current_progress_record['bytes'], current_progress_record['resumed_bytes']), (40, 40))
                return True
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_root_path/'records')), \
                    patch('huggingface_hub.hf_hub_download', fake_hub_download), \
                    patch('workflow.common.model_huggingface_recovery.recover_huggingface_partial', fake_partial_recovery):
                model_huggingface_download.tracked_hf_hub_download('Comfy-Org/Wan-2.1', 'vae.bin', revision='a'*40, local_dir=current_root_path)
            current_result_record = list_model_download_records(current_root_path/'records')[0]
            self.assertEqual((current_result_record['status'], current_result_record['resumed_bytes']), ('completed', 40))

    def test_management_page_uses_wan_prepare_and_reports_queue(self):
        from workflow.common.model_preparation_controls import execute_model_preparation_command
        commands=[]
        def execute(service,command,payload):
            commands.append((service,command,payload))
            if command=='model-status':return {'ready':False,'message':'모델 준비 필요'}
            if command=='history':return {'records':[{'request':{'action':'prepare'},'status':{'status':'queued'}}]}
            if command=='prepare':return {'id':'test','status':'queued'}
            raise AssertionError(command)
        status=execute_model_preparation_command('wan22-fun-control','model-status',{},execute)
        self.assertEqual(status['preparation_status'],'queued');self.assertIn('대기 중',status['message'])
        self.assertEqual(execute_model_preparation_command('wan22-fun-control','prepare',{'action':'prepare'},execute)['status'],'queued')
        self.assertIn(('wan22-fun-control','prepare',{'action':'prepare'}),commands)

    def test_management_allows_retry_after_failed_preparation_with_existing_files(self):
        from workflow.common.model_preparation_controls import execute_model_preparation_command
        def execute(service,command,payload):
            if command=='model-status':return {'ready':True,'message':'모델 파일 준비 완료'}
            return {'records':[{'request':{'action':'prepare'},'status':{'status':'failed'}}]}
        status=execute_model_preparation_command('wan22-fun-control','model-status',{},execute)
        self.assertFalse(status['ready']);self.assertEqual(status['preparation_status'],'failed');self.assertIn('실패',status['message'])
