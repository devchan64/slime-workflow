"""관리 작업 위임 중복 방지와 불확실한 접수 복구 검증."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesDelegationTests(unittest.TestCase):
    def test_kimodo_resume_proposal_requires_single_valid_target(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_resume_proposal
        current_proposal_value={'job_id':'2026-11-20_00-00-00-12345678','expected_resume_fingerprint':'a'*64}
        current_answer_text='HERMES_KIMODO_RESUME_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_KIMODO_RESUME_PROPOSAL'
        self.assertEqual(parse_hermes_kimodo_resume_proposal(current_answer_text),current_proposal_value)
        for current_bad_value in ({**current_proposal_value,'job_id':'../outside'},{**current_proposal_value,'expected_resume_fingerprint':'bad'},{**current_proposal_value,'extra':True}):
            with self.subTest(current_bad_value=current_bad_value),self.assertRaises(ValueError):parse_hermes_kimodo_resume_proposal('HERMES_KIMODO_RESUME_PROPOSAL\n'+json.dumps(current_bad_value)+'\nEND_HERMES_KIMODO_RESUME_PROPOSAL')
        with self.assertRaises(ValueError):parse_hermes_kimodo_resume_proposal(current_answer_text+'\n'+current_answer_text)

    def test_model_preparation_proposal_accepts_only_one_registered_service(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_model_preparation_proposal
        current_answer_text='제안입니다.\nHERMES_MODEL_PREPARATION_PROPOSAL\n{"service":"flux-image"}\nEND_HERMES_MODEL_PREPARATION_PROPOSAL'
        self.assertEqual(parse_hermes_model_preparation_proposal(current_answer_text),{'service':'flux-image'})
        for current_bad_text in (current_answer_text+'\n'+current_answer_text,current_answer_text.replace('flux-image','unknown-service'),current_answer_text.replace('{"service":"flux-image"}','{"service":"flux-image","request_id":"invented"}'),current_answer_text.replace('{"service":"flux-image"}','{"service":"flux-image","service":"kimodo"}')):
            with self.subTest(current_bad_text=current_bad_text),self.assertRaises(ValueError):parse_hermes_model_preparation_proposal(current_bad_text)

    def test_unreadable_receipt_never_dispatches_or_reports_absent(self):
        from workflow.domains.hermes_agent import audio_resume_operations, field_map_operations
        current_identifier='receipt_error_123'
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_draft={'map':'sample','revision':'revision','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_record_path=current_root_path/(current_identifier+'.json')
            current_record_path.write_text('{"existing":true}')
            current_store_value=HermesDelegationStore(current_root_path)
            current_lstat_method=Path.lstat
            def reject_receipt_stat(current_path_value,*current_arguments,**current_keywords):
                if current_path_value==current_record_path:raise PermissionError('unreadable')
                return current_lstat_method(current_path_value,*current_arguments,**current_keywords)
            current_submit_mock=Mock()
            with patch.object(Path,'exists',return_value=False),patch.object(Path,'lstat',autospec=True,side_effect=reject_receipt_stat),patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',current_root_path),patch.object(audio_resume_operations,'call_hermes_audio_service') as current_audio_mock,patch.object(field_map_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(field_map_operations,'call_field_map_editor') as current_map_mock:
                with self.assertRaises(PermissionError):current_store_value.read_delegation_status(current_identifier)
                with self.assertRaises(PermissionError):current_store_value.execute_delegation_once(current_identifier,{},current_submit_mock)
                with self.assertRaises(PermissionError):current_store_value.read_service_delegation(current_identifier,'writer-agent')
                with self.assertRaises(PermissionError):current_store_value.execute_service_delegation_once(current_identifier,'writer-agent',{},current_submit_mock,lambda current_request_value:None)
                with self.assertRaises(PermissionError):audio_resume_operations.read_hermes_audio_resume_receipt(current_identifier)
                with self.assertRaises(PermissionError):audio_resume_operations.submit_hermes_audio_resume_once(current_identifier,'music-heartmula',current_job_identifier,'a'*64)
                with self.assertRaises(PermissionError):field_map_operations.save_hermes_field_map_once(current_identifier,current_draft,current_token)
                current_submit_mock.assert_not_called()
                current_audio_mock.assert_not_called()
                current_map_mock.assert_not_called()
            self.assertEqual(current_record_path.read_text(),'{"existing":true}')

    def test_unreadable_receipt_list_blocks_resume_and_priority(self):
        from workflow.domains.hermes_agent import audio_resume_operations, priority_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_iterdir_method=Path.iterdir
            def reject_receipt_listing(current_path_value,*current_arguments,**current_keywords):
                if current_path_value==current_root_path:raise PermissionError('unreadable')
                return current_iterdir_method(current_path_value,*current_arguments,**current_keywords)
            with patch.object(Path,'iterdir',autospec=True,side_effect=reject_receipt_listing),patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',current_root_path),patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',current_root_path),patch.object(audio_resume_operations,'call_hermes_audio_service') as current_audio_mock,patch('workflow.common.gpu_job_queue.prioritize_waiting_generation') as current_priority_mock:
                with self.assertRaises(PermissionError):audio_resume_operations.submit_hermes_audio_resume_once('resume_error_123','music-heartmula',current_job_identifier,'a'*64)
                with self.assertRaises(PermissionError):priority_operations.submit_hermes_priority_once('priority_error_123','kimodo',current_job_identifier,'b'*64)
                current_audio_mock.assert_not_called()
                current_priority_mock.assert_not_called()
            self.assertEqual(list(current_root_path.glob('*.json')),[])

    def test_keyframe_delegation_preserves_input_and_rejects_id_reuse(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS
        current_request={key:value for key,value in KIMODO_DEFAULT_SETTINGS.items() if key != 'schema_version'}
        current_request.update(action='generate',prompt='walk',frames=30,steps=2,seed=42,post_processing=True,
                               keyframes=[{'id':'a'*32,'frame':1},{'id':'b'*32,'frame':20}])
        current_review_value={'request_id':'keyframe_request_1','request':current_request}
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_manager_value=HermesServiceManager(current_root_path/'jobs')
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value),patch('workflow.common.management_gateway.execute_management_command',return_value={'id':'2026-11-18_00-00-00-12345678'}) as current_gateway_mock:
                self.assertFalse(current_manager_value.execute_hermes_command('hermes-delegate-kimodo',current_review_value)['duplicate'])
                self.assertTrue(current_manager_value.execute_hermes_command('hermes-delegate-kimodo',current_review_value)['duplicate'])
                self.assertEqual(current_gateway_mock.call_args.args[2]['keyframes'],current_review_value['request']['keyframes'])
                current_changed_value={**current_review_value,'request':{**current_review_value['request'],'keyframes':[{'id':'a'*32,'frame':2}]}}
                with self.assertRaises(ValueError):
                    current_manager_value.execute_hermes_command('hermes-delegate-kimodo',current_changed_value)
                current_gateway_mock.assert_called_once()

    def test_proposal_is_strict_and_never_submits(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal
        current_answer_text = '생성 제안입니다.\nHERMES_KIMODO_PROPOSAL\n{"prompt":"walk forward","frames":90,"steps":100,"seed":42}\nEND_HERMES_KIMODO_PROPOSAL'
        self.assertEqual(parse_hermes_kimodo_proposal(current_answer_text)['prompt'], 'walk forward')
        for current_invalid_text in (current_answer_text + '\n' + current_answer_text, current_answer_text.replace('"seed":42', '"seed":42,"seed":43'), current_answer_text.replace('"seed":42', '"seed":42,"url":"https://invalid"'), current_answer_text.replace('"frames":90', '"frames":1'), current_answer_text.replace('END_HERMES_KIMODO_PROPOSAL', '')):
            with self.subTest(answer=current_invalid_text), self.assertRaises(ValueError):
                parse_hermes_kimodo_proposal(current_invalid_text)

    def test_kimodo_example_proposal_requires_registered_example(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal
        def answer(value):
            return 'HERMES_KIMODO_PROPOSAL\n'+json.dumps(value)+'\nEND_HERMES_KIMODO_PROPOSAL'
        self.assertEqual(parse_hermes_kimodo_proposal(answer({'example_id':'male_floor_rest_cycle'})), {'example_id':'male_floor_rest_cycle'})
        for value in ({'example_id':'../invalid'}, {'example_id':'male_floor_rest_cycle','frames':160}, {'example_id':None}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_hermes_kimodo_proposal(answer(value))

    def test_flux_proposal_rejects_extra_duplicate_and_invalid_inputs(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_proposal
        current_answer = '제안입니다.\nHERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        self.assertEqual(parse_hermes_flux_proposal(current_answer)['seed'],42)
        for current_bad_answer in (current_answer+'\n'+current_answer, current_answer.replace('"seed":42','"seed":42,"seed":43'), current_answer.replace('"seed":42','"seed":42,"images":[]'), current_answer.replace('"width":512','"width":513'), current_answer.replace('END_HERMES_FLUX_PROPOSAL','')):
            with self.subTest(answer=current_bad_answer), self.assertRaises(ValueError):
                parse_hermes_flux_proposal(current_bad_answer)

    def test_flux_proposal_supports_registered_image_profiles(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_proposal
        for current_service in ('flux-image','flux-character','flux-prop','flux-vegetation','flux-seamless','flux-building','flux-billboard','flux-mannequin'):
            current_payload={'service':current_service,'prompt':'blue sky','width':512,'height':512,'seed':42}
            current_answer='HERMES_FLUX_PROPOSAL\n'+json.dumps(current_payload)+'\nEND_HERMES_FLUX_PROPOSAL'
            self.assertEqual(parse_hermes_flux_proposal(current_answer)['service'],current_service)
        for current_service in ('flux-expression','unknown'):
            current_payload={'service':current_service,'prompt':'blue sky','width':512,'height':512,'seed':42}
            with self.assertRaises(ValueError):parse_hermes_flux_proposal('HERMES_FLUX_PROPOSAL\n'+json.dumps(current_payload)+'\nEND_HERMES_FLUX_PROPOSAL')
        current_payload={'service':'flux-seamless','prompt':'blue sky','width':768,'height':512,'seed':42}
        with self.assertRaises(ValueError):parse_hermes_flux_proposal('HERMES_FLUX_PROPOSAL\n'+json.dumps(current_payload)+'\nEND_HERMES_FLUX_PROPOSAL')

    def test_flux_expression_proposal_validates_registered_preset(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_proposal
        current_payload={'service':'flux-expression','prompt':'joy','width':512,'height':512,'seed':42}
        current_answer='HERMES_FLUX_PROPOSAL\n'+json.dumps(current_payload)+'\nEND_HERMES_FLUX_PROPOSAL'
        self.assertEqual(parse_hermes_flux_proposal(current_answer),current_payload)
        current_payload['prompt']='not_a_real_expression'
        with self.assertRaises(ValueError):parse_hermes_flux_proposal('HERMES_FLUX_PROPOSAL\n'+json.dumps(current_payload)+'\nEND_HERMES_FLUX_PROPOSAL')

    def test_flux_proposal_requires_completed_untruncated_job(self):
        import json
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_service = HermesServiceManager(Path(current_temp_root))
            current_job_id = '2026-11-18_00-00-00-12345678'
            current_job_path = Path(current_temp_root) / current_job_id
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text('{}')
            (current_job_path / 'status.json').write_text('{"status":"running"}')
            current_answer = 'HERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
            (current_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer}))
            with self.assertRaises(ValueError):
                current_service.execute_hermes_command('hermes-flux-proposal', {'id':current_job_id})
            (current_job_path / 'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service.execute_hermes_command('hermes-flux-proposal', {'id':current_job_id})['proposal']['width'],512)
            (current_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer+'x'*8001}))
            with self.assertRaises(ValueError):
                current_service.execute_hermes_command('hermes-flux-proposal', {'id':current_job_id})

    def test_video_proposal_limits_service_mode_and_attachments(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal,HERMES_VIDEO_PROPOSAL_MODES
        from workflow.domains.hermes_agent.service import HermesServiceManager
        for current_service_name,current_modes_value in HERMES_VIDEO_PROPOSAL_MODES.items():
            for current_mode_value in current_modes_value:
                current_proposal_value={'service':current_service_name,'mode':current_mode_value,'prompt':'' if current_service_name=='dwpose' else 'a scene'}
                current_answer_value='설명\nHERMES_VIDEO_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_VIDEO_PROPOSAL\n검토 필요'
                self.assertEqual(parse_hermes_video_proposal(current_answer_value),current_proposal_value)
        current_proposal_value={'service':'wan22-vace','mode':'text','prompt':'a scene'}
        for current_bad_value in ({**current_proposal_value,'path':'/private'},{**current_proposal_value,'mode':'pose_video'},{**current_proposal_value,'service':'unknown'},{**current_proposal_value,'prompt':''}):
            with self.assertRaises(ValueError):
                parse_hermes_video_proposal('HERMES_VIDEO_PROPOSAL\n'+json.dumps(current_bad_value)+'\nEND_HERMES_VIDEO_PROPOSAL')
        current_answer_value='HERMES_VIDEO_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_VIDEO_PROPOSAL'
        with self.assertRaises(ValueError):
            parse_hermes_video_proposal(current_answer_value+'\n'+current_answer_value)
        with tempfile.TemporaryDirectory() as current_root_name:
            current_service_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-video-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-video-proposal',{'id':current_job_identifier})['proposal'],current_proposal_value)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value+'x'*8001}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-video-proposal',{'id':current_job_identifier})

    def test_writer_proposal_validates_request_and_completed_job(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_writer_proposal
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_value={'mode':'write','prompt':'마을 소개를 작성한다'}
        current_answer_value='HERMES_WRITER_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_WRITER_PROPOSAL'
        self.assertEqual(parse_hermes_writer_proposal(current_answer_value),current_proposal_value)
        for current_bad_value in ({'mode':'write','prompt':''},{'mode':'learn','prompt':'unexpected'},{'mode':'delete','prompt':'x'},{'mode':'write','prompt':'x','path':'/tmp/x'}):
            with self.assertRaises(ValueError):
                parse_hermes_writer_proposal('HERMES_WRITER_PROPOSAL\n'+json.dumps(current_bad_value)+'\nEND_HERMES_WRITER_PROPOSAL')
        with self.assertRaises(ValueError):parse_hermes_writer_proposal(current_answer_value+'\n'+current_answer_value)
        with tempfile.TemporaryDirectory() as current_root_name:
            current_service_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value}))
            with self.assertRaises(ValueError):current_service_value.execute_hermes_command('hermes-writer-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-writer-proposal',{'id':current_job_identifier})['proposal'],current_proposal_value)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value+'x'*8001}))
            with self.assertRaises(ValueError):current_service_value.execute_hermes_command('hermes-writer-proposal',{'id':current_job_identifier})

    def test_audio_proposal_validates_service_fields_and_completed_job(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_audio_proposal
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_value={'service':'sfx-dasheng-audiogen','request':{'action':'generate','prompt':'water splash','seed':42,'loop_request':False}}
        current_answer_value='효과음 제안입니다.\nHERMES_AUDIO_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_AUDIO_PROPOSAL\n\n확인 후 접수하세요.'
        self.assertEqual(parse_hermes_audio_proposal(current_answer_value),current_proposal_value)
        current_music_value={'service':'music-heartmula','request':{'action':'generate','prompt':'piano','lyrics':'[Verse]\nHello','duration_seconds':30,'seed':7,'loop_request':False}}
        self.assertEqual(parse_hermes_audio_proposal('HERMES_AUDIO_PROPOSAL\n'+json.dumps(current_music_value)+'\nEND_HERMES_AUDIO_PROPOSAL'),current_music_value)
        for current_bad_value in ({**current_proposal_value,'service':'music-magenta'},{**current_proposal_value,'request':{**current_proposal_value['request'],'duration_seconds':10}},{**current_proposal_value,'request':{**current_proposal_value['request'],'action':'prepare'}},{**current_music_value,'request':{**current_music_value['request'],'loop_request':True}}):
            with self.assertRaises(ValueError):
                parse_hermes_audio_proposal('HERMES_AUDIO_PROPOSAL\n'+json.dumps(current_bad_value)+'\nEND_HERMES_AUDIO_PROPOSAL')
        with self.assertRaises(ValueError):
            parse_hermes_audio_proposal(current_answer_value+'\n'+current_answer_value)
        with tempfile.TemporaryDirectory() as current_root_name:
            current_service_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-audio-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-audio-proposal',{'id':current_job_identifier})['proposal'],current_proposal_value)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value+'x'*8001}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-audio-proposal',{'id':current_job_identifier})

    @patch('workflow.domains.translation.service.load_approved_translation_terms',return_value=[])
    def test_translation_proposal_rejects_unsafe_and_requires_completed_job(self,current_terms_mock):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_translation_proposal
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_value={'text':'푸른 나무','target_language':'en','glossary':[{'source':'나무','target':'tree'}]}
        current_answer_value='제안입니다.\nHERMES_TRANSLATION_PROPOSAL\n'+json.dumps(current_proposal_value,ensure_ascii=False)+'\nEND_HERMES_TRANSLATION_PROPOSAL\n\n검토 후 접수하세요.'
        self.assertEqual(parse_hermes_translation_proposal(current_answer_value),current_proposal_value)
        for current_bad_value in ({**current_proposal_value,'target_language':'fr'},{**current_proposal_value,'text':''},{**current_proposal_value,'glossary':[{'source':'없는 단어','target':'x'}]},{**current_proposal_value,'command':'run'}):
            with self.assertRaises(ValueError):
                parse_hermes_translation_proposal('HERMES_TRANSLATION_PROPOSAL\n'+json.dumps(current_bad_value)+'\nEND_HERMES_TRANSLATION_PROPOSAL')
        with self.assertRaises(ValueError):
            parse_hermes_translation_proposal(current_answer_value+'\n'+current_answer_value)
        with tempfile.TemporaryDirectory() as current_root_name:
            current_service_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-translation-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-translation-proposal',{'id':current_job_identifier})['proposal'],current_proposal_value)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value+'x'*8001}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-translation-proposal',{'id':current_job_identifier})

    def test_sprite_proposal_requires_valid_single_block(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_sprite_proposal
        current_proposal_record={'path':'assets/characters/default/animations/test/sheet.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        def render_test_proposal(current_value_record):
            return '설명\nHERMES_SPRITE_PROPOSAL\n'+json.dumps(current_value_record)+'\nEND_HERMES_SPRITE_PROPOSAL\n검토하세요.'
        current_answer_text=render_test_proposal(current_proposal_record)
        self.assertEqual(parse_hermes_sprite_proposal(current_answer_text),current_proposal_record)
        for current_invalid_record in ({**current_proposal_record,'path':'../secret.png'},{**current_proposal_record,'snapshot':'old'},{**current_proposal_record,'columns':True},{**current_proposal_record,'anchors':[]},{**current_proposal_record,'anchors':current_proposal_record['anchors']*2},{**current_proposal_record,'image':'data'}):
            with self.subTest(proposal=current_invalid_record),self.assertRaises(ValueError):parse_hermes_sprite_proposal(render_test_proposal(current_invalid_record))
        with self.assertRaises(ValueError):parse_hermes_sprite_proposal(current_answer_text+'\n'+current_answer_text)

    def test_sprite_proposal_service_requires_completed_untruncated_job(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_record={'path':'assets/characters/default/animations/test/sheet.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        current_answer_text='HERMES_SPRITE_PROPOSAL\n'+json.dumps(current_proposal_record)+'\nEND_HERMES_SPRITE_PROPOSAL'
        with TemporaryDirectory() as current_root_name:
            current_manager_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_text}))
            with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-sprite-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_manager_value.execute_hermes_command('hermes-sprite-proposal',{'id':current_job_identifier})['proposal'],current_proposal_record)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_text+'x'*8001}))
            with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-sprite-proposal',{'id':current_job_identifier})

    def test_effect_proposal_requires_valid_single_block(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_effect_proposal
        current_proposal_record={'id':'firefly-v1','revision':'a'*64,'target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]}
        def render_test_proposal(current_value_record):
            return '설명\nHERMES_EFFECT_PROPOSAL\n'+json.dumps(current_value_record)+'\nEND_HERMES_EFFECT_PROPOSAL\n검토하세요.'
        current_answer_text=render_test_proposal(current_proposal_record)
        self.assertEqual(parse_hermes_effect_proposal(current_answer_text),current_proposal_record)
        for current_invalid_record in ({**current_proposal_record,'target':[0,0,0,1]},{**current_proposal_record,'alpha':True},{**current_proposal_record,'revision':'old'},{**current_proposal_record,'image':'path'}):
            with self.subTest(proposal=current_invalid_record),self.assertRaises(ValueError):parse_hermes_effect_proposal(render_test_proposal(current_invalid_record))
        with self.assertRaises(ValueError):parse_hermes_effect_proposal(current_answer_text+'\n'+current_answer_text)

    def test_effect_proposal_service_requires_completed_untruncated_job(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_record={'id':'firefly-v1','revision':'a'*64,'target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]}
        current_answer_text='HERMES_EFFECT_PROPOSAL\n'+json.dumps(current_proposal_record)+'\nEND_HERMES_EFFECT_PROPOSAL'
        with TemporaryDirectory() as current_root_name:
            current_manager_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_text}))
            with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-effect-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_manager_value.execute_hermes_command('hermes-effect-proposal',{'id':current_job_identifier})['proposal'],current_proposal_record)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_text+'x'*8001}))
            with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-effect-proposal',{'id':current_job_identifier})

    def test_billboard_proposal_requires_observed_scalar_properties(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_billboard_proposal
        current_proposal_record={'texture':'tree-v1','expected':{'displayHeight':520},'values':{'displayHeight':500}}
        def render_test_answer(current_value_record):
            return '설명\nHERMES_BILLBOARD_PROPOSAL\n'+json.dumps(current_value_record)+'\nEND_HERMES_BILLBOARD_PROPOSAL\n검토하세요.'
        self.assertEqual(parse_hermes_billboard_proposal(render_test_answer(current_proposal_record)),current_proposal_record)
        for current_invalid_record in ({**current_proposal_record,'expected':{}},{**current_proposal_record,'values':{'image':'path'}},{**current_proposal_record,'values':{'displayHeight':float('nan')}},{**current_proposal_record,'texture':'../escape'}):
            with self.subTest(proposal=current_invalid_record),self.assertRaises(ValueError):
                parse_hermes_billboard_proposal(render_test_answer(current_invalid_record))

    def test_billboard_proposal_service_requires_completed_job(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_record={'texture':'tree-v1','expected':{'displayHeight':520},'values':{'displayHeight':500}}
        current_answer_text='HERMES_BILLBOARD_PROPOSAL\n'+json.dumps(current_proposal_record)+'\nEND_HERMES_BILLBOARD_PROPOSAL'
        with TemporaryDirectory() as current_root_name:
            current_manager_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_text}))
            with self.assertRaises(ValueError):
                current_manager_value.execute_hermes_command('hermes-billboard-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_manager_value.execute_hermes_command('hermes-billboard-proposal',{'id':current_job_identifier})['proposal'],current_proposal_record)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_text+'x'*8001}))
            with self.assertRaises(ValueError):
                current_manager_value.execute_hermes_command('hermes-billboard-proposal',{'id':current_job_identifier})

    def test_city_and_building_proposal_service_requires_complete_untruncated_job(self):
        import json
        from workflow.common.management_gateway import resolve_management_command,identify_management_command
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposals={
            'city':{'map':'stonewarm','generation':5,'revision':2,'changes':[{'path':['data','name'],'before':'기존','after':'변경'}]},
            'building':{'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}},
        }
        with tempfile.TemporaryDirectory() as current_root_name:
            current_manager=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            for current_kind,current_proposal in current_proposals.items():
                with self.subTest(kind=current_kind):
                    current_command='hermes-'+current_kind+'-proposal'
                    current_payload={'id':current_job_identifier}
                    current_method,current_route=resolve_management_command('hermes-agent',current_command,current_payload)
                    self.assertEqual(identify_management_command(current_route,current_method,current_payload)[:2],('hermes-agent',current_command))
                    current_answer='HERMES_'+current_kind.upper()+'_PROPOSAL\n'+json.dumps(current_proposal,ensure_ascii=False)+'\nEND_HERMES_'+current_kind.upper()+'_PROPOSAL'
                    (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer}))
                    (current_job_path/'status.json').write_text('{"status":"running"}')
                    with self.assertRaises(ValueError):current_manager.execute_hermes_command(current_command,current_payload)
                    (current_job_path/'status.json').write_text('{"status":"completed"}')
                    self.assertEqual(current_manager.execute_hermes_command(current_command,current_payload),{'job_id':current_job_identifier,'proposal':current_proposal})
                    (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer+'x'*8001}))
                    with self.assertRaises(ValueError):current_manager.execute_hermes_command(current_command,current_payload)

    def test_field_proposal_rejects_unsafe_and_requires_completed_job(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_field_proposal
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_proposal_value={'map':'moss-clearing','revision':'a'*64,'cells':[{'column':1,'row':2,'tile':'m','height':0,'blocked':False}]}
        current_answer_value='제안입니다.\nHERMES_FIELD_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_FIELD_PROPOSAL'
        self.assertEqual(parse_hermes_field_proposal(current_answer_value),current_proposal_value)
        self.assertEqual(parse_hermes_field_proposal(current_answer_value+'\n\n저장 전 검토가 필요합니다.'),current_proposal_value)
        with self.assertRaises(ValueError):
            parse_hermes_field_proposal(current_answer_value+'\n'+current_answer_value)
        for current_bad_value in ({**current_proposal_value,'cells':current_proposal_value['cells']*2},{**current_proposal_value,'cells':[{**current_proposal_value['cells'][0],'column':True}]},{**current_proposal_value,'cells':[]},{**current_proposal_value,'objects':[]}):
            with self.assertRaises(ValueError):
                parse_hermes_field_proposal('HERMES_FIELD_PROPOSAL\n'+json.dumps(current_bad_value)+'\nEND_HERMES_FIELD_PROPOSAL')
        with tempfile.TemporaryDirectory() as current_root_name:
            current_service_value=HermesServiceManager(Path(current_root_name))
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=Path(current_root_name)/current_job_identifier
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"running"}')
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-field-proposal',{'id':current_job_identifier})
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-field-proposal',{'id':current_job_identifier})['proposal'],current_proposal_value)
            (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer_value+'x'*8001}))
            with self.assertRaises(ValueError):
                current_service_value.execute_hermes_command('hermes-field-proposal',{'id':current_job_identifier})

    def test_service_proposal_requires_completed_untruncated_job(self):
        import json
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_service_value = HermesServiceManager(Path(current_temp_root))
            current_job_identifier = '2026-11-18_00-00-00-12345678'
            current_job_path = Path(current_temp_root) / current_job_identifier
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text('{}')
            (current_job_path / 'status.json').write_text('{"status":"running"}')
            current_final_answer = 'HERMES_KIMODO_PROPOSAL\n{"prompt":"walk forward","frames":90,"steps":100,"seed":42}\nEND_HERMES_KIMODO_PROPOSAL'
            (current_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':current_final_answer}))
            with self.assertRaisesRegex(ValueError, '완료된'):
                current_service_value.execute_hermes_command('hermes-kimodo-proposal', {'id':current_job_identifier})
            (current_job_path / 'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-kimodo-proposal', {'id':current_job_identifier})['proposal']['seed'], 42)
            (current_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':current_final_answer + 'x' * 8001}))
            with self.assertRaisesRegex(ValueError, '잘려'):
                current_service_value.execute_hermes_command('hermes-kimodo-proposal', {'id':current_job_identifier})

    def test_receipt_history_includes_unknown_and_hides_input_hash(self):
        import json
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_store_value.execute_delegation_once('request_123456', {'prompt':'private text'}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_delegation_once('request_654321', {}, Mock(side_effect=TimeoutError()))
            (Path(current_temp_root) / 'corrupt_123456.json').write_text('not json')
            (Path(current_temp_root) / 'effect_123456.json').write_text(json.dumps({'version':10,'id':'effect_123456','state':'completed','effect':{'id':'test-effect'}}))
            (Path(current_temp_root) / 'reserve_123456.json').write_text(json.dumps({'version':13,'id':'reserve_123456','state':'dispatching'}))
            (Path(current_temp_root) / 'keyframe_123456.json').write_text(json.dumps({'version':14,'id':'keyframe_123456','state':'dispatching'}))
            (Path(current_temp_root) / 'linked_123456.json').symlink_to(Path(current_temp_root) / 'request_123456.json')
            current_result_value = current_store_value.list_delegation_receipts()
            current_records_by_id = {current_record['request_id']: current_record for current_record in current_result_value['records']}
            self.assertEqual(current_records_by_id['request_123456']['state'], 'accepted')
            self.assertEqual(current_records_by_id['request_654321']['state'], 'unknown')
            self.assertEqual(current_records_by_id['corrupt_123456']['state'], 'unavailable')
            self.assertNotIn('linked_123456', current_records_by_id)
            self.assertNotIn('effect_123456', current_records_by_id)
            self.assertNotIn('reserve_123456', current_records_by_id)
            self.assertNotIn('keyframe_123456', current_records_by_id)
            self.assertNotIn('private text', json.dumps(current_result_value))
            self.assertNotIn('request_sha256', json.dumps(current_result_value))

    def test_job_status_only_queries_accepted_receipt(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = CurrentStore(Path(current_temp_root) / 'delegations')
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore', return_value=current_store_value), patch('workflow.common.management_gateway.execute_management_command', return_value={'status':'completed'}) as current_gateway_mock:
                self.assertEqual(current_service_value.execute_hermes_command('hermes-delegation-job-status', {'request_id':'request_123456'})['receipt']['state'], 'not_found')
                current_gateway_mock.assert_not_called()
                current_store_value.execute_delegation_once('request_123456', {}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
                current_result_value = current_service_value.execute_hermes_command('hermes-delegation-job-status', {'request_id':'request_123456'})
                self.assertEqual(current_result_value['job']['status'], 'completed')
                self.assertEqual((current_result_value['receipt']['request_id'],current_result_value['receipt']['service']),('request_123456','kimodo'))
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('kimodo', 'status', {'id':'2026-11-18_00-00-00-12345678'}))
                current_gateway_mock.return_value={'id':'2026-11-18_00-00-00-ffffffff','status':'completed'}
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-job-status', {'request_id':'request_123456'})
                current_gateway_mock.return_value={'id':'2026-11-18_00-00-00-12345678','status':'completed'}
                self.assertEqual(current_service_value.execute_hermes_command('hermes-delegation-job-status', {'request_id':'request_123456'})['job']['id'],'2026-11-18_00-00-00-12345678')

    def test_separate_processes_reuse_receipt_and_crash_remains_unknown(self):
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_child_source = """import json, pathlib, sys, time
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
root=pathlib.Path(sys.argv[1])
def submit(record):
 with (root/'calls').open('a') as stream: stream.write('called\\n')
 time.sleep(.15)
 return {'id':'2026-11-18_00-00-00-12345678'}
