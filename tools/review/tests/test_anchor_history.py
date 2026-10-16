"""좌표 누적 저장·재조회·잘못된 좌표 거절 검증."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.character_animation import anchor_history
from tools.review.common.management_gateway import execute_management_command

class AnchorHistoryTests(unittest.TestCase):
    def test_reset_validates_all_records_before_hiding_any(self):
        current_scope_payload = {'animation_id': 'test.idle', 'animation_version': '1'}
        with tempfile.TemporaryDirectory() as current_workspace_directory, patch.object(anchor_history, 'ANCHOR_HISTORY_ROOT', Path(current_workspace_directory)):
            current_result_paths = []
            for current_identifier_suffix in ('11111111', '22222222'):
                current_history_identifier = '2026-01-02_03-04-05-' + current_identifier_suffix
                current_history_path = anchor_history.resolve_anchor_history_directory(current_history_identifier)
                current_history_path.mkdir(parents=True)
                current_result_path = current_history_path / 'result.json'
                current_result_path.write_text(json.dumps({'id': current_history_identifier, 'source': {'animationId': 'test.idle', 'animationVersion': '1'}}))
                current_result_paths.append(current_result_path)
            current_invalid_record = json.loads(current_result_paths[1].read_text())
            current_invalid_record['id'] = '2026-01-02_03-04-05-33333333'
            current_result_paths[1].write_text(json.dumps(current_invalid_record))
            current_original_bytes = {current_result_path: current_result_path.read_bytes() for current_result_path in current_result_paths}
            with self.assertRaisesRegex(ValueError, '기록 ID'):
                execute_management_command('character-animation', 'anchor-history-reset', current_scope_payload)
            for current_result_path in current_result_paths:
                self.assertEqual(current_result_path.read_bytes(), current_original_bytes[current_result_path])
                self.assertFalse((current_result_path.parent / 'history-hidden.json').exists())

    def test_history_rejects_external_links_before_read_or_reset(self):
        current_history_identifier = '2026-01-02_03-04-05-1234abcd'
        current_scope_payload = {'animation_id': 'test.idle', 'animation_version': '1'}
        with tempfile.TemporaryDirectory() as current_workspace_directory, tempfile.TemporaryDirectory() as current_external_directory, patch.object(anchor_history, 'ANCHOR_HISTORY_ROOT', Path(current_workspace_directory)):
            current_external_path = Path(current_external_directory)
            current_record_path = current_external_path / 'result.json'
            current_record_path.write_text(json.dumps({'id': current_history_identifier, 'source': {'animationId': 'test.idle', 'animationVersion': '1'}}))
            current_history_path = Path(current_workspace_directory) / current_history_identifier[:19] / current_history_identifier
            current_history_path.parent.mkdir()
            current_history_path.symlink_to(current_external_path, target_is_directory=True)
            for current_command_name, current_payload_record in (
                ('anchor-history', current_scope_payload), ('anchor-history-reset', current_scope_payload),
                ('anchor-load', {'id': current_history_identifier})):
                with self.subTest(command=current_command_name), self.assertRaisesRegex(ValueError, '경로 오류'):
                    anchor_history.execute_anchor_history_command(current_command_name, current_payload_record)
            self.assertEqual(list(current_external_path.iterdir()), [current_record_path])
            current_history_path.unlink()
            current_history_path.mkdir()
            (current_history_path / 'result.json').symlink_to(current_record_path)
            with self.assertRaisesRegex(ValueError, '내부 심볼릭 링크'):
                anchor_history.execute_anchor_history_command('anchor-history-reset', current_scope_payload)
            self.assertFalse((current_external_path / 'history-hidden.json').exists())

    def test_persistent_versions_and_validation(self):
        document_record_value={'schemaVersion':1,'artifactType':'character-animation-anchor-review','description':'검수','coordinateMode':'anchor','source':{'animationId':'test.idle','animationVersion':'1','sheets':[{'image':'sheet.png','sha256':'a'*64}]},'frames':[{'frameId':'down_left.0','direction':'down_left','image':'sheet.png','rect':{'x':0,'y':0,'width':100,'height':100},'points':[{'x':50.25,'y':90}],'anchor':{'x':50.25,'y':90}}]}
        with tempfile.TemporaryDirectory() as temporary_directory_value,patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',Path(temporary_directory_value)):
            first_record_value=execute_management_command('character-animation','anchor-save',{'document':document_record_value})
            second_record_value=execute_management_command('character-animation','anchor-save',{'document':document_record_value})
            self.assertNotEqual(first_record_value['id'],second_record_value['id'])
            history_record_value=execute_management_command('character-animation','anchor-history',{'animation_id':'test.idle','animation_version':'1'})
            self.assertEqual(len(history_record_value['items']),2)
            self.assertEqual(execute_management_command('character-animation','anchor-load',{'id':first_record_value['id']})['document'],document_record_value)
            for invalid_coordinate_value in [float('nan'),-1,100,True]:
                invalid_document_value=copy.deepcopy(document_record_value);invalid_document_value['frames'][0]['anchor']['x']=invalid_coordinate_value
                with self.assertRaises(ValueError):execute_management_command('character-animation','anchor-save',{'document':invalid_document_value})
            for invalid_version_value in (True, 1.0, '1', None):
                invalid_document_value=copy.deepcopy(document_record_value)
                invalid_document_value['schemaVersion']=invalid_version_value
                with self.subTest(schema_version=invalid_version_value):
                    with self.assertRaisesRegex(ValueError,'버전'):
                        execute_management_command('character-animation','anchor-save',{'document':invalid_document_value})
            for invalid_hash_value in (None, 42, [], {}):
                invalid_document_value=copy.deepcopy(document_record_value)
                invalid_document_value['source']['sheets'][0]['sha256']=invalid_hash_value
                with self.subTest(sheet_hash=invalid_hash_value):
                    with self.assertRaisesRegex(ValueError,'시트 해시 오류'):
                        execute_management_command('character-animation','anchor-save',{'document':invalid_document_value})
            for invalid_sheet_value in (
                {'image':'sheet.png','sha256':'a'*64,'unexpected':True},
                {'image':'sheet.png','sha256':'a'*64,'direction':'side'},
                {'image':' ','sha256':'a'*64},
            ):
                invalid_document_value=copy.deepcopy(document_record_value)
                invalid_document_value['source']['sheets']=[invalid_sheet_value]
                with self.subTest(sheet=invalid_sheet_value):
                    with self.assertRaises(ValueError):
                        execute_management_command('character-animation','anchor-save',{'document':invalid_document_value})
            for invalid_identifier_value in ('', ' '):
                invalid_document_value=copy.deepcopy(document_record_value)
                invalid_document_value['frames'][0]['frameId']=invalid_identifier_value
                with self.assertRaisesRegex(ValueError,'프레임 ID 오류'):
                    execute_management_command('character-animation','anchor-save',{'document':invalid_document_value})
            directional_document_value=copy.deepcopy(document_record_value)
            directional_document_value['source']['sheets'][0]['direction']='down_left'
            self.assertEqual(anchor_history.validate_anchor_document(directional_document_value),directional_document_value)
            with self.assertRaises(ValueError):execute_management_command('character-animation','anchor-load',{'id':'../outside'})
            self.assertEqual(len(list(Path(temporary_directory_value).glob('*/*/result.json'))),2)

            reset_scope_value={'animation_id':'test.idle','animation_version':'1'}
            self.assertEqual(execute_management_command('character-animation','anchor-history-reset',reset_scope_value)['cleared'],2)
            self.assertEqual(execute_management_command('character-animation','anchor-history',reset_scope_value)['items'],[])
            self.assertEqual(execute_management_command('character-animation','anchor-load',{'id':first_record_value['id']})['document'],document_record_value)
            execute_management_command('character-animation','anchor-save',{'document':document_record_value})
            self.assertEqual(len(execute_management_command('character-animation','anchor-history',reset_scope_value)['items']),1)
