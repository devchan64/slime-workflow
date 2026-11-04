"""공용 메뉴가 맵 콘텐츠 API와 독립적으로 로드되는지 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.ui.gradio.management_menu_app import load_manager_page_records

class ManagementMenuOfflineTests(unittest.TestCase):
    def test_map_menu_preserves_registered_categories_without_network(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_menu_path=Path(current_temp_directory)/'menu.json'
            current_menu_path.write_text(json.dumps({'pages':[{'id':'map-review-test','label':'검증 도시 · 도시맵 검수','path':'/review','category':'town-map-review','description':'검증'}]}))
            with patch('urllib.request.urlopen',side_effect=AssertionError('메뉴에서 네트워크 호출 금지')):
                current_page_records=load_manager_page_records(current_menu_path,current_animation_catalog=True)
            current_map_record=next(current_page_record for current_page_record in current_page_records if current_page_record['id']=='map-review-test')
            self.assertEqual(current_map_record['category'],'map-review')
