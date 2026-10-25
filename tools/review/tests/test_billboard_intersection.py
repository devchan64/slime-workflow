"""점유 크기별 교차점과 내부 차단 영역 계약."""
import unittest
from tools.review.common.sprite_display_properties import calculate_billboard_intersection_properties,collect_billboard_blocked_cells

class BillboardIntersectionTests(unittest.TestCase):
    def test_explicit_blocking_covers_the_entire_footprint(self):
        for current_columns_count,current_rows_count in ((1,1),(2,1),(2,2),(3,2),(3,3),(4,4)):
            for current_blocking_choice in (False,True):
                current_property_values=calculate_billboard_intersection_properties({'groundFootprintColumns':current_columns_count,'groundFootprintRows':current_rows_count,'anchorX':-.2,'anchorY':.1,'billboardBlocksMovement':current_blocking_choice})
                self.assertEqual(current_property_values['billboardBlocksMovement'],current_blocking_choice)
                self.assertEqual((current_property_values['anchorX'],current_property_values['anchorY']),(-.2,.1))
                current_actual_cells=collect_billboard_blocked_cells([{**current_property_values,'position':{'column':10,'row':20}}])
                current_expected_cells={(10+current_column_offset,20+current_row_offset) for current_column_offset in range(current_columns_count) for current_row_offset in range(current_rows_count)} if current_blocking_choice else set()
                self.assertEqual(current_actual_cells,current_expected_cells)
