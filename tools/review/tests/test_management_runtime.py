"""서비스 조립·경로 소유권·초기화 실패와 종료 계약."""
import contextlib
import io
from pathlib import Path
import signal
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES
from tools.review.common.management_runtime import ManagementServiceRuntime, bind_stored_management_service
from tools.review import gateway_server


class ManagementRuntimeTests(unittest.TestCase):
    def create_service_bindings(self):
        return {
            service_command_name: bind_stored_management_service(Mock(return_value=True), Path('/tmp')/service_command_name)
            for service_command_name in MANAGEMENT_SERVICE_ROUTES
        }

    def test_missing_or_unknown_binding_fails_at_startup(self):
        for invalid_binding_records in ({}, self.create_service_bindings() | {'unknown': object()}):
            with self.assertRaisesRegex(ValueError, '관리 서비스 연결 불일치'):
                ManagementServiceRuntime(invalid_binding_records, Mock(), Mock())

    def test_result_file_is_dispatched_only_to_owning_service(self):
        service_binding_records = self.create_service_bindings()
        legacy_request_handler = Mock()
        runtime_service_manager = ManagementServiceRuntime(service_binding_records, legacy_request_handler, Mock())
        current_http_handler = SimpleNamespace(command='GET', path='/image-generation/jobs/2026-09-30_01-02-03-12345678/result.png')
        self.assertTrue(runtime_service_manager.dispatch_runtime_request(current_http_handler))
        for service_command_name, service_binding_record in service_binding_records.items():
            self.assertEqual(service_binding_record.request_handler_callback.call_count, int(service_command_name == 'qwen-2512'))
        legacy_request_handler.assert_not_called()

    def test_record_folder_uses_same_service_binding(self):
        service_binding_records = self.create_service_bindings()
        runtime_service_manager = ManagementServiceRuntime(service_binding_records, Mock(), Mock())
        current_http_handler = SimpleNamespace(command='POST', path='/management/record-folder/open')
        with patch('tools.review.common.management_runtime.handle_record_folder_request', return_value=True) as record_folder_handler:
            self.assertTrue(runtime_service_manager.dispatch_runtime_request(current_http_handler))
        recorded_folder_routes = record_folder_handler.call_args.args[1]
        for service_command_name, service_route_prefix in MANAGEMENT_SERVICE_ROUTES.items():
            record_storage_root, record_path_resolver = recorded_folder_routes[service_route_prefix]
            self.assertEqual(record_storage_root, service_binding_records[service_command_name].record_storage_root)
            self.assertEqual(record_path_resolver('same-id'), record_storage_root/'same-id')

    def test_legacy_writer_handler_and_close_are_explicit(self):
        legacy_request_handler = Mock(return_value=True)
        runtime_cleanup_callback = Mock()
        runtime_service_manager = ManagementServiceRuntime(self.create_service_bindings(), legacy_request_handler, runtime_cleanup_callback)
        current_http_handler = SimpleNamespace(command='GET', path='/writer-agent/api/state')
        self.assertTrue(runtime_service_manager.dispatch_runtime_request(current_http_handler))
        legacy_request_handler.assert_called_once_with(current_http_handler)
        runtime_service_manager.close_runtime_services()
        runtime_service_manager.close_runtime_services()
        runtime_cleanup_callback.assert_called_once_with()
        with self.assertRaisesRegex(RuntimeError, '종료된 관리 서비스'):
            runtime_service_manager.dispatch_runtime_request(current_http_handler)

    def test_initialization_failure_is_logged_and_restores_signal_handler(self):
        previous_signal_handler = signal.getsignal(signal.SIGTERM)
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(gateway_server, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch('tools.review.common.management_runtime.create_management_runtime', side_effect=ValueError('설정 누락')), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, '설정 누락'):
                gateway_server.run_management_gateway(9871)
            gateway_log_paths = list(Path(temporary_directory_name).rglob('*.log'))
            self.assertEqual(len(gateway_log_paths), 1)
            self.assertIn('/failure Traceback', gateway_log_paths[0].read_text())
            self.assertIn('설정 누락', gateway_log_paths[0].read_text())
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous_signal_handler)
