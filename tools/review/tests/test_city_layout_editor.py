import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.map_assets import city_editor


class CityEditorTests(unittest.TestCase):
    def setUp(self):
        self.document = {'managementId':'config.city-layouts.stonewarm','data':{'version':1,'cityId':'stonewarm','columns':5,'rows':5,'safeTown':True,'terrainRows':['sspss']*5,'startPoint':{'column':2,'row':3},'buildings':[{'id':'stonewarm-guild','name':'길드','facilityId':'stonewarm-guild','origin':{'column':0,'row':1},'width':1,'height':1,'facing':'east','entrance':{'column':1,'row':1},'sprite':{'textureKey':'town-test-guild-v1','contentWidth':0.8}}],'objects':[],'connections':[{'column':2,'row':0,'direction':'north','id':'gate','target':'other'}]}}
        self.properties = {'town-test-guild-v1':{'anchorX':0.5,'anchorY':1.0}}
        self.bundle = {'generation':5,'revisions':{'city_layouts/stonewarm.yaml':2},'documents':{'city_layouts/stonewarm.yaml':copy.deepcopy(self.document),'sprite-display-properties.yaml':{'data':self.properties}}}
        self.payload = {'map':'stonewarm','generation':5,'revision':2,'document':copy.deepcopy(self.document)}
        self.temporary = tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        for current_patch in [patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch.object(city_editor,'CITY_EDITOR_STORAGE_ROOT',Path(self.temporary.name)),patch.object(city_editor,'execute_content_api_request',side_effect=self.mock_api)]:
            current_patch.start();self.addCleanup(current_patch.stop)
        self.saved=[]
    def mock_api(self,current_method,current_route,current_payload=None):
        if 'review-bundle' in current_route:return copy.deepcopy(self.bundle)
        if current_route.endswith('map-changes'):
            self.saved.append(current_payload);return {'saved':True}
        raise AssertionError('예상하지 못한 서비스 경로: '+current_route)
    def test_preview_and_save_use_same_document(self):
        self.payload['document']['data']['version']=2
        current_preview=city_editor.preview_city_editor_changes(self.payload)
        self.assertTrue(current_preview['changed'])
        self.assertTrue(city_editor.save_city_editor_changes({**self.payload,'token':current_preview['token']})['saved'])
        self.assertEqual(self.saved[0]['documents'][0]['document'],self.payload['document'])
        self.assertEqual(self.saved[0]['expectedGeneration'],5)
    def test_invalid_stale_and_changed_drafts_rejected(self):
        with self.assertRaisesRegex(ValueError,'변경되었습니다'):city_editor.preview_city_editor_changes({**self.payload,'revision':1})
        current_invalid=copy.deepcopy(self.payload);current_invalid['document']['data']['buildings'][0]['entrance']['column']=4
        with self.assertRaisesRegex(ValueError,'출입구'):city_editor.preview_city_editor_changes(current_invalid)
        current_preview=city_editor.preview_city_editor_changes(self.payload)
        with self.assertRaisesRegex(ValueError,'먼저 검증'):city_editor.save_city_editor_changes({**current_invalid,'token':current_preview['token']})
        self.assertFalse(self.saved)
    def test_change_after_preview_is_rejected(self):
        current_preview=city_editor.preview_city_editor_changes(self.payload)
        self.bundle['generation']+=1
        with self.assertRaisesRegex(ValueError,'변경되었습니다'):city_editor.save_city_editor_changes({**self.payload,'token':current_preview['token']})
        self.assertFalse(self.saved)

if __name__ == '__main__':unittest.main()
