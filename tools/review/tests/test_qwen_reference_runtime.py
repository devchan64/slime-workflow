"""추론 실행기의 일반 참조와 AnyPose 입력 계약을 검증한다."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from generators.animation.qwen_pose.runtime import load_generation_reference_image

class QwenReferenceRuntimeTests(unittest.TestCase):
    def test_arbitrary_reference_preserves_dimensions_and_pixels(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_image_path=Path(temporary_directory_name)/'reference.png'
            for current_image_size in ((464,455),(256,256),(512,512)):
                Image.new('RGB',current_image_size,(20,40,60)).save(current_image_path)
                current_loaded_image=load_generation_reference_image(current_image_path,False)
                self.assertEqual(current_loaded_image.size,current_image_size)
                self.assertEqual(current_loaded_image.getpixel((0,0)),(20,40,60))

    def test_anypose_still_requires_fixed_dimensions(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_image_path=Path(temporary_directory_name)/'reference.png'
            Image.new('RGB',(256,256)).save(current_image_path)
            with self.assertRaisesRegex(ValueError,'AnyPose 입력'):
                load_generation_reference_image(current_image_path,True)
            Image.new('RGB',(512,512)).save(current_image_path)
            self.assertEqual(load_generation_reference_image(current_image_path,True).size,(512,512))

    def test_transparent_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_image_path=Path(temporary_directory_name)/'reference.png'
            Image.new('RGBA',(256,256),(0,0,0,0)).save(current_image_path)
            with self.assertRaisesRegex(ValueError,'투명 참조'):
                load_generation_reference_image(current_image_path,False)
