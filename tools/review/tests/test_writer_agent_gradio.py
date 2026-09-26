import unittest

from tools.review.ui.gradio.writer_agent_app import build_writer_agent_interface


class WriterAgentGradioTest(unittest.TestCase):
    def test_embeds_existing_writer_agent_manager(self):
        interface_blocks_value = build_writer_agent_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('/writer-agent/embedded/', str(configuration_value))


if __name__ == '__main__':
    unittest.main()
