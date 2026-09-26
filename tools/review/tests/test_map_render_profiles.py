"""맵 검수가 렌더링 프로필을 사용하는지 검증한다."""
from pathlib import Path
import unittest

from tools.review.build_map_review import load_map_render_profiles


WORKFLOW_ROOT = Path(__file__).resolve().parents[3]


class MapRenderProfileTests(unittest.TestCase):
    def test_building_review_templates_use_shared_profile_values(self):
        render_profile_values = load_map_render_profiles()
        self.assertEqual(render_profile_values['wall_height'], 80)

        map_review_source = (WORKFLOW_ROOT / 'assets/world/isloon/map-review.html').read_text(encoding='utf-8')
        self.assertNotIn('VOLUME_FLOOR_HEIGHT_PIXELS', map_review_source)
        self.assertIn('currentVolumeRenderProfile.wall_height', map_review_source)