print(json.dumps(HermesDelegationStore(root/'records').execute_delegation_once('request_123456', {'service':'kimodo'}, submit)))
"""
            current_children = [subprocess.Popen([sys.executable, '-c', current_child_source, current_temp_root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
            current_results = []
            for current_child_process in current_children:
                current_stdout_text, current_stderr_text = current_child_process.communicate(timeout=15)
                self.assertEqual(current_child_process.returncode, 0, current_stderr_text)
                current_results.append(json.loads(current_stdout_text))
            self.assertEqual(sum(not current_result_value['duplicate'] for current_result_value in current_results), 1)
            self.assertEqual((Path(current_temp_root) / 'calls').read_text().count('called'), 1)
            current_crash_source = """import os,sys
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
HermesDelegationStore(sys.argv[1]).execute_delegation_once('crash_request_123', {}, lambda request: os._exit(37))
"""
            current_crash_process = subprocess.run([sys.executable, '-c', current_crash_source, str(Path(current_temp_root) / 'records')], timeout=15)
            self.assertEqual(current_crash_process.returncode, 37)
            self.assertEqual(HermesDelegationStore(Path(current_temp_root) / 'records').read_delegation_status('crash_request_123')['state'], 'unknown')

    def test_cancel_requires_matching_accepted_delegation(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = CurrentStore(Path(current_temp_root) / 'delegations')
            current_store_value.execute_delegation_once('request_123456', {}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore', return_value=current_store_value), patch('workflow.common.management_gateway.execute_management_command', return_value={'status':'running','cancel_requested':True}) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'2026-11-18_00-00-01-12345678'})
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_654321', 'job_id':'2026-11-18_00-00-00-12345678'})
                current_gateway_mock.assert_not_called()
                current_gateway_mock.return_value={'status':'running','cancel_requested':True,'id':'2026-11-18_00-00-01-12345678'}
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'2026-11-18_00-00-00-12345678'})
                current_gateway_mock.reset_mock()
                current_gateway_mock.return_value={'status':'running','cancel_requested':True}
                current_cancel_result = current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'2026-11-18_00-00-00-12345678'})
                self.assertTrue(current_cancel_result['cancel_requested'])
                self.assertEqual(current_cancel_result['status'], 'running')
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('kimodo', 'cancel', {'id':'2026-11-18_00-00-00-12345678'}))

    def test_receipt_lookup_does_not_submit_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            self.assertEqual(current_store_value.read_delegation_status('request_123456')['state'], 'not_found')
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            current_store_value.execute_delegation_once('request_123456', {'service':'kimodo'}, current_submit_mock)
            self.assertEqual(HermesDelegationStore(current_temp_root).read_delegation_status('request_123456'), {'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'})
            self.assertEqual(current_submit_mock.call_count, 1)
            current_failed_submit = Mock(side_effect=TimeoutError('lost'))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_delegation_once('request_654321', {}, current_failed_submit)
            self.assertEqual(current_store_value.read_delegation_status('request_654321')['state'], 'unknown')
            self.assertEqual(current_failed_submit.call_count, 1)
            with self.assertRaises(ValueError):
                current_store_value.read_delegation_status('../outside')

    def test_versioned_receipts_keep_services_and_legacy_separate(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_job_id = '2026-11-18_00-00-00-12345678'
            self.assertEqual(current_store_value.read_service_delegation('missing_request_1','flux-image'),{'state':'not_found','request_id':'missing_request_1','service':'flux-image'})
            current_submit_mock = Mock(return_value={'id':current_job_id})
            current_validate_mock = Mock()
            current_store_value.execute_delegation_once('legacy_request_1', {'service':'kimodo'}, current_submit_mock)
            current_result = current_store_value.execute_service_delegation_once('future_request_1', 'flux-image', {'prompt':'x'}, current_submit_mock, current_validate_mock)
            self.assertEqual(current_result['service'], 'flux-image')
            self.assertEqual(current_store_value.read_service_delegation('future_request_1', 'flux-image')['job_id'], current_job_id)
            self.assertEqual(current_store_value.read_service_delegation('future_request_1', 'flux-image')['request_id'],'future_request_1')
            with self.assertRaises(ValueError):
                current_store_value.read_service_delegation('future_request_1', 'kimodo')
            with self.assertRaises(ValueError):
                current_store_value.read_delegation_status('future_request_1')
            with self.assertRaises(ValueError):
                current_store_value.read_service_delegation('legacy_request_1', 'flux-image')
            with self.assertRaises(ValueError):
                current_store_value.execute_service_delegation_once('legacy_request_1', 'flux-image', {'prompt':'x'}, current_submit_mock, current_validate_mock)
            with self.assertRaises(ValueError):
                current_store_value.execute_service_delegation_once('future_request_1', 'kimodo', {'prompt':'x'}, current_submit_mock, current_validate_mock)
            self.assertEqual([item['request_id'] for item in current_store_value.list_delegation_receipts()['records']], ['legacy_request_1'])
            self.assertEqual(current_submit_mock.call_count, 2)

    def test_versioned_receipts_are_idempotent_under_race_and_lost_reply(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            current_validate_mock = Mock()
            def submit_current_request(current_unused_value):
                return current_store_value.execute_service_delegation_once('same_request_123', 'flux-image', {'prompt':'x'}, current_submit_mock, current_validate_mock)
            with ThreadPoolExecutor(max_workers=6) as current_thread_pool:
                current_results = list(current_thread_pool.map(submit_current_request, range(6)))
            self.assertEqual(current_submit_mock.call_count, 1)
            self.assertEqual(current_validate_mock.call_count, 1)
            self.assertEqual(sum(not current_result['duplicate'] for current_result in current_results), 1)
            with self.assertRaises(ValueError):
                current_store_value.execute_service_delegation_once('same_request_123', 'flux-image', {'prompt':'y'}, current_submit_mock, current_validate_mock)
            current_failed_mock = Mock(side_effect=TimeoutError('lost'))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_service_delegation_once('lost_request_123', 'flux-image', {}, current_failed_mock, current_validate_mock)
            self.assertEqual(current_store_value.read_service_delegation('lost_request_123', 'flux-image')['state'], 'unknown')
            self.assertEqual(current_store_value.read_service_delegation('lost_request_123', 'flux-image')['request_id'],'lost_request_123')
            self.assertEqual(current_store_value.execute_service_delegation_once('lost_request_123', 'flux-image', {}, current_failed_mock, current_validate_mock)['state'], 'unknown')
            current_failed_mock.assert_called_once()

    def test_changed_receipt_is_not_overwritten_after_service_accepts(self):
        import json
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value=HermesDelegationStore(current_temp_root)
            for current_version_name in ('legacy','service'):
                with self.subTest(version=current_version_name):
                    current_identifier_value=current_version_name+'_changed_123'
                    current_record_path=current_store_value.resolve_delegation_record_path(current_identifier_value)
                    def current_submit_value(current_request_value):
                        current_changed_record=json.loads(current_record_path.read_text())
                        current_changed_record['external_change']='preserve'
                        current_record_path.write_text(json.dumps(current_changed_record))
                        return {'id':'2026-11-18_00-00-00-12345678'}
                    current_submit_mock=Mock(side_effect=current_submit_value)
                    with self.assertRaisesRegex(ValueError,'기록이 변경'):
                        if current_version_name=='legacy':current_store_value.execute_delegation_once(current_identifier_value,{},current_submit_mock)
                        else:current_store_value.execute_service_delegation_once(current_identifier_value,'flux-image',{},current_submit_mock,lambda current_value:None)
                    current_changed_record=json.loads(current_record_path.read_text())
                    self.assertEqual(current_changed_record['state'],'dispatching')
                    self.assertEqual(current_changed_record['external_change'],'preserve')
                    if current_version_name=='legacy':current_retry_value=current_store_value.execute_delegation_once(current_identifier_value,{},current_submit_mock)
                    else:current_retry_value=current_store_value.execute_service_delegation_once(current_identifier_value,'flux-image',{},current_submit_mock,lambda current_value:None)
                    self.assertEqual(current_retry_value['state'],'unknown')
                    self.assertTrue(current_retry_value['duplicate'])
                    current_submit_mock.assert_called_once()

    def test_versioned_history_excludes_other_services_and_input(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            current_store_value.execute_delegation_once('legacy_request_1', {'prompt':'legacy-secret'}, current_submit_mock)
            current_store_value.execute_service_delegation_once('flux_request_123', 'flux-image', {'prompt':'secret'}, current_submit_mock, Mock())
            current_store_value.execute_service_delegation_once('other_request_123', 'other-service', {'prompt':'secret'}, current_submit_mock, Mock())
            current_records = current_store_value.list_service_delegations('flux-image')['records']
            self.assertEqual([item['request_id'] for item in current_records], ['flux_request_123'])
            self.assertNotIn('secret', str(current_records))
            self.assertNotIn('sha256', str(current_records))

    def test_versioned_receipt_validation_and_malformed_reply(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'invalid'})
            current_validator_mock = Mock(side_effect=ValueError('bad input'))
            with self.assertRaises(ValueError):
                current_store_value.execute_service_delegation_once('valid_request_1', 'flux-image', {}, current_submit_mock, current_validator_mock)
            self.assertFalse((Path(current_temp_root) / 'valid_request_1.json').exists())
            current_submit_mock.assert_not_called()
            with self.assertRaises(ValueError):
                current_store_value.execute_service_delegation_once('valid_request_1', 'flux-image', {}, current_submit_mock, Mock())
            self.assertEqual(current_store_value.read_service_delegation('valid_request_1', 'flux-image')['state'], 'unknown')
            self.assertEqual(current_store_value.execute_service_delegation_once('valid_request_1', 'flux-image', {}, current_submit_mock, Mock())['state'], 'unknown')
            current_submit_mock.assert_called_once()

    def test_versioned_receipt_is_unique_across_processes(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_child_source = """import pathlib, sys, time
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
root=pathlib.Path(sys.argv[1])
def submit(record):
 with (root/'calls').open('a') as stream: stream.write('called\\n')
 time.sleep(.15)
 return {'id':'2026-11-18_00-00-00-12345678'}
