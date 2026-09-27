"""좌표 누적 저장·재조회·잘못된 좌표 거절 검증."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.character_animation import anchor_history
from tools.review.common.management_gateway import execute_management_command

class AnchorHistoryTests(unittest.TestCase):
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
            with self.assertRaises(ValueError):execute_management_command('character-animation','anchor-load',{'id':'../outside'})
            self.assertEqual(len(list(Path(temporary_directory_value).glob('*/*/result.json'))),2)

            reset_scope_value={'animation_id':'test.idle','animation_version':'1'}
            self.assertEqual(execute_management_command('character-animation','anchor-history-reset',reset_scope_value)['cleared'],2)
            self.assertEqual(execute_management_command('character-animation','anchor-history',reset_scope_value)['items'],[])
            self.assertEqual(execute_management_command('character-animation','anchor-load',{'id':first_record_value['id']})['document'],document_record_value)
            execute_management_command('character-animation','anchor-save',{'document':document_record_value})
            self.assertEqual(len(execute_management_command('character-animation','anchor-history',reset_scope_value)['items']),1)
