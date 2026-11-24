import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch

from PIL import Image
from workflow.domains.wan_i2v.input_restore import load_saved_input


class WanI2VInputRestoreTests(unittest.TestCase):
    def test_valid_input_and_invalid_reference_or_retired_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); job='2026-11-23_16-58-20-3599c3b1'; target=root/job; target.mkdir()
            output=io.BytesIO(); Image.new('RGB',(832,480),'white').save(output,format='PNG'); image=output.getvalue()
            (target/'reference-1.png').write_bytes(image)
            saved={'action':'generate','prompt':'motion','negative_prompt':'','width':832,'height':480,'frames':21,'steps':4,'seed':42,'flow_shift':5,'guidance_scale':1,'lora_mode':'lightning','kungfu_strength':1,'tag':'wan22-i2v','references':['reference-1.png'],'reference_snapshots':[{'path':'reference-1.png','order':1,'bytes':len(image),'sha256':hashlib.sha256(image).hexdigest()}]}
            (target/'request.json').write_text(json.dumps(saved))
            self.assertEqual(load_saved_input(root,job)['request']['prompt'],'motion')
            from fastapi.testclient import TestClient
            from workflow.common.management_asgi import build_management_application
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with patch('generators.wan_i2v.contracts.JOB_STORAGE',root), TestClient(app) as client:
                response=client.get(f'/management/assistant/wan22-i2v-input/{job}')
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertEqual(response.json()['request']['lora_mode'],'lightning')
            (target/'reference-1.png').write_bytes(image+b'changed')
            with self.assertRaises(ValueError): load_saved_input(root,job)
            with patch('generators.wan_i2v.contracts.JOB_STORAGE',root), TestClient(app) as client:
                self.assertEqual(client.get(f'/management/assistant/wan22-i2v-input/{job}').status_code,422)
            (target/'reference-1.png').write_bytes(image); saved['lora_mode']='kungfu'
            (target/'request.json').write_text(json.dumps(saved))
            with self.assertRaises(ValueError): load_saved_input(root,job)
