"""도메인 이동 이후 정식 경로·호환 진입점·UI 파일 계약."""
import importlib
import unittest
from tools.review.ui_assets import REVIEW_UI_FILES, resolve_review_ui_asset

class DomainLayoutTests(unittest.TestCase):
    def test_registered_ui_files_exist(self):
        for asset_file_name in REVIEW_UI_FILES:
            self.assertTrue(resolve_review_ui_asset(asset_file_name).is_file(),asset_file_name)
        with self.assertRaises(ValueError):resolve_review_ui_asset('../serve.py')

    def test_legacy_modules_share_canonical_state(self):
        for original_module_name,domain_module_name in [('character_animation_jobs','domains.character_animation.character_animation_jobs'),('momask_jobs','domains.momask.momask_jobs'),('management_gateway','common.management_gateway')]:
            self.assertIs(importlib.import_module('tools.review.'+original_module_name),importlib.import_module('tools.review.'+domain_module_name))

    def test_record_storage_is_shared(self):
        from tools.review.common.generation_records import write_record_atomically
        from tools.review.domains.character_animation import character_animation_jobs
        from tools.review.domains.momask import momask_jobs
        self.assertIs(character_animation_jobs.write_record_atomically,write_record_atomically)
        self.assertIs(momask_jobs.write_record_atomically,write_record_atomically)
