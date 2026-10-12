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

    def test_identity_reference_roundtrip(self):
        from generators.vace.timeline import verify_timeline_request,load_identity_references
        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
        import json
        current_payload_record=self.build_valid_payload()
        current_identity_buffer=io.BytesIO()
        Image.new('RGB',(16,16),'blue').save(current_identity_buffer,format='PNG')
        current_payload_record['images'].append(base64.b64encode(current_identity_buffer.getvalue()).decode())
        current_payload_record['identity_reference_count']=1
        current_validated_record=validate_timeline_request(current_payload_record)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)
            current_saved_record={**{k:v for k,v in current_validated_record.items() if k!='images'},**save_three_reference_inputs(current_job_root,current_validated_record)}
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            verify_timeline_request(current_job_root)
            self.assertEqual(load_identity_references(current_job_root,current_saved_record)[0].getpixel((0,0)),(0,0,255))
            self.assertEqual(assemble_timeline_inputs(current_job_root,current_saved_record)[0][2].getpixel((256,256)),(255,0,0))
            (current_job_root/current_saved_record['references'][-1]).write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_timeline_request(current_job_root)

    def test_identity_count_rejected(self):
        for current_bad_count in (True,2,-1,1.0):
            current_payload_record=self.build_valid_payload()
            current_payload_record['identity_reference_count']=current_bad_count
            with self.assertRaises(ValueError):validate_timeline_request(current_payload_record)
        current_payload_record=self.build_valid_payload()
        current_payload_record['identity_reference_count']=1
        with self.assertRaises(ValueError):validate_timeline_request(current_payload_record)
