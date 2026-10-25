"""점유 배율 전환·재실행과 기존 크기 보존을 확인한다."""
import unittest
from tools.review.maintenance.migrate_shadow_sizes import migrate_shadow_size_values
from tools.review.common.sprite_display_properties import normalize_sprite_property_precision

class ShadowSizeMigrationTests(unittest.TestCase):
    def test_preserves_lengths_and_other_properties(self):
        for current_column_count,current_row_count in ((1,1),(2,3),(3,2),(8,8)):
            current_original_values=dict(anchorX=0,anchorY=-.2,groundFootprintColumns=current_column_count,groundFootprintRows=current_row_count,displayHeight=128,billboardAnchorMode='tile-intersection',shadowCoordinateVersion=2,shadowOffsetColumn=.2,shadowOffsetRow=-.1,shadowScaleX=.53,shadowScaleY=.37)
            current_updated_values=migrate_shadow_size_values(current_original_values)
            self.assertAlmostEqual(current_updated_values['shadowScaleX']*current_column_count,.53,delta=.000004)
            self.assertAlmostEqual(current_updated_values['shadowScaleY']*current_row_count,.37,delta=.000004)
            for current_property_name in set(current_original_values)-{'shadowScaleX','shadowScaleY'}:
                self.assertEqual(current_original_values[current_property_name],current_updated_values[current_property_name])
            self.assertEqual(migrate_shadow_size_values(current_updated_values),current_updated_values)
            self.assertEqual(normalize_sprite_property_precision(current_updated_values),current_updated_values)

    def test_unknown_version_rejected(self):
        with self.assertRaises(ValueError):
            migrate_shadow_size_values(dict(anchorX=0,anchorY=0,shadowSizeVersion=3))
