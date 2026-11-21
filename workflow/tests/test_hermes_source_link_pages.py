"""대화의 원 서비스 링크를 받는 공용 생성기 화면 구성을 확인한다."""
import asyncio
import unittest

from workflow.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES
from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
from gui.ui.shared.audio_generator_page import build_music_interface
from gui.ui.shared.flux_image_page import build_flux_image_page


class HermesSourceLinkPageTests(unittest.TestCase):
    def test_flux_and_audio_pages_receive_linked_job(self):
        async def inspect_linked_source_pages():
            for current_service_name in (*FLUX_IMAGE_PROFILE_RECORDS,*HERMES_AUDIO_SERVICES):
                with self.subTest(service=current_service_name):
                    if current_service_name in FLUX_IMAGE_PROFILE_RECORDS:
                        current_page_value=build_flux_image_page(current_service_name,'http://127.0.0.1:19999',19999)
                    else:
                        current_page_value=build_music_interface(current_service_name,'http://127.0.0.1:19999')
                    current_page_config=current_page_value.config
                    self.assertTrue(any("searchParams.get('job')" in str(current_dependency.get('js','')) for current_dependency in current_page_config['dependencies']))
                    self.assertTrue(any(current_component['props'].get('value')=='전달된 작업을 이력에서 찾기' for current_component in current_page_config['components']))
        asyncio.run(inspect_linked_source_pages())
