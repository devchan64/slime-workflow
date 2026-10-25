"""크롭 확인·불변 파일 게시·DB 응답 유실 재시도 검증."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from tools.review.domains.map_assets import database_images


class DatabaseImageTests(unittest.TestCase):
    def test_published_image_checks_registered_hash_and_path(self):
        from tools.review.common.map_asset_http import read_map_asset_response
        with TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)
            current_image_path=current_asset_root/'image.png'
            Image.new('RGBA',(2,2),'green').save(current_image_path)
            current_image_bytes=current_image_path.read_bytes()
            current_image_digest=hashlib.sha256(current_image_bytes).hexdigest()
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(
                    database_images,'execute_content_api_request',return_value={'path':'image.png'}) as current_api_mock:
                self.assertEqual(read_map_asset_response('/management/map-assets/database-images/'+current_image_digest),(current_image_bytes,'image/png'))
                current_image_path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'해시'):
                    database_images.read_database_published_image(current_image_digest)
                current_api_mock.return_value={'path':'../outside.png'}
                with self.assertRaisesRegex(ValueError,'경로'):
                    database_images.read_database_published_image(current_image_digest)
                with self.assertRaisesRegex(ValueError,'형식'):
                    database_images.read_database_published_image('../image.png')

    def test_crop_preserves_source_and_retries_same_database_request(self):
        with TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)
            current_source_path=current_asset_root/'assets/billboards/test.png'
            current_source_path.parent.mkdir(parents=True)
            current_source_image=Image.new('RGBA',(100,100))
            ImageDraw.Draw(current_source_image).rectangle((20,10,59,59),fill='green')
            current_source_image.save(current_source_path)
            current_original_bytes=current_source_path.read_bytes()
            current_asset_record={'assetId':'test','revision':2,'retired':False,'metadata':{},
                'properties':{'anchorX':0,'anchorY':0,'displayHeight':100,'billboardAnchorMode':'tile-intersection','groundFootprintColumns':1,'groundFootprintRows':1,'billboardBlocksMovement':False,'shadowOffsetColumn':0,'shadowOffsetRow':0,'shadowScaleX':1,'shadowScaleY':1,'shadowCoordinateVersion':2,'shadowSizeVersion':2},
                'image':{'imageId':'test','version':'v1','path':'assets/billboards/test.png','publishedPath':'/registered-assets/assets/billboards/test.png',
                    'sha256':hashlib.sha256(current_original_bytes).hexdigest(),'width':100,'height':100}}
            current_request_record={'texture':'test','revision':json.dumps({'test':2})}
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(database_images,'EDITOR_STORAGE_DIRECTORY',current_asset_root/'pending'),patch.object(database_images,'execute_content_api_request') as current_api_mock:
                current_api_mock.return_value=current_asset_record
                current_preview_record=database_images.preview_database_image_crop(current_request_record)
                self.assertEqual(current_preview_record['after'],[40,50])
                self.assertEqual(current_preview_record['properties']['displayHeight'],50)
                self.assertEqual(current_preview_record['properties']['anchorY'],-0.5)
                current_confirm_record={**current_request_record,'token':current_preview_record['token']}
                current_api_mock.side_effect=OSError('응답 유실')
                with self.assertRaises(OSError):database_images.save_database_image_change(current_confirm_record)
                current_first_request=current_api_mock.call_args
                self.assertEqual(current_source_path.read_bytes(),current_original_bytes)
                self.assertEqual(len(list((current_asset_root/'assets/billboards/versions').glob('*.png'))),1)
                current_api_mock.side_effect=None
                current_api_mock.return_value={'saved':True}
                database_images.save_database_image_change(current_confirm_record)
                self.assertEqual(current_api_mock.call_args,current_first_request)
                with self.assertRaisesRegex(ValueError,'대상이 변경'):
                    database_images.save_database_image_change({**current_confirm_record,'texture':'other'})

                current_api_mock.side_effect=[current_asset_record,{'saved':True}]
                database_images.resize_database_asset_image({**current_request_record,'size':64})
                current_resize_request=current_api_mock.call_args
                self.assertEqual(current_resize_request.args[2]['properties'],current_asset_record['properties'])
                self.assertEqual(current_resize_request.args[2]['image']['width'],64)
                current_api_mock.side_effect=None
                database_images.resize_database_asset_image({**current_request_record,'size':64})
                self.assertEqual(current_api_mock.call_args,current_resize_request)
