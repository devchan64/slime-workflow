import json
import socket
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent.management_bridge import handle_hermes_observer_connection
from workflow.domains.hermes_agent.model_backup_observer import observe_backup


class HermesBackupObserverTest(unittest.TestCase):
    def test_compare_returns_summary_without_file_paths(self):
        response = {'files': [{'status': 'missing', 'path': 'private'}, {'status': 'different', 'path': 'other'}],
                    'complete': True, 'comparison_basis': 'size_and_mtime', 'source_errors': [], 'backup_errors': []}
        with patch('workflow.domains.hermes_agent.model_backup_observer.execute_management_command', return_value=response) as command:
            result = observe_backup('compare', 'model')
        self.assertEqual(result['counts'], {'missing': 1, 'different': 1})
        self.assertNotIn('private', json.dumps(result))
        self.assertEqual(command.call_args.args[:3], ('model-downloads', 'backup-compare', {'model': 'model'}))

    def test_bridge_uses_only_fixed_read_operations(self):
        for request, expected in ((b'model-backup-models\n', ('models',)),
                                  (b'model-backup-history\n', ('history',)),
                                  (b'model-backup-compare model\n', ('compare', 'model'))):
            with self.subTest(request=request):
                client, server = socket.socketpair()
                with client, patch('workflow.domains.hermes_agent.model_backup_observer.observe_backup', return_value={'ok': True}) as observe:
                    thread = threading.Thread(target=handle_hermes_observer_connection, args=(server,))
                    thread.start()
                    client.sendall(request)
                    result = json.loads(client.makefile('rb').readline())
                    thread.join(timeout=3)
                    self.assertEqual(result, {'ok': True})
                    observe.assert_called_once_with(*expected)

    def test_rejects_invalid_model(self):
        for name in ('../model', 'a/b', '', '..'):
            with self.assertRaises(ValueError):
                observe_backup('compare', name)

    def test_isolated_client_can_request_comparison(self):
        executable = shutil.which('bwrap')
        if not executable:
            self.skipTest('bubblewrap이 없습니다.')
        from workflow.domains.hermes_agent import management_status_client
        with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            socket_path = Path(directory) / 'observer.sock'
            listener.bind(str(socket_path))
            listener.listen(1)
            listener.settimeout(5)
            def serve():
                try:
                    connection, _ = listener.accept()
                    handle_hermes_observer_connection(connection)
                except OSError:
                    return
            with patch('workflow.domains.hermes_agent.model_backup_observer.observe_backup', return_value={'model': 'sample', 'counts': {'missing': 1}}):
                thread = threading.Thread(target=serve, daemon=True)
                thread.start()
                command = [executable, '--unshare-all', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
                           '--ro-bind', '/lib64', '/lib64', '--dir', '/control', '--bind', str(socket_path), '/control/management-status.sock',
                           '--ro-bind', str(Path(management_status_client.__file__)), '/control/management-status.py',
                           '--proc', '/proc', '--dev', '/dev', '--', '/usr/bin/python3', '/control/management-status.py',
                           'model-backup-compare', 'sample']
                completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
                if completed.returncode and 'No permissions to create a new namespace' in completed.stderr:
                    self.skipTest('이 환경은 격리 네임스페이스 실행을 허용하지 않습니다.')
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)['counts'], {'missing': 1})
                thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
