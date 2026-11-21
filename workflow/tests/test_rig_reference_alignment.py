"""입력 리그 정렬은 캐릭터 원본을 변경하지 않는다."""
import unittest
from PIL import Image,ImageDraw
from generators.animation.align_rig_reference import align_rig_reference

class RigReferenceAlignmentTests(unittest.TestCase):
    def test_bounds_and_original_are_preserved(self):
        character_image_value=Image.new('RGB',(512,512),'white')
        ImageDraw.Draw(character_image_value).rectangle((100,50,299,449),fill='red')
        pose_image_value=Image.new('RGB',(512,512),'black')
        ImageDraw.Draw(pose_image_value).rectangle((200,100,299,299),fill='white')
        original_image_bytes=character_image_value.tobytes()
        aligned_image_value,alignment_record_value=align_rig_reference(character_image_value,pose_image_value)
        self.assertEqual(aligned_image_value.getbbox(),(100,50,300,450))
        self.assertEqual(alignment_record_value['scale_x'],2)
        self.assertEqual(alignment_record_value['scale_y'],2)
        self.assertEqual(character_image_value.tobytes(),original_image_bytes)
    def test_empty_foreground_rejected(self):
        with self.assertRaises(ValueError):align_rig_reference(Image.new('RGB',(512,512),'white'),Image.new('RGB',(512,512),'black'))
