"""어깨 인접성 완화의 범위와 혼합 삼각형 보존을 검증한다."""
import unittest
from generators.hy_motion.shoulder_adjacency_filter import calculate_bone_distance, select_excluded_pairs, build_filtered_batches


class ShoulderAdjacencyFilterTests(unittest.TestCase):
    def setUp(self):
        self.current_parent_names = {'spine02': None, 'spine01': 'spine02'}
        for current_side_name in ('L', 'R'):
            self.current_parent_names.update({f'clavicle.{current_side_name}': 'spine01', f'shoulder01.{current_side_name}': f'clavicle.{current_side_name}', f'upperarm01.{current_side_name}': f'shoulder01.{current_side_name}', f'upperarm02.{current_side_name}': f'upperarm01.{current_side_name}', f'lowerarm01.{current_side_name}': f'upperarm02.{current_side_name}'})

    def test_hop_count_and_scope(self):
        self.assertEqual(calculate_bone_distance(self.current_parent_names, 'upperarm02.R', 'spine02'), 5)
        current_selected_pairs = select_excluded_pairs(self.current_parent_names)
        self.assertEqual(len(current_selected_pairs), 8)
        self.assertNotIn(('lowerarm01.R', 'spine01'), current_selected_pairs)

    def test_pair_override_changes_only_selected_pair(self):
        from generators.hy_motion.collision_relations import load_collision_relations
        current_relation_record, current_profile_hash = load_collision_relations()
        current_original_pairs = select_excluded_pairs(self.current_parent_names)
        current_relation_record['pair_overrides'] = [{'arm_bone': 'upperarm01.L', 'body_bone': 'spine01', 'policy': 'check', 'reason': '검사 복원'}]
        self.assertEqual(select_excluded_pairs(self.current_parent_names, current_relation_record), current_original_pairs - {('upperarm01.L', 'spine01')})
        self.assertEqual(len(current_profile_hash), 64)

    def test_relation_file_rejects_unknown_fields(self):
        import tempfile
        from pathlib import Path
        import yaml
        from generators.hy_motion.collision_relations import load_collision_relations
        current_relation_record, _ = load_collision_relations()
        current_relation_record['unknown'] = True
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_profile_path = Path(current_directory_name) / 'relations.yaml'
            current_profile_path.write_text(yaml.safe_dump(current_relation_record))
            with self.assertRaises(ValueError):
                load_collision_relations(current_profile_path)

    def test_more_than_five_hops_is_kept(self):
        self.current_parent_names['spine03'] = 'spine02'
        self.current_parent_names['spine01'] = 'spine03'
        self.assertNotIn(('upperarm02.R', 'spine02'), select_excluded_pairs(self.current_parent_names))

    def test_invalid_graph_fails(self):
        with self.assertRaises(ValueError):
            calculate_bone_distance({'a': 'b', 'b': 'a'}, 'a', 'b')
        with self.assertRaises(ValueError):
            calculate_bone_distance({'a': None, 'b': None}, 'a', 'b')

    def test_mixed_faces_and_distant_body_are_kept(self):
        current_vertex_labels = ['upperarm01.L'] * 3 + ['lowerarm01.L'] * 3 + ['spine01'] * 3 + ['pelvis'] * 3
        current_partition_faces = {'L': [(0, 1, 2), (3, 4, 5), (1, 2, 3)], 'R': [], 'body': [(6, 7, 8), (9, 10, 11), (7, 8, 9)]}
        current_collision_batches = build_filtered_batches(current_partition_faces, current_vertex_labels, frozenset({('upperarm01.L', 'spine01')}))
        current_body_by_face = {current_arm_face: current_body_faces for _, current_arm_faces, current_body_faces in current_collision_batches for current_arm_face in current_arm_faces}
        self.assertNotIn((6, 7, 8), current_body_by_face[(0, 1, 2)])
        self.assertIn((9, 10, 11), current_body_by_face[(0, 1, 2)])
        self.assertIn((7, 8, 9), current_body_by_face[(0, 1, 2)])
        self.assertEqual(current_body_by_face[(3, 4, 5)], current_partition_faces['body'])
        self.assertEqual(current_body_by_face[(1, 2, 3)], current_partition_faces['body'])

    def test_empty_exclusion_preserves_partitions(self):
        current_partition_faces = {'L': [(0, 1, 2)], 'R': [], 'body': [(3, 4, 5)]}
        self.assertEqual(build_filtered_batches(current_partition_faces, ['upperarm01.L'] * 3 + ['spine01'] * 3, frozenset()), [('L', [(0, 1, 2)], [(3, 4, 5)])])
