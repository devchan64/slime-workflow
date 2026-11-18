"""Hermes 상태에서 메모리 보호와 오류 비공개를 검증한다."""
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import audio_operations, translation_operations, writer_operations
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_failure_reason


class HermesFailureObserverTests(unittest.TestCase):
    def test_fixed_messages_do_not_expose_error_details(self):
        for current_error_value,current_expected_code in (("시스템 RAM 보호: /private/secret", "host_memory_guard"), ("시스템 RAM 감시 실패: /private/secret", "host_memory_monitor_failed")):
            with self.subTest(code=current_expected_code):
                current_result_value=observe_hermes_failure_reason('failed',current_error_value)
                self.assertEqual(current_result_value['failure_code'],current_expected_code)
                self.assertNotIn('private',str(current_result_value))
                self.assertEqual(observe_hermes_failure_reason('running',current_error_value),{})
        self.assertEqual(observe_hermes_failure_reason('failed','다른 오류: /private/secret'),{})

    def test_audio_translation_writer_expose_guard_classification(self):
        current_receipt_value={'state':'accepted','job_id':'job123'}
        current_guard_error='시스템 RAM 보호: /private/secret'
        for current_module_value,current_service_name,current_response_value,current_reader_value in (
            (audio_operations,'call_hermes_audio_service',{'id':'job123','status':'failed','error':current_guard_error},lambda:audio_operations.read_hermes_audio_status('request_123','music-heartmula')),
            (translation_operations,'call_hermes_translation_service',{'id':'job123','status':{'status':'failed','error':current_guard_error}},lambda:translation_operations.read_hermes_translation_status('request_123')),
            (writer_operations,'call_hermes_writer_service',{'id':'job123','status':{'stage':'failed','error':current_guard_error}},lambda:writer_operations.read_hermes_writer_status('request_123')),
        ):
            with self.subTest(service=current_service_name), patch.object(current_module_value,'HermesDelegationStore') as current_store_mock, patch.object(current_module_value,current_service_name,return_value=current_response_value):
                current_store_mock.return_value.read_service_delegation.return_value=current_receipt_value
                current_result_value=current_reader_value()
                self.assertEqual(current_result_value['job']['failure_code'],'host_memory_guard')
                self.assertNotIn('private',str(current_result_value))


class HermesGuardSourceIntegrationTests(unittest.TestCase):
    def test_music_queue_guard_overrides_attempt_error_and_reaches_hermes(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.domains.music.generation import MusicGenerationManager
        with TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)/'job123'
            current_attempt_root=current_job_root/'attempts'/('a'*32)
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'current-attempt.json').write_text(json.dumps({'id':'a'*32}))
            (current_attempt_root/'error.json').write_text(json.dumps({'error':'worker error'}))
            current_manager_value=MusicGenerationManager('music-heartmula')
            current_receipt_value={'state':'accepted','job_id':'job123'}
            for current_queue_error,current_expected_error in (('시스템 RAM 보호: /private/secret','시스템 RAM 보호: /private/secret'),('other queue error','worker error')):
                (current_job_root/'status.json').write_text(json.dumps({'status':'failed','error':current_queue_error}))
                current_source_value=current_manager_value.read_music_status(current_job_root,False)
                self.assertEqual(current_source_value['error'],current_expected_error)
                if current_queue_error.startswith('시스템 RAM 보호:'):
                    with patch.object(audio_operations,'HermesDelegationStore') as current_store_mock, patch.object(audio_operations,'call_hermes_audio_service',return_value=current_source_value):
                        current_store_mock.return_value.read_service_delegation.return_value=current_receipt_value
                        current_result_value=audio_operations.read_hermes_audio_status('request_123','music-heartmula')
                        self.assertEqual(current_result_value['job']['failure_code'],'host_memory_guard')
                        self.assertNotIn('private',str(current_result_value))

    def test_writer_guard_survives_missing_supervisor_and_terminal_yaml(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from generators.writer_agent.management import WriterAgentManager
        with TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)/'job123'
            current_job_root.mkdir()
            current_manager_value=WriterAgentManager(Path(current_directory_name)/'workspace.yaml')
            current_guard_error='시스템 RAM 감시 실패: /private/secret'
            (current_job_root/'status.json').write_text(json.dumps({'status':'failed','error':current_guard_error}))
            for current_stage_value in ('reasoning','failed'):
                current_source_value=current_manager_value.resolve_observed_status({'id':'job123','stage':current_stage_value,'error':'worker error'},current_job_root)
                self.assertEqual(current_source_value['stage'],'failed')
                self.assertEqual(current_source_value['error'],current_guard_error)
                with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value={'id':'job123','status':current_source_value}):
                    current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':'job123'}
                    current_result_value=writer_operations.read_hermes_writer_status('request_123')
                    self.assertEqual(current_result_value['job']['failure_code'],'host_memory_monitor_failed')
                    self.assertNotIn('private',str(current_result_value))
            current_completed_value={'id':'job123','stage':'completed'}
            self.assertEqual(current_manager_value.resolve_observed_status(current_completed_value,current_job_root),current_completed_value)
