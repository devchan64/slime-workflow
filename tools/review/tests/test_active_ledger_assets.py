"""폐기된 DB 이력이 활성 원장 동기화를 막거나 복원하지 않는지 검증한다."""
import unittest
from tools.review.domains.map_assets.database_ledger import resolve_active_ledger_assets

class ActiveLedgerAssetTests(unittest.TestCase):
    def test_retired_history_stays_outside_active_ledger(self):
        current_active_record={'assetId':'active-grass','retired':False}
        current_retired_record={'assetId':'retired-grass','retired':True}
        self.assertEqual(resolve_active_ledger_assets([current_active_record,current_retired_record],[{'texture_key':'active-grass'}]),{'active-grass':current_active_record})

    def test_active_mismatch_remains_an_error(self):
        for current_catalog_records in ([],[{'texture_key':'unknown-grass'}]):
            with self.assertRaisesRegex(ValueError,'활성 빌보드 ID'):
                resolve_active_ledger_assets([{'assetId':'active-grass','retired':False},{'assetId':'retired-grass','retired':True}],current_catalog_records)

    def test_catalog_retirement_record_is_preserved(self):
        current_retired_record={'assetId':'retired-grass','retired':True}
        self.assertEqual(resolve_active_ledger_assets([current_retired_record],[{'texture_key':'retired-grass'}]),{'retired-grass':current_retired_record})
