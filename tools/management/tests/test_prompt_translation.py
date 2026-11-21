import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.management.domains.translation import service
from tools.management.common.management_gateway import resolve_management_command, identify_management_command


class TranslationServiceTests(unittest.TestCase):
    def test_translation_resume_preview_validates_stored_job_and_command(self):
        from tools.management.common.generation_records import write_record_atomically
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_manager_value=service.TranslationServiceManager()
            current_manager_value.job_storage_root=Path(current_directory_name)/'jobs'
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=current_manager_value.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_request_value=service.validate_translation_submission({'text':'나무','target_language':'en'})
            write_record_atomically(current_job_path/'request.json',{**current_request_value,'model_id':'google/translategemma-4b-it'})
            write_record_atomically(current_job_path/'status.json',{'status':'failed'})
            write_record_atomically(current_job_path/'gpu-command.json',{'service':'prompt-translation','command':service.build_translation_worker_command(current_job_path)})
            with patch('tools.management.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                current_preview_value=current_manager_value.execute_translation_command('resume-preview',{'id':current_job_identifier})
                self.assertEqual(current_preview_value['status'],'failed')
                self.assertNotIn('text',current_preview_value)
                current_fingerprint_value=current_preview_value['expected_resume_fingerprint']
                write_record_atomically(current_job_path/'status.json',{'status':'cancelled'})
                with self.assertRaises(ValueError):current_manager_value.execute_translation_command('resume',{'id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value})
                current_launch_mock.assert_not_called()
                current_preview_value=current_manager_value.execute_translation_command('resume-preview',{'id':current_job_identifier})
                current_result_value=current_manager_value.execute_translation_command('resume',{'id':current_job_identifier,'expected_resume_fingerprint':current_preview_value['expected_resume_fingerprint']})
                self.assertEqual(current_result_value['status'],'queued')
                current_launch_mock.assert_called_once()

    def test_semantic_review_requires_exact_evidence_and_never_automatically_approves(self):
        from generators.prompt_translation.semantic_review import find_negated_source_clauses, validate_semantic_review
        semantic_source_values = find_negated_source_clauses('문자·격자선은 넣지 않는다. 크기는 유지한다.')
        self.assertEqual(semantic_source_values, ['문자·격자선은 넣지 않는다'])
        self.assertEqual(find_negated_source_clauses('그림자는 제외한다. 문자를 넣지 말 것.'), ['그림자는 제외한다', '문자를 넣지 말 것'])
        semantic_target_text = 'No text, but add grid lines.'
        semantic_valid_record = {'results': [{'id': 0, 'verdict': 'contradicted', 'evidence': 'add grid lines'}]}
        semantic_check_values = validate_semantic_review(semantic_valid_record, semantic_source_values, semantic_target_text)
        self.assertEqual(semantic_check_values[0]['status'], 'review')
        self.assertIn('상충 가능성', semantic_check_values[0]['target'])
        for semantic_invalid_record in ({'results': []}, {'results': [{'id': 0, 'verdict': 'preserved', 'evidence': 'made up'}]}, {'results': [{'id': 0, 'verdict': 'preserved', 'evidence': ''}]}):
            with self.assertRaises(ValueError):
                validate_semantic_review(semantic_invalid_record, semantic_source_values, semantic_target_text)

    def test_negation_and_conditions_require_relevant_evidence(self):
        from generators.prompt_translation.quality_checks import inspect_translation_quality
        quality_source_text = '원본의 머리 크기와 다리 길이를 바꾸지 않는다. 투명 배경 4프레임. 문자·격자선은 넣지 않는다.'
        quality_good_results = {
            'en': 'Do not change head size or leg length. Transparent background with 4 frames. Do not include text or grid lines.',
            'zh-CN': '不改变头部大小和腿的长度。透明背景，4帧。不添加文字或网格线。',
        }
        for quality_language, quality_good_text in quality_good_results.items():
            quality_check_values = inspect_translation_quality(quality_source_text, quality_good_text, quality_language)
            self.assertTrue(all(quality_check['status'] == ('review' if quality_check['source_ref'] == '부정 표현 후보 규칙' else 'matched') for quality_check in quality_check_values))
            quality_missing_values = inspect_translation_quality(quality_source_text, 'text grid lines head size leg length' if quality_language == 'en' else '文字网格线头部大小腿的长度', quality_language)
            self.assertTrue(all(quality_check['status'] == 'review' for quality_check in quality_missing_values))
        quality_unsupported_values = inspect_translation_quality('새를 추가하지 않는다.', 'Add a bird.', 'en')
        self.assertEqual(quality_unsupported_values[0]['status'], 'review')
        self.assertEqual(quality_unsupported_values[0]['source_ref'], '미지원 부정문')
        quality_condition_values = inspect_translation_quality('참조가 있으면 나무를 추가한다.', 'Add a tree.', 'en')
        self.assertEqual(quality_condition_values[0]['source_ref'], '미지원 조건문')
        quality_contradiction_values = inspect_translation_quality('문자·격자선은 넣지 않는다.', 'No text, but add text and grid lines.', 'en')
        self.assertTrue(all(quality_check['status'] == 'review' for quality_check in quality_contradiction_values))

    def test_layout_and_condition_checks_report_uncertainty(self):
        from generators.prompt_translation.quality_checks import inspect_translation_quality
        quality_source_text = '4열×1행을 만든다. 눈의 크기와 간격을 모든 방향에서 유지한다.'
        for quality_language, quality_correct_text, quality_reversed_text in [
            ('en', '4 columns and 1 row; eye size and spacing across all views', '4 rows and 1 column'),
            ('zh-CN', '4列1行，所有方向的眼睛大小和间距', '4行1列'),
        ]:
            quality_correct_checks = inspect_translation_quality(quality_source_text, quality_correct_text, quality_language)
            self.assertEqual([quality_check['status'] for quality_check in quality_correct_checks], ['matched', 'matched', 'matched'])
            quality_reversed_checks = inspect_translation_quality(quality_source_text, quality_reversed_text, quality_language)
            self.assertEqual([quality_check['status'] for quality_check in quality_reversed_checks], ['reversed', 'review', 'review'])
            quality_unknown_checks = inspect_translation_quality(quality_source_text, 'unrecognized', quality_language)
            self.assertTrue(all(quality_check['status'] == 'review' for quality_check in quality_unknown_checks))
        self.assertEqual(inspect_translation_quality('일반 문장', 'text', 'en'), [])

    def test_approved_terms_report_mismatch_without_changing_result(self):
        from generators.prompt_translation.terms import load_approved_translation_terms, compare_translation_terms
        current_terms = load_approved_translation_terms('en')
        current_checks = compare_translation_terms('이슬온 마을', 'A village called Isle On.', current_terms)
        self.assertEqual(current_checks[0]['status'], 'mismatch')
        self.assertEqual(current_checks[0]['target'], 'Iseulon')
        self.assertEqual(compare_translation_terms('이슬온', 'Iseulon', current_terms)[0]['status'], 'matched')
        self.assertEqual(compare_translation_terms('셀 음영', 'cell shading', current_terms)[0]['status'], 'mismatch')
        self.assertEqual(compare_translation_terms('셀 음영', 'cel shading', current_terms)[0]['status'], 'matched')
        self.assertEqual(load_approved_translation_terms('zh-CN'), [])

    def test_glossary_input_rejects_ambiguous_terms(self):
        from generators.prompt_translation.terms import validate_translation_glossary
        from tools.management.ui.gradio.prompt_translation_app import parse_translation_glossary
        self.assertEqual(parse_translation_glossary('이슬온 => Iseulon'), [{'source':'이슬온', 'target':'Iseulon'}])
        for current_bad_terms in ([{'source': 'a', 'target': ''}], [{'source': 'a', 'target':'b'}, {'source':'a','target':'c'}], [{'source':'a','target':'b','extra':True}]):
            with self.assertRaises(ValueError):
                validate_translation_glossary(current_bad_terms)
        with self.assertRaises(ValueError):
            parse_translation_glossary('형식 오류')

    def test_translate_gemma_simplified_chinese_language_code(self):
        from generators.prompt_translation.worker import resolve_translation_target_code
        self.assertEqual(resolve_translation_target_code('zh-CN'), 'zh-Hans')
        self.assertEqual(resolve_translation_target_code('en'), 'en')

    def test_gateway_logs_return_only_last_16000_bytes(self):
        import threading
        from http.server import ThreadingHTTPServer
        from tools.management.common.management_gateway import ManagementCommandGateway, execute_management_command
        from tools.management.gateway_server import create_gateway_request_handler
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_manager_value=service.TranslationServiceManager()
            current_manager_value.job_storage_root=Path(current_directory_name)/'jobs'
            current_job_identifier='2026-11-18_12-00-00-aaaaaaaa'
            current_job_path=current_manager_value.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps({'text':'fixture','target_language':'en','glossary':[]}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'failed'}))
            (current_job_path/'worker.log').write_bytes(b'A'*1000+b'B'*16000)
            current_gateway_value=ManagementCommandGateway({'prompt-translation':current_manager_value.handle_translation_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            try:
                current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
                current_log_result=execute_management_command('prompt-translation','logs',{'id':current_job_identifier},current_gateway_origin)
                self.assertEqual(current_log_result,'B'*16000)
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_linked_history_selects_real_translation_record(self):
        from tools.management.ui.gradio.prompt_translation_app import build_translation_interface
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_manager_value=service.TranslationServiceManager()
            current_manager_value.job_storage_root=Path(current_temp_directory)/'jobs'
            current_job_identifier='2026-11-15_12-00-00-12345678'
            current_job_path=current_manager_value.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps({'text':'나무','target_language':'en','glossary':[]}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_path/'result.json').write_text(json.dumps({'text':'tree'}))
            current_command_names=[]
            def execute_temporary_translation(current_service_name,current_command_name,current_payload_record):
                self.assertEqual(current_service_name,'prompt-translation')
                current_command_names.append(current_command_name)
                return current_manager_value.execute_translation_command(current_command_name,current_payload_record)
            with patch('tools.management.ui.gradio.prompt_translation_app.execute_remote_management_command',side_effect=execute_temporary_translation):
                current_interface_value=build_translation_interface()
                current_link_callbacks=[current_dependency.fn for current_dependency in current_interface_value.fns.values() if getattr(current_dependency.fn,'__name__','')=='open_linked_generation_history']
                self.assertEqual(len(current_link_callbacks),1)
                current_updates=current_link_callbacks[0](current_job_identifier,4)
            self.assertEqual(current_updates[0]['value'],current_job_identifier)
            self.assertIn('작업을 선택했습니다',current_updates[-1])
            self.assertEqual(current_command_names,['history','history'])
            self.assertTrue((current_job_path/'result.json').is_file())

    def test_gateway_round_trip(self):
        for translation_command_name, translation_payload_record in [('translation-submit', {'text': '나무', 'target_language': 'en'}), ('translation-status', {'id': '2026-11-15_12-00-00-12345678'}), ('translation-history', {})]:
            translation_method_value, translation_route_value = resolve_management_command('prompt-translation', translation_command_name, translation_payload_record)
            self.assertEqual(identify_management_command(translation_route_value, translation_method_value, translation_payload_record), ('prompt-translation', translation_command_name, translation_payload_record))

    def test_common_history_cleanup_and_status_contract(self):
        with tempfile.TemporaryDirectory() as translation_temp_directory:
            translation_manager_value = service.TranslationServiceManager()
            translation_manager_value.job_storage_root = Path(translation_temp_directory) / 'jobs'
            translation_manager_value.job_storage_root.mkdir()
            translation_job_ids = ['2026-11-15_12-00-00-12345678', '2026-11-15_12-00-01-12345678']
            for translation_job_identifier, translation_status_value in zip(translation_job_ids, ('completed', 'queued')):
                translation_job_path = translation_manager_value.job_storage_root / translation_job_identifier
                translation_job_path.mkdir()
                (translation_job_path / 'request.json').write_text(json.dumps({'text': '나무', 'target_language': 'en', 'glossary': []}))
                (translation_job_path / 'status.json').write_text(json.dumps({'status': translation_status_value}))
                (translation_job_path / 'worker.log').write_text('실행 기록')
            translation_completed_path = translation_manager_value.job_storage_root / translation_job_ids[0]
            (translation_completed_path / 'result.json').write_text(json.dumps({'text': 'tree'}))
            translation_history_records = translation_manager_value.execute_translation_command('history', {})['records']
            self.assertEqual(len(translation_history_records), 2)
            self.assertEqual(translation_manager_value.execute_translation_command('status', {'id': translation_job_ids[0]})['result']['text'], 'tree')
            translation_preview_record = translation_manager_value.execute_translation_command('history-reset-preview', {})
            self.assertFalse(translation_preview_record['can_reset'])
            with self.assertRaises(ValueError):
                translation_manager_value.execute_translation_command('history-reset', {'action': 'reset', 'expected_jobs': translation_preview_record['jobs']})
            with self.assertRaises(ValueError):
                translation_manager_value.execute_translation_command('history-delete', {'id': translation_job_ids[1]})
            self.assertTrue(translation_completed_path.exists())
            translation_deleted_record = translation_manager_value.execute_translation_command('history-delete', {'id': translation_job_ids[0]})
            self.assertEqual(translation_deleted_record['deleted_jobs'], 1)
            self.assertGreater(translation_deleted_record['deleted_bytes'], 0)
            self.assertFalse(translation_completed_path.exists())
            self.assertTrue((translation_manager_value.job_storage_root / translation_job_ids[1]).exists())

    def test_queue_preserves_original_and_checks_input(self):
        with tempfile.TemporaryDirectory() as translation_temp_directory:
            translation_temp_path = Path(translation_temp_directory)
            translation_manager_value = service.TranslationServiceManager()
            translation_manager_value.job_storage_root = translation_temp_path / 'jobs'
            (translation_temp_path / 'model').mkdir()
            (translation_temp_path / 'model' / 'manifest.json').write_text('{}')
            (translation_temp_path / 'python').touch()
            with patch.object(service, 'TRANSLATION_MODEL_ROOT', translation_temp_path / 'model'), patch.object(service, 'TRANSLATION_PYTHON_PATH', translation_temp_path / 'python'), patch.object(service, 'launch_gpu_process') as translation_launch_mock:
                for translation_bad_payload in ({'text': '', 'target_language': 'en'}, {'text': '나무', 'target_language': 'ja'}, {'text': '나무', 'target_language': 'en', 'extra': 1}):
                    with self.assertRaises(ValueError):
                        translation_manager_value.execute_translation_command('translation-submit', translation_bad_payload)
                translation_submission_value = translation_manager_value.execute_translation_command('translation-submit', {'text': '나무', 'target_language': 'zh-CN'})
                translation_job_path = translation_manager_value.job_storage_root / translation_submission_value['id']
                self.assertEqual(json.loads((translation_job_path / 'request.json').read_text())['text'], '나무')
                self.assertEqual(translation_launch_mock.call_args.args[2], 'prompt-translation')
                (translation_job_path / 'status.json').write_text('{"status":"completed"}')
                (translation_job_path / 'result.json').write_text('{"text":"树"}')
                self.assertEqual(translation_manager_value.execute_translation_command('translation-status', {'id': translation_submission_value['id']})['result']['text'], '树')
                self.assertEqual(len(translation_manager_value.execute_translation_command('translation-history', {})['records']), 1)
                with self.assertRaises(ValueError):
                    translation_manager_value.execute_translation_command('translation-status', {'id': '../outside'})


if __name__ == '__main__':
    unittest.main()

class TranslationModelManagementTests(unittest.TestCase):
    def test_fixed_revision_preparation_and_model_management_registration(self):
        from generators.prompt_translation.prepare import TRANSLATION_MODEL_REVISION
        from tools.management.common.model_prepare_worker import MODEL_PREPARATION_PROFILES
        from tools.management.ui.gradio.model_management_app import MODEL_PREPARATION_SERVICES
        from tools.management.common.gradio_model_download import MODEL_DOWNLOAD_PREFIXES
        self.assertEqual(len(TRANSLATION_MODEL_REVISION), 40)
        self.assertIn('prompt-translation-model', MODEL_PREPARATION_PROFILES)
        self.assertIn(('TranslateGemma 4B', 'prompt-translation'), MODEL_PREPARATION_SERVICES)
        self.assertIn('google/translategemma-4b-it', MODEL_DOWNLOAD_PREFIXES['prompt-translation'])
        self.assertEqual(resolve_management_command('prompt-translation', 'prepare', {'action': 'prepare'})[0], 'POST')
        with self.assertRaises(ValueError):
            resolve_management_command('prompt-translation', 'prepare', {'action': 'prepare', 'revision': 'arbitrary'})

    def test_translation_page_has_model_management_link_and_history_timer(self):
        from tools.management.ui.gradio.prompt_translation_app import build_translation_interface
        from tools.management.ui.gradio.management_menu_app import build_management_menu_interface
        translation_interface_value, _ = build_management_menu_interface([], 8770, build_translation_interface())
        translation_config_value=translation_interface_value.get_config_file()
        self.assertTrue(any(current_component.get('props',{}).get('value')=='전달된 작업을 이력에서 찾기' for current_component in translation_config_value['components']))
        self.assertTrue(any("searchParams.get('job')" in str(current_dependency.get('js','')) for current_dependency in translation_config_value['dependencies']))
        translation_configuration_value = translation_interface_value.get_config_file()
        self.assertTrue(translation_configuration_value['connect_heartbeat'])
        self.assertTrue(any(current_component.get('props', {}).get('link') == '/management/?tool=model-management&category=model-management' for current_component in translation_configuration_value['components']))
