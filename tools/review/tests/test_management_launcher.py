"""실행·설치 분리와 공용 실행기의 인자·실패·종료 계약."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import signal
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.review.common import management_launcher, management_process, management_setup


class ManagementLauncherTests(unittest.TestCase):
    def setUp(self):
        from tools.review.common import gpu_job_queue
        self.queue_temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.queue_temporary_directory.cleanup)
        self.queue_directory_patch = patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', Path(self.queue_temporary_directory.name) / 'queue')
        self.queue_directory_patch.start()
        self.addCleanup(self.queue_directory_patch.stop)

    def test_setup_plan_is_read_only_and_reports_models_and_missing_management(self):
        import json
        from tools.review.common import management_setup_plan
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_missing_path = Path(temporary_directory_name) / 'missing'
            current_output_stream = io.StringIO()
            with patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(current_missing_path)}, clear=True), \
                    patch.object(management_setup_plan, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), \
                    patch.object(management_launcher, 'ManagementLaunchLogger') as current_logger_mock, \
                    patch.object(management_launcher, 'prepare_management_environments') as current_prepare_mock, \
                    contextlib.redirect_stdout(current_output_stream):
                self.assertEqual(management_launcher.run_management_launcher(['setup', '--scope', 'writer-runtime', '--plan']), 0)
            current_plan_record = json.loads(current_output_stream.getvalue())
            self.assertIn('.model/writer-agent', current_plan_record['targets'])
            self.assertIn('모델 두 개', current_plan_record['models'])
            self.assertTrue(current_plan_record['missing_requirements'])
            self.assertFalse(current_missing_path.exists())
            current_logger_mock.assert_not_called()
            current_prepare_mock.assert_not_called()

    def test_setup_plan_reports_workspace_disk_without_mutating(self):
        from tools.review.common import management_setup_plan
        with patch.object(management_setup_plan.shutil, 'disk_usage', return_value=__import__('collections').namedtuple('DiskValues', 'total used free')(9 * 1024 * 1024, 4 * 1024 * 1024, 5 * 1024 * 1024)):
            current_plan_record = management_setup_plan.describe_management_setup('management')
        self.assertEqual(current_plan_record['workspace_free_mib'], 5)
        with patch.object(management_setup_plan.shutil, 'disk_usage', side_effect=OSError('unavailable')):
            current_unknown_plan = management_setup_plan.describe_management_setup('management')
        self.assertIsNone(current_unknown_plan['workspace_free_mib'])

    def test_setup_plan_reports_kimodo_source_and_renderer_override(self):
        from tools.review.common import management_setup_plan
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_frontend_path = Path(temporary_directory_name) / 'frontend'
            with patch.dict(os.environ, {'FRONTEND_REPOSITORY_PATH': str(current_frontend_path)}, clear=True):
                current_kimodo_plan = management_setup_plan.describe_management_setup('kimodo-runtime')
                current_renderer_plan = management_setup_plan.describe_management_setup('renderer')
            self.assertIn('.local/kimodo/upstream', current_kimodo_plan['targets'])
            self.assertIn('공식 고정 소스', current_kimodo_plan['downloads'])
            self.assertIn(str(current_frontend_path / '.tmp/field-renderer'), current_renderer_plan['targets'])
            self.assertTrue(any('package.json' in current_requirement_message for current_requirement_message in current_renderer_plan['missing_requirements']))
            for current_package_name in ('esbuild', 'phaser', 'yaml'):
                self.assertTrue(any(current_package_name in current_requirement_message and 'npm ci' in current_requirement_message for current_requirement_message in current_renderer_plan['missing_requirements']))
            self.assertFalse(current_frontend_path.exists())
            current_existing_runtime = Path(temporary_directory_name) / '.venv-music-heartmula'
            current_existing_runtime.mkdir()
            with patch.object(management_setup_plan, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)):
                current_music_plan = management_setup_plan.describe_management_setup('heartmula-runtime')
            self.assertTrue(current_music_plan['existing_blockers'])
            self.assertTrue(current_existing_runtime.is_dir())

    def test_management_group_includes_startup_watch_and_handoff_contracts(self):
        from tools.review.tests import run_management_audit
        current_group_modules = run_management_audit.MANAGEMENT_AUDIT_GROUPS['management']
        current_module_suffixes = {current_module_name.rsplit('.', 1)[-1] for current_module_name in current_group_modules}
        self.assertTrue({'test_content_launch_config', 'test_gateway_existing_process', 'test_gateway_watch',
                         'test_review_startup', 'test_review_watch', 'test_management_launcher'} <= current_module_suffixes)
        self.assertEqual(len(current_group_modules), len(set(current_group_modules)))
        self.assertTrue(set(current_group_modules) <= set(run_management_audit.MANAGEMENT_AUDIT_MODULES))

    def test_diagnostics_reports_unreadable_and_unseen_reservations_without_removing_them(self):
        import json
        from tools.review.common import gpu_job_queue
        from tools.review.common.management_diagnostics import inspect_gpu_queue_reservations
        current_active_directory = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active'
        current_active_directory.mkdir(parents=True)
        current_invalid_path = current_active_directory / 'invalid.json'
        current_invalid_path.write_text('{')
        current_stale_path = current_active_directory / 'setup.json'
        current_stale_path.write_text(json.dumps({'pid':99999999,'pid_start_token':'old','service':'management-setup'}))
        current_reservation_result = inspect_gpu_queue_reservations()
        self.assertEqual(current_reservation_result['status'], 'available')
        self.assertIn({'reservation_file':'invalid.json','service':'unknown','process':'unreadable'}, current_reservation_result['reservations'])
        self.assertIn({'reservation_file':'setup.json','service':'management-setup','pid':99999999,'process':'not_seen_check_host'}, current_reservation_result['reservations'])
        self.assertTrue(current_invalid_path.exists())
        self.assertTrue(current_stale_path.exists())

    def test_shared_environment_reservation_blocks_gpu_start_without_holding_queue_lock(self):
        from tools.review.common import gpu_job_queue
        import fcntl
        with management_setup.hold_shared_environment_reservation():
            current_active_paths = list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json'))
            self.assertEqual(len(current_active_paths), 1)
            current_reservation_record = __import__('json').loads(current_active_paths[0].read_text())
            self.assertEqual(current_reservation_record['service'], 'management-setup')
            self.assertIsNone(gpu_job_queue.select_runnable_ticket(999999, 'vram', ['management-setup']))
            with (gpu_job_queue.GPU_QUEUE_DIRECTORY / 'execution.lock').open('a') as current_lock_stream:
                fcntl.flock(current_lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertFalse(gpu_job_queue.recover_stale_hermes_reservation(current_reservation_record))
        self.assertEqual(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json')), [])

    def test_failed_setup_releases_its_own_reservation(self):
        from tools.review.common import gpu_job_queue
        with self.assertRaisesRegex(RuntimeError, '설치 실패'):
            with management_setup.hold_shared_environment_reservation():
                raise RuntimeError('설치 실패')
        self.assertEqual(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json')), [])

    def test_shared_environment_setup_rejects_existing_gpu_reservation(self):
        from tools.review.common import gpu_job_queue
        current_active_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active'
        current_active_path.mkdir(parents=True)
        current_job_reservation = current_active_path / 'existing.json'
        current_job_reservation.write_text('{}')
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.object(management_setup, 'IMAGE_ENVIRONMENT_PATH', Path(temporary_directory_name) / 'shared'), \
                patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(Path(temporary_directory_name) / 'shared')}, clear=True), \
                patch.object(management_setup, 'run_logged_management_command') as setup_command_mock:
            with self.assertRaisesRegex(RuntimeError, 'GPU 작업'):
                management_setup.prepare_management_environments(None, 'management')
            setup_command_mock.assert_not_called()
        self.assertTrue(current_job_reservation.is_file())

    def test_gui_source_argument_overrides_environment_without_duplicate(self):
        with patch.dict(os.environ, {'FRONTEND_REPOSITORY_PATH': '/unused/frontend', 'REVIEW_SERVER_PORT': '9890'}):
            selected_command_values = management_launcher.build_management_launch_command('gui', ['--root', '/tmp/review folder', '--port', '9891'])
        self.assertNotIn('--frontend-repo', selected_command_values)
        self.assertEqual(selected_command_values[-4:], ['--root', '/tmp/review folder', '--port', '9891'])
        self.assertNotIn('pip', selected_command_values)

    def test_gateway_does_not_require_frontend_or_gradio(self):
        with patch.dict(os.environ, {'FRONTEND_REPOSITORY_PATH': '/missing/frontend', 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': '/missing/gradio', 'MANAGEMENT_GATEWAY_PORT': '9892'}):
            selected_command_values = management_launcher.build_management_launch_command('gateway', ['--writer-agent-config', '/tmp/config with spaces.yaml'])
        self.assertIn('9892', selected_command_values)
        self.assertEqual(selected_command_values[-1], '/tmp/config with spaces.yaml')

    def test_snapshot_worker_uses_independent_launcher_without_gui_ports(self):
        with patch.dict(os.environ,{'MANAGEMENT_GATEWAY_PORT':'9892','REVIEW_SERVER_PORT':'9890',
                'FRONTEND_REPOSITORY_PATH':'/missing/frontend','MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH':'/missing/gradio'}):
            current_launch_command=management_launcher.build_management_launch_command('snapshot',['--server','http://127.0.0.1:9892','--once'])
        self.assertTrue(current_launch_command[1].endswith('maintenance/content_snapshot_worker.py'))
        self.assertEqual(current_launch_command[2:],['--server','http://127.0.0.1:9892','--once'])

    def test_service_commands_use_existing_gateway_cli(self):
        with patch.object(management_launcher.subprocess, 'run') as gateway_cli_mock:
            gateway_cli_mock.return_value.returncode = 12
            current_exit_code = management_launcher.run_management_launcher(['command', 'hermes-model', 'prepare'])
            self.assertEqual(current_exit_code, 12)
            current_command_values = gateway_cli_mock.call_args.args[0]
            self.assertEqual(current_command_values[-3:], ['command', 'hermes-model', 'prepare'])
            self.assertEqual(Path(current_command_values[0]), management_launcher.resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python')
            self.assertEqual(Path(current_command_values[1]), management_launcher.WORKFLOW_ROOT_DIRECTORY / 'tools/manager.py')

    def test_missing_environment_fails_without_installing(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': temporary_directory_name}), patch.object(management_launcher.subprocess, 'Popen') as command_process_mock:
            with self.assertRaisesRegex(ValueError, 'setup_management.sh'):
                management_launcher.build_management_launch_command('gateway', [])
            command_process_mock.assert_not_called()

    def test_relative_environment_uses_repository_root(self):
        with patch.dict(os.environ, {'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': '.tmp/custom environment'}):
            selected_environment_path = management_launcher.resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv-management')
        self.assertEqual(selected_environment_path, management_launcher.WORKFLOW_ROOT_DIRECTORY/'.tmp/custom environment')

    def test_setup_prepares_image_and_separate_management_environment(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_image_path = current_root_path / 'image'
            current_shared_path = current_root_path / 'runtime'
            current_frontend_path = current_root_path / 'frontend'
            current_package_path = current_frontend_path / 'packages/field-renderer/package.json'
            current_package_path.parent.mkdir(parents=True)
            current_package_path.write_text('{"version":"1.0.0"}')
            with patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(current_shared_path), 'FRONTEND_REPOSITORY_PATH': str(current_frontend_path)}, clear=True), \
                    patch.object(management_setup, 'IMAGE_ENVIRONMENT_PATH', current_image_path), \
                    patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
                management_launcher.prepare_management_environments(None)
        command_argument_records = [current_call_value.args[0] for current_call_value in run_command_mock.call_args_list]
        current_image_commands = [current_command for current_command in command_argument_records if current_command[0] == str(current_image_path / 'bin/python')]
        current_shared_commands = [current_command for current_command in command_argument_records if current_command[0] == str(current_shared_path / 'bin/python')]
        self.assertTrue(any(management_setup.IMAGE_ROCM_INDEX_URL in current_command for current_command in current_image_commands))
        self.assertTrue(any(str(management_setup.IMAGE_REQUIREMENTS_PATH) in current_command and str(management_setup.IMAGE_CONSTRAINTS_PATH) in current_command for current_command in current_image_commands))
        self.assertTrue(any('QwenImage21Pipeline' in ' '.join(current_command) for current_command in current_image_commands))
        self.assertTrue(any('ModularPipeline' in ' '.join(current_command) and '_get_qkv_projections' in ' '.join(current_command) for current_command in current_image_commands))
        self.assertTrue(any(str(management_setup.WORKFLOW_ROOT_DIRECTORY / 'tools/review/requirements.txt') in current_command for current_command in current_shared_commands))
        self.assertFalse(any(management_setup.IMAGE_ROCM_INDEX_URL in current_command for current_command in current_shared_commands))
        self.assertIn(['npm', '--prefix', str(current_frontend_path), 'run', 'build:field-renderer'], command_argument_records)

    def test_setup_uses_constraints_for_shared_image_environment(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_image_path = Path(temporary_directory_name) / 'image'
            current_frontend_path = Path(temporary_directory_name) / 'frontend'
            current_package_path = current_frontend_path / 'packages/field-renderer/package.json'
            current_package_path.parent.mkdir(parents=True)
            current_package_path.write_text('{"version":"1.0.0"}')
            with patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(current_image_path), 'FRONTEND_REPOSITORY_PATH': str(current_frontend_path)}, clear=True), \
                    patch.object(management_setup, 'IMAGE_ENVIRONMENT_PATH', current_image_path), \
                    patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
                management_launcher.prepare_management_environments(None)
        command_argument_records = [current_call_value.args[0] for current_call_value in run_command_mock.call_args_list]
        current_gui_install = next(current_command for current_command in command_argument_records if str(management_setup.WORKFLOW_ROOT_DIRECTORY / 'tools/review/requirements.txt') in current_command)
        self.assertIn(str(management_setup.IMAGE_CONSTRAINTS_PATH), current_gui_install)
        self.assertEqual(sum('venv' in current_command for current_command in command_argument_records), 1)

    def test_management_only_setup_skips_gpu_and_renderer(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': temporary_directory_name}, clear=True), \
                patch.object(management_setup, 'prepare_image_runtime_environment') as image_prepare_mock, \
                patch.object(management_setup, 'prepare_management_renderer') as renderer_prepare_mock, \
                patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
            management_setup.prepare_management_environments(None, 'management')
            image_prepare_mock.assert_not_called()
            renderer_prepare_mock.assert_not_called()
            self.assertTrue(any('requirements.txt' in str(current_call.args[0]) for current_call in run_command_mock.call_args_list))

    def test_image_scope_does_not_prepare_gui_or_renderer(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.object(management_setup, 'IMAGE_ENVIRONMENT_PATH', Path(temporary_directory_name)), \
                patch.object(management_setup, 'prepare_image_runtime_environment') as image_prepare_mock, \
                patch.object(management_setup, 'prepare_management_renderer') as renderer_prepare_mock, \
                patch.object(management_setup, 'run_logged_management_command'):
            management_setup.prepare_management_environments(None, 'image')
            image_prepare_mock.assert_called_once()
            renderer_prepare_mock.assert_not_called()

    def test_read_only_diagnostics_reports_missing_without_creating_environment(self):
        from tools.review.common.management_diagnostics import inspect_management_environment
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(Path(temporary_directory_name) / 'missing')}, clear=True), \
                patch('tools.review.common.gpu_status.read_gpu_status', return_value={'status': 'unavailable', 'processes': []}), \
                contextlib.redirect_stdout(io.StringIO()) as diagnostic_output_stream:
            self.assertEqual(inspect_management_environment(), 1)
            self.assertFalse((Path(temporary_directory_name) / 'missing').exists())
            self.assertIn('missing', diagnostic_output_stream.getvalue())

    def test_dependency_diagnostics_uses_checker_without_importing_its_packages(self):
        from tools.review.common import management_diagnostics
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name) / 'environment'
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(current_environment_path)], check=True)
            current_site_directory = next(current_environment_path.glob('lib/python*/site-packages'))
            current_metadata_directory = current_site_directory / 'trial_package-1.0.dist-info'
            current_metadata_directory.mkdir()
            (current_metadata_directory / 'METADATA').write_text('Metadata-Version: 2.1\nName: trial-package\nVersion: 1.0\nRequires-Dist: packaging\n')
            with patch.object(management_diagnostics, 'resolve_management_environment', return_value=Path(sys.prefix)):
                current_conflict_record = management_diagnostics.inspect_environment_dependencies(current_environment_path)
            self.assertEqual(current_conflict_record['status'], 'inconsistent')
            self.assertTrue(any('packaging' in current_issue for current_issue in current_conflict_record['issues']))

    def test_dependency_diagnostics_checks_metadata_without_running_pth_code(self):
        from tools.review.common.management_diagnostics import inspect_environment_dependencies
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name) / 'environment'
            subprocess.run([sys.executable, '-m', 'venv', str(current_environment_path)], check=True)
            current_site_directory = next(current_environment_path.glob('lib/python*/site-packages'))
            current_metadata_directory = current_site_directory / 'trial_package-1.0.dist-info'
            current_metadata_directory.mkdir()
            (current_metadata_directory / 'METADATA').write_text('Metadata-Version: 2.1\nName: trial-package\nVersion: 1.0\nRequires-Dist: absent-trial-package>=1\n')
            current_marker_path = Path(temporary_directory_name) / 'must-not-exist'
            current_pth_file = current_site_directory / 'unsafe.pth'
            current_pth_file.write_text("import pathlib; pathlib.Path(" + repr(str(current_marker_path)) + ").touch()\n")
            current_uncertain_record = inspect_environment_dependencies(current_environment_path)
            self.assertEqual(current_uncertain_record['status'], 'unknown')
            self.assertTrue(any('absent-trial-package' in current_issue for current_issue in current_uncertain_record['issues']))
            self.assertFalse(current_marker_path.exists())
            current_pth_file.unlink()
            current_conflict_record = inspect_environment_dependencies(current_environment_path)
            self.assertEqual(current_conflict_record['status'], 'inconsistent')
            self.assertFalse(current_marker_path.exists())

    def test_diagnostics_guidance_preserves_existing_generator_environments(self):
        from tools.review.common.management_diagnostics import attach_environment_recovery_guidance
        current_check_names = ('gradio_python', 'frontend_source', 'hermes_mcp', 'writer_server',
                               'kimodo_python', 'wan_fun_python', 'heartmula_python', 'sfx_python', 'hermes_model')
        current_check_records = {current_check_name: {'status': 'unknown'} for current_check_name in current_check_names}
        attach_environment_recovery_guidance(current_check_records)
        self.assertIn('--scope kimodo-runtime', current_check_records['kimodo_python']['next'])
        self.assertIn('자동 변경하지 않습니다', current_check_records['kimodo_python']['recovery_note'])
        self.assertIn('자동 변경하지 않습니다', current_check_records['heartmula_python']['recovery_note'])
        self.assertIn('모델 두 개', current_check_records['writer_server']['recovery_note'])
        self.assertIn('model prepare hermes-model', current_check_records['hermes_model']['prepare'])

    def test_system_memory_diagnostic_reports_swap_and_unknown_without_writing(self):
        from tools.review.common.management_diagnostics import inspect_system_memory
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_memory_path = Path(temporary_directory_name) / 'meminfo'
            current_memory_path.write_text('MemTotal: 8192 kB\nMemAvailable: 4096 kB\nSwapTotal: 2048 kB\nSwapFree: 512 kB\n')
            current_memory_record = inspect_system_memory(current_memory_path)
            self.assertEqual(current_memory_record['status'], 'observed')
            self.assertEqual(current_memory_record['available_mib'], 4)
            self.assertEqual(current_memory_record['swap_used_mib'], 1)
            current_memory_path.write_text('MemTotal: 1 kB\n')
            self.assertEqual(inspect_system_memory(current_memory_path)['status'], 'unknown')
            self.assertEqual(len(list(Path(temporary_directory_name).iterdir())), 1)

    def test_image_diagnostics_uses_worker_path_not_management_override(self):
        from tools.review.common import management_diagnostics
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_trial_root = Path(temporary_directory_name)
            current_worker_root = current_trial_root / '.venv'
            current_management_root = current_trial_root / 'management'
            (current_worker_root / 'bin').mkdir(parents=True)
            (current_worker_root / 'bin/python').symlink_to(sys.executable)
            current_before_paths = set(current_trial_root.rglob('*'))
            with patch.object(management_diagnostics, 'WORKFLOW_ROOT_DIRECTORY', current_trial_root), \
                    patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(current_management_root)}, clear=True):
                current_image_record = management_diagnostics.inspect_image_worker_environment()
            self.assertEqual(current_image_record['path'], str(current_worker_root))
            self.assertIn('av', current_image_record['missing_modules'])
            self.assertEqual(current_image_record['status'], 'missing_packages')
            self.assertEqual(set(current_trial_root.rglob('*')), current_before_paths)
            self.assertFalse(current_management_root.exists())

    def test_diagnostics_detects_missing_python_packages_without_writing(self):
        from tools.review.common.management_diagnostics import inspect_management_python
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name)
            (current_environment_path / 'bin').mkdir()
            (current_environment_path / 'bin/python').symlink_to(sys.executable)
            current_before_paths = set(current_environment_path.rglob('*'))
            current_check_result = inspect_management_python(current_environment_path, ('json', 'slime_nonexistent_module_5729'))
            self.assertEqual(current_check_result['status'], 'missing_packages')
            self.assertEqual(current_check_result['missing_modules'], ['slime_nonexistent_module_5729'])
            self.assertEqual(set(current_environment_path.rglob('*')), current_before_paths)

    def test_python_diagnostics_does_not_execute_pth_code(self):
        from tools.review.common.management_diagnostics import inspect_management_python
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name)
            current_site_path = current_environment_path / 'lib/python3.14/site-packages'
            current_site_path.mkdir(parents=True)
            current_marker_path = current_environment_path / 'executed'
            (current_environment_path / 'bin').mkdir()
            (current_environment_path / 'bin/python').symlink_to(sys.executable)
            (current_site_path / 'fixture.pth').write_text('import pathlib; pathlib.Path(' + repr(str(current_marker_path)) + ').touch()\n')
            current_result_record = inspect_management_python(current_environment_path, ('json',))
            self.assertEqual(current_result_record['status'], 'present')
            self.assertTrue(current_result_record['path_setup_code_skipped'])
            self.assertFalse(current_marker_path.exists())

    def test_diagnostics_reports_shared_and_missing_path_references(self):
        from tools.review.common.management_diagnostics import inspect_environment_path_references
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name)
            current_site_path = current_environment_path / 'lib/python3.14/site-packages'
            current_site_path.mkdir(parents=True)
            (current_site_path / 'available').mkdir()
            (current_site_path / 'fixture.pth').write_text('available\nmissing\nimport os\n')
            current_reference_record = inspect_environment_path_references(current_environment_path)
            self.assertEqual(current_reference_record, {'files':1, 'present':1, 'missing':1, 'executable_lines':1, 'unreadable':0})

    def test_audio_diagnostics_uses_service_contract_runtime_path(self):
        from types import SimpleNamespace
        from tools.review.common import management_diagnostics
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_management_python = current_root_path / 'manager/bin/python'
            current_management_python.parent.mkdir(parents=True)
            current_management_python.touch()
            current_audio_python = current_root_path / 'audio/bin/python'
            with patch.object(management_diagnostics.subprocess, 'run', return_value=SimpleNamespace(stdout=str(current_audio_python) + '\n')) as current_probe_mock, \
                    patch.object(management_diagnostics, 'inspect_environment_dependencies', return_value={'status':'inconsistent','issues':['mismatch']}):
                current_result_record = management_diagnostics.inspect_generator_environment(current_management_python, 'music-heartmula', True)
            self.assertEqual(current_result_record['path'], str(current_audio_python.parent.parent))
            self.assertEqual(current_result_record['dependencies']['status'], 'inconsistent')
            self.assertIn('resolve_music_paths', current_probe_mock.call_args.args[0][5])

    def test_kimodo_diagnostics_uses_registered_runtime_path(self):
        from tools.review.common import management_diagnostics
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_management_python = current_root_path / 'management/bin/python'
            current_management_python.parent.mkdir(parents=True)
            current_management_python.touch()
            current_kimodo_python = current_root_path / 'separate/bin/python'
            with patch.object(management_diagnostics.subprocess, 'run') as probe_process_mock:
                probe_process_mock.return_value.stdout = str(current_kimodo_python) + '\n'
                current_result_record = management_diagnostics.inspect_kimodo_environment(current_management_python)
            self.assertEqual(current_result_record['status'], 'missing')
            self.assertEqual(current_result_record['path'], str(current_root_path / 'separate'))

    def test_model_inventory_reports_unavailable_without_management_python(self):
        from tools.review.common.management_diagnostics import inspect_registered_model_inventory
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_missing_python = Path(temporary_directory_name) / 'missing/bin/python'
            current_inventory_record = inspect_registered_model_inventory(current_missing_python)
            self.assertEqual(current_inventory_record['status'], 'unavailable')
            self.assertFalse(current_missing_python.exists())

    def test_diagnostics_reports_invalid_hermes_source_and_unverified_model(self):
        import json
        from tools.review.common import management_diagnostics
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            (current_root_path / '.local/hermes-agent-runtime').mkdir(parents=True)
            with patch.object(management_diagnostics, 'WORKFLOW_ROOT_DIRECTORY', current_root_path), \
                    patch('tools.review.domains.hermes_agent.runtime_integrity.verify_hermes_runtime_integrity', side_effect=ValueError('리비전 불일치')), \
                    patch('tools.review.common.hermes_model_download.inspect_hermes_model_files', return_value=False), \
                    patch('tools.review.common.gpu_status.read_gpu_status', return_value={'status':'unavailable'}), \
                    contextlib.redirect_stdout(io.StringIO()) as diagnostic_output_stream:
                management_diagnostics.inspect_management_environment()
            current_diagnostic_record = json.loads(diagnostic_output_stream.getvalue())
            self.assertEqual(current_diagnostic_record['hermes_source']['status'], 'invalid')
            self.assertEqual(current_diagnostic_record['hermes_source']['detail'], '리비전 불일치')
            self.assertNotEqual(current_diagnostic_record['hermes_model']['status'], 'marker_valid')

    def test_port_diagnostics_reports_only_valid_self_reported_identity(self):
        from tools.review.common import management_diagnostics
        current_response_value = SimpleNamespace(status=200, read=lambda current_maximum_bytes: b'{"status":"ok","role":"management-gui","pid":42,"launch_token":"secret"}', __enter__=lambda current_self: current_self, __exit__=lambda *current_arguments: None)
        from contextlib import contextmanager
        @contextmanager
        def open_test_response(*current_arguments, **current_options):
            yield current_response_value
        with patch.object(management_diagnostics, 'build_opener') as current_opener_mock:
            current_opener_mock.return_value.open = open_test_response
            current_identity_record = management_diagnostics.inspect_management_port_identity(8770, '/management/gui-health')
        self.assertEqual(current_identity_record, {'identity': 'self_reported', 'reported_role': 'management-gui', 'reported_pid': 42})
        self.assertNotIn('secret', str(current_identity_record))
        current_response_value.read = lambda current_maximum_bytes: b'{"status":"ok","role":"other","pid":42}'
        with patch.object(management_diagnostics, 'build_opener') as current_opener_mock:
            current_opener_mock.return_value.open = open_test_response
            self.assertEqual(management_diagnostics.inspect_management_port_identity(8770, '/management/gui-health'), {'identity': 'unknown'})

    def test_gateway_port_diagnostics_reports_queue_feature_without_secrets(self):
        import json
        from contextlib import contextmanager
        from tools.review.common import management_diagnostics
        current_response_value=SimpleNamespace(status=200,read=lambda current_maximum_bytes:b'')
        @contextmanager
        def open_test_response(*current_arguments,**current_options):
            yield current_response_value
        for current_features_value,current_expected_status in ((['hermes-gpu-queue-v1'],'supported'),([], 'not_reported'),(None,'unknown'),(['bad']*65,'unknown')):
            with self.subTest(features=current_features_value):
                current_response_value.read=lambda current_maximum_bytes:json.dumps({'status':'ok','role':'management-gateway','pid':42,'launch_token':'secret','features':current_features_value}).encode()
                with patch.object(management_diagnostics,'build_opener') as current_opener_mock:
                    current_opener_mock.return_value.open=open_test_response
                    current_identity_record=management_diagnostics.inspect_management_port_identity(8771,'/management/health')
                self.assertEqual(current_identity_record['hermes_gpu_queue'],current_expected_status)
                self.assertNotIn('secret',str(current_identity_record))

    def test_diagnostics_distinguishes_unavailable_gpu_from_idle(self):
        from tools.review.common.management_diagnostics import inspect_management_environment
        with patch('tools.review.common.gpu_status.read_gpu_status', return_value={'status': 'unavailable', 'processes': []}), \
                contextlib.redirect_stdout(io.StringIO()) as diagnostic_output_stream:
            inspect_management_environment()
        import json
        self.assertEqual(json.loads(diagnostic_output_stream.getvalue())['gpu']['status'], 'unavailable')

    def test_group_preview_and_execution_use_same_registered_modules(self):
        from tools.review.tests import run_management_audit
        with contextlib.redirect_stdout(io.StringIO()) as help_output_stream, self.assertRaises(SystemExit) as help_exit_record:
            run_management_audit.run_management_audit_cli(['--help'])
        self.assertEqual(help_exit_record.exception.code, 0)
        self.assertIn('--module MODULE', help_output_stream.getvalue())
        self.assertNotIn(run_management_audit.MANAGEMENT_AUDIT_MODULES[0], help_output_stream.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as error_output_stream, self.assertRaises(SystemExit) as error_exit_record:
            run_management_audit.run_management_audit_cli(['--module', 'unregistered'])
        self.assertEqual(error_exit_record.exception.code, 2)
        self.assertIn('--list-all', error_output_stream.getvalue())
        self.assertNotIn(run_management_audit.MANAGEMENT_AUDIT_MODULES[0], error_output_stream.getvalue())
        with contextlib.redirect_stdout(io.StringIO()) as all_output_stream, patch.object(run_management_audit, 'execute_music_regression') as audit_not_started_mock:
            self.assertEqual(run_management_audit.run_management_audit_cli(['--list-all']), 0)
        self.assertEqual(all_output_stream.getvalue().splitlines(), list(run_management_audit.MANAGEMENT_AUDIT_MODULES))
        audit_not_started_mock.assert_not_called()
        with contextlib.redirect_stdout(io.StringIO()) as group_output_stream:
            self.assertEqual(run_management_audit.run_management_audit_cli(['--list-group', 'hermes']), 0)
        current_module_names = group_output_stream.getvalue().splitlines()
        self.assertTrue(current_module_names)
        self.assertTrue(set(current_module_names).issubset(run_management_audit.MANAGEMENT_AUDIT_MODULES))
        with patch.object(run_management_audit, 'execute_music_regression', return_value=7) as audit_execution_mock:
            self.assertEqual(run_management_audit.run_management_audit_cli(['--group', 'hermes']), 7)
            self.assertEqual(list(audit_execution_mock.call_args.args[0]), current_module_names)

    def test_help_and_test_lists_work_without_runtime_or_writes(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_missing_path = Path(temporary_directory_name) / 'missing-environment'
            current_environment_values = {**os.environ, 'VIRTUAL_ENVIRONMENT_PATH': str(current_missing_path), 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': str(current_missing_path)}
            for current_arguments, current_expected_text in ((['test', '--help'], '--list-all'), (['test', '--list-all'], 'tools.review.tests.test_management_launcher'), (['test', '--list-group', 'hermes'], 'tools.review.tests.test_hermes_'), (['gui', '--help'], '--no-takeover'), (['gateway', '--help'], '--port'), (['help', 'hermes-model'], 'model-status'), (['help', 'kimodo', 'generate'], '--payload-file'), (['help', 'music-heartmula', 'generate'], '관리 환경'), (['help', 'flux-expression', 'generate'], '프리셋')):
                with self.subTest(arguments=current_arguments):
                    current_result_record = subprocess.run([str(management_launcher.WORKFLOW_ROOT_DIRECTORY / 'scripts/workflow.sh'), *current_arguments], env=current_environment_values, capture_output=True, text=True, timeout=30)
                    self.assertEqual(current_result_record.returncode, 0, current_result_record.stderr)
                    self.assertIn(current_expected_text, current_result_record.stdout)
            self.assertFalse(current_missing_path.exists())

    def test_existing_hermes_runtime_is_verified_not_overwritten(self):
        from tools.review.domains.hermes_agent import runtime_integrity
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_runtime_path = current_root_path / '.local/hermes-agent-runtime'
            current_runtime_path.mkdir(parents=True)
            with patch.object(management_setup, 'WORKFLOW_ROOT_DIRECTORY', current_root_path), \
                    patch.object(runtime_integrity, 'verify_hermes_runtime_integrity') as integrity_check_mock, \
                    patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
                management_setup.prepare_hermes_runtime_environment(unittest.mock.Mock())
                integrity_check_mock.assert_called_once_with(current_runtime_path)
                run_command_mock.assert_not_called()

    def test_hermes_setup_uses_selected_management_uv(self):
        from tools.review.domains.hermes_agent import runtime_integrity
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_uv_path = current_root_path / 'custom/bin/uv'
            current_uv_path.parent.mkdir(parents=True)
            current_uv_path.write_text('fixture')
            current_uv_path.chmod(0o755)
            current_runtime_path = current_root_path / '.local/hermes-agent-runtime'
            current_command_records = []
            def record_hermes_setup_command(current_command_values, current_logger_value):
                current_command_records.append(current_command_values)
                if current_command_values[:2] == ['git', 'clone']:
                    current_runtime_path.mkdir(parents=True)
            with patch.object(management_setup, 'WORKFLOW_ROOT_DIRECTORY', current_root_path), \
                    patch.object(management_setup, 'resolve_management_environment', return_value=current_root_path / 'custom'), \
                    patch.object(runtime_integrity, 'verify_hermes_runtime_integrity'), \
                    patch.object(management_setup, 'run_logged_management_command', side_effect=record_hermes_setup_command):
                management_setup.prepare_hermes_runtime_environment(None)
            current_sync_command = next(current_command for current_command in current_command_records if str(current_uv_path) in current_command)
            self.assertIn('UV_PROJECT_ENVIRONMENT=' + str(current_runtime_path / '.venv'), current_sync_command)
            self.assertEqual(current_sync_command[current_sync_command.index(str(current_uv_path)) + 1], 'sync')

    def test_missing_codex_path_prints_safe_existing_and_add_commands(self):
        import shlex
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)/'workflow space'
            current_executable_path=Path(current_temporary_directory)/'Codex App'/'codex'
            current_executable_path.parent.mkdir(parents=True)
            current_executable_path.write_text('fixture')
            current_executable_path.chmod(0o755)
            current_output_stream=io.StringIO()
            with patch.dict(os.environ,{'CODEX_CLI_PATH':str(current_executable_path)},clear=True),patch.object(management_launcher,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(management_launcher.shutil,'which',return_value=None),contextlib.redirect_stdout(current_output_stream):
                management_launcher.print_hermes_codex_cli_guidance()
            current_output_lines=current_output_stream.getvalue().splitlines()
            current_commands=[shlex.split(current_line_value.strip()) for current_line_value in current_output_lines if current_line_value.startswith('  ')]
            self.assertEqual(current_commands[0],[str(current_executable_path),'mcp','get','slime-hermes'])
            self.assertEqual(current_commands[1],[str(current_executable_path),'mcp','add','slime-hermes','--',str(current_root_path/'.local/hermes-mcp/bin/python'),str(current_root_path/'tools/review/domains/hermes_agent/mcp_server.py')])
            self.assertIn('등록되지 않은 경우에만',current_output_stream.getvalue())

    def test_missing_codex_without_app_shows_install_guidance(self):
        current_output_stream=io.StringIO()
        with patch.dict(os.environ,{},clear=True),patch.object(management_launcher.shutil,'which',return_value=None),patch.object(Path,'is_file',return_value=False),contextlib.redirect_stdout(current_output_stream):
            management_launcher.print_hermes_codex_cli_guidance()
        self.assertIn('찾지 못했습니다',current_output_stream.getvalue())
        self.assertIn('https://developers.openai.com/codex/mcp',current_output_stream.getvalue())

    def test_available_codex_path_needs_no_fallback_guidance(self):
        current_output_stream=io.StringIO()
        with patch.object(management_launcher.shutil,'which',return_value='/usr/bin/codex'),contextlib.redirect_stdout(current_output_stream):
            management_launcher.print_hermes_codex_cli_guidance()
        self.assertEqual(current_output_stream.getvalue(),'')

    def test_hermes_mcp_setup_guidance_only_after_success(self):
        with patch.object(management_launcher,'ManagementLaunchLogger'),patch.object(management_launcher,'prepare_management_environments') as current_prepare_mock,patch.object(management_launcher,'print_hermes_codex_cli_guidance') as current_guidance_mock,patch('tools.review.common.management_setup_plan.print_management_setup_plan'):
            self.assertEqual(management_launcher.run_management_launcher(['setup','--scope','hermes-mcp']),0)
            current_guidance_mock.assert_called_once_with()
            current_guidance_mock.reset_mock()
            self.assertEqual(management_launcher.run_management_launcher(['setup','--scope','hermes-mcp','--plan']),0)
            self.assertEqual(management_launcher.run_management_launcher(['setup','--scope','renderer']),0)
            current_guidance_mock.assert_not_called()
            current_prepare_mock.side_effect=ValueError('준비 실패')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(management_launcher.run_management_launcher(['setup','--scope','hermes-mcp']),1)
            current_guidance_mock.assert_not_called()

    def test_incomplete_mcp_environment_is_not_modified(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_environment_path = current_root_path / '.local/hermes-mcp'
            current_environment_path.mkdir(parents=True)
            current_marker_path = current_environment_path / 'keep.txt'
            current_marker_path.write_text('preserve')
            with patch.object(management_setup, 'WORKFLOW_ROOT_DIRECTORY', current_root_path), \
                    patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
                with self.assertRaisesRegex(ValueError, '불완전'):
                    management_setup.prepare_hermes_mcp_environment(None)
                run_command_mock.assert_not_called()
            self.assertEqual(current_marker_path.read_text(), 'preserve')

    def test_legacy_wrappers_reach_unified_launcher_help(self):
        for current_script_name, current_help_text in (('setup_management.sh', '--scope'),
                                                       ('run_management_gui.sh', '--no-takeover'),
                                                       ('run_management_gateway.sh', '--port'),
                                                       ('watch_review_server.sh', '--watch')):
            with self.subTest(script=current_script_name):
                current_script_path = management_launcher.WORKFLOW_ROOT_DIRECTORY / 'scripts' / current_script_name
                current_result_record = subprocess.run([str(current_script_path), '--help'], capture_output=True, text=True, timeout=30)
                self.assertEqual(current_result_record.returncode, 0, current_result_record.stderr)
                self.assertIn(current_help_text, current_result_record.stdout)

    def test_isolated_workflow_commands_use_selected_management_python(self):
        selected_environment_values = {**os.environ, 'VIRTUAL_ENVIRONMENT_PATH': sys.prefix,
                                       'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': sys.prefix}
        for selected_mode_name in ('gui', 'gateway'):
            with self.subTest(mode=selected_mode_name):
                current_result_record = subprocess.run(
                    [str(management_launcher.WORKFLOW_ROOT_DIRECTORY / 'scripts/workflow.sh'), selected_mode_name, '--help'],
                    env=selected_environment_values, capture_output=True, text=True, timeout=30)
                self.assertEqual(current_result_record.returncode, 0, current_result_record.stderr)
                self.assertIn('--port', current_result_record.stdout)

    def test_writer_runtime_setup_verifies_existing_and_refuses_mismatch(self):
        import json
        from generators.writer_agent import prepare as writer_prepare_module
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_root_path = Path(temporary_directory_name)
            current_runtime_root = current_root_path / 'writer'
            current_model_root = current_root_path / 'models'
            current_module_root = current_root_path / 'module'
            for current_directory_path in (current_runtime_root, current_model_root, current_module_root):
                current_directory_path.mkdir()
            current_binary_path = current_runtime_root / 'server'
            current_writer_python = current_runtime_root / 'venv/bin/python'
            current_writer_python.parent.mkdir(parents=True)
            current_writer_python.touch()
            (current_runtime_root / 'venv/pyvenv.cfg').touch()
            for current_file_path in (current_binary_path, current_model_root/'model.gguf', current_model_root/'embedding.gguf', current_module_root/'requirements.lock'):
                current_file_path.write_text(current_file_path.name)
            current_manifest_path = current_runtime_root / 'prepared.json'
            current_manifest_path.write_text(json.dumps({'backend':'rocm','gpu_architecture':'gfx1151','server_release_name':'release',
                'model_file_sha256':'model.gguf', 'embedding_file_sha256':'embedding.gguf', 'requirements_file_sha256':'requirements.lock', 'server_binary_sha256':'server'}))
            def calculate_trial_digest(current_file_path):
                return current_file_path.read_text()
            with patch.object(writer_prepare_module, 'RUNTIME_INSTALL_ROOT', current_runtime_root), \
                    patch.object(writer_prepare_module, 'RUNTIME_SERVER_PATH', current_binary_path), \
                    patch.object(writer_prepare_module, 'RUNTIME_PYTHON_PATH', current_writer_python), \
                    patch.object(writer_prepare_module, 'MODEL_DOWNLOAD_ROOT', current_model_root), \
                    patch.object(writer_prepare_module, 'MODEL_DOWNLOAD_NAME', 'model.gguf'), \
                    patch.object(writer_prepare_module, 'EMBEDDING_DOWNLOAD_NAME', 'embedding.gguf'), \
                    patch.object(writer_prepare_module, 'MODEL_DOWNLOAD_SHA256', 'model.gguf'), \
                    patch.object(writer_prepare_module, 'EMBEDDING_DOWNLOAD_SHA256', 'embedding.gguf'), \
                    patch.object(writer_prepare_module, 'SOURCE_RELEASE_NAME', 'release'), \
                    patch.object(writer_prepare_module, 'WORKFLOW_MODULE_ROOT', current_module_root), \
                    patch.object(writer_prepare_module, 'calculate_file_digest', side_effect=calculate_trial_digest), \
                    patch.object(management_setup, 'run_logged_management_command') as current_run_mock:
                current_logger_mock = __import__('unittest.mock', fromlist=['Mock']).Mock()
                management_setup.prepare_writer_runtime_environment(current_logger_mock)
                current_binary_path.write_text('changed')
                with self.assertRaisesRegex(ValueError, '자동 변경하지 않습니다'):
                    management_setup.prepare_writer_runtime_environment(current_logger_mock)
                current_run_mock.assert_called_once()
                self.assertIn('-I', current_run_mock.call_args.args[0])
                self.assertEqual(current_binary_path.read_text(), 'changed')

    def test_writer_fresh_setup_bootstrap_runs_in_selected_python(self):
        from generators.writer_agent import prepare as writer_prepare_module
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_runtime_root = Path(temporary_directory_name) / 'writer'
            current_writer_python = current_runtime_root / 'venv/bin/python'
            with patch.object(writer_prepare_module, 'RUNTIME_INSTALL_ROOT', current_runtime_root), \
                    patch.object(writer_prepare_module, 'RUNTIME_PYTHON_PATH', current_writer_python), \
                    patch.object(management_setup, 'run_logged_management_command') as current_run_mock:
                management_setup.prepare_writer_runtime_environment(None)
            current_command_values = current_run_mock.call_args.args[0]
            current_help_command = current_command_values[:-2] + ['--help']
            current_help_result = subprocess.run(current_help_command, capture_output=True, text=True, timeout=30)
            self.assertEqual(current_help_result.returncode, 0, current_help_result.stderr)
            self.assertIn('--run-dir', current_help_result.stdout)
            self.assertFalse(current_runtime_root.exists())

    def test_writer_bootstrap_finds_selected_management_uv(self):
        from generators.writer_agent import prepare as writer_prepare_module
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_trial_root = Path(temporary_directory_name)
            current_python_bin = current_trial_root / 'management/bin'
            current_python_bin.mkdir(parents=True)
            (current_python_bin / 'python').symlink_to(sys.executable)
            current_uv_path = current_python_bin / 'uv'
            current_uv_path.write_text('#!/bin/sh\n')
            current_uv_path.chmod(0o755)
            current_package_root = current_trial_root / 'generators/writer_agent'
            current_package_root.mkdir(parents=True)
            (current_package_root / '__init__.py').write_text('')
            (current_package_root / 'prepare.py').write_text('import shutil; print(shutil.which("uv"))')
            current_writer_root = current_trial_root / 'writer'
            with patch.object(writer_prepare_module, 'RUNTIME_INSTALL_ROOT', current_writer_root), \
                    patch.object(writer_prepare_module, 'RUNTIME_PYTHON_PATH', current_writer_root / 'venv/bin/python'), \
                    patch.object(management_setup, 'WORKFLOW_ROOT_DIRECTORY', current_trial_root), \
                    patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(current_python_bin.parent), 'PATH': '/usr/bin:/bin'}, clear=True), \
                    patch.object(management_setup, 'run_logged_management_command') as current_run_mock:
                management_setup.prepare_writer_runtime_environment(None)
            current_command_values = current_run_mock.call_args.args[0]
            current_result_value = subprocess.run(current_command_values, capture_output=True, text=True, timeout=30, env={'PATH': '/usr/bin:/bin'})
            self.assertEqual(current_result_value.returncode, 0, current_result_value.stderr)
            self.assertEqual(current_result_value.stdout.strip(), str(current_uv_path))

    def test_setup_plan_does_not_require_uv_for_hermes_mcp(self):
        from tools.review.common import management_setup_plan
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.object(management_setup_plan, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), \
                patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': str(Path(temporary_directory_name) / 'missing')}, clear=True), \
                patch.object(management_setup_plan.shutil, 'which', return_value=None):
            current_mcp_plan = management_setup_plan.describe_management_setup('hermes-mcp')
            current_writer_plan = management_setup_plan.describe_management_setup('writer-runtime')
            self.assertFalse(any('uv' in current_requirement_message for current_requirement_message in current_mcp_plan['missing_requirements']))
            self.assertTrue(any('uv' in current_requirement_message for current_requirement_message in current_writer_plan['missing_requirements']))

    def test_writer_new_environment_rechecks_existing_paths(self):
        from generators.writer_agent import prepare as writer_prepare_module
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_runtime_root = Path(temporary_directory_name) / 'writer'
            current_runtime_root.mkdir()
            current_writer_python = current_runtime_root / 'venv/bin/python'
            current_writer_python.parent.mkdir(parents=True)
            with patch.object(writer_prepare_module, 'RUNTIME_INSTALL_ROOT', current_runtime_root), \
                    patch.object(writer_prepare_module, 'RUNTIME_PYTHON_PATH', current_writer_python), \
                    patch.object(writer_prepare_module, 'prepare_runtime_environment') as current_prepare_mock:
                with self.assertRaises(ValueError):
                    writer_prepare_module.prepare_new_writer_environment()
                current_prepare_mock.assert_not_called()

    def test_writer_runtime_scope_reserves_queue_before_preparation(self):
        from tools.review.common import gpu_job_queue
        def inspect_writer_reservation(current_logger_value):
            self.assertEqual(len(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json'))), 1)
        with patch.object(management_setup, 'prepare_writer_runtime_environment', side_effect=inspect_writer_reservation) as current_setup_mock:
            management_setup.prepare_management_environments(None, 'writer-runtime')
        current_setup_mock.assert_called_once()

    def test_heartmula_runtime_setup_reserves_gpu_queue(self):
        from tools.review.common import gpu_job_queue
        def observe_music_setup_command(current_command_values, current_logger_value):
            self.assertIn('generators/music/heartmula/setup_runtime.py', current_command_values[-1])
            self.assertEqual(len(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json'))), 1)
        with patch.object(management_setup, 'run_logged_management_command', side_effect=observe_music_setup_command) as current_command_mock:
            management_setup.prepare_management_environments(None, 'heartmula-runtime')
        current_command_mock.assert_called_once()
        self.assertFalse(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json')))

    def test_kimodo_runtime_setup_reserves_gpu_queue(self):
        from tools.review.common import gpu_job_queue
        def observe_kimodo_setup_command(current_command_values, current_logger_value):
            self.assertIn('generators/kimodo/setup_runtime.py', current_command_values[-1])
            self.assertEqual(len(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json'))), 1)
        with patch.object(management_setup, 'run_logged_management_command', side_effect=observe_kimodo_setup_command) as current_command_mock:
            management_setup.prepare_management_environments(None, 'kimodo-runtime')
        current_command_mock.assert_called_once()
        self.assertFalse(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json')))

    def test_sfx_runtime_setup_reserves_gpu_queue(self):
        from generators.sound_effects import setup_runtime
        from tools.review.common import gpu_job_queue
        def observe_active_setup_reservation():
            current_reservations_list = list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json'))
            self.assertEqual(len(current_reservations_list), 1)
        with patch.object(setup_runtime, 'install_effects_runtime', side_effect=observe_active_setup_reservation) as current_setup_mock:
            management_setup.prepare_management_environments(None, 'sfx-runtime')
        current_setup_mock.assert_called_once_with()
        self.assertFalse(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json')))

    def test_wan_runtime_setup_reserves_queue_and_skips_models(self):
        from generators.wan_fun import setup_rocm
        with patch.object(setup_rocm, 'setup_fun_rocm_environment') as current_setup_mock:
            management_setup.prepare_management_environments(None, 'wan-fun-runtime')
        current_setup_mock.assert_called_once_with(prepare_model_assets=False)
        from tools.review.common import gpu_job_queue
        self.assertFalse(list((gpu_job_queue.GPU_QUEUE_DIRECTORY / 'active').glob('*.json')))

    def test_stack_port_probe_allows_closed_connections_and_rejects_listener(self):
        import socket
        from tools.review.common import management_stack
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener_socket_handle:
            listener_socket_handle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener_socket_handle.bind(('127.0.0.1', 0))
            listener_socket_handle.listen()
            listener_port_number = listener_socket_handle.getsockname()[1]
            with self.assertRaisesRegex(ValueError, '포트를 사용할 수 없습니다'):
                management_stack.check_management_stack_port(listener_port_number)
            with socket.create_connection(('127.0.0.1', listener_port_number)) as client_socket_handle:
                accepted_socket_handle, _ = listener_socket_handle.accept()
                accepted_socket_handle.close()
                client_socket_handle.recv(1)
        management_stack.check_management_stack_port(listener_port_number)

    def test_stack_refuses_occupied_port_before_starting_processes(self):
        from tools.review.common import management_stack
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.object(management_stack, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), \
                patch.object(management_launcher, 'build_management_launch_command'), \
                patch.object(management_stack, 'check_management_stack_port', side_effect=ValueError('포트 사용 중')), \
                patch.object(management_stack.subprocess, 'Popen') as process_launch_mock, \
                patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, '포트 사용 중'):
                management_stack.start_management_stack()
            process_launch_mock.assert_not_called()

    def test_stack_starts_independent_processes_without_gui_takeover(self):
        from tools.review.common import management_stack
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.object(management_stack, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), \
                patch.object(management_launcher, 'build_management_launch_command'), \
                patch.object(management_stack, 'check_management_stack_port'), \
                patch.object(management_stack, 'wait_management_stack_endpoint') as endpoint_check_mock, \
                patch.object(management_stack.subprocess, 'Popen') as process_launch_mock, \
                patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(management_stack.start_management_stack(), 0)
            self.assertEqual(process_launch_mock.call_count, 2)
            self.assertEqual(endpoint_check_mock.call_count, 2)
            self.assertTrue(all(current_call.kwargs['start_new_session'] for current_call in process_launch_mock.call_args_list))
            self.assertIn('--no-takeover', process_launch_mock.call_args_list[1].args[0])
            current_gateway_token = process_launch_mock.call_args_list[0].kwargs['env']['SLIME_MANAGEMENT_STACK_TOKEN']
            current_gui_token = process_launch_mock.call_args_list[1].kwargs['env']['SLIME_MANAGEMENT_STACK_TOKEN']
            self.assertNotEqual(current_gateway_token, current_gui_token)
            self.assertEqual(endpoint_check_mock.call_args_list[0].args[3], current_gateway_token)
            self.assertEqual(endpoint_check_mock.call_args_list[1].args[3], current_gui_token)

    def test_stack_rejects_another_process_health_response(self):
        import itertools
        import json
        from unittest.mock import MagicMock
        from tools.review.common import management_stack
        current_process_mock = MagicMock()
        current_process_mock.poll.return_value = None
        current_response_mock = MagicMock()
        current_response_mock.status = 200
        current_response_mock.read.return_value = json.dumps({'role':'management-gateway','status':'ok','launch_token':'another'}).encode()
        current_opener_mock = MagicMock()
        current_opener_mock.open.return_value.__enter__.return_value = current_response_mock
        current_clock_counter = itertools.count()
        with patch.object(management_stack, 'STACK_START_TIMEOUT_SECONDS', 3), \
                patch.object(management_stack, 'build_opener', return_value=current_opener_mock), \
                patch.object(management_stack.time, 'monotonic', side_effect=lambda: next(current_clock_counter)), \
                patch.object(management_stack.time, 'sleep'):
            with self.assertRaises(TimeoutError):
                management_stack.wait_management_stack_endpoint(current_process_mock, 'http://127.0.0.1:8771/management/health', 'management-gateway', 'expected', Path('/tmp/stack-test.log'))
        current_process_mock.terminate.assert_not_called()
        current_process_mock.kill.assert_not_called()

    def test_stack_does_not_stop_gateway_when_gui_start_fails(self):
        from tools.review.common import management_stack
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.object(management_stack, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), \
                patch.object(management_launcher, 'build_management_launch_command'), \
                patch.object(management_stack, 'check_management_stack_port'), \
                patch.object(management_stack, 'wait_management_stack_endpoint', side_effect=[None, RuntimeError('GUI 실패')]), \
                patch.object(management_stack.subprocess, 'Popen') as process_launch_mock, \
                patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'GUI 실패'):
                management_stack.start_management_stack()
            process_launch_mock.return_value.terminate.assert_not_called()
            process_launch_mock.return_value.kill.assert_not_called()

    def test_gui_accepts_no_takeover_option(self):
        from tools.review.serve import parse_review_arguments
        self.assertTrue(parse_review_arguments(['--no-takeover']).no_takeover)
        self.assertFalse(parse_review_arguments([]).no_takeover)

    def test_unsupported_image_platform_stops_before_install(self):
        current_invoked_commands = []
        def execute_platform_probe(current_command_values, current_logger_value):
            current_invoked_commands.append(current_command_values)
            if current_command_values[1:2] == ['-c'] and 'platform.machine' in current_command_values[2]:
                current_platform_code = "import platform; platform.machine=lambda: 'aarch64'; " + current_command_values[2]
                current_probe_result = subprocess.run([sys.executable, '-I', '-B', '-c', current_platform_code], capture_output=True, text=True)
                if current_probe_result.returncode:
                    raise subprocess.CalledProcessError(current_probe_result.returncode, current_command_values, stderr=current_probe_result.stderr)
        with patch.object(management_setup, 'run_logged_management_command', side_effect=execute_platform_probe):
            with self.assertRaises(subprocess.CalledProcessError) as current_platform_error:
                management_setup.prepare_image_runtime_environment(Path(sys.executable), None)
        self.assertIn('Linux x86_64 Python 3.14', current_platform_error.exception.stderr)
        self.assertFalse(any('install' in current_command_values for current_command_values in current_invoked_commands))

    def test_existing_incompatible_torch_is_not_replaced(self):
        with patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
            management_setup.prepare_image_runtime_environment(Path('/tmp/image/bin/python'), None)
        current_preflight_code = run_command_mock.call_args_list[0].args[0][-1]
        current_fake_code = "import sys,types; m=types.ModuleType('importlib.metadata'); m.version=lambda n: '2.0.0'; import importlib.util; importlib.util.find_spec=lambda n: object(); sys.modules['importlib.metadata']=m; "
        for current_python_flags in ([], ['-O']):
            current_process_result = subprocess.run([sys.executable, *current_python_flags, '-c', current_fake_code + current_preflight_code], capture_output=True, text=True)
            self.assertNotEqual(current_process_result.returncode, 0)
            self.assertIn('기존 PyTorch 빌드를 교체하지 않습니다', current_process_result.stderr)

    def test_incomplete_virtual_environment_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name) / 'environment'
            current_environment_path.mkdir()
            current_user_file = current_environment_path / 'keep.txt'
            current_user_file.write_text('preserve')
            with patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
                with self.assertRaisesRegex(ValueError, '덮어쓰지 않습니다'):
                    management_setup.prepare_virtual_environment(current_environment_path, None)
                run_command_mock.assert_not_called()
            self.assertEqual(current_user_file.read_text(), 'preserve')

    def test_gradio_uses_shared_environment_and_allows_explicit_override(self):
        with patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': '.tmp/shared'}, clear=True):
            self.assertEqual(management_launcher.resolve_gradio_environment(), management_launcher.WORKFLOW_ROOT_DIRECTORY/'.tmp/shared')
            with patch.dict(os.environ, {'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': '.tmp/ui'}):
                self.assertEqual(management_launcher.resolve_gradio_environment(), management_launcher.WORKFLOW_ROOT_DIRECTORY/'.tmp/ui')

    def test_failure_preserves_output_and_exact_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), contextlib.redirect_stdout(io.StringIO()):
            launcher_trace_logger = management_launcher.ManagementLaunchLogger('test')
            try:
                with self.assertRaises(subprocess.CalledProcessError) as command_error_context:
                    management_launcher.run_logged_management_command([sys.executable, '-c', 'print("실패 원인", flush=True); raise SystemExit(7)'], launcher_trace_logger)
                self.assertEqual(command_error_context.exception.returncode, 7)
                self.assertIn('실패 원인', launcher_trace_logger.output_log_path.read_text())
            finally:
                launcher_trace_logger.close_launch_log()

    def test_silent_command_emits_heartbeat(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch.object(management_process, 'LAUNCHER_HEARTBEAT_SECONDS', .05), contextlib.redirect_stdout(io.StringIO()):
            launcher_trace_logger = management_launcher.ManagementLaunchLogger('test')
            try:
                management_launcher.run_logged_management_command([sys.executable, '-c', 'import time; time.sleep(.3)'], launcher_trace_logger)
                self.assertIn('/heartbeat pid=', launcher_trace_logger.output_log_path.read_text())
            finally:
                launcher_trace_logger.close_launch_log()

    def test_gradio_configuration_does_not_import_process_launcher(self):
        subprocess.run([sys.executable, '-c', "import sys; import tools.review.common.gradio_process; assert 'tools.review.common.management_launcher' not in sys.modules; assert 'tools.review.common.management_process' not in sys.modules; assert 'tools.review.common.management_setup' not in sys.modules"], check=True)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux 프로세스 상태 검사')
    def test_stubborn_child_is_stopped_but_unrelated_session_survives(self):
        independent_process_handle = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
        stubborn_process_identifier = None
        try:
            with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), contextlib.redirect_stdout(io.StringIO()):
                child_marker_path = Path(temporary_directory_name)/'child.pid'
                child_source_text = f"import os, signal, time; from pathlib import Path; signal.signal(signal.SIGTERM, signal.SIG_IGN); Path({str(child_marker_path)!r}).write_text(str(os.getpid())); time.sleep(30)"
                parent_source_text = "import subprocess, sys, time; from pathlib import Path; subprocess.Popen([sys.executable, '-c', " + repr(child_source_text) + "]); marker_path = Path(" + repr(str(child_marker_path)) + "); deadline_time = time.monotonic() + 5\nwhile not marker_path.exists() and time.monotonic() < deadline_time: time.sleep(.01)\nassert marker_path.exists()"
                launcher_trace_logger = management_process.ManagementLaunchLogger('test')
                try:
                    management_process.run_logged_management_command([sys.executable, '-c', parent_source_text], launcher_trace_logger)
                finally:
                    launcher_trace_logger.close_launch_log()
                stubborn_process_identifier = int(child_marker_path.read_text())
                child_status_path = Path(f'/proc/{stubborn_process_identifier}/stat')
                for cleanup_attempt_number in range(100):
                    if not child_status_path.exists() or child_status_path.read_text().split(') ')[1][0] == 'Z':
                        break
                    time.sleep(.01)
                else:
                    self.fail('종료된 부모가 남긴 자식이 실행 중입니다.')
                self.assertIsNone(independent_process_handle.poll())
        finally:
            if stubborn_process_identifier is not None:
                try:
                    os.kill(stubborn_process_identifier, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            independent_process_handle.terminate()
            independent_process_handle.wait(timeout=5)
