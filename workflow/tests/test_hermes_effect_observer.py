"""Hermes 이펙트 조회의 입력과 응답 경계 검증."""
import unittest
from unittest.mock import patch
from workflow.domains.hermes_agent import effect_observer


class HermesEffectObserverTests(unittest.TestCase):
    @patch.object(effect_observer,'call_hermes_effect_editor')
    def test_catalog_filters_pages_and_rejects_invalid_input(self,current_editor_mock):
        current_editor_mock.return_value={'effects':[{'id':'firefly-v1','name':'반딧불'},{'id':'fog-v1','name':'안개'}]}
        current_result_record=effect_observer.list_hermes_effect_catalog({'query':'반딧불','limit':1})
        self.assertEqual(current_result_record['items'],[{'id':'firefly-v1','name':'반딧불'}])
        self.assertIsNone(current_result_record['next_offset'])
        for current_bad_request in ({'command':'save'},{'limit':True},{'offset':-1},{'query':'a\nb'}):
            with self.subTest(request=current_bad_request),self.assertRaises(ValueError):effect_observer.list_hermes_effect_catalog(current_bad_request)

    @patch.object(effect_observer,'call_hermes_effect_editor')
    def test_detail_drops_images_paths_and_checks_alignment(self,current_editor_mock):
        current_alignment_record={'key':'safe-firefly','texture':'fireflies','alpha':0.5,'target':[0,0,1,1],'frames':[[0,0,1,1]]}
        current_editor_mock.return_value={'revision':'a'*64,'document':{'id':'firefly-v1','name':'반딧불','renderer':'swarm','rows':1,'columns':1,'frames':1,'alignment':current_alignment_record,'image':'/private/a.png'},'sheetImage':'data:secret','hostImage':'secret'}
        current_result_record=effect_observer.read_hermes_effect_detail('firefly-v1')
        self.assertEqual(current_result_record['alignment'],current_alignment_record)
        self.assertNotIn('secret',str(current_result_record))
        self.assertNotIn('/private',str(current_result_record))
        current_alignment_record['alpha']=float('nan')
        with self.assertRaises(ValueError):effect_observer.read_hermes_effect_detail('firefly-v1')
        with self.assertRaises(ValueError):effect_observer.read_hermes_effect_detail('../path')

    @patch.object(effect_observer,'call_hermes_effect_editor')
    def test_waypoint_without_alignment_is_explicit(self,current_editor_mock):
        current_editor_mock.return_value={'revision':'b'*64,'document':{'id':'waypoint-v4','name':'웨이포인트','renderer':'waypoint-animation','rows':2,'columns':4,'frames':8},'animationMetadata':{'private':'secret'}}
        current_result_record=effect_observer.read_hermes_effect_detail('waypoint-v4')
        self.assertIsNone(current_result_record['alignment'])
        self.assertNotIn('secret',str(current_result_record))
