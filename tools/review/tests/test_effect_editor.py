"""발광 명령의 DB 연결과 입력 경계 검증."""
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets.effect_editor import execute_effect_editor_command

class EffectEditorTests(unittest.TestCase):
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_list_filters_non_alignment_effects(self,current_api_mock):
        current_api_mock.return_value={'effects':[{'id':'a','name':'A'},{'id':'b','name':'B','alignment':{}}]}
        self.assertEqual(execute_effect_editor_command('effect-list',{}),{'effects':[{'id':'b','name':'B'}]})
    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_waypoint_effect_is_listed_and_loads_six_frames_without_billboard(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        from unittest.mock import Mock
        current_effect_record={'id':'waypoint-guide-v3','name':'웨이포인트 안내','renderer':'waypoint-animation','image':'assets/sprites/effects/waypoint/guide.png','animation':'assets/sprites/effects/waypoint/guide.animation.json','frames':6}
        current_api_mock.return_value={'effects':[current_effect_record]}
        self.assertEqual(execute_effect_editor_command('effect-list',{})['effects'],[{'id':'waypoint-guide-v3','name':'웨이포인트 안내'}])
        current_tiles_mock.return_value=(None,{})
        current_image_path=Mock();current_image_path.read_bytes.return_value=b'png'
        current_animation_path=Mock();current_animation_path.read_text.return_value='{"frames":[{},{},{},{},{},{}]}'
        current_resolver_mock.side_effect=[(current_image_path,{}),(current_animation_path,{})]
        current_detail_record=execute_effect_editor_command('effect-load',{'id':'waypoint-guide-v3'})
        self.assertIsNone(current_detail_record['hostImage'])
        self.assertEqual(len(current_detail_record['animationMetadata']['frames']),6)
        self.assertEqual(current_api_mock.call_count,2)

    def test_waypoint_replacement_requires_same_selection_and_confirmed_input(self):
        import json
        import gradio as gr
        from tools.review.ui.gradio.effect_editor_app import prepare_waypoint_effect_replacement,confirm_waypoint_effect_replacement
        current_detail_record={'document':{'id':'waypoint-guide-v3','renderer':'waypoint-animation'},'revision':'original'}
        current_effect_record={'id':'waypoint-guide-v4','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8,'image':'assets/sprites/effects/waypoint/guide.png','animation':'assets/sprites/effects/waypoint/guide.animation.json'}
        current_effect_json=json.dumps(current_effect_record)
        current_pending_record,_,_=prepare_waypoint_effect_replacement(current_detail_record,current_effect_json)
        with patch('tools.review.ui.gradio.effect_editor_app.execute_remote_management_command',return_value={'id':'waypoint-guide-v4'}) as current_gateway_mock:
            with self.assertRaises(gr.Error):confirm_waypoint_effect_replacement(current_detail_record,current_pending_record,json.dumps({**current_effect_record,'id':'changed'}))
            current_gateway_mock.assert_not_called()
            confirm_waypoint_effect_replacement(current_detail_record,current_pending_record,current_effect_json)
            current_gateway_mock.assert_called_once_with('map-assets','effect-replace',current_pending_record)

    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_save_preserves_revision_and_request(self,current_api_mock):
        current_payload={'id':'sample','requestId':'request','expectedRevision':'revision','alignment':{}}
        execute_effect_editor_command('effect-save',current_payload)
        current_api_mock.assert_called_once_with('PATCH','/internal/v1/content/effects/sample',{key:value for key,value in current_payload.items() if key!='id'})
    def test_save_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):execute_effect_editor_command('effect-save',{'path':'/tmp/a'})

    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_swarm_load_does_not_require_billboard(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        from unittest.mock import Mock
        current_api_mock.return_value={'effects':[{'id':'moth-swarm-v1','renderer':'swarm','image':'assets/sprites/effects/terrain/moth-swarm-sheet-v1.png','alignment':{'texture':'moths'}}]}
        current_tiles_mock.return_value=(None,{})
        current_image_path=Mock();current_image_path.read_bytes.return_value=b'png'
        current_resolver_mock.return_value=(current_image_path,{})
        current_result_record=execute_effect_editor_command('effect-load',{'id':'moth-swarm-v1'})
        self.assertIsNone(current_result_record['hostImage'])
        self.assertEqual(current_api_mock.call_count,1)

    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_registration_verifies_registered_files_before_endpoint(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        current_tiles_mock.return_value=('root',{})
        current_api_mock.side_effect=[{'capabilities':{'effectAlignmentUniqueness':True}},{'effects':[]},{'created':True}]
        current_effect_payload={'id':'lake-fog-v1','renderer':'fog','image':'assets/sprites/effects/fog.png','animation':'assets/sprites/effects/fog.json'}
        execute_effect_editor_command('effect-register',current_effect_payload)
        self.assertEqual([current_call.args[0] for current_call in current_resolver_mock.call_args_list],[current_effect_payload['image'],current_effect_payload['animation']])
        self.assertEqual(current_api_mock.call_args_list[-1].args,('POST','/internal/v1/content/effects',current_effect_payload))
        current_api_mock.reset_mock()
        current_api_mock.side_effect=[{'capabilities':{'effectAlignmentUniqueness':True}},{'effects':[]}]
        current_resolver_mock.side_effect=ValueError('등록되지 않은 에셋')
        with self.assertRaises(ValueError):
            execute_effect_editor_command('effect-register',current_effect_payload)
        self.assertEqual(current_api_mock.call_count,2)
        self.assertEqual(current_api_mock.call_args.args[:2],('GET','/internal/v1/content/effects'))

    def test_registration_verifies_real_registry_and_hash_before_database(self):
        import hashlib
        import tempfile
        from pathlib import Path
        import yaml
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)
            current_relative_path='assets/sprites/effects/test/fog.png'
            current_image_path=current_asset_root/current_relative_path
            current_image_path.parent.mkdir(parents=True)
            current_image_path.write_bytes(b'approved image')
            current_registry_record={'schema_version':1,'assets':[{'managementId':'test-fog','version':'1','path':current_relative_path,'sha256':hashlib.sha256(b'approved image').hexdigest(),'source':{}}]}
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump(current_registry_record))
            current_effect_payload={'id':'fog-v1','renderer':'fog','image':current_relative_path}
            with patch.dict('os.environ',{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',side_effect=lambda method,route,*args: {'capabilities':{'effectAlignmentUniqueness':True}} if route.endswith('/status') else {'effects':[]} if method=='GET' else {'created':True}) as current_api_mock:
                execute_effect_editor_command('effect-register',current_effect_payload)
                self.assertEqual(current_api_mock.call_count,3)
                current_api_mock.reset_mock()
                current_image_path.write_bytes(b'changed image')
                with self.assertRaisesRegex(ValueError,'해시 불일치'):
                    execute_effect_editor_command('effect-register',current_effect_payload)
                with self.assertRaisesRegex(ValueError,'미등록'):
                    execute_effect_editor_command('effect-register',{**current_effect_payload,'image':'assets/sprites/effects/test/missing.png'})
                self.assertTrue(all(call.args[0]=='GET' for call in current_api_mock.call_args_list))

    def test_old_server_rejects_alignment_registration_before_write(self):
        from tools.review.domains.map_assets.effect_editor import validate_effect_registration_conflicts
        for current_renderer_name in ('fog','swarm'):
            with self.subTest(renderer=current_renderer_name),patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',return_value={}) as current_api_mock:
                with self.assertRaisesRegex(ValueError,'지원하지 않습니다'):
                    validate_effect_registration_conflicts({'id':'new-effect','renderer':current_renderer_name})
                current_api_mock.assert_called_once_with('GET','/internal/v1/content/status')

    def test_direct_registration_rejects_existing_alignment_texture(self):
        current_effect_value={'id':'new-glow','alignment':{'texture':'mushroom','key':'new-key'}}
        current_existing_value={'id':'old-glow','alignment':{'texture':'mushroom','key':'old-key'}}
        with patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',return_value={'effects':[current_existing_value]}) as current_api_mock:
            with self.assertRaisesRegex(ValueError,'이미 있습니다'):
                execute_effect_editor_command('effect-register',current_effect_value)
            current_api_mock.assert_called_once_with('GET','/internal/v1/content/effects')

    def test_reviewed_registration_rechecks_database_target(self):
        from tools.review.common.management_gateway import resolve_management_command
        self.assertEqual(resolve_management_command('map-assets','effect-register-reviewed',{}),('POST','/map-assets/editor-effect-register-reviewed'))
        from tools.review.domains.map_assets.effect_editor import register_reviewed_effect_with_target
        current_effect_value={'id':'glow-v1','renderer':'billboard-glow','alignment':{'texture':'mushroom','key':'glow'}}
        current_request_value={'effect':current_effect_value,'target_revision':1}
        with patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',side_effect=[{'capabilities':{'reviewedBillboardEffectRegistration':True}},{'effects':[{'id':'other','alignment':{'texture':'mushroom','key':'other'}}]}]),patch('tools.review.domains.map_assets.effect_editor.execute_effect_editor_command') as current_register_mock:
            with self.assertRaisesRegex(ValueError,'이미 있습니다'):
                register_reviewed_effect_with_target(current_request_value)
            current_register_mock.assert_not_called()
        with patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',side_effect=[{'capabilities':{'reviewedBillboardEffectRegistration':True}},{'effects':[]}]),patch('tools.review.domains.map_assets.database_editor.load_database_editor_catalog',return_value={'storage':'database','assets':[{'texture':'mushroom','databaseRevision':2}]}),patch('tools.review.domains.map_assets.effect_editor.execute_effect_editor_command') as current_register_mock:
            with self.assertRaisesRegex(ValueError,'변경'):
                register_reviewed_effect_with_target(current_request_value)
            current_register_mock.assert_not_called()
        with patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',side_effect=[{'capabilities':{'reviewedBillboardEffectRegistration':True}},{'effects':[]},{'created':True}]) as current_api_mock,patch('tools.review.domains.map_assets.database_editor.load_database_editor_catalog',return_value={'storage':'database','assets':[{'texture':'mushroom','databaseRevision':1}]}),patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles',return_value=(None,[])),patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset'):
            self.assertTrue(register_reviewed_effect_with_target(current_request_value)['created'])
            current_api_mock.assert_called_with('POST','/internal/v1/content/effects/reviewed',{'effect':current_effect_value,'expectedBillboardRevision':1})

    def test_legacy_waypoint_without_capabilities_remains_supported(self):
        from tools.review.domains.map_assets.effect_editor import validate_effect_registration_conflicts
        current_effect_value={'id':'new-waypoint','renderer':'waypoint-animation'}
        with patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',return_value={'effects':[]}) as current_api_mock:
            self.assertTrue(validate_effect_registration_conflicts(current_effect_value)['available'])
            current_api_mock.assert_called_once_with('GET','/internal/v1/content/effects')

    def test_reviewed_registration_does_not_fall_back_on_old_server(self):
        from tools.review.domains.map_assets.effect_editor import register_reviewed_effect_with_target
        current_effect_value={'id':'glow-v1','renderer':'billboard-glow','alignment':{'texture':'mushroom','key':'glow'}}
        current_request_value={'effect':current_effect_value,'target_revision':1}
        with patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request',return_value={}) as current_api_mock,patch('tools.review.domains.map_assets.database_editor.load_database_editor_catalog',return_value={'storage':'database','assets':[{'texture':'mushroom','databaseRevision':1}]}),patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles',return_value=(None,[])),patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset'):
            with self.assertRaisesRegex(ValueError,'지원하지 않습니다'):
                register_reviewed_effect_with_target(current_request_value)
            self.assertEqual(current_api_mock.call_count,1)
            self.assertEqual(current_api_mock.call_args.args[1],'/internal/v1/content/status')

    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_image_replacement_checks_registry_before_save(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        current_tiles_mock.return_value=('root',{})
        current_payload={'id':'fog','requestId':'request','expectedRevision':'revision','alignment':{},'image':'assets/sprites/effects/terrain/fog-v2.png'}
        execute_effect_editor_command('effect-save',current_payload)
        current_resolver_mock.assert_called_once_with(current_payload['image'],'root',{},'assets/sprites/effects')
        current_api_mock.assert_called_once_with('PATCH','/internal/v1/content/effects/fog',{k:v for k,v in current_payload.items() if k!='id'})
