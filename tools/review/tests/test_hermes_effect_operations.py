"""이펙트 편집의 입력·리비전·중복 및 불확실 응답을 검사한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.hermes_agent import effect_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesEffectOperationTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_root=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_root.cleanup)
        self.current_store_value=HermesDelegationStore(Path(self.current_temp_root.name))
        self.current_original_values={'key':'safe-firefly','texture':'fireflies','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]}
        self.current_detail_record={'id':'firefly-v1','revision':'a'*64,'alignment':self.current_original_values,'frames':1}
        self.current_draft_record={'id':'firefly-v1','revision':'a'*64,'target':[0,0,1,1],'alpha':0.7,'frames':[[0,0,1,1]]}
        self.current_preview_token=effect_operations.validate_hermes_effect_edit(self.current_draft_record)
        current_store_patch=patch.object(effect_operations,'HermesDelegationStore',return_value=self.current_store_value)
        current_store_patch.start();self.addCleanup(current_store_patch.stop)
        current_conflict_patch=patch.object(effect_operations,'check_hermes_effect_registration')
        current_conflict_patch.start();self.addCleanup(current_conflict_patch.stop)

    def test_preview_and_duplicate_save_preserve_connection(self):
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=self.current_detail_record), patch.object(effect_operations,'call_hermes_effect_editor',return_value={'saved':True,'revision':'b'*64}) as current_editor_mock:
            current_preview_record=effect_operations.preview_hermes_effect_edit(self.current_draft_record)
            self.assertEqual(current_preview_record['after']['texture'],'fireflies')
            current_save_args=('effect_request_123',self.current_draft_record,self.current_preview_token)
            self.assertTrue(effect_operations.save_hermes_effect_edit_once(*current_save_args)['saved'])
            self.assertTrue(effect_operations.save_hermes_effect_edit_once(*current_save_args)['duplicate'])
            self.assertEqual(current_editor_mock.call_count,1)
            current_payload_record=current_editor_mock.call_args.args[1]
            self.assertEqual(current_payload_record['expectedRevision'],'a'*64)
            self.assertEqual(current_payload_record['alignment']['key'],'safe-firefly')
            import uuid
            self.assertEqual(str(uuid.UUID(current_payload_record['requestId'])),current_payload_record['requestId'])
            self.assertEqual(self.current_store_value.list_delegation_receipts()['records'],[])

    def test_unknown_is_not_redispatched(self):
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=self.current_detail_record), patch.object(effect_operations,'call_hermes_effect_editor',side_effect=OSError('lost')) as current_editor_mock:
            current_save_args=('effect_request_123',self.current_draft_record,self.current_preview_token)
            with self.assertRaises(OSError):effect_operations.save_hermes_effect_edit_once(*current_save_args)
            self.assertEqual(effect_operations.read_hermes_effect_edit_receipt('effect_request_123')['state'],'unknown')
            self.assertEqual(effect_operations.save_hermes_effect_edit_once(*current_save_args)['state'],'unknown')
            self.assertEqual(current_editor_mock.call_count,1)

    def test_waypoint_replacement_review_duplicate_and_uncertain_response(self):
        current_effect_value={'id':'waypoint-v2','name':'새 웨이포인트','image':'assets/sprites/effects/new.png','animation':'assets/sprites/effects/new.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
        current_draft_value={'id':'waypoint-v1','revision':'a'*64,'effect':current_effect_value}
        current_old_value={'id':'waypoint-v1','name':'기존','renderer':'waypoint-animation','revision':'a'*64,'frames':6}
        import hashlib, json
        from PIL import Image
        current_image_path=Path(self.current_temp_root.name)/'source.png'
        current_animation_path=Path(self.current_temp_root.name)/'animation.json'
        Image.new('RGBA',(40,20)).save(current_image_path)
        current_animation_path.write_text(json.dumps({'sheet':{'width':40,'height':20},'frames':[{'rect':{'x':0,'y':0,'width':10,'height':10}}]*8}))
        def resolve_test_source(current_path_value,*current_arguments):
            current_source_path=current_image_path if current_path_value.endswith('.png') else current_animation_path
            return current_source_path,{'source':current_path_value,'sha256':hashlib.sha256(current_source_path.read_bytes()).hexdigest(),'version':'1','managementId':'test','repository':'slime-assets'}
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=current_old_value),patch('tools.review.common.map_tile_assets.load_registered_tiles',return_value=(Path('/unused'),{})),patch('tools.review.common.map_tile_assets.resolve_registered_asset',side_effect=resolve_test_source),patch.object(effect_operations,'call_hermes_effect_editor',return_value={'saved':True,'id':'waypoint-v2','replaced':'waypoint-v1','generation':4,'snapshot':'pending'}) as current_gateway_mock:
            current_preview_value=effect_operations.preview_hermes_waypoint_replacement(current_draft_value)
            self.assertEqual(current_preview_value['metadata_frames'],8)
            self.assertIn('게임 표시는 변경되지 않습니다',current_preview_value['note'])
            current_animation_path.write_text(json.dumps({'sheet':{'width':40,'height':20},'frames':[{'rect':{'x':39,'y':0,'width':10,'height':10}}]*8}))
            with self.assertRaisesRegex(ValueError,'이미지 범위'):
                effect_operations.preview_hermes_waypoint_replacement(current_draft_value)
            current_animation_path.write_text(json.dumps({'sheet':{'width':40,'height':20},'frames':[{'rect':{'x':0,'y':0,'width':10,'height':10}}]*7}))
            with self.assertRaisesRegex(ValueError,'프레임 수'):
                effect_operations.preview_hermes_waypoint_replacement(current_draft_value)
            current_animation_path.write_text(json.dumps({'sheet':{'width':40,'height':20},'frames':[{'rect':{'x':0,'y':0,'width':10,'height':10}}]*8}))
            current_save_args=('waypoint_request_1',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(effect_operations.replace_hermes_waypoint_once(*current_save_args)['state'],'completed')
            self.assertTrue(effect_operations.replace_hermes_waypoint_once(*current_save_args)['duplicate'])
            current_receipt_value=effect_operations.read_hermes_waypoint_replacement_receipt('waypoint_request_1')
            self.assertEqual((current_receipt_value['state'],current_receipt_value['generation'],current_receipt_value['ledger_status_at_save']),('completed',4,'pending'))
            current_gateway_mock.assert_called_once()
            with self.assertRaises(ValueError):
                effect_operations.replace_hermes_waypoint_once('waypoint_request_1',{**current_draft_value,'id':'other'},current_preview_value['review_sha256'])
            current_gateway_mock.side_effect=OSError('lost')
            with self.assertRaises(OSError):
                effect_operations.replace_hermes_waypoint_once('waypoint_request_2',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(effect_operations.replace_hermes_waypoint_once('waypoint_request_2',current_draft_value,current_preview_value['review_sha256'])['state'],'unknown')
            self.assertEqual(effect_operations.read_hermes_waypoint_replacement_receipt('waypoint_request_2')['state'],'unknown')
            self.assertEqual(current_gateway_mock.call_count,2)
            current_gateway_mock.side_effect=None
            current_gateway_mock.return_value={'saved':True,'id':'wrong-id','replaced':'waypoint-v1'}
            with self.assertRaises(ValueError):
                effect_operations.replace_hermes_waypoint_once('waypoint_request_4',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(effect_operations.read_hermes_waypoint_replacement_receipt('waypoint_request_4')['state'],'unknown')
            self.assertEqual(effect_operations.replace_hermes_waypoint_once('waypoint_request_4',current_draft_value,current_preview_value['review_sha256'])['state'],'unknown')
            self.assertEqual(current_gateway_mock.call_count,3)
            current_receipt_path=self.current_store_value.resolve_delegation_record_path('waypoint_request_1')
            current_receipt_record=json.loads(current_receipt_path.read_text())
            current_receipt_record['result_id']='wrong-id'
            current_receipt_path.write_text(json.dumps(current_receipt_record))
            with self.assertRaises(ValueError):
                effect_operations.replace_hermes_waypoint_once(*current_save_args)
            with self.assertRaises(ValueError):
                effect_operations.read_hermes_waypoint_replacement_receipt('waypoint_request_1')
            with self.assertRaises(ValueError):
                effect_operations.replace_hermes_waypoint_once('waypoint_request_3',current_draft_value,'c'*64)
            self.assertEqual(current_gateway_mock.call_count,3)

    def test_waypoint_review_with_registered_asset_repository(self):
        current_effect_value={'id':'waypoint-guide-v4','name':'웨이포인트 안내','image':'assets/sprites/effects/waypoint/waypoint-guide-v4.png','animation':'assets/sprites/effects/waypoint/waypoint-guide-v4.animation.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
        current_draft_value={'id':'waypoint-guide-v3','revision':'a'*64,'effect':current_effect_value}
        current_old_value={'id':'waypoint-guide-v3','name':'이전','renderer':'waypoint-animation','revision':'a'*64,'frames':6}
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=current_old_value):
            current_preview_value=effect_operations.preview_hermes_waypoint_replacement(current_draft_value)
        self.assertEqual(current_preview_value['metadata_frames'],8)
        self.assertEqual(current_preview_value['sheet_pixels'],{'width':1774,'height':887})
        self.assertEqual(current_preview_value['sources']['image']['source'],current_effect_value['image'])
        self.assertEqual(len(current_preview_value['sources']['animation']['sha256']),64)

    def test_registration_review_and_unknown_do_not_repeat_database_write(self):
        current_effect_value={'id':'fog-test-v1','name':'안개','image':'assets/sprites/effects/terrain/lake-fog-sheet-v2.png','renderer':'fog','columns':4,'rows':2,'frames':8,'alignment':{'key':'test-fog','texture':'fog','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
        current_review_value=effect_operations.preview_hermes_effect_registration(current_effect_value)
        self.assertEqual(current_review_value['sources']['image']['source'],current_effect_value['image'])
        self.assertEqual(current_review_value['sheet_pixels'],{'width':1774,'height':887})
        self.assertTrue(current_review_value['effect_editor_available'])
        current_barrier_value={'id':'barrier-test-v1','name':'안전지대','image':'assets/sprites/effects/safe-barrier/safe-barrier-aura-v2-source.png','renderer':'safe-barrier-aura','columns':4,'rows':2,'frames':8}
        self.assertFalse(effect_operations.preview_hermes_effect_registration(current_barrier_value)['effect_editor_available'])
        with self.assertRaisesRegex(ValueError,'alignment'):
            effect_operations.preview_hermes_effect_registration({**current_barrier_value,'alignment':current_effect_value['alignment']})
        with self.assertRaisesRegex(ValueError,'alignment'):
            effect_operations.preview_hermes_effect_registration({key:value for key,value in current_effect_value.items() if key!='alignment'})
        with patch.object(effect_operations,'call_hermes_effect_editor',return_value={'created':True,'id':'fog-test-v1','generation':3,'snapshot':'pending'}) as current_gateway_mock:
            current_args=('effect_register_123',current_effect_value,current_review_value['review_sha256'])
            self.assertEqual(effect_operations.register_hermes_effect_once(*current_args)['generation'],3)
            self.assertTrue(effect_operations.register_hermes_effect_once(*current_args)['duplicate'])
            self.assertEqual(effect_operations.read_hermes_effect_registration_receipt('effect_register_123')['generation'],3)
            current_gateway_mock.assert_called_once()
            current_gateway_mock.side_effect=OSError('lost')
            with self.assertRaises(OSError):
                effect_operations.register_hermes_effect_once('effect_register_456',current_effect_value,current_review_value['review_sha256'])
            self.assertEqual(effect_operations.register_hermes_effect_once('effect_register_456',current_effect_value,current_review_value['review_sha256'])['state'],'unknown')
            self.assertEqual(effect_operations.read_hermes_effect_registration_receipt('effect_register_456')['state'],'unknown')
            self.assertEqual(current_gateway_mock.call_count,2)
        with self.assertRaises(ValueError):
            effect_operations.preview_hermes_effect_registration({**current_effect_value,'image':'assets/sprites/effects/not-registered.png'})
        with self.assertRaises(ValueError):
            effect_operations.preview_hermes_effect_registration({**current_effect_value,'renderer':'waypoint-animation'})
        current_waypoint_value={'id':'waypoint-test-v1','name':'웨이포인트','image':'assets/sprites/effects/waypoint/waypoint-guide-v4.png','animation':'assets/sprites/effects/waypoint/waypoint-guide-v4.animation.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
        self.assertEqual(effect_operations.preview_hermes_effect_registration(current_waypoint_value)['sheet_pixels'],{'width':1774,'height':887})

    def test_billboard_effect_requires_existing_unique_target(self):
        current_effect_value={'id':'glow-test-v1','name':'발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'test-glow','texture':'mushroom-variant-2-v1','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
        with patch.object(effect_operations,'call_hermes_effect_editor',return_value={'storage':'database','assets':[{'texture':'mushroom-variant-2-v1','databaseRevision':1}]}):
            current_review_value=effect_operations.preview_hermes_effect_registration(current_effect_value)
            self.assertEqual(current_review_value['linked_billboard']['texture'],'mushroom-variant-2-v1')
        with patch.object(effect_operations,'call_hermes_effect_editor',return_value={'assets':[{'texture':'mushroom-variant-2-v1'}]}),self.assertRaises(ValueError):
            effect_operations.preview_hermes_effect_registration(current_effect_value)
        for current_assets_value in ([],[{'texture':'mushroom-variant-2-v1','databaseRevision':1}]*2,[{'texture':'mushroom-variant-2-v1'}],[{'texture':'mushroom-variant-2-v1','databaseRevision':True}],[{'texture':'mushroom-variant-2-v1','databaseRevision':'a'*64}]):
            with patch.object(effect_operations,'call_hermes_effect_editor',return_value={'storage':'database','assets':current_assets_value}),self.assertRaises(ValueError):
                effect_operations.preview_hermes_effect_registration(current_effect_value)

    def test_billboard_registration_rechecks_target_revision_before_dispatch(self):
        current_effect_value={'id':'glow-test-v1','name':'발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'test-glow','texture':'mushroom-variant-2-v1','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
        current_revision_value=[1]
        def call_test_effect_editor(current_command_name,current_payload_value):
            if current_command_name=='asset-list':
                return {'storage':'database','assets':[{'texture':'mushroom-variant-2-v1','databaseRevision':current_revision_value[0]}]}
            self.fail('변경된 검토 결과로 등록을 요청했습니다.')
        with patch.object(effect_operations,'call_hermes_effect_editor',side_effect=call_test_effect_editor):
            current_review_value=effect_operations.preview_hermes_effect_registration(current_effect_value)
            current_revision_value[0]=2
            with self.assertRaisesRegex(ValueError,'변경'):
                effect_operations.register_hermes_effect_once('effect_stale_123',current_effect_value,current_review_value['review_sha256'])
            self.assertEqual(effect_operations.read_hermes_effect_registration_receipt('effect_stale_123')['state'],'not_found')

    def test_billboard_old_server_failure_keeps_unknown_receipt(self):
        current_effect_value={'id':'glow-old-server','name':'발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'old-server-glow','texture':'mushroom-variant-2-v1','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
        def call_test_effect_editor(current_command_name,current_payload_value):
            if current_command_name=='asset-list':
                return {'storage':'database','assets':[{'texture':'mushroom-variant-2-v1','databaseRevision':1}]}
            if current_command_name=='effect-register-reviewed':
                raise ValueError('콘텐츠 API 오류 (404)')
            self.fail('검토된 등록 이외의 경로를 호출했습니다.')
        with patch.object(effect_operations,'call_hermes_effect_editor',side_effect=call_test_effect_editor) as current_gateway_mock:
            current_review_value=effect_operations.preview_hermes_effect_registration(current_effect_value)
            current_request_values=('old_server_glow_123',current_effect_value,current_review_value['review_sha256'])
            with self.assertRaisesRegex(ValueError,'404'):
                effect_operations.register_hermes_effect_once(*current_request_values)
            current_call_count=current_gateway_mock.call_count
            self.assertEqual(effect_operations.read_hermes_effect_registration_receipt('old_server_glow_123')['state'],'unknown')
            self.assertEqual(effect_operations.register_hermes_effect_once(*current_request_values)['state'],'unknown')
            self.assertEqual(current_gateway_mock.call_count,current_call_count)

    def test_stale_invalid_and_waypoint_edits_rejected(self):
        for current_invalid_record in ({**self.current_draft_record,'alpha':float('nan')},{**self.current_draft_record,'target':[0,0,0,1]},{**self.current_draft_record,'frames':[]},{**self.current_draft_record,'image':'path'}):
            with self.subTest(draft=current_invalid_record),self.assertRaises(ValueError):effect_operations.validate_hermes_effect_edit(current_invalid_record)
        for current_detail_value in ({**self.current_detail_record,'revision':'b'*64},{**self.current_detail_record,'alignment':None},{**self.current_detail_record,'frames':8}):
            with self.subTest(detail=current_detail_value),patch.object(effect_operations,'read_hermes_effect_detail',return_value=current_detail_value),self.assertRaises(ValueError):effect_operations.preview_hermes_effect_edit(self.current_draft_record)
