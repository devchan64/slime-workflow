"""큰 장식이 경계·단차·다른 점유 영역을 침범하지 않는지 검사한다."""
import unittest
from tools.review.domains.map_assets.placement import calculate_centered_footprint_cells, validate_scenery_ground_placement


class SceneryGroundPlacementTests(unittest.TestCase):
    def test_centered_even_footprint_touches_neighbor_cells(self):
        self.assertEqual(calculate_centered_footprint_cells((2, 2), 2, 2), {(2, 2), (3, 2), (2, 3), (3, 3)})
        self.assertEqual(calculate_centered_footprint_cells((2, 2), 1, 1), {(2, 2)})

    def test_boundary_slope_and_reserved_cells_are_rejected(self):
        current_elevation_rows = [[0] * 5 for current_row_index in range(5)]
        current_ground_cells = calculate_centered_footprint_cells((2, 2), 2, 2)
        self.assertIsNone(validate_scenery_ground_placement(current_ground_cells, current_elevation_rows, set()))
        self.assertEqual(validate_scenery_ground_placement(calculate_centered_footprint_cells((4, 4), 2, 2), current_elevation_rows, set()), '맵 경계 침범')
        self.assertEqual(validate_scenery_ground_placement(current_ground_cells, current_elevation_rows, {(3, 3)}), '예약 영역 중첩')
        current_elevation_rows[3][3] = 2
        self.assertEqual(validate_scenery_ground_placement(current_ground_cells, current_elevation_rows, set()), '접지 영역 고도 불일치')

    def test_different_centers_with_overlapping_footprints_fail(self):
        from tools.review.domains.map_assets.placement import validate_scenery_object_collisions
        current_property_catalog = {'rock': {'groundFootprintColumns': 2, 'groundFootprintRows': 2}}
        current_object_records = [dict(id='left-rock', kind='decoration', textureKey='rock', position=dict(column=2, row=2)), dict(id='right-rock', kind='decoration', textureKey='rock', position=dict(column=3, row=2))]
        with self.assertRaisesRegex(ValueError, 'left-rock ↔ right-rock: 점유 영역 충돌'):
            validate_scenery_object_collisions(current_object_records, current_property_catalog, [[0] * 8 for current_row_index in range(8)])
        current_object_records[1]['position']['column'] = 5
        validate_scenery_object_collisions(current_object_records, current_property_catalog, [[0] * 8 for current_row_index in range(8)])

    def test_review_builder_rejects_colliding_map_data(self):
        from unittest.mock import patch
        from tools.review.build_block_map_review import build_registered_map_review
        current_map_record = dict(objects=[dict(id=current_object_name, kind='decoration', textureKey='rock', position=dict(column=2, row=2)) for current_object_name in ('first-rock', 'second-rock')], spriteProperties={'rock': dict(groundFootprintColumns=1, groundFootprintRows=1)}, elevations=['00000'] * 5)
        with patch('tools.review.common.map_asset_sources.load_registered_map_review', return_value=current_map_record), patch('tools.review.common.map_asset_sources.load_review_map_identifiers', return_value=([], ['test-map'])):
            with self.assertRaisesRegex(ValueError, 'first-rock ↔ second-rock'):
                build_registered_map_review('test-map')

    def test_image_silhouette_does_not_override_tile_footprint(self):
        from PIL import Image
        from tools.review.domains.map_assets.placement import validate_scenery_image_footprint
        current_source_image = Image.new('RGBA', (128, 128), 'white')
        for current_tile_width, current_display_height in [(80, 145), (160, 290)]:
            validate_scenery_image_footprint('tree', current_source_image, dict(anchorX=0.5, displayHeight=current_display_height, groundFootprintColumns=1, groundFootprintRows=1), current_tile_width)

    def test_canopy_and_transparent_padding_do_not_inflate_contact_width(self):
        from PIL import Image, ImageDraw
        from tools.review.domains.map_assets.placement import validate_scenery_image_footprint
        current_source_image = Image.new('RGBA', (128, 128))
        current_image_drawing = ImageDraw.Draw(current_source_image)
        current_image_drawing.rectangle((0, 0, 127, 60), fill='white')
        current_image_drawing.rectangle((60, 61, 68, 120), fill='white')
        validate_scenery_image_footprint('tree', current_source_image, dict(anchorX=0.5, displayHeight=280, groundFootprintColumns=1, groundFootprintRows=1), 80)
        with self.assertRaisesRegex(ValueError, '불투명 영역이 없는'):
            validate_scenery_image_footprint('empty', Image.new('RGBA', (128, 128)), dict(anchorX=0.5, displayHeight=80, groundFootprintColumns=1, groundFootprintRows=1), 80)

    def test_declared_tile_contact_rejects_height_changes(self):
        from PIL import Image
        from tools.review.domains.map_assets.placement import validate_image_contact_elevations
        current_source_image = Image.new('RGBA', (128, 128), 'white')
        current_object_record = dict(id='tree', textureKey='tree', position=dict(column=3, row=3), tileAnchor='center')
        current_property_values = dict(anchorX=0.5, anchorY=0.87, displayHeight=290, groundFootprintColumns=1, groundFootprintRows=1)
        current_elevation_rows = [[0] * 8 for current_row_index in range(8)]
        current_elevation_rows[3][3] = 2
        with self.assertRaisesRegex(ValueError, '주변 단차 경계'):
            validate_image_contact_elevations(current_object_record, current_source_image, current_property_values, current_elevation_rows, 80, 40)
        current_property_values.update(groundFootprintColumns=2, groundFootprintRows=2)
        with self.assertRaisesRegex(ValueError, '접지 영역 고도 불일치'):
            validate_image_contact_elevations(current_object_record, current_source_image, current_property_values, current_elevation_rows, 80, 40)

    def test_single_tile_rejects_adjacent_and_diagonal_height_changes(self):
        for current_neighbor_position in ((2, 3), (3, 2), (4, 3), (3, 4), (4, 4)):
            current_elevation_rows = [[0] * 7 for current_row_index in range(7)]
            current_neighbor_column, current_neighbor_row = current_neighbor_position
            current_elevation_rows[current_neighbor_row][current_neighbor_column] = 1
            self.assertEqual(validate_scenery_ground_placement({(3, 3)}, current_elevation_rows, set()), '접지 주변 단차 경계 침범')
        self.assertIsNone(validate_scenery_ground_placement({(0, 0)}, [[0] * 7 for current_row_index in range(7)], set()))
