"""시작 메뉴가 맵 본문 로드를 유발하지 않는지 검증한다."""
import os
import unittest
from unittest.mock import patch
from tools.review.common.map_asset_sources import load_review_map_menu
from tools.review.common.game_render_metrics import load_game_city_export_sources


class ReviewStartupMenuTests(unittest.TestCase):
    def test_database_menu_reads_asset_snapshot_without_database(self):
        from tools.review.common.map_asset_sources import CURRENT_REVIEW_ASSET_SOURCE
        def build_checked_menu_records():
            self.assertTrue(CURRENT_REVIEW_ASSET_SOURCE.get())
            return [{'kind':'town'},{'kind':'field'}]
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'tools.review.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('DB 조회 금지')),patch(
                'tools.review.common.map_asset_sources.build_registered_map_menu',side_effect=build_checked_menu_records),patch(
                'tools.review.common.map_asset_sources.load_registered_map_review',side_effect=AssertionError('본문 조회 금지')):
            current_menu_rows=load_review_map_menu()
            self.assertEqual([current_menu_row['kind'] for current_menu_row in current_menu_rows],['town','field'])
            self.assertFalse(CURRENT_REVIEW_ASSET_SOURCE.get())

    def test_render_metrics_do_not_load_map_bodies(self):
        with patch('tools.review.common.map_asset_sources.load_registered_map_review',side_effect=AssertionError('본문 조회 금지')):
            self.assertGreater(load_game_city_export_sources()[0],0)
