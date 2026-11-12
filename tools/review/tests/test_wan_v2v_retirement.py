"""폐기한 RGB V2V가 관리도구에 다시 등록되지 않는지 확인한다."""
import unittest

from tools.review.common.management_asgi import MANAGEMENT_INTERFACE_BUILDERS
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_SERVICE_ROUTES
from tools.review.ui.gradio.management_menu_app import NATIVE_MANAGEMENT_APPLICATIONS


class RetiredVideoGeneratorTests(unittest.TestCase):
    def test_retired_generator_is_not_registered(self):
        self.assertNotIn('wan22-v2v', MANAGEMENT_SERVICE_COMMANDS)
        self.assertNotIn('wan22-v2v', MANAGEMENT_SERVICE_ROUTES)
        self.assertNotIn('wan22-v2v-generator', MANAGEMENT_INTERFACE_BUILDERS)
        self.assertNotIn('wan22-v2v-generator', NATIVE_MANAGEMENT_APPLICATIONS)


if __name__ == '__main__':
    unittest.main()
