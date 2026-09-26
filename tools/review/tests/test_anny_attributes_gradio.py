import unittest

from tools.review.ui.gradio.anny_attributes_app import build_anny_attribute_interface


class AnnyAttributesGradioTest(unittest.TestCase):
    def test_embeds_existing_attribute_renderer(self):
        interface_blocks_value = build_anny_attribute_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('/anny-attributes/embedded/', str(configuration_value))


if __name__ == '__main__':
    unittest.main()