HermesDelegationStore(root/'records').execute_service_delegation_once('same_request_123', 'flux-image', {'prompt':'x'}, submit, lambda request: None)
"""
            current_children = [subprocess.Popen([sys.executable, '-c', current_child_source, current_temp_root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
            for current_child_process in current_children:
                current_stdout_text, current_stderr_text = current_child_process.communicate(timeout=15)
                self.assertEqual(current_child_process.returncode, 0, current_stderr_text)
            self.assertEqual((Path(current_temp_root) / 'calls').read_text().count('called'), 1)

    def test_parallel_retries_use_one_submission_and_same_job(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            def submit_same_request(current_unused_value):
                return HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo', 'prompt':'걷기'}, current_submit_mock)
            with ThreadPoolExecutor(max_workers=6) as current_thread_pool:
                current_results = list(current_thread_pool.map(submit_same_request, range(6)))
            self.assertEqual(current_submit_mock.call_count, 1)
            self.assertEqual(sum(not current_result['duplicate'] for current_result in current_results), 1)
            self.assertEqual({current_result['job_id'] for current_result in current_results}, {'2026-11-18_00-00-00-12345678'})
            with self.assertRaisesRegex(ValueError, '다른 입력'):
                HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo', 'prompt':'달리기'}, current_submit_mock)

    def test_lost_response_is_never_submitted_again_after_reopen(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_submit_mock = Mock(side_effect=TimeoutError('응답 유실'))
            with self.assertRaises(TimeoutError):
                HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo'}, current_submit_mock)
            current_recovery_result = HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo'}, current_submit_mock)
            self.assertEqual(current_recovery_result['state'], 'unknown')
            self.assertEqual(current_submit_mock.call_count, 1)
            self.assertNotIn('kimodo', (Path(current_temp_root) / 'request_123456.json').read_text())

    def test_validation_failure_precedes_dispatch_record_and_retry_skips_validation(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            current_validate_mock = Mock(side_effect=ValueError('invalid'))
            with self.assertRaises(ValueError):
                current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock, current_validate_mock)
            self.assertFalse((Path(current_temp_root) / 'request_123456.json').exists())
            current_submit_mock.assert_not_called()
            current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock)
            self.assertEqual(current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock, current_validate_mock)['state'], 'accepted')
            self.assertEqual(current_validate_mock.call_count, 1)

    def test_flux_delegation_validates_dispatches_and_confines_job_target(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = CurrentStore(Path(current_temp_root) / 'delegations')
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            current_job_id = '2026-11-18_00-00-00-12345678'
            current_request_record = {'action':'generate', 'prompt':'blue sky', 'images':[], 'width':512, 'height':512, 'steps':16, 'seed':42}
            current_payload_record = {'request_id':'flux_request_123', 'request':current_request_record}
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore', return_value=current_store_value), patch('workflow.common.management_gateway.execute_management_command', return_value={'id':current_job_id}) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegate-flux-image', {'request_id':'invalid_req_123', 'request':{**current_request_record, 'steps':999}})
                current_gateway_mock.assert_not_called()
                self.assertFalse((Path(current_temp_root) / 'delegations' / 'invalid_req_123.json').exists())
                current_result = current_service_value.execute_hermes_command('hermes-delegate-flux-image', current_payload_record)
                self.assertEqual(current_result['job_id'], current_job_id)
                self.assertTrue(current_service_value.execute_hermes_command('hermes-delegate-flux-image', current_payload_record)['duplicate'])
                current_gateway_mock.assert_called_once()
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('flux-image', 'generate', current_request_record))
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'flux_request_123','job_id':current_job_id})
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-flux-delegation-cancel', {'request_id':'flux_request_123','job_id':'2026-11-18_00-00-01-12345678'})
                current_gateway_mock.assert_called_once()
                current_gateway_mock.return_value = {'status':'running', 'cancel_requested':True,'id':'2026-11-18_00-00-01-12345678'}
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-flux-delegation-cancel', {'request_id':'flux_request_123','job_id':current_job_id})
                current_gateway_mock.return_value = {'status':'running', 'cancel_requested':True}
                self.assertTrue(current_service_value.execute_hermes_command('hermes-flux-delegation-cancel', {'request_id':'flux_request_123','job_id':current_job_id})['cancel_requested'])
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('flux-image','cancel', {'id':current_job_id}))
                current_gateway_mock.return_value = {'status':'cancelled'}
                self.assertEqual(current_service_value.execute_hermes_command('hermes-flux-delegation-status', {'request_id':'flux_request_123'})['job']['status'], 'cancelled')
                current_image_path='/flux-image-generator/jobs/'+current_job_id+'/result.png'
                current_gateway_mock.return_value={'status':'completed','image':current_image_path,'legacy_field':'preserved'}
                current_status_value=current_service_value.execute_hermes_command('hermes-flux-delegation-status', {'request_id':'flux_request_123'})
                self.assertEqual(current_status_value['job'],current_gateway_mock.return_value)
                self.assertEqual(current_status_value['result'],{'image':current_image_path,'status':'available'})
                current_gateway_mock.return_value={'status':'completed','image':'https://example.com/result.png'}
                self.assertEqual(current_service_value.execute_hermes_command('hermes-flux-delegation-status', {'request_id':'flux_request_123'})['result'],{'image':None,'status':'unavailable'})
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('flux-image','status', {'id':current_job_id}))

    def test_service_dispatches_to_registered_kimodo_command_once(self):
        from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        current_request_value = {current_key: current_value for current_key, current_value in KIMODO_DEFAULT_SETTINGS.items() if current_key != 'schema_version'}
        current_request_value['action'] = 'generate'
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore', side_effect=lambda: CurrentStore(Path(current_temp_root) / 'delegations')), patch('workflow.common.management_gateway.execute_management_command', return_value={'id':'2026-11-18_00-00-00-12345678'}) as current_gateway_mock:
                current_payload_value = {'request_id':'request_123456', 'request':current_request_value}
                self.assertFalse(current_service_value.execute_hermes_command('hermes-delegate-kimodo', current_payload_value)['duplicate'])
                self.assertTrue(current_service_value.execute_hermes_command('hermes-delegate-kimodo', current_payload_value)['duplicate'])
                self.assertEqual(current_gateway_mock.call_count, 1)
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('kimodo', 'generate', current_request_value))

    def test_invalid_identifier_and_bad_response_do_not_allow_relaunch(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'../outside'})
            with self.assertRaises(ValueError):
                current_store_value.execute_delegation_once('../outside', {}, current_submit_mock)
            current_submit_mock.assert_not_called()
            with self.assertRaises(ValueError):
                current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock)
            self.assertEqual(current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock)['state'], 'unknown')
            self.assertEqual(current_submit_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
