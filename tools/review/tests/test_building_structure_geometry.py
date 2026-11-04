"""제작된 가이드 전체의 접지·문·배율 계약 검증."""
import json
import unittest
from tools.review.domains.image.building_prompt import BUILDING_STRUCTURE_RECORDS
from tools.review.domains.image.building_structure_guides import BUILDING_STRUCTURE_ROOT


class BuildingStructureGeometryTests(unittest.TestCase):
    def test_all_footprints_and_doors_match_world_units(self):
        for current_identifier,current_structure_record in BUILDING_STRUCTURE_RECORDS.items():
            with self.subTest(guide=current_identifier):
                current_geometry_record=json.loads((BUILDING_STRUCTURE_ROOT/(current_identifier+'.geometry.json')).read_text())
                current_back_point,current_left_point,current_front_point,current_right_point=current_geometry_record['groundPoints']
                self.assertAlmostEqual(current_front_point[0]-current_left_point[0],80*current_structure_record['width'])
                self.assertAlmostEqual(current_front_point[1]-current_left_point[1],40*current_structure_record['width'])
                self.assertAlmostEqual(current_right_point[0]-current_front_point[0],80*current_structure_record['depth'])
                self.assertAlmostEqual(current_right_point[1]-current_front_point[1],-40*current_structure_record['depth'])
                current_door_points=current_geometry_record['doorPoints']
                self.assertAlmostEqual(current_door_points[0][0],current_door_points[3][0])
                self.assertAlmostEqual(current_door_points[0][1]-current_door_points[3][1],128)
                self.assertAlmostEqual(abs(current_door_points[1][0]-current_door_points[0][0]),80*current_structure_record['doorWidth'])
                self.assertEqual(current_geometry_record['wallHeight'],80*current_structure_record['floors'])
                for current_suffix_text in ('.png','.svg','-review.png'):
                    self.assertTrue((BUILDING_STRUCTURE_ROOT/(current_identifier+current_suffix_text)).is_file())
                for current_x_value,current_y_value in current_geometry_record['groundPoints']:
                    self.assertTrue(0<current_x_value<1024 and 0<current_y_value<1024)

    def test_hip_roofs_have_connected_planar_faces_and_visible_pitch(self):
        from collections import Counter
        from tools.review.domains.image.building_structure_guides import render_building_structure
        for current_identifier,current_structure_record in BUILDING_STRUCTURE_RECORDS.items():
            if current_structure_record['roof'] != 'hip':
                continue
            with self.subTest(guide=current_identifier):
                current_image_value,current_svg_text=render_building_structure(current_structure_record)
                current_geometry_record=current_image_value.info['geometry']
                current_stored_record=json.loads((BUILDING_STRUCTURE_ROOT/(current_identifier+'.geometry.json')).read_text())
                self.assertEqual(json.loads(json.dumps(current_geometry_record)),current_stored_record)
                self.assertEqual(current_svg_text,(BUILDING_STRUCTURE_ROOT/(current_identifier+'.svg')).read_text())
                from PIL import Image
                self.assertEqual(current_image_value.tobytes(),Image.open(BUILDING_STRUCTURE_ROOT/(current_identifier+'.png')).tobytes())
                current_roof_faces=current_geometry_record['roofFaces']
                self.assertEqual(len(current_roof_faces),4)
                self.assertEqual(sum(current_face_record['visible'] for current_face_record in current_roof_faces),2)
                current_width_count=current_structure_record['width']
                current_depth_count=current_structure_record['depth']
                current_wall_height=current_structure_record['floors']*80
                current_roof_height=current_structure_record['roofRise']
                self.assertGreater(current_roof_height,40*(current_width_count/2+0.1))
                current_edge_counts=Counter()
                for current_face_record in current_roof_faces:
                    current_world_points=[tuple(current_point_value) for current_point_value in current_face_record['worldPoints']]
                    self.assertEqual(len(current_world_points),len(set(current_world_points)))
                    self.assertIn(len(current_world_points),(3,4))
                    for current_point_index,current_start_point in enumerate(current_world_points):
                        current_end_point=current_world_points[(current_point_index+1)%len(current_world_points)]
                        current_edge_counts[tuple(sorted((current_start_point,current_end_point)))]+=1
                    # 모든 꼭짓점이 같은 지붕 경사면에 속한다.
                    current_first_point,current_second_point,current_third_point=current_world_points[:3]
                    current_first_vector=[current_second_point[i]-current_first_point[i] for i in range(3)]
                    current_second_vector=[current_third_point[i]-current_first_point[i] for i in range(3)]
                    current_normal_vector=[current_first_vector[1]*current_second_vector[2]-current_first_vector[2]*current_second_vector[1],current_first_vector[2]*current_second_vector[0]-current_first_vector[0]*current_second_vector[2],current_first_vector[0]*current_second_vector[1]-current_first_vector[1]*current_second_vector[0]]
                    for current_world_point in current_world_points:
                        self.assertAlmostEqual(sum(current_normal_vector[i]*(current_world_point[i]-current_first_point[i]) for i in range(3)),0)
                current_boundary_edges=[current_edge_value for current_edge_value,current_edge_count in current_edge_counts.items() if current_edge_count==1]
                self.assertEqual(len(current_boundary_edges),4)
                self.assertTrue(all(current_point_value[2]==current_wall_height for current_edge_value in current_boundary_edges for current_point_value in current_edge_value))
                self.assertTrue(all(current_edge_count in (1,2) for current_edge_count in current_edge_counts.values()))
                current_ridge_points=current_geometry_record['roofRidge']
                self.assertEqual(len(current_ridge_points),1 if current_width_count==current_depth_count else 2)
                self.assertAlmostEqual(current_ridge_points[-1][1]-current_ridge_points[0][1],current_depth_count-current_width_count)
                for current_ridge_point in current_ridge_points:
                    self.assertEqual(current_ridge_point[0],current_width_count/2)
                    self.assertEqual(current_ridge_point[2],current_wall_height+current_roof_height)
