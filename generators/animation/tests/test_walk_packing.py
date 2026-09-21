"""게임용 패킹의 셀 보존·누락 거부 계약을 확인한다."""
from pathlib import Path
import tempfile
import json
import hashlib
import unittest
from PIL import Image
from generators.animation.pack_walk_sheets import pack_walk_frames


class WalkSheetPackingTests(unittest.TestCase):
    def test_all_cells_preserve_rgba(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            source_cell_root=temporary_root_path/'cells'
            source_cell_root.mkdir()
            source_frame_records=[]
            for direction_index_value,direction_key_name in enumerate(('down_left','down_right','up_left','up_right')):
                for frame_index_value in range(8):
                    frame_identifier_value=f'{direction_key_name}.{frame_index_value}'
                    source_cell_image=Image.new('RGBA',(384,384))
                    source_cell_image.putpixel((frame_index_value+1,direction_index_value+1),(direction_index_value*40,frame_index_value*20,180,255))
                    source_cell_path=source_cell_root/(frame_identifier_value+'.png')
                    source_cell_image.save(source_cell_path)
                    source_frame_records.append({'frameId':frame_identifier_value,'anchor':{'x':192,'y':336},'sha256':hashlib.sha256(source_cell_path.read_bytes()).hexdigest()})
            (source_cell_root/'frames.json').write_text(json.dumps({'frames':source_frame_records,'clips':[],'normalization':{'fixture':True}}))
            packed_output_root=temporary_root_path/'packed'
            pack_walk_frames(source_cell_root,packed_output_root)
            output_frame_records=json.loads((packed_output_root/'walk.animation.json').read_text())['frames']
            self.assertEqual(len(output_frame_records),32)
            for output_frame_record in output_frame_records:
                frame_rectangle_values=output_frame_record['rect']
                packed_sheet_image=Image.open(packed_output_root/output_frame_record['texture'])
                self.assertEqual(packed_sheet_image.size,(1536,1536))
                recovered_cell_image=packed_sheet_image.crop((frame_rectangle_values['x'],frame_rectangle_values['y'],frame_rectangle_values['x']+384,frame_rectangle_values['y']+384))
                source_cell_image=Image.open(source_cell_root/(output_frame_record['frameId']+'.png'))
                self.assertEqual(recovered_cell_image.tobytes(),source_cell_image.tobytes())

    def test_missing_frames_fail(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path=Path(temporary_root_name)
            (temporary_root_path/'frames.json').write_text(json.dumps({'frames':[],'clips':[],'normalization':{}}))
            with self.assertRaisesRegex(ValueError,'중복·누락'):
                pack_walk_frames(temporary_root_path,temporary_root_path/'out')
