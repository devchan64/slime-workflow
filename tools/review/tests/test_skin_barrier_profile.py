"""채택 설정·입력 거절 계약을 확인한다."""
import tempfile
import unittest
from pathlib import Path
import yaml
from generators.hy_motion.skin_barrier_profile import load_skin_barrier, SKIN_BARRIER_PROFILE


class SkinBarrierProfileTests(unittest.TestCase):
    def test_adjacency_profile_is_explicit_candidate(self):
        current_candidate_record = load_skin_barrier(SKIN_BARRIER_PROFILE.with_name('anny-adjacency-barrier.yaml'))
        self.assertEqual(current_candidate_record['adjacent_connections'], 'upperarm_upper_spine_five_hops')
        self.assertEqual(current_candidate_record['approval_status'], 'candidate')
        self.assertEqual(load_skin_barrier()['adjacent_connections'], 'excluded')

    def test_temporal_candidate_keeps_default_unchanged(self):
        current_candidate_record = load_skin_barrier(SKIN_BARRIER_PROFILE.with_name('anny-temporal-barrier.yaml'))
        self.assertEqual(current_candidate_record['initialization'], 'previous_pose_with_lateral_collision_repair')
        self.assertEqual(current_candidate_record['approval_status'], 'candidate')
        self.assertEqual(load_skin_barrier()['profile_id'], 'anny-neutral-v4-skin-barrier-v1')

    def test_candidate_extends_proximal_chain_without_replacing_default(self):
        current_candidate_record = load_skin_barrier(SKIN_BARRIER_PROFILE.with_name('anny-proximal-barrier.yaml'))
        self.assertEqual(current_candidate_record['bone_prefixes'][:3], ['clavicle', 'shoulder01', 'upperarm01'])
        self.assertEqual(current_candidate_record['approval_status'], 'candidate')
        self.assertEqual(current_candidate_record['initialization'], 'bilateral_rest_to_lateral_first_clear')
        self.assertEqual(load_skin_barrier()['profile_id'], 'anny-neutral-v4-skin-barrier-v1')

    def test_accepted_profile_preserves_reviewed_values(self):
        current_profile_record = load_skin_barrier()
        self.assertEqual(current_profile_record['minimum_surface_clearance_m'], .0005)
        self.assertEqual(current_profile_record['angle_step_degrees'], 2)
        self.assertEqual(current_profile_record['adjacent_connections'], 'excluded')
        self.assertEqual(current_profile_record['approval_status'], 'accepted_with_replay_warnings')

    def test_invalid_profile_fields_are_rejected(self):
        current_original_record = load_skin_barrier()
        for current_field_name, current_invalid_value in (('unknown', 1), ('schema_version', True), ('bone_prefixes', ['wrist']), ('angle_step_degrees', float('nan')), ('minimum_surface_clearance_m', -1), ('audit_substeps', True), ('boundary_refinements', 25), ('adjacent_connections', 'blocked')):
            with self.subTest(field=current_field_name), tempfile.TemporaryDirectory() as current_temp_directory:
                current_profile_path = Path(current_temp_directory) / 'profile.yaml'
                current_profile_path.write_text(yaml.safe_dump({**current_original_record, current_field_name: current_invalid_value}))
                with self.assertRaises(ValueError):
                    load_skin_barrier(current_profile_path)

    def test_duplicate_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_profile_path = Path(current_temp_directory) / 'profile.yaml'
            current_profile_path.write_text(SKIN_BARRIER_PROFILE.read_text() + '\nschema_version: 1\n')
            with self.assertRaises(ValueError):
                load_skin_barrier(current_profile_path)
