"""후보 지정의 원본 일치·엄격한 입력·기하 축·게이트웨이 저장 계약."""
import copy
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import numpy as np
from tools.review.domains.anny import landmarks
from tools.review.common.management_gateway import ManagementCommandGateway, resolve_management_command, execute_gateway_cli
from tools.review.tests import test_management_gateway


class AnnyLandmarkContractTest(unittest.TestCase):
    def test_invalid_json_returns_http_400_without_service_execution(self):
        current_request_factory=test_management_gateway.GatewayContractTest().create_request_handler
        current_gateway_value=ManagementCommandGateway({'anny-landmarks':landmarks.handle_landmark_request})
        for current_payload_text in ('{"source":{},"source":{},"points":{}}','{"source":NaN,"points":{}}','{"source":Infinity,"points":{}}'):
            for current_request_path in ('/anny-landmarks/landmark-save','/management/command'):
                with self.subTest(payload=current_payload_text,path=current_request_path):
                    current_request_text=current_payload_text if current_request_path!='/management/command' else '{"service":"anny-landmarks","command":"landmark-save","payload":'+current_payload_text+'}'
                    current_request_bytes=current_request_text.encode()
                    current_request_handler=current_request_factory(current_request_path,{})
                    current_request_handler.rfile=io.BytesIO(current_request_bytes)
                    current_request_handler.headers['Content-Length']=str(len(current_request_bytes))
                    with patch.object(landmarks,'execute_landmark_command') as current_execute_mock:
                        self.assertTrue(current_gateway_value.handle(current_request_handler))
                    self.assertEqual(current_request_handler.responses,[400])
                    self.assertIn('error',json.loads(current_request_handler.wfile.getvalue()))
                    current_execute_mock.assert_not_called()

    @classmethod
    def setUpClass(cls):
        cls.current_source_record = landmarks.load_landmark_source()

    def create_candidate_draft(self):
        return {'source': copy.deepcopy(self.current_source_record['source']), 'points': {'left_elbow_medial': {'position': self.current_source_record['vertices'][0], 'method': 'surface_pick', 'evidence': '검증용 합성 지정 · 해부학적 위치 아님'}}}

    def test_browser_projection_and_picking(self):
        current_process_result = subprocess.run(['node', str(Path(__file__).with_name('anny_landmarks.test.mjs'))], capture_output=True, text=True)
        self.assertEqual(current_process_result.returncode, 0, current_process_result.stderr)

    def test_source_height_and_hash(self):
        current_vertex_values = np.asarray(self.current_source_record['vertices'])
        self.assertAlmostEqual(float(current_vertex_values[:, 2].min()), 0)
        self.assertAlmostEqual(float(current_vertex_values[:, 2].max()), 1.6)
        self.assertEqual(len(self.current_source_record['source']['npz_sha256']), 64)

    def test_rig_reference_matches_original_transform(self):
        with np.load(landmarks.LANDMARK_ASSET_DIRECTORY / 'anny-rest-rig.npz') as current_rig_archive:
            current_bone_names = current_rig_archive['bone_names'].tolist()
            for current_reference_record in self.current_source_record['rig_reference'].values():
                current_expected_point = current_rig_archive['bone_matrices'][current_bone_names.index(current_reference_record['bone']), :3, 3].astype(float)
                current_expected_point[2] -= self.current_source_record['source']['floor_offset_native']
                current_expected_point *= self.current_source_record['source']['scale_to_meters']
                np.testing.assert_allclose(current_reference_record['position'], current_expected_point)
                self.assertEqual(current_reference_record['kind'], 'rig_head_not_anatomical_landmark')

    def test_rig_reference_missing_bone_rejected(self):
        with self.assertRaises(ValueError):
            landmarks.extract_rig_reference(['wrong'], np.eye(4)[None], 0, 1)

    def test_comparison_does_not_approve_or_modify_candidates(self):
        current_draft_record = self.create_candidate_draft()
        current_original_draft = copy.deepcopy(current_draft_record)
        current_review_record = landmarks.build_landmark_review(current_draft_record['points'], self.current_source_record)
        self.assertEqual(current_review_record['rig_comparison'], [])
        self.assertFalse(current_review_record['retarget_ready'])
        self.assertEqual(current_draft_record, current_original_draft)
        current_shoulder_position = self.current_source_record['rig_reference']['left_shoulder']['position']
        current_draft_record['points']['left_shoulder_center'] = {'position': current_shoulder_position, 'method': 'manual_xyz', 'evidence': '합성 검사'}
        current_review_record = landmarks.build_landmark_review(current_draft_record['points'], self.current_source_record)
        self.assertEqual(current_review_record['rig_comparison'][0]['offset_m'], 0)
        self.assertFalse(current_review_record['anatomical_verified'])
        self.assertFalse(current_review_record['retarget_ready'])

    def test_invalid_point_inputs(self):
        for current_bad_value in ([True, 0, 0], [float('nan'), 0, 0], [0, 0], [100, 0, 0], 'xyz'):
            with self.subTest(current_bad_value=current_bad_value), self.assertRaises(ValueError):
                current_draft_record = self.create_candidate_draft()
                current_draft_record['points']['left_elbow_medial']['position'] = current_bad_value
                landmarks.validate_landmark_draft(current_draft_record, self.current_source_record)

    def test_unknown_fields_and_missing_evidence(self):
        for current_field_name, current_bad_value in (('approved', True), ('method', 'clinical'), ('evidence', ' ')):
            with self.subTest(current_field_name=current_field_name), self.assertRaises(ValueError):
                current_draft_record = self.create_candidate_draft()
                current_draft_record['points']['left_elbow_medial'][current_field_name] = current_bad_value
                landmarks.validate_landmark_draft(current_draft_record, self.current_source_record)

    def test_source_change_rejected(self):
        current_draft_record = self.create_candidate_draft()
        current_draft_record['source']['version'] = 3
        with self.assertRaises(ValueError):
            landmarks.validate_landmark_draft(current_draft_record, self.current_source_record)

    def test_surface_pick_must_match_vertex(self):
        current_draft_record = self.create_candidate_draft()
        current_draft_record['points']['left_elbow_medial']['position'] = [0, 0, .8]
        with self.assertRaises(ValueError):
            landmarks.validate_landmark_draft(current_draft_record, self.current_source_record)
        current_draft_record['points']['left_elbow_medial']['method'] = 'manual_xyz'
        landmarks.validate_landmark_draft(current_draft_record, self.current_source_record)

    def test_no_axes_for_missing_points(self):
        current_review_record = landmarks.build_candidate_axes({})
        self.assertEqual(current_review_record['axes'], [])
        self.assertFalse(current_review_record['anatomical_verified'])

    def test_axes_are_right_handed_but_not_verified(self):
        current_point_records = {}
        for current_side_name, current_side_sign in (('left', 1), ('right', -1)):
            for current_point_name, current_position_values in zip(landmarks.LANDMARK_POINT_LABELS, ([0, 0, 1.5], [-.1, 0, 1], [.1, 0, 1], [.1, 0, .5], [-.1, 0, .5])):
                current_point_records[f'{current_side_name}_{current_point_name}'] = {'position': [current_position_values[0] * current_side_sign, *current_position_values[1:]]}
        current_review_record = landmarks.build_candidate_axes(current_point_records)
        self.assertEqual(len(current_review_record['axes']), 4)
        for current_axis_record in current_review_record['axes']:
            current_axis_matrix = np.asarray(current_axis_record['axes'])
            np.testing.assert_allclose(current_axis_matrix @ current_axis_matrix.T, np.eye(3))
            self.assertAlmostEqual(np.linalg.det(current_axis_matrix), 1)
        self.assertFalse(current_review_record['anatomical_verified'])
        for current_point_record in current_point_records.values():
            current_point_record['position'] = [0, 0, 1]
        self.assertEqual(landmarks.build_candidate_axes(current_point_records)['axes'], [])

    def test_immutable_save_load_history_and_stale_source(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory, patch.object(landmarks, 'LANDMARK_STORAGE_DIRECTORY', Path(current_temporary_directory)):
            current_first_record = landmarks.execute_landmark_command('landmark-save', self.create_candidate_draft())
            current_second_record = landmarks.execute_landmark_command('landmark-save', self.create_candidate_draft())
            self.assertNotEqual(current_first_record['id'], current_second_record['id'])
            self.assertEqual(len(landmarks.execute_landmark_command('landmark-history', {})['records']), 2)
            self.assertEqual(landmarks.execute_landmark_command('landmark-load', {'id': current_first_record['id']}), current_first_record)
            current_changed_source = copy.deepcopy(self.current_source_record)
            current_changed_source['source']['version'] = 5
            with patch.object(landmarks, 'load_landmark_source', return_value=current_changed_source), self.assertRaises(ValueError):
                landmarks.execute_landmark_command('landmark-load', {'id': current_first_record['id']})

    def test_paths_and_apply_are_rejected(self):
        for current_record_identifier in ('../../etc/passwd', '/etc/passwd', 'invalid'):
            with self.assertRaises(ValueError):
                landmarks.resolve_landmark_record(current_record_identifier)
        for current_command_name in ('approve', 'apply', 'generate'):
            with self.assertRaises(ValueError):
                resolve_management_command('anny-landmarks', current_command_name, {})

    def test_history_rejects_links_and_mismatched_record_identity(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory, patch.object(landmarks,'LANDMARK_STORAGE_DIRECTORY',Path(current_temporary_directory)/'records'):
            current_saved_record=landmarks.execute_landmark_command('landmark-save',self.create_candidate_draft())
            current_record_path=landmarks.resolve_landmark_record(current_saved_record['id'])
            current_original_text=current_record_path.read_text()
            for current_field_name,current_invalid_value in [('id','different'),('status','approved')]:
                current_invalid_record={**current_saved_record,current_field_name:current_invalid_value}
                current_record_path.write_text(json.dumps(current_invalid_record))
                with self.assertRaisesRegex(ValueError,'ID 또는 후보 상태'):
                    landmarks.execute_landmark_command('landmark-load',{'id':current_saved_record['id']})
            current_record_path.write_text(current_original_text)
            current_external_path=Path(current_temporary_directory)/'external.json'
            current_external_path.write_text(current_original_text)
            current_record_path.unlink()
            current_record_path.symlink_to(current_external_path)
            with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                landmarks.execute_landmark_command('landmark-load',{'id':current_saved_record['id']})
            with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                landmarks.execute_landmark_command('landmark-history',{})
            self.assertEqual(current_external_path.read_text(),current_original_text)

    def test_saved_record_rejects_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory, patch.object(landmarks,'LANDMARK_STORAGE_DIRECTORY',Path(current_temporary_directory)):
            current_saved_record=landmarks.execute_landmark_command('landmark-save',self.create_candidate_draft())
            current_record_path=landmarks.resolve_landmark_record(current_saved_record['id'])
            current_original_text=json.dumps(current_saved_record)
            current_invalid_texts=[
                current_original_text.replace('"status": "candidate"','"status": "candidate", "status": "candidate"'),
                current_original_text.replace('"method": "surface_pick"','"method": "surface_pick", "method": "surface_pick"'),
                *[current_original_text.replace('"anatomical_verified": false','"anatomical_verified": '+current_constant_name) for current_constant_name in ('NaN','Infinity','-Infinity')],
            ]
            for current_invalid_text in current_invalid_texts:
                self.assertNotEqual(current_invalid_text,current_original_text)
                current_record_path.write_text(current_invalid_text)
                with self.assertRaisesRegex(ValueError,'JSON (중복 필드|비유한 숫자)'):
                    landmarks.execute_landmark_command('landmark-load',{'id':current_saved_record['id']})
            current_record_path.write_text(current_original_text)
            self.assertEqual(landmarks.execute_landmark_command('landmark-load',{'id':current_saved_record['id']}),current_saved_record)

    def test_date_and_record_directory_links_are_rejected(self):
        for current_link_scope in ('date','record'):
            with self.subTest(scope=current_link_scope),tempfile.TemporaryDirectory() as current_temporary_directory:
                current_storage_root=Path(current_temporary_directory)/'records'
                current_external_root=Path(current_temporary_directory)/'external'
                current_storage_root.mkdir()
                current_external_root.mkdir()
                current_date_identifier='2026-10-16_01-02-03'
                current_record_identifier=current_date_identifier+'/'+'a'*32
                if current_link_scope=='date':
                    (current_external_root/('a'*32)).mkdir()
                    current_external_file=current_external_root/('a'*32)/'candidate.json'
                    (current_storage_root/current_date_identifier).symlink_to(current_external_root,target_is_directory=True)
                else:
                    (current_storage_root/current_date_identifier).mkdir()
                    current_external_file=current_external_root/'candidate.json'
                    (current_storage_root/current_record_identifier).symlink_to(current_external_root,target_is_directory=True)
                current_external_file.write_text('외부 파일은 읽지 않습니다.')
                with patch.object(landmarks,'LANDMARK_STORAGE_DIRECTORY',current_storage_root):
                    with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                        landmarks.resolve_landmark_record(current_record_identifier)
                    with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                        landmarks.execute_landmark_command('landmark-load',{'id':current_record_identifier})
                    with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                        landmarks.execute_landmark_command('landmark-history',{})
                self.assertEqual(current_external_file.read_text(),'외부 파일은 읽지 않습니다.')

    def test_gui_cli_share_gateway_contract(self):
        current_gateway_object = ManagementCommandGateway({'anny-landmarks': landmarks.handle_landmark_request})
        current_payload_record = self.create_candidate_draft()
        current_request_factory = test_management_gateway.GatewayContractTest().create_request_handler
        current_gui_request = current_request_factory('/management/command', {'service': 'anny-landmarks', 'command': 'landmark-preview', 'payload': current_payload_record})
        current_legacy_request = current_request_factory('/anny-landmarks/landmark-preview', current_payload_record)
        current_gateway_object.handle(current_gui_request)
        current_gateway_object.handle(current_legacy_request)
        self.assertEqual(current_gui_request.responses, [200])
        self.assertEqual(json.loads(current_gui_request.wfile.getvalue()), json.loads(current_legacy_request.wfile.getvalue()))
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_payload_path = Path(current_temporary_directory) / 'input.json'
            current_payload_path.write_text(json.dumps(current_payload_record))
            with patch('tools.review.common.management_gateway.execute_management_command', return_value={'status': 'candidate'}) as current_command_mock:
                execute_gateway_cli(['command', 'anny-landmarks', 'landmark-preview', '--payload-file', str(current_payload_path)])
            self.assertEqual(current_command_mock.call_args.args[:3], ('anny-landmarks', 'landmark-preview', current_payload_record))

    def test_gateway_save_history_load_preserves_candidate(self):
        current_gateway_object = ManagementCommandGateway({'anny-landmarks': landmarks.handle_landmark_request})
        current_request_factory = test_management_gateway.GatewayContractTest().create_request_handler
        current_candidate_draft = self.create_candidate_draft()
        with tempfile.TemporaryDirectory() as current_temporary_directory, patch.object(landmarks, 'LANDMARK_STORAGE_DIRECTORY', Path(current_temporary_directory)):
            current_save_request = current_request_factory('/management/command', {'service': 'anny-landmarks', 'command': 'landmark-save', 'payload': current_candidate_draft})
            self.assertTrue(current_gateway_object.handle(current_save_request))
            self.assertEqual(current_save_request.responses, [200])
            current_saved_record = json.loads(current_save_request.wfile.getvalue())
            current_history_request = current_request_factory('/management/command', {'service': 'anny-landmarks', 'command': 'landmark-history', 'payload': {}})
            current_gateway_object.handle(current_history_request)
            self.assertEqual(current_history_request.responses, [200])
            self.assertIn(current_saved_record['id'], json.loads(current_history_request.wfile.getvalue())['records'])
            current_load_request = current_request_factory('/management/command', {'service': 'anny-landmarks', 'command': 'landmark-load', 'payload': {'id': current_saved_record['id']}})
            current_gateway_object.handle(current_load_request)
            self.assertEqual(current_load_request.responses, [200])
            self.assertEqual(json.loads(current_load_request.wfile.getvalue())['draft'], current_candidate_draft)


if __name__ == '__main__':
    unittest.main()
