import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from tools.review.domains.map_assets.anchors import save_map_sprite_anchor

class MapAssetAnchorTests(unittest.TestCase):
    def test_anchor_save_preserves_placement_and_rejects_stale(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_temp_root=Path(current_temp_name)
            current_asset_root=current_temp_root/'slime-assets'
            current_map_path=current_asset_root/'assets/maps/city_layouts/test.yaml'
            current_map_path.parent.mkdir(parents=True)
            current_object_record={'id':'sample','textureKey':'bin','position':{'column':2,'row':3},'displayHeight':64,'anchorX':0.5,'anchorY':1}
            current_map_path.write_text(yaml.safe_dump({'data':{'objects':[current_object_record]}}))
            current_map_hash=hashlib.sha256(current_map_path.read_bytes()).hexdigest()
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':[{'managementId':'test','version':'v1','path':'assets/maps/city_layouts/test.yaml','source':{},'sha256':current_map_hash}]}))
            current_backend_root=current_temp_root/'slime-backend';current_backend_root.mkdir()
            (current_backend_root/'map-data.lock.yaml').write_text('sha256: '+current_map_hash)
            current_request_payload={'map':'test','kind':'town','texture':'bin','anchorX':0.6,'anchorY':0.9,'expected':[{'id':'sample','anchorX':0.5,'anchorY':1}]}
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}):
                self.assertEqual(save_map_sprite_anchor(current_request_payload)['count'],1)
                current_saved_record=yaml.safe_load(current_map_path.read_text())['data']['objects'][0]
                self.assertEqual(current_saved_record['displayHeight'],64)
                self.assertEqual(current_saved_record['position'],current_object_record['position'])
                self.assertEqual(current_saved_record['anchorY'],0.9)
                with self.assertRaises(ValueError):save_map_sprite_anchor(current_request_payload)
                with self.assertRaises(ValueError):save_map_sprite_anchor({**current_request_payload,'anchorX':2})

                current_layout_request={**current_request_payload,'expected':[{'id':'sample','anchorX':0.6,'anchorY':0.9,'groundFootprintColumns':1,'groundFootprintRows':1,'displayHeight':64}],'layout':{'groundFootprintColumns':2,'groundFootprintRows':1,'displayHeight':140}}
                self.assertEqual(save_map_sprite_anchor(current_layout_request)['count'],1)
                current_layout_saved=yaml.safe_load(current_map_path.read_text())['data']['objects'][0]
                self.assertEqual(current_layout_saved['groundFootprintColumns'],2)
                self.assertEqual(current_layout_saved['displayHeight'],140)
                self.assertEqual(current_layout_saved['position'],current_object_record['position'])
