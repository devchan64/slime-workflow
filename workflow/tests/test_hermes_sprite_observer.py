"""등록 스프라이트 관측의 경로·해시·페이징 검사."""
import base64
import unittest
from unittest.mock import patch
from workflow.domains.hermes_agent import sprite_observer


class HermesSpriteObserverTests(unittest.TestCase):
    @patch.object(sprite_observer,'call_hermes_sprite_editor')
    def test_catalog_validates_paths_hashes_and_pagination(self,current_editor_mock):
        current_editor_mock.return_value={'items':[{'path':'assets/characters/default/animations/rest/a.png','label':'기본 휴식','sha256':'a'*64,'animationIds':['character.rest']}]}
        current_result_record=sprite_observer.read_hermes_sprite_catalog({'query':'휴식','limit':1})
        self.assertEqual(current_result_record['items'][0]['animation_ids'],['character.rest'])
        current_editor_mock.assert_called_once_with('sheet-search',{'query':'휴식','source':'assets'})
        for current_bad_request in ({'source':'baseline'},{'offset':True},{'limit':31}):
            with self.subTest(request=current_bad_request),self.assertRaises(ValueError):sprite_observer.read_hermes_sprite_catalog(current_bad_request)
        current_editor_mock.return_value={'items':[{'path':'assets/../secret.png','label':'test','sha256':'a'*64}]}
        with self.assertRaises(ValueError):sprite_observer.read_hermes_sprite_catalog({})

    @patch.object(sprite_observer,'call_hermes_sprite_editor')
    def test_detail_excludes_image_and_pages_frames(self,current_editor_mock):
        current_asset_path='assets/characters/default/animations/rest/a.png'
        current_frames_value=[{'frameId':'f'+str(current_frame_index),'rect':{'x':current_frame_index,'y':0,'width':10,'height':10},'anchor':{'x':5.0,'y':9}} for current_frame_index in range(3)]
        current_editor_mock.return_value={'path':current_asset_path,'image':base64.b64encode(b'test-image').decode(),'metadataSha256':'b'*64,'animation':{'animationId':'character.rest','version':'v1','frames':current_frames_value,'private':'secret'}}
        current_first_record=sprite_observer.read_hermes_sprite_sheet({'path':current_asset_path,'limit':1})
        current_result_record=sprite_observer.read_hermes_sprite_sheet({'path':current_asset_path,'offset':1,'limit':1,'snapshot':current_first_record['snapshot']})
        self.assertEqual(current_result_record['frames'][0]['id'],'f1')
        self.assertEqual(current_result_record['next_offset'],2)
        self.assertEqual(current_result_record['animation']['frame_count'],3)
        self.assertNotIn('secret',str(current_result_record))
        self.assertNotIn('image',current_result_record)
        with self.assertRaises(ValueError):sprite_observer.read_hermes_sprite_sheet({'path':current_asset_path,'offset':1})
        current_editor_mock.return_value['metadataSha256']='c'*64
        with self.assertRaisesRegex(ValueError,'원본이 변경'):sprite_observer.read_hermes_sprite_sheet({'path':current_asset_path,'offset':1,'snapshot':current_first_record['snapshot']})
        with self.assertRaises(ValueError):sprite_observer.read_hermes_sprite_sheet({'path':'/tmp/x.png'})
