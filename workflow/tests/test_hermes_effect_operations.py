"""이펙트 편집의 입력·리비전·중복 및 불확실 응답을 검사한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.domains.hermes_agent import effect_operations
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesEffectOperationTests(unittest.TestCase):
    def test_oversized_effect_receipt_blocks_external_registration(self):
        from workflow.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            current_store_value=HermesDelegationStore(current_root_path)
            current_effect_value={'id':'effect-test','name':'x'*HERMES_DELEGATION_RECORD_MAXIMUM_BYTES}
            with patch.object(effect_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(effect_operations,'preview_hermes_effect_registration',return_value={'review_sha256':'a'*64}),patch.object(effect_operations,'call_hermes_effect_editor') as current_gateway_mock:
                with self.assertRaisesRegex(ValueError,'접수 기록 크기 초과'):
                    effect_operations.register_hermes_effect_once('request_123',current_effect_value,'a'*64)
                current_gateway_mock.assert_not_called()
                self.assertFalse((current_root_path/'request_123.json').exists())

    def test_effect_receipt_target_matches_and_legacy_is_distinct(self):
        from workflow.domains.hermes_agent.effect_operations import inspect_hermes_effect_receipt
        current_record={'version':8,'id':'effect_request_123','state':'dispatching','effect_id':'fire'}
        self.assertEqual(inspect_hermes_effect_receipt(current_record,'effect_request_123')['effect_id'],'fire')
        current_record['effect_id']='../invalid'
        with self.assertRaises(ValueError):inspect_hermes_effect_receipt(current_record,'effect_request_123')
        del current_record['effect_id']
        self.assertNotIn('effect_id',inspect_hermes_effect_receipt(current_record,'effect_request_123'))

    def test_history_rejects_mismatched_effect_and_labels_legacy(self):
        import os, subprocess
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--test',str(root/'workflow/tests/effect_proposal_protocol.test.mjs')],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_effect_summary_preserves_each_frame_and_scope(self):
        import os, subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'effect.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'EffectProposal.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {EffectProposalReview}=require(process.argv[1]);
              const preview={id:'firefly-v1',before:{alpha:0.5,target:[0,0,1,1],frames:[[0,0,1,1],[1,1,2,2]]},after:{alpha:0.7,target:[1,0,1,1],frames:[[0,0,1,1],[2,1,2,2]]},note:'모든 맵에 적용'};
              process.stdout.write(server.renderToStaticMarkup(React.createElement(EffectProposalReview,{preview,busy:true})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        for value in ('불투명도','0.5','0.7','프레임 1','[1,1,2,2]','[2,1,2,2]','모든 맵에 적용','이펙트 도구','확인 후 저장','취소','disabled'):
            self.assertIn(value,markup)

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
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=self.current_detail_record), patch.object(effect_operations,'call_hermes_effect_editor',return_value={'saved':True,'revision':'b'*64,'generation':4,'snapshot':'pending'}) as current_editor_mock:
            current_preview_record=effect_operations.preview_hermes_effect_edit(self.current_draft_record)
            self.assertEqual(current_preview_record['after']['texture'],'fireflies')
            current_save_args=('effect_request_123',self.current_draft_record,self.current_preview_token)
            self.assertTrue(effect_operations.save_hermes_effect_edit_once(*current_save_args)['saved'])
            self.assertEqual(effect_operations.read_hermes_effect_edit_receipt('effect_request_123')['effect_id'],self.current_draft_record['id'])
            current_receipt=effect_operations.read_hermes_effect_edit_receipt('effect_request_123')
            self.assertEqual((current_receipt['generation'],current_receipt['ledger_status_at_save']),(4,'pending'))
            self.assertTrue(effect_operations.save_hermes_effect_edit_once(*current_save_args)['duplicate'])
            self.assertEqual(current_editor_mock.call_count,1)
            current_payload_record=current_editor_mock.call_args.args[1]
            self.assertEqual(current_payload_record['expectedRevision'],'a'*64)
            self.assertEqual(current_payload_record['alignment']['key'],'safe-firefly')
            import uuid
            self.assertEqual(str(uuid.UUID(current_payload_record['requestId'])),current_payload_record['requestId'])
            self.assertEqual(self.current_store_value.list_delegation_receipts()['records'],[])

    def test_changed_receipt_after_effect_save_is_not_overwritten(self):
        import json
        current_record_path=self.current_store_value.resolve_delegation_record_path('effect_request_123')
        def current_editor_response(current_command_name,current_payload_record):
            current_receipt_value=json.loads(current_record_path.read_text())
            current_receipt_value['external_change']='preserve'
            current_record_path.write_text(json.dumps(current_receipt_value))
            return {'saved':True,'revision':'b'*64}
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=self.current_detail_record),patch.object(effect_operations,'call_hermes_effect_editor',side_effect=current_editor_response) as current_editor_mock:
            current_save_args=('effect_request_123',self.current_draft_record,self.current_preview_token)
            with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):effect_operations.save_hermes_effect_edit_once(*current_save_args)
            self.assertEqual(effect_operations.save_hermes_effect_edit_once(*current_save_args)['state'],'unknown')
            current_editor_mock.assert_called_once()
            self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_unknown_is_not_redispatched(self):
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=self.current_detail_record), patch.object(effect_operations,'call_hermes_effect_editor',side_effect=OSError('lost')) as current_editor_mock:
            current_save_args=('effect_request_123',self.current_draft_record,self.current_preview_token)
            with self.assertRaises(OSError):effect_operations.save_hermes_effect_edit_once(*current_save_args)
            self.assertEqual(effect_operations.read_hermes_effect_edit_receipt('effect_request_123')['state'],'unknown')
            self.assertEqual(effect_operations.read_hermes_effect_edit_receipt('effect_request_123')['effect_id'],self.current_draft_record['id'])
            self.assertEqual(effect_operations.save_hermes_effect_edit_once(*current_save_args)['state'],'unknown')
            self.assertEqual(current_editor_mock.call_count,1)

    def test_registration_service_receipt_prevents_duplicate_write(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_draft={'id':'fog-test-v1'}
        current_review={'request_id':'registration_request_123','draft':current_draft,'review_sha256':'a'*64}
        manager=HermesServiceManager(Path(self.current_temp_root.name)/'jobs')
        with patch.object(effect_operations,'preview_hermes_effect_registration',return_value={'review_sha256':'a'*64}), patch.object(effect_operations,'call_hermes_effect_editor',return_value={'created':True,'id':'fog-test-v1','generation':3,'snapshot':'pending'}) as current_editor:
            first=manager.execute_hermes_command('hermes-effect-register',current_review)
            second=manager.execute_hermes_command('hermes-effect-register',current_review)
            self.assertEqual(first['state'],'completed')
            self.assertTrue(second['duplicate'])
            self.assertEqual(second['id'],'fog-test-v1')
            current_editor.assert_called_once()

    def test_effect_registration_and_waypoint_preserve_changed_receipt(self):
        import json
        current_cases=(('registration',{'id':'new-effect'},'preview_hermes_effect_registration','register_hermes_effect_once',{'created':True,'id':'new-effect','generation':2,'snapshot':'pending'}),('waypoint',{'id':'old-effect','revision':'b'*64,'effect':{'id':'new-effect'}},'preview_hermes_waypoint_replacement','replace_hermes_waypoint_once',{'saved':True,'id':'new-effect','replaced':'old-effect','generation':2,'snapshot':'pending'}))
        for current_kind_name,current_draft_value,current_preview_name,current_save_name,current_response_value in current_cases:
            with self.subTest(kind=current_kind_name):
                current_request_value=current_kind_name+'_request_123'
                current_record_path=self.current_store_value.resolve_delegation_record_path(current_request_value)
                def current_editor_response(current_command_name,current_payload_record):
                    current_receipt_value=json.loads(current_record_path.read_text())
                    current_receipt_value['external_change']='preserve'
                    current_record_path.write_text(json.dumps(current_receipt_value))
                    return current_response_value
                with patch.object(effect_operations,current_preview_name,return_value={'review_sha256':'a'*64}),patch.object(effect_operations,'call_hermes_effect_editor',side_effect=current_editor_response) as current_editor_mock:
                    current_save_function=getattr(effect_operations,current_save_name)
                    with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):current_save_function(current_request_value,current_draft_value,'a'*64)
                    self.assertEqual(current_save_function(current_request_value,current_draft_value,'a'*64)['state'],'unknown')
                    current_editor_mock.assert_called_once()
                    self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

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
        with patch.object(effect_operations,'read_hermes_effect_detail',return_value=current_old_value),patch('workflow.common.map_tile_assets.load_registered_tiles',return_value=(Path('/unused'),{})),patch('workflow.common.map_tile_assets.resolve_registered_asset',side_effect=resolve_test_source),patch.object(effect_operations,'call_hermes_effect_editor',return_value={'saved':True,'id':'waypoint-v2','replaced':'waypoint-v1','generation':4,'snapshot':'pending'}) as current_gateway_mock:
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
