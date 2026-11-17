import unittest
import tempfile
from unittest.mock import patch

from tools.review.ui.gradio import hermes_agent_app
from tools.review.ui.gradio.management_menu_app import load_manager_page_records
from tools.review.common.management_asgi import build_management_blocks
from pathlib import Path


class HermesGradioTests(unittest.TestCase):
    def test_management_page_composes_with_menu(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_source_path = Path(hermes_temporary_root) / 'manager.json'
            hermes_source_path.write_text('{"pages":[]}')
            hermes_page_records = load_manager_page_records(hermes_source_path)
            self.assertIn('hermes-agent', [hermes_page_record['id'] for hermes_page_record in hermes_page_records])
            with patch.dict('os.environ', {'SLIME_MANAGEMENT_MENU_SOURCE': str(Path(hermes_temporary_root) / 'missing.json')}):
                hermes_interface_blocks, hermes_mount_options = build_management_blocks('hermes-agent', 8770, hermes_source_path)
            hermes_component_labels = [getattr(hermes_component_value, 'label', None) for hermes_component_value in hermes_interface_blocks.blocks.values()]
            self.assertIn('작업 지시', hermes_component_labels)
            self.assertIn('검토용 변경 diff', hermes_component_labels)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_submission_passes_stable_request_identifier(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'2026-11-17_10-00-00-12345678', 'duplicate':False}
        hermes_job_identifier, hermes_status_text = hermes_agent_app.submit_hermes_work_request('작업', 'same-request-1234')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-submit', {'prompt':'작업', 'request_id':'same-request-1234'})
        self.assertEqual(hermes_job_identifier, '2026-11-17_10-00-00-12345678')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command', side_effect=ValueError('지원하지 않는 관리 명령'))
    def test_history_explains_gateway_version_error(self, hermes_gateway_mock):
        hermes_history_rows, hermes_history_message = hermes_agent_app.refresh_hermes_work_history()
        self.assertEqual(hermes_history_rows, [])
        self.assertIn('게이트웨이 실행 상태와 버전', hermes_history_message)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_submission_includes_selected_verification_modules(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'2026-11-17_10-00-00-12345678', 'duplicate':False}
        hermes_agent_app.submit_hermes_work_request('작업', 'request-1234', 'tools.review.tests.test_hermes_service\n')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-submit', {'prompt':'작업', 'request_id':'request-1234', 'verification_modules':['tools.review.tests.test_hermes_service']})


if __name__ == '__main__':
    unittest.main()
