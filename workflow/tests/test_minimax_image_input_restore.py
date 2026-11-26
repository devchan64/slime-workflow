"""Saved image input is read only and must retain verified reference bytes."""
import base64
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from generators.minimax_h3_image.contracts import validate_request
from workflow.domains.image.three_reference_generation import save_three_reference_inputs
from workflow.domains.minimax_h3_image.input_restore import load_saved_input


class MiniMaxImageRestoreTests(unittest.TestCase):
    def test_restore_two_references_and_downscale_in_order(self):
        with tempfile.TemporaryDirectory() as temp:
            job = '2026-11-26_12-00-00-12345678'
            directory = Path(temp) / job
            directory.mkdir()
            images = []
            for color in ('red', 'blue'):
                data = io.BytesIO()
                Image.new('RGB', (2, 2), color).save(data, format='PNG')
                images.append(base64.b64encode(data.getvalue()).decode('ascii'))
            request = {'action':'generate', 'prompt':'two references', 'images':images,
                       'width':1664, 'height':960, 'steps':6, 'seed':42,
                       'output_size':{'width':832, 'height':480}}
            saved = save_three_reference_inputs(directory, validate_request(request))
            (directory / 'request.json').write_text(json.dumps(saved))
            self.assertEqual(load_saved_input(temp, job)['request'], request)

    def test_restore_and_reject_modified_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            job = '2026-11-26_12-00-00-12345678'
            directory = Path(temp) / job
            directory.mkdir()
            image = io.BytesIO()
            Image.new('RGB', (2, 2), 'red').save(image, format='PNG')
            encoded = base64.b64encode(image.getvalue()).decode('ascii')
            request = {'action':'generate', 'prompt':'red house', 'images':[encoded], 'width':832,
                       'height':480, 'steps':6, 'seed':42}
            saved = save_three_reference_inputs(directory, validate_request(request))
            (directory / 'request.json').write_text(json.dumps(saved))
            self.assertEqual(load_saved_input(temp, job), {'id':job, 'request':request})
            (directory / 'reference-1.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                load_saved_input(temp, job)

    def test_restore_without_reference_and_reject_wrong_id(self):
        with tempfile.TemporaryDirectory() as temp:
            job = '2026-11-26_12-00-00-12345678'
            directory = Path(temp) / job
            directory.mkdir()
            request = {'action':'generate', 'prompt':'landscape', 'images':[], 'width':1024,
                       'height':1024, 'steps':6, 'seed':2}
            saved = save_three_reference_inputs(directory, validate_request(request))
            (directory / 'request.json').write_text(json.dumps(saved))
            self.assertEqual(load_saved_input(temp, job)['request'], request)
            with self.assertRaises(ValueError):
                load_saved_input(temp, '../request.json')

    def test_reject_reference_symlink_and_changed_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            job = '2026-11-26_12-00-00-12345678'
            directory = Path(temp) / job
            directory.mkdir()
            image = io.BytesIO()
            Image.new('RGB', (2, 2), 'red').save(image, format='PNG')
            encoded = base64.b64encode(image.getvalue()).decode('ascii')
            request = {'action':'generate', 'prompt':'red house', 'images':[encoded], 'width':832,
                       'height':480, 'steps':6, 'seed':42}
            saved = save_three_reference_inputs(directory, validate_request(request))
            metadata = directory / 'request.json'
            metadata.write_text(json.dumps(saved))
            reference = directory / 'reference-1.png'
            reference.unlink()
            outside = Path(temp) / 'outside.png'
            outside.write_bytes(image.getvalue())
            reference.symlink_to(outside)
            with self.assertRaises((ValueError, OSError)):
                load_saved_input(temp, job)
            reference.unlink()
            reference.write_bytes(image.getvalue())
            saved['user_prompt'] = 'different prompt'
            metadata.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                load_saved_input(temp, job)


if __name__ == '__main__':
    unittest.main()
