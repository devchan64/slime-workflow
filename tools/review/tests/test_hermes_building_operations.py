"""건물 앵커 위임의 검토·충돌·응답 유실을 검사한다."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import building_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesBuildingOperationsTests(unittest.TestCase):
    def test_review_save_duplicate_and_response_loss(self):
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog_value={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft_value['expected'],'maps':[{'map':'test-city'}],'image':'/private'}]}
        with TemporaryDirectory() as current_directory_name, patch.object(building_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory_name))), patch.object(building_operations,'call_field_map_editor') as current_gateway_mock:
            current_gateway_mock.side_effect=lambda current_command_name,current_payload_value: current_catalog_value if current_command_name=='building-list' else {'saved':True}
            current_preview_value=building_operations.preview_hermes_building_anchor(current_draft_value)
            self.assertEqual(current_preview_value['maps'],['test-city'])
            self.assertNotIn('/private',str(current_preview_value))
            current_saved_value=building_operations.save_hermes_building_anchor('building_123',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(current_saved_value['state'],'completed')
            self.assertTrue(building_operations.save_hermes_building_anchor('building_123',current_draft_value,current_preview_value['review_sha256'])['duplicate'])
            self.assertEqual(sum(current_call.args[0]=='building-save' for current_call in current_gateway_mock.call_args_list),1)
            current_gateway_mock.side_effect=lambda current_command_name,current_payload_value: current_catalog_value if current_command_name=='building-list' else (_ for _ in ()).throw(OSError('lost'))
            with self.assertRaises(OSError):building_operations.save_hermes_building_anchor('building_456',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(building_operations.read_hermes_building_receipt('building_456')['state'],'unknown')
            self.assertEqual(building_operations.save_hermes_building_anchor('building_456',current_draft_value,current_preview_value['review_sha256'])['state'],'unknown')

    def test_changed_state_or_non_anchor_change_is_rejected(self):
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1,'displayWidthAdjustment':0,'displayHeightAdjustment':0},'properties':{'anchorX':0.6,'anchorY':1,'displayWidthAdjustment':0,'displayHeightAdjustment':0}}
        with patch.object(building_operations,'call_field_map_editor',return_value={'generation':4,'assets':[]}):
            with self.assertRaisesRegex(ValueError,'세대'):building_operations.preview_hermes_building_anchor(current_draft_value)
        current_draft_value['properties']['displayWidthAdjustment']=1
        with self.assertRaisesRegex(ValueError,'앵커'):building_operations.inspect_hermes_building_draft(current_draft_value)
