"""Gradio 페이지의 공용 관리 메뉴 경로를 검증한다."""
import unittest

from tools.review.common.gradio_navigation import build_management_navigation


class GradioNavigationTests(unittest.TestCase):
    def test_navigation_uses_same_port_relative_paths(self):
        navigation_html_text=build_management_navigation('/momask-generator/')
        self.assertIn('href="/management/"',navigation_html_text)
        self.assertIn('href="/character-animation/"',navigation_html_text)
        self.assertNotIn('8871',navigation_html_text)
        self.assertIn('aria-current="page"',navigation_html_text)
