"""배치 항목 삭제 시 프레임과 마스크의 대응을 검증한다."""
import unittest
from tools.review.ui.gradio.vace_timeline_app import remove_timeline_image


class VaceTimelineEditorTests(unittest.TestCase):
    def test_remove_middle_preserves_frame_numbers_and_masks(self):
        self.assertEqual(remove_timeline_image(['a','b','c'],[[1,False],[13,True],[35,False]],[(1,'b')]),
                         (['a','c'],[[1,False],[35,False]],['a','c']))

    def test_remove_last_clears_inputs(self):
        self.assertEqual(remove_timeline_image(['a'],[[1,True]],[(0,'a')]),([],[],None))

    def test_stale_selection_is_rejected(self):
        with self.assertRaises(Exception):
            remove_timeline_image(['b'],[[18,True]],[(0,'a')])

    def test_remove_all_items(self):
        self.assertEqual(remove_timeline_image(['a','b'],[[1,True],[18,False]],[(0,'a'),(1,'b')]),([],[],None))
