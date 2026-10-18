import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import yaml
from tools.review.domains.map_assets.resize import resize_registered_image


class MapAssetResizeTests(unittest.TestCase):
    def test_resize_and_reject_stale_source(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_temp_root=Path(current_temp_name)
            current_asset_root=current_temp_root/'assets-repo'
            current_frontend_root=current_temp_root/'frontend'
            current_image_path=current_asset_root/'assets/billboards/sample.png'
            current_image_path.parent.mkdir(parents=True)
            current_frontend_root.mkdir()
            Image.new('RGBA',(512,256),(50,100,150,128)).save(current_image_path)
            current_source_hash=hashlib.sha256(current_image_path.read_bytes()).hexdigest()
            current_source_record={'managementId':'sample','version':'v1','path':'assets/billboards/sample.png','sha256':current_source_hash,'width':512,'height':256,'source':{}}
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':[current_source_record]},sort_keys=False))
            for current_lock_name in ('map-assets.lock.yaml','sprite-assets.lock.yaml'):
                (current_frontend_root/current_lock_name).write_text('sha256: '+current_source_hash+'\n')
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root),'SLIME_FRONTEND_ROOT':str(current_frontend_root)}),patch('tools.review.domains.map_assets.resize.RESIZE_STORAGE_DIRECTORY',current_temp_root/'history'):
                current_request_payload={'path':current_source_record['path'],'sha256':current_source_hash,'size':128}
                current_result_record=resize_registered_image(current_request_payload)
                self.assertEqual(current_result_record['size'],[128,64])
                with Image.open(current_image_path) as current_result_image:
                    self.assertEqual(current_result_image.size,(128,64))
                    self.assertEqual(current_result_image.mode,'RGBA')
                self.assertIn(current_result_record['sha256'],(current_frontend_root/'sprite-assets.lock.yaml').read_text())
                self.assertEqual(yaml.safe_load((current_asset_root/'asset-registry.yaml').read_text())['assets'][0]['width'],128)
                with self.assertRaisesRegex(ValueError,'原本|원본이 변경'):
                    resize_registered_image(current_request_payload)
                with self.assertRaisesRegex(ValueError,'확대'):
                    resize_registered_image({**current_request_payload,'sha256':current_result_record['sha256'],'size':512})
                with self.assertRaises(ValueError):
                    resize_registered_image({**current_request_payload,'path':'assets/billboards/../../secret.png'})
