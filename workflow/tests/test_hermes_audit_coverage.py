import unittest
from unittest.mock import patch
from workflow.maintenance.check_hermes_audit_coverage import inspect_hermes_command_coverage


class HermesAuditCoverageTests(unittest.TestCase):
    def test_detects_missing_obsolete_duplicate_and_duplicate_section(self):
        current_registered_commands={'example-service':('read','write'),'other-service':('list',)}
        current_audit_text="""## example-service
| 등록 명령 | 확인 |
| --- | --- |
| `read` | 확인 |
| `read` | 중복 |
| `old` | 과거 |
## other-service
| `list` | 확인 |
"""
        with patch('workflow.maintenance.check_hermes_audit_coverage.MANAGEMENT_SERVICE_COMMANDS',current_registered_commands):
            current_coverage_value=inspect_hermes_command_coverage(current_audit_text)
            self.assertEqual(current_coverage_value['missing'],[('example-service','write')])
            self.assertEqual(current_coverage_value['obsolete'],[('example-service','old')])
            self.assertEqual(current_coverage_value['duplicates'],[('example-service','read')])
            self.assertEqual(current_coverage_value['unregistered_sections'],[])
            current_removed_value=inspect_hermes_command_coverage(current_audit_text+'\n## removed-service\n| `old` | 이전 기능 |\n## 참고\n설명 문단\n')
            self.assertEqual(current_removed_value['unregistered_sections'],['removed-service'])
            with self.assertRaises(ValueError):inspect_hermes_command_coverage(current_audit_text+'\n## example-service\n')
