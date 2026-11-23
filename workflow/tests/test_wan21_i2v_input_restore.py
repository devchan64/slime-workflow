import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from workflow.domains.wan21_i2v.input_restore import load_saved_input


class Wan21InputRestoreTests(unittest.TestCase):
    def test_restores_validated_input_and_rejects_changed_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = '2026-11-23_16-58-20-3599c3b1'
            target = root / job
            target.mkdir()
            output = io.BytesIO()
            Image.new('RGB', (832,480), 'white').save(output, format='PNG')
            image = output.getvalue()
            (target/'reference-1.png').write_bytes(image)
            saved = {'action':'generate','prompt':'one slash','negative_prompt':'','width':832,'height':480,'frames':21,'steps':4,'seed':42,'flow_shift':5,'guidance_scale':1,'acceleration':True,'action_lora':True,'action_variant':'fight','action_strength':1,'tag':'wan21-i2v','references':['reference-1.png'],'reference_snapshots':[{'path':'reference-1.png','order':1,'bytes':len(image),'sha256':hashlib.sha256(image).hexdigest()}]}
            (target/'request.json').write_text(json.dumps(saved))
            result = load_saved_input(root, job)
            self.assertEqual(result['id'], job)
            self.assertEqual(base64.b64decode(result['request']['images'][0]), image)
            self.assertEqual(result['request']['prompt'], 'one slash')
            (target/'reference-1.png').write_bytes(image+b'changed')
            with self.assertRaises(ValueError):
                load_saved_input(root, job)
            saved['steps'] = 101
            (target/'reference-1.png').write_bytes(image)
            (target/'request.json').write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                load_saved_input(root, job)
