"""격리 에셋에서 Hermes 앵커 검토와 실제 편집기 저장을 검증한다."""
import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from PIL import Image
from tools.review.domains.character_animation import sprite_sheet_editor
from tools.review.domains.hermes_agent import sprite_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesSpriteOperationsTests(unittest.TestCase):
    def setUp(self):
        current_temp_directory=tempfile.TemporaryDirectory();self.addCleanup(current_temp_directory.cleanup)
        self.current_root_path=Path(current_temp_directory.name)
        self.current_asset_root=self.current_root_path/'slime-assets'
        current_sprite_directory=self.current_asset_root/'assets/characters/default/animations/test'
        current_sprite_directory.mkdir(parents=True)
        self.current_frontend_root=self.current_root_path/'slime-frontend';self.current_frontend_root.mkdir()
        self.current_image_path=current_sprite_directory/'sheet.png'
        current_image_value=Image.new('RGBA',(8,4),(10,20,30,255));current_image_value.paste((210,30,40,255),(4,0,8,4));current_image_value.save(self.current_image_path)
        self.current_metadata_path=current_sprite_directory/'sheet.animation.json'
        self.current_animation_record={'animationId':'character.test','version':'v1','sheet':{'width':8,'height':4},'frames':[{'frameId':'idle.0','rect':{'x':0,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':3}},{'frameId':'idle.1','rect':{'x':4,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':3}}],'clips':[{'clipId':'idle','loop':True,'nextClipId':None,'frames':[{'frameId':'idle.0','durationMs':167},{'frameId':'idle.1','durationMs':166}]}]}
        self.current_metadata_path.write_text(json.dumps(self.current_animation_record))
        current_records=[{'managementId':current_file_path.name,'version':'v1','path':current_file_path.relative_to(self.current_asset_root).as_posix(),'sha256':hashlib.sha256(current_file_path.read_bytes()).hexdigest(),'source':{}} for current_file_path in (self.current_image_path,self.current_metadata_path)]
        (self.current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':current_records}))
        (self.current_frontend_root/'sprite-assets.lock.yaml').write_text(yaml.safe_dump({'files':[{'path':current_record['path'],'source_path':current_record['path'],'sha256':current_record['sha256']} for current_record in current_records]}))
        self.current_path_value=current_records[0]['path']
        current_image_hash=current_records[0]['sha256'];current_metadata_hash=current_records[1]['sha256']
        current_snapshot_digest=hashlib.sha256((current_image_hash+':'+current_metadata_hash).encode()).hexdigest()
        self.current_draft_record={'path':self.current_path_value,'snapshot':current_snapshot_digest,'columns':2,'anchors':[{'frame_id':'idle.0','x':2,'y':3}]}
        self.current_store_value=HermesDelegationStore(self.current_root_path/'receipts')
        current_environment_patch=patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(self.current_asset_root)});current_environment_patch.start();self.addCleanup(current_environment_patch.stop)
        current_jobs_patch=patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',self.current_root_path/'jobs');current_jobs_patch.start();self.addCleanup(current_jobs_patch.stop)
        current_store_patch=patch.object(sprite_operations,'HermesDelegationStore',return_value=self.current_store_value);current_store_patch.start();self.addCleanup(current_store_patch.stop)
        def execute_test_editor(current_command_name,current_payload_record):
            if current_command_name=='sheet-image':return sprite_sheet_editor.execute_sprite_asset_command('sheet-image',current_payload_record)
            if current_command_name=='sheet-export':return sprite_sheet_editor.execute_sprite_sheet_export(current_payload_record)
            if current_command_name=='sheet-gif':return sprite_sheet_editor.execute_sprite_gif_export(current_payload_record)
            if current_command_name=='sheet-update':return sprite_sheet_editor.update_registered_sprite_sheet(current_payload_record)
            raise ValueError('unexpected command')
        current_editor_patch=patch.object(sprite_operations,'call_hermes_sprite_editor',side_effect=execute_test_editor);current_editor_patch.start();self.addCleanup(current_editor_patch.stop)

    def test_preview_and_save_update_registry_and_lock_once(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        from tools.review.ui.gradio.hermes_agent_app import format_conversation_sprite_changes
        current_summary_value=format_conversation_sprite_changes(current_preview_record)
        self.assertIn('변경 앵커 1개',current_summary_value)
        self.assertIn('프레임 배치',current_summary_value)
        self.assertIn(current_preview_record['output_sha256'],current_summary_value)
        self.assertIn(current_preview_record['clips'][0]['id'],current_summary_value)
        self.assertIn('클립: '+current_preview_record['clips'][0]['id'],current_summary_value)
        self.assertIn(str(current_preview_record['clips'][0]['frames'][0]['duration_ms'])+'ms',current_summary_value)
        self.assertEqual(current_preview_record['changed_anchors'][0]['after'],{'x':2,'y':3})
        self.assertEqual(current_preview_record['output_sheet'],{'width':8,'height':4})
        self.assertEqual(hashlib.sha256(base64.b64decode(current_preview_record['preview_image'])).hexdigest(),current_preview_record['output_sha256'])
        self.assertEqual(len(current_preview_record['frame_layout']),2)
        self.assertEqual(current_preview_record['frame_layout'][1]['after'],{'x':4,'y':0,'width':4,'height':4})
        current_save_args=('sprite_request_123',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
        self.assertTrue(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['saved'])
        self.assertEqual(sprite_operations.read_hermes_sprite_anchor_receipt('sprite_request_123')['path'],self.current_draft_record['path'])
        self.assertTrue(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['duplicate'])
        current_animation_value=json.loads(self.current_metadata_path.read_text())
        self.assertEqual(current_animation_value['frames'][0]['anchor'],{'x':2,'y':3})
        self.assertEqual(current_animation_value['clips'],self.current_animation_record['clips'])
        current_registry_records={current_record['path']:current_record for current_record in yaml.safe_load((self.current_asset_root/'asset-registry.yaml').read_text())['assets']}
        for current_lock_record in yaml.safe_load((self.current_frontend_root/'sprite-assets.lock.yaml').read_text())['files']:
            self.assertEqual(current_lock_record['sha256'],current_registry_records[current_lock_record['source_path']]['sha256'])
        with self.assertRaisesRegex(ValueError,'원본이 변경'):sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        self.assertEqual(self.current_store_value.list_delegation_receipts()['records'],[])

    def test_changed_receipt_after_sprite_save_is_not_overwritten(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_save_args=('sprite_request_123',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
        current_record_path=self.current_store_value.resolve_delegation_record_path('sprite_request_123')
        current_original_editor=sprite_operations.call_hermes_sprite_editor.side_effect
        def current_editor_response(current_command_name,current_payload_value):
            current_result_value=current_original_editor(current_command_name,current_payload_value)
            if current_command_name=='sheet-update':
                current_receipt_value=json.loads(current_record_path.read_text())
                current_receipt_value['external_change']='preserve'
                current_record_path.write_text(json.dumps(current_receipt_value))
            return current_result_value
        with patch.object(sprite_operations,'call_hermes_sprite_editor',side_effect=current_editor_response) as current_editor_mock:
            with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)
            self.assertEqual(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(item.args[0]=='sheet-update' for item in current_editor_mock.call_args_list),1)
            self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_registered_clip_playback_preserves_order_and_timing(self):
        from io import BytesIO
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_playback_record=sprite_operations.render_hermes_sprite_clip_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],'idle')
        current_gif_bytes=base64.b64decode(current_playback_record['gif'],validate=True)
        self.assertEqual(hashlib.sha256(current_gif_bytes).hexdigest(),current_playback_record['sha256'])
        self.assertEqual(current_playback_record['durations_ms'],[170,160])
        self.assertTrue(current_playback_record['loop'])
        with Image.open(BytesIO(current_gif_bytes)) as current_gif_image:
            self.assertEqual(current_gif_image.n_frames,2)
            self.assertEqual(current_gif_image.info['duration'],170)
            current_first_pixel=current_gif_image.convert('RGB').getpixel((2,2))
            current_gif_image.seek(1)
            self.assertEqual(current_gif_image.info['duration'],160)
            self.assertNotEqual(current_first_pixel,current_gif_image.convert('RGB').getpixel((2,2)))
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_clip_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],'missing')
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_clip_playback(self.current_draft_record,current_preview_record['token'],'0'*64,'idle')

    def test_clip_duration_rounding_preserves_cycle_length(self):
        current_frame_values=[{'duration_ms':current_duration_value} for current_duration_value in (167,166,167)*4]
        current_duration_values=sprite_operations.quantize_hermes_sprite_clip_durations(current_frame_values)
        self.assertEqual(current_duration_values[:3],[170,160,170])
        self.assertEqual(sum(current_duration_values),2000)
        self.assertTrue(all(current_duration_value>=10 and current_duration_value%10==0 for current_duration_value in current_duration_values))

    def test_reviewed_playback_uses_real_gif_and_rejects_mismatch(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_playback_record=sprite_operations.render_hermes_sprite_anchor_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],8)
        current_gif_bytes=base64.b64decode(current_playback_record['gif'],validate=True)
        self.assertTrue(current_gif_bytes.startswith((b'GIF87a',b'GIF89a')))
        self.assertEqual(hashlib.sha256(current_gif_bytes).hexdigest(),current_playback_record['sha256'])
        self.assertEqual(current_playback_record['frame_count'],2)
        self.assertIn('균일 FPS',current_playback_record['note'])
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_anchor_playback(self.current_draft_record,current_preview_record['token'],'0'*64,8)
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_anchor_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],7)
        self.assertEqual(self.current_image_path.read_bytes(),base64.b64decode(sprite_sheet_editor.execute_sprite_asset_command('sheet-image',{'path':self.current_path_value})['image']))

    def test_stale_source_invalid_frame_and_unknown_response(self):
        with self.assertRaises(ValueError):sprite_operations.preview_hermes_sprite_anchor_edit({**self.current_draft_record,'anchors':[{'frame_id':'missing','x':0,'y':0}]})
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_original_editor=sprite_operations.call_hermes_sprite_editor
        def execute_lost_editor(current_command_name,current_payload_record):
            if current_command_name=='sheet-update':raise OSError('lost response')
            return current_original_editor(current_command_name,current_payload_record)
        with patch.object(sprite_operations,'call_hermes_sprite_editor',side_effect=execute_lost_editor) as current_editor_mock:
            current_save_args=('sprite_request_456',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
            with self.assertRaises(OSError):sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)
            self.assertEqual(sprite_operations.read_hermes_sprite_anchor_receipt('sprite_request_456')['state'],'unknown')
            self.assertEqual(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(current_call.args[0]=='sheet-update' for current_call in current_editor_mock.call_args_list),1)
