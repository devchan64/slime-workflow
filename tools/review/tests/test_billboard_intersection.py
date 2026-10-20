"""점유 크기별 교차점과 내부 차단 영역 계약."""
import unittest
from tools.review.common.sprite_display_properties import calculate_billboard_intersection_properties,collect_billboard_blocked_cells

class BillboardIntersectionTests(unittest.TestCase):
    def test_intersection_and_interior_cells(self):
        for current_columns_count,current_rows_count,current_anchor_pair,current_blocked_count in ((1,1,(.5,1),0),(2,1,(.75,1.25),0),(2,2,(.5,1.5),0),(3,2,(1,2),0),(3,3,(.5,2.5),1),(4,4,(.5,3.5),4)):
            with self.subTest(size=(current_columns_count,current_rows_count)):
                current_property_values=calculate_billboard_intersection_properties({'groundFootprintColumns':current_columns_count,'groundFootprintRows':current_rows_count,'displayHeight':300,'anchorX':-2,'anchorY':-2,'billboardBlocksMovement':True})
                self.assertEqual((current_property_values['anchorX'],current_property_values['anchorY']),current_anchor_pair)
                current_blocked_cells=collect_billboard_blocked_cells([{**current_property_values,'position':{'column':10,'row':20}}])
                self.assertEqual(len(current_blocked_cells),current_blocked_count)
                self.assertNotIn((10,20),current_blocked_cells)
                if current_blocked_count:self.assertIn((11,21),current_blocked_cells)
