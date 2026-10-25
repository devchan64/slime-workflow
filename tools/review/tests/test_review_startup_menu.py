"""시작 메뉴가 맵 본문 로드를 유발하지 않는지 검증한다."""
import os
import unittest
from unittest.mock import patch
from tools.review.common.map_asset_sources import load_review_map_menu
from tools.review.common.game_render_metrics import load_game_city_export_sources


class ReviewStartupMenuTests(unittest.TestCase):
    def test_database_menu_uses_single_index_request(self):
        current_documents={'city_layouts/index.yaml':{'data':{'includes':{'layouts':{'town':'town.yaml'}}}},
            'field_tiles/index.yaml':{'data':{'includes':{'maps':{'field':'field.yaml'}}}},
            'map_names/town.yaml':{'data':{'ko':'마을'}},'map_names/field.yaml':{'data':{'ko':'필드'}}}
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch('tools.review.domains.map_assets.database_client.execute_content_api_request',return_value={'documents':current_documents}) as current_api_mock,patch('tools.review.common.map_asset_sources.load_registered_map_review',side_effect=AssertionError('본문 조회 금지')):
            current_menu_rows=load_review_map_menu()
            self.assertEqual([current_menu_row['kind'] for current_menu_row in current_menu_rows],['town','field'])
            current_api_mock.assert_called_once_with('GET','/internal/v1/content/review-bundle')
            del current_documents['map_names/town.yaml']
            with self.assertRaises(KeyError):load_review_map_menu()

    def test_render_metrics_do_not_load_map_bodies(self):
        with patch('tools.review.common.map_asset_sources.load_registered_map_review',side_effect=AssertionError('본문 조회 금지')):
            self.assertGreater(load_game_city_export_sources()[0],0)
