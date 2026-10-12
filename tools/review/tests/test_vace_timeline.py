"""희소 프레임 위치·수정 마스크·저장 무결성 검증."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from generators.vace.timeline import validate_timeline_request,assemble_timeline_inputs


class VaceTimelineContractTests(unittest.TestCase):
    def build_valid_payload(self):
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(16,16),'red').save(current_image_buffer,format='PNG')
        return dict(action='generate',prompt='전신 걷기',images=[base64.b64encode(current_image_buffer.getvalue()).decode()],frame_entries=[{'frame':2,'editable':True}],frames=5,width=512,height=512,seed=42)

    def test_sparse_editable_frame(self):
        current_request_record=validate_timeline_request(self.build_valid_payload())
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_job_root=Path(current_temporary_directory)
            (current_job_root/'reference-1.png').write_bytes(base64.b64decode(current_request_record['images'][0]))
            current_request_record['references']=['reference-1.png']
            current_video_frames,current_mask_frames=assemble_timeline_inputs(current_job_root,current_request_record)
            self.assertEqual(current_video_frames[0].getpixel((256,256)),(127,127,127))
            self.assertEqual(current_video_frames[2].getpixel((256,256)),(255,0,0))
            self.assertTrue(all(current_mask_image.getextrema()==((255,255),)*3 for current_mask_image in current_mask_frames))
            current_request_record['frame_entries'][0]['editable']=False
            self.assertEqual(assemble_timeline_inputs(current_job_root,current_request_record)[1][2].getpixel((0,0)),(0,0,0))

    def test_invalid_frame_rejected(self):
        for current_bad_frame in [-1,5,True,1.5]:
            current_payload_record=self.build_valid_payload()
            current_payload_record['frame_entries'][0]['frame']=current_bad_frame
            with self.assertRaises(ValueError):validate_timeline_request(current_payload_record)

    def test_duplicate_frame_rejected(self):
        current_payload_record=self.build_valid_payload()
        current_payload_record['images']*=2
        current_payload_record['frame_entries']*=2
        with self.assertRaises(ValueError):validate_timeline_request(current_payload_record)
