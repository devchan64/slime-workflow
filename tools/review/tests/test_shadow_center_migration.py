"""중심 좌표 변환의 위치 보존과 재실행 안전성을 검증한다."""
import unittest
from tools.review.maintenance.migrate_shadow_centers import migrate_shadow_property_values

class ShadowCenterMigrationTests(unittest.TestCase):
    def test_preserves_world_center_and_other_fields(self):
        for current_column_count in (1,2,3,8):
            for current_row_count in (1,2,3,8):
                current_old_values=dict(anchorX=0,anchorY=-0.2,groundFootprintColumns=current_column_count,groundFootprintRows=current_row_count,displayHeight=128,billboardAnchorMode='tile-intersection',shadowOffsetColumn=-0.3,shadowOffsetRow=-0.2,shadowScaleX=0.6,shadowScaleY=0.8)
                current_new_values=migrate_shadow_property_values(current_old_values)
                for current_count,current_field in ((current_column_count,'shadowOffsetColumn'),(current_row_count,'shadowOffsetRow')):
                    current_old_origin=0.5 if current_count==1 else current_count-1
                    self.assertAlmostEqual(current_old_origin+current_old_values[current_field],(current_count-1)/2+current_new_values[current_field])
                for current_field in set(current_old_values)-{'shadowOffsetColumn','shadowOffsetRow'}:
                    self.assertEqual(current_new_values[current_field],current_old_values[current_field])
                self.assertEqual(migrate_shadow_property_values(current_new_values),current_new_values)

    def test_rejects_unknown_or_boolean_version(self):
        for current_invalid_version in (3,True):
            with self.assertRaises(ValueError):
                migrate_shadow_property_values(dict(anchorX=0,anchorY=0,shadowCoordinateVersion=current_invalid_version))
