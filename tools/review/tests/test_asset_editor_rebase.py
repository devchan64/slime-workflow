"""누적 편집은 유지하고 최신 원본의 변경 필드만 검증한다."""
import unittest
from unittest.mock import patch
from tools.review.ui.gradio import asset_editor_app as editor


class AssetEditorRebaseTests(unittest.TestCase):
    def test_saved_revision_refresh_preserves_detail_and_selection(self):
        current_detail_record={'texture':'selected','databaseRevision':1,'image':'preview'}
        current_catalog_record={'assets':[{'texture':'selected','databaseRevision':2}]}
        self.assertEqual(editor.refresh_saved_asset_revision(current_catalog_record,current_detail_record,'selected · DB 저장 완료 · 파일 스냅샷 대기'),
            {**current_detail_record,'databaseRevision':2})
        for current_feedback_text in ('저장 실패','other · DB 저장 완료','selected · 저장 중…'):
            self.assertEqual(editor.refresh_saved_asset_revision(current_catalog_record,current_detail_record,current_feedback_text),editor.gr.skip())

    def test_merge_latest_fields_and_report_conflicts(self):
        current_catalog_record={'revision':'old','assets':[{'texture':'rock','properties':{'anchorX':0,'anchorY':0}}]}
        current_latest_catalog={'revision':'new','assets':[{'texture':'rock','properties':{'anchorX':0.2,'anchorY':0.7}}]}
        current_edit_payload={'revision':'old','changes':[{'texture':'rock','values':{'anchorX':0.5}}]}
        with patch.object(editor,'build_asset_editor_payload',return_value=current_edit_payload), patch.object(editor,'execute_remote_management_command',side_effect=[current_latest_catalog,{'token':'verified','map_warnings':[]}]) as current_gateway_mock:
            current_pending_record,current_preview_record,_,_=editor.preview_asset_editor_changes(current_catalog_record,[])
        self.assertEqual(current_gateway_mock.call_args.args[2],{'revision':'new','changes':[{'texture':'rock','values':{'anchorX':0.5}}]})
        self.assertEqual(current_pending_record['editing_payload'],current_edit_payload)
        self.assertEqual(current_preview_record['conflicts'][0]['latest'],0.2)

    def test_removed_unchanged_asset_does_not_block(self):
        current_catalog_record={'revision':'old','assets':[{'texture':'rock','properties':{'anchorX':0}},{'texture':'retired','properties':{}}]}
        current_edit_payload={'revision':'old','changes':[{'texture':'rock','values':{'anchorX':0.5}}]}
        current_latest_catalog={'revision':'new','assets':[{'texture':'rock','properties':{'anchorX':0}}]}
        with patch.object(editor,'build_asset_editor_payload',return_value=current_edit_payload), patch.object(editor,'execute_remote_management_command',side_effect=[current_latest_catalog,{'token':'verified'}]):
            current_pending_record,current_preview_record,_,_=editor.preview_asset_editor_changes(current_catalog_record,[])
        self.assertEqual(current_pending_record['revision'],'new')
        self.assertEqual(current_preview_record['conflicts'],[])

    def test_changed_table_after_preview_cannot_save(self):
        with patch.object(editor,'build_asset_editor_payload',return_value={'revision':'old','changes':[]}), patch.object(editor,'execute_remote_management_command') as current_gateway_mock:
            with self.assertRaises(Exception):
                editor.save_asset_editor_changes({},[],{'editing_payload':{'revision':'old','changes':[1]}})
        current_gateway_mock.assert_not_called()

    def test_selected_save_sends_only_selected_id(self):
        current_property_record={'anchorX':0,'anchorY':0,'groundFootprintColumns':1,'groundFootprintRows':1,'displayHeight':80,'billboardAnchorMode':'tile-intersection','billboardBlocksMovement':False,'shadowOffsetColumn':0,'shadowOffsetRow':0,'shadowScaleX':1,'shadowScaleY':1}
        current_catalog_record={'revision':'latest','assets':[{'texture':current_texture_key,'properties':dict(current_property_record)} for current_texture_key in ('selected','other')]}
        current_table_values=[[current_texture_key,'이름',0,0,1,1,80,'top',0,0,1,1,False,0] for current_texture_key in ('selected','other')]
        with patch.object(editor,'load_asset_editor_catalog',return_value=(current_catalog_record,current_table_values,'')),patch.object(editor,'execute_remote_management_command',side_effect=[{'token':'verified','map_warnings':[]},{'saved':True}]) as current_gateway_mock:
            editor.save_selected_asset_properties({'texture':'selected'},0,0,1,1,100,'top',0,0,1,1,False)
        for current_gateway_call in current_gateway_mock.call_args_list:
            self.assertEqual(current_gateway_call.args[2]['changes'],[{'texture':'selected','values':{'displayHeight':100}}])
