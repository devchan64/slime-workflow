"""GUI 워치의 연속 저장 묶기와 준비 산출물 재사용 경계 검증."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.management import serve


class ReviewWatchTests(unittest.TestCase):
    def test_changed_files_include_additions_and_deletions(self):
        self.assertEqual(serve.collect_changed_review_paths((('a',1,2),('b',1,2)),(('a',2,2),('c',1,2))),['a','b','c'])

    def test_only_management_ui_python_changes_reuse_preparation(self):
        current_workflow_root=Path(serve.__file__).resolve().parents[2]
        current_safe_paths=[str(current_workflow_root/'tools/management/ui/gradio/asset_editor_app.py'),str(current_workflow_root/'tools/management/common/gradio_asset_editor.py')]
        self.assertTrue(serve.can_reuse_review_directory(current_safe_paths))
        for current_unsafe_path in ('tools/management/serve.py','tools/management/build_map_review.py','tools/management/ui/map/map.js','tools/management/domains/map_assets/editor.py','tools/management/ui/gradio/theme.css'):
            self.assertFalse(serve.can_reuse_review_directory(current_safe_paths+[str(current_workflow_root/current_unsafe_path)]))
        self.assertFalse(serve.can_reuse_review_directory([]))

    def test_assistant_bundle_and_catalog_reuse_prepared_directory(self):
        root=Path(serve.__file__).resolve().parent
        changed=[root.parents[1]/'gui/dist/app.js',root.parents[1]/'gui/index.html',root.parents[1]/'gui/style.css',root/'common/management_catalog.py']
        self.assertTrue(serve.can_reuse_review_directory(changed))
        self.assertFalse(serve.can_reuse_review_directory([*changed,root/'build_map_review.py']))

    def test_burst_waits_until_latest_change_settles(self):
        current_first_snapshot=(('a',1,2),)
        current_last_snapshot=(('a',2,2),)
        with patch.object(serve.time,'monotonic',side_effect=[0,0,.5,.5,1,1.5]),patch.object(serve.time,'sleep'),patch.object(serve,'snapshot_review_watch_paths',side_effect=[current_last_snapshot,current_last_snapshot,current_last_snapshot]):
            self.assertEqual(serve.settle_review_watch_snapshot([],current_first_snapshot),current_last_snapshot)

    def test_reuse_skips_all_preparation_and_missing_root_fails(self):
        with tempfile.TemporaryDirectory() as current_temporary_name:
            current_record_path=Path(current_temporary_name)/'prepared.json'
            current_record_path.write_text(json.dumps({'root':current_temporary_name}))
            with patch.dict(os.environ,{'SLIME_REVIEW_REUSE_PREPARED':'1','SLIME_REVIEW_PREPARED_RECORD':str(current_record_path)}),patch.object(serve,'prepare_review_directory') as current_prepare_mock:
                self.assertEqual(serve.prepare_watched_review_directory(None)[:2],(Path(current_temporary_name),'reuse'))
                current_prepare_mock.assert_not_called()
                current_record_path.write_text(json.dumps({'root':current_temporary_name+'/missing'}))
                with self.assertRaisesRegex(ValueError,'폴더가 없습니다'):serve.prepare_watched_review_directory(None)

    def test_full_preparation_when_reuse_is_disabled(self):
        with patch.dict(os.environ,{'SLIME_REVIEW_REUSE_PREPARED':'0'}),patch.object(serve,'prepare_review_directory',return_value=Path('/tmp/example')) as current_prepare_mock:
            self.assertEqual(serve.prepare_watched_review_directory(None)[:2],(Path('/tmp/example'),'build'))
            current_prepare_mock.assert_called_once_with(None)
