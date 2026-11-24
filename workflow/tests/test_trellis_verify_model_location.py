import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.trellis_experiment import verify_model


class TrellisVerifyLocationTest(unittest.TestCase):
    def test_manifest_is_written_to_resolved_installation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'weight').write_bytes(b'abc')
            response = {'sha': verify_model.REVISION, 'siblings': [
                {'rfilename': 'weight', 'size': 3, 'lfs': {'sha256': hashlib.sha256(b'abc').hexdigest()}}]}
            with patch.object(verify_model, 'resolve_trellis_model', return_value=root), \
                    patch.object(verify_model, 'urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
                verify_model.main()
            self.assertEqual(json.loads((root / 'verified-manifest.json').read_text())['files'][0]['path'], 'weight')
