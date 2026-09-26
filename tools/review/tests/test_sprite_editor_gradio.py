"""스프라이트 편집기 Gradio 연결을 검증한다."""
import unittest

from tools.review.ui.gradio.sprite_editor_app import build_sprite_editor_interface


class SpriteEditorGradioTests(unittest.TestCase):
    def test_interface_keeps_browser_editor_route(self):
        interface_blocks_value=build_sprite_editor_interface(8770)
        configuration_record_value=interface_blocks_value.get_config_file()
        self.assertIn('/character-animation/sprite-editor',str(configuration_record_value))
