"""게이트웨이 watch 옵션·감시 경계·재시작 연결 계약."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from workflow.common import gateway_watch, management_process
from workflow.gateway_server import parse_gateway_arguments


class GatewayWatchTests(unittest.TestCase):
    def test_watch_includes_map_builder_source(self):
        current_builder_path = gateway_watch.WORKFLOW_ROOT_DIRECTORY/'workflow/build_block_map_review.py'
        self.assertIn(current_builder_path, gateway_watch.collect_gateway_watch_paths())

    def test_gateway_exposes_selected_writer_config_and_restores_environment(self):
        import os
        from types import SimpleNamespace
        from workflow import gateway_server
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)
            current_config_path=current_root_path/'separate-workspace.yaml'
            current_runtime_value=SimpleNamespace(dispatch_runtime_request=lambda *current_request_values:None,close_runtime_services=lambda:None)
            current_seen_values=[]
            class TemporaryGatewayServer:
                def __init__(self,*current_server_arguments):pass
                def __enter__(self):return self
                def __exit__(self,*current_exit_values):return False
                def serve_forever(self,poll_interval):current_seen_values.append(os.environ.get('SLIME_WRITER_WORKSPACE_CONFIG'))
            with patch.dict(os.environ,{'SLIME_WRITER_WORKSPACE_CONFIG':'previous-config'}),patch.object(gateway_server,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(gateway_server,'ThreadingHTTPServer',TemporaryGatewayServer),patch.object(gateway_server.signal,'signal',return_value=None),patch('workflow.common.content_launch_config.apply_content_launch_configuration'),patch('workflow.common.management_runtime.create_management_runtime',return_value=current_runtime_value):
                gateway_server.run_management_gateway(19999,current_config_path)
                self.assertEqual(os.environ['SLIME_WRITER_WORKSPACE_CONFIG'],'previous-config')
            self.assertEqual(current_seen_values,[str(current_config_path)])

    def test_gateway_writer_environment_restored_on_start_failure(self):
        import os
        from workflow import gateway_server
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)
            current_config_path=current_root_path/'separate-workspace.yaml'
            with patch.dict(os.environ,{'SLIME_WRITER_WORKSPACE_CONFIG':'previous-config'}),patch.object(gateway_server,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(gateway_server.signal,'signal',return_value=None),patch('workflow.common.content_launch_config.apply_content_launch_configuration'),patch('workflow.common.management_runtime.create_management_runtime',side_effect=RuntimeError('임시 시작 실패')),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'임시 시작 실패'):
                    gateway_server.run_management_gateway(19999,current_config_path)
                self.assertEqual(os.environ['SLIME_WRITER_WORKSPACE_CONFIG'],'previous-config')
            with patch.dict(os.environ,{'SLIME_WRITER_WORKSPACE_CONFIG':'previous-config'}),patch.object(gateway_server,'WORKFLOW_ROOT_DIRECTORY',current_root_path/'missing-parent'/'file'),patch('pathlib.Path.mkdir',side_effect=OSError('임시 로그 오류')),patch('workflow.common.content_launch_config.apply_content_launch_configuration'):
                with self.assertRaisesRegex(OSError,'임시 로그 오류'):
                    gateway_server.run_management_gateway(19999,current_config_path)
                self.assertEqual(os.environ['SLIME_WRITER_WORKSPACE_CONFIG'],'previous-config')

    def test_gateway_invalid_config_does_not_replace_signal_handler(self):
        import os
        from workflow import gateway_server
        with tempfile.TemporaryDirectory() as current_temporary_directory,patch.dict(os.environ,{'SLIME_WRITER_WORKSPACE_CONFIG':'previous-config'}),patch.object(gateway_server,'WORKFLOW_ROOT_DIRECTORY',Path(current_temporary_directory)),patch.object(gateway_server.signal,'signal') as current_signal_mock,patch('workflow.common.content_launch_config.apply_content_launch_configuration'):
            with self.assertRaises(TypeError):gateway_server.run_management_gateway(19999,123)
            current_signal_mock.assert_not_called()
            self.assertEqual(os.environ['SLIME_WRITER_WORKSPACE_CONFIG'],'previous-config')

    def test_gateway_custom_writer_config_reaches_hermes_queue_snapshot(self):
        import json
        import os
        import yaml
        from types import SimpleNamespace
        from workflow import gateway_server
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent import management_observer
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)
            current_workflow_root=current_root_path/'workflow'
            current_queue_path=current_workflow_root/'.tmp'/'gpu-queue'
            current_queue_path.mkdir(parents=True)
            current_state_path=current_root_path/'writer-state'
            current_job_path=current_state_path/'jobs'/'20261121-120000-12345678'
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'writer-agent'}))
            (current_queue_path/'ticket.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_path)}))
            current_config_path=current_root_path/'writer-custom.yaml'
            current_config_path.write_text(yaml.safe_dump({'schema_version':1,'document_root':str(current_root_path/'docs'),'state_root':str(current_state_path),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None}))
            current_runtime_value=SimpleNamespace(dispatch_runtime_request=lambda *current_request_values:None,close_runtime_services=lambda:None)
            current_snapshot_values=[]
            class TemporaryGatewayServer:
                def __init__(self,*current_server_arguments):pass
                def __enter__(self):return self
                def __exit__(self,*current_exit_values):return False
                def serve_forever(self,poll_interval):current_snapshot_values.append(HermesServiceManager().execute_hermes_command('hermes-management-status',{}))
            with patch.object(gateway_server,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root),patch.object(gateway_server,'ThreadingHTTPServer',TemporaryGatewayServer),patch.object(gateway_server.signal,'signal',return_value=None),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_path),patch('workflow.common.content_launch_config.apply_content_launch_configuration'),patch('workflow.common.management_runtime.create_management_runtime',return_value=current_runtime_value),patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch.object(management_observer,'inspect_hermes_model_status',return_value={}),patch.object(management_observer,'read_hermes_generator_snapshot',return_value={}),patch.object(management_observer,'read_hermes_gpu_reservation_snapshot',return_value={}),patch.object(management_observer,'read_hermes_recent_job_snapshot',return_value={}):
                gateway_server.run_management_gateway(19999,current_config_path)
            self.assertEqual(current_snapshot_values[0]['queue']['status'],'available')
            self.assertEqual(current_snapshot_values[0]['queue']['jobs'][0]['id'],current_job_path.name)
            self.assertTrue((current_queue_path/'ticket.json').is_file())
            self.assertFalse((current_root_path/'docs').exists())

    def test_watch_option_preserves_server_arguments(self):
        argument_record_values = parse_gateway_arguments(['--watch', '--port', '9871', '--writer-agent-config', '/tmp/writer config.yaml'])
        self.assertTrue(argument_record_values.watch)
        self.assertEqual(argument_record_values.port, 9871)
        self.assertEqual(argument_record_values.writer_agent_config, Path('/tmp/writer config.yaml'))
        self.assertFalse(parse_gateway_arguments([]).watch)

    def test_snapshot_tracks_create_edit_delete_but_excludes_ui_and_results(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            source_root_directory = Path(temporary_directory_name)
            initial_snapshot_values = gateway_watch.snapshot_gateway_watch_paths([source_root_directory])
            for ignored_relative_path in ('ui/app.py', '.tmp/job/status.json', '__pycache__/worker.py', 'tests/test_worker.py', 'management_launcher.py', 'manager.html'):
                ignored_source_path = source_root_directory/ignored_relative_path
                ignored_source_path.parent.mkdir(parents=True, exist_ok=True)
                ignored_source_path.write_text('ignored')
            self.assertEqual(gateway_watch.snapshot_gateway_watch_paths([source_root_directory]), initial_snapshot_values)
            source_module_path = source_root_directory/'service.py'
            source_module_path.write_text('first')
            created_snapshot_values = gateway_watch.snapshot_gateway_watch_paths([source_root_directory])
            self.assertNotEqual(created_snapshot_values, initial_snapshot_values)
            source_module_path.write_text('changed service')
            self.assertNotEqual(gateway_watch.snapshot_gateway_watch_paths([source_root_directory]), created_snapshot_values)
            source_module_path.unlink()
            self.assertEqual(gateway_watch.snapshot_gateway_watch_paths([source_root_directory]), initial_snapshot_values)

    def test_missing_writer_configuration_creation_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            writer_config_path = Path(temporary_directory_name)/'workspace.yaml'
            previous_source_snapshot = gateway_watch.snapshot_gateway_watch_paths([writer_config_path])
            writer_config_path.write_text('schema_version: 1')
            self.assertNotEqual(previous_source_snapshot, gateway_watch.snapshot_gateway_watch_paths([writer_config_path]))

    def test_watch_restarts_only_when_requested_and_keeps_arguments(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch.object(gateway_watch, 'run_logged_management_command', side_effect=[True, False]) as run_command_mock, contextlib.redirect_stdout(io.StringIO()):
            gateway_watch.run_gateway_watch_mode(9871, Path('/tmp/writer config.yaml'))
        self.assertEqual(run_command_mock.call_count, 2)
        for current_call_value in run_command_mock.call_args_list:
            self.assertNotIn('--watch', current_call_value.args[0])
            self.assertEqual(current_call_value.args[0][-4:], ['--port', '9871', '--writer-agent-config', '/tmp/writer config.yaml'])

    def test_process_restart_terminates_child_and_returns_restart_signal(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), contextlib.redirect_stdout(io.StringIO()):
            launcher_trace_logger = management_process.ManagementLaunchLogger('test')
            try:
                self.assertTrue(management_process.run_logged_management_command([sys.executable, '-c', 'import time; time.sleep(30)'], launcher_trace_logger, lambda: True))
                self.assertIn('/restart ', launcher_trace_logger.output_log_path.read_text())
            finally:
                launcher_trace_logger.close_launch_log()

    def test_failed_start_does_not_loop_or_hide_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch.object(gateway_watch, 'run_logged_management_command', side_effect=subprocess.CalledProcessError(1, ['gateway'])) as run_command_mock, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError):
                gateway_watch.run_gateway_watch_mode(9871)
            run_command_mock.assert_called_once()
