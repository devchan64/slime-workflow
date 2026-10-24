"""미설정 에셋이 목록 전체를 중단하지 않는지 검증한다."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import gradio as gr
from tools.review.ui.gradio import asset_editor_app


class UnconfiguredAssetEditorTests(unittest.TestCase):
    def test_unconfigured_asset_lists_without_inventing_properties(self):
        current_catalog_data={'revision':'test','assets':[{'texture':'unconfigured-tree','name':'미설정 나무','properties':None,'maps':[],'image':'unused.png','category':'large-trees'}]}
        with patch.object(asset_editor_app,'execute_remote_management_command',return_value=current_catalog_data):
            current_loaded_data,current_table_rows,_=asset_editor_app.load_asset_editor_catalog()
        self.assertTrue(all(current_value is None for current_value in current_table_rows[0][2:13]))
        self.assertEqual(asset_editor_app.build_asset_editor_payload(current_loaded_data,current_table_rows)['changes'],[])
        current_table_rows[0][2:13]=[0,0,1,1,128,'top',0,0,1,1,False]
        current_request_data=asset_editor_app.build_asset_editor_payload(current_loaded_data,current_table_rows)
        self.assertEqual(len(current_request_data['changes']),1)
        self.assertIsNone(current_loaded_data['assets'][0]['properties'])
