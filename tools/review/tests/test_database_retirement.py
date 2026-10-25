"""DB 폐기의 확인 대상 고정과 재시도 요청 보존."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets import database_retirement


class DatabaseRetirementTests(unittest.TestCase):
    def test_confirm_and_retry_keep_prepared_request(self):
        current_input_record={'texture':'grass','revision':json.dumps({'grass':2})}
        with TemporaryDirectory() as current_directory_name,patch.object(database_retirement,'EDITOR_STORAGE_DIRECTORY',Path(current_directory_name)),patch.object(database_retirement,'execute_content_api_request') as current_api_mock:
            current_api_mock.return_value={'assetId':'grass','expectedRevision':2,'expectedGeneration':9,'maps':[]}
            current_plan_record=database_retirement.preview_database_asset_retirement(current_input_record)
            self.assertEqual(current_api_mock.call_count,1)
            self.assertTrue(current_api_mock.call_args.args[1].endswith('retirement-preview'))
            current_confirm_record={**current_input_record,'token':current_plan_record['token']}
            database_retirement.execute_database_asset_retirement(current_confirm_record)
            current_first_request=current_api_mock.call_args
            database_retirement.execute_database_asset_retirement(current_confirm_record)
            self.assertEqual(current_first_request,current_api_mock.call_args)
            with self.assertRaisesRegex(ValueError,'대상이 변경'):
                database_retirement.execute_database_asset_retirement({**current_confirm_record,'texture':'other'})
            self.assertEqual(current_api_mock.call_count,3)
