import unittest

from tools.review.ui.gradio.writer_agent_app import build_writer_agent_interface, create_writer_agent_loader, read_writer_agent_markup


class WriterAgentGradioTest(unittest.TestCase):
    def test_uses_gradio_custom_component(self):
        interface_blocks_value = build_writer_agent_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('writer-agent-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))

    def test_loader_targets_writer_agent_service(self):
        loader_script_text=create_writer_agent_loader(8770)
        self.assertIn("writerAgentServerBase='http://127.0.0.1:8770'",loader_script_text)
        self.assertIn("+'/writer-agent/manager.js'",loader_script_text)
        self.assertIn('id="apply"',read_writer_agent_markup())


if __name__ == '__main__':
    unittest.main()
