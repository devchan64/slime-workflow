"""걷기 참조 매니페스트의 중복 키 거절 계약."""
from pathlib import Path
import copy
import yaml
import tempfile
import unittest
from unittest.mock import patch
from tools.review.domains.image.pose_motion_reference import load_motion_reference, validate_motion_reference_manifest, MOTION_REFERENCE_ROOT


class PoseReferenceManifestTests(unittest.TestCase):
    def test_duplicate_manifest_rejected_before_reference_read(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_manifest_root = Path(current_directory_name)
            (current_manifest_root/'manifest.yaml').write_text('frames: 35\nframes: 1\n')
            with patch('tools.review.domains.image.pose_motion_reference.MOTION_REFERENCE_ROOT',current_manifest_root):
                with self.assertRaisesRegex(ValueError,'중복 키: frames'):
                    load_motion_reference('down_left',1)

    def test_metadata_and_camera_fields_rejected(self):
        current_valid_record = yaml.safe_load((MOTION_REFERENCE_ROOT/'manifest.yaml').read_text())
        current_invalid_values = (
            ('asset_id', ''), ('status', None), ('version', True), ('version', 0),
            ('fps', 0), ('source_fps', float('nan')), ('cycle_seconds', float('inf')),
            ('preview_frames', [True]*35), ('projection', 'invalid'),
            ('fov_degrees', 180), ('camera_elevation_degrees', 91), ('camera', {}),
        )
        for current_field_name, current_invalid_value in current_invalid_values:
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record[current_field_name] = current_invalid_value
            with self.subTest(field=current_field_name), self.assertRaisesRegex(ValueError, current_field_name):
                validate_motion_reference_manifest(current_invalid_record)
        for current_field_name, current_invalid_value in (
            ('unknown', 1), ('location', [0, 0]), ('target', [0, True, 0]),
            ('rotation_quaternion_wxyz', [0, 0, 0, 0]), ('distance', -1),
            ('ortho_scale', 0), ('fov_degrees', float('nan')), ('framing', []),
            ('projection', 'orthographic'), ('azimuth_degrees', '45'),
        ):
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record['camera']['down_left'][current_field_name] = current_invalid_value
            with self.subTest(camera_field=current_field_name), self.assertRaisesRegex(ValueError, 'camera.down_left'):
                validate_motion_reference_manifest(current_invalid_record)
        for current_invalid_path in ('../source.png', '/source.png', 'a//b.png', 'a/./b.png', 1):
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record['files'][current_invalid_path] = 'a'*64
            with self.subTest(path=current_invalid_path), self.assertRaisesRegex(ValueError, '경로'):
                validate_motion_reference_manifest(current_invalid_record)
        current_invalid_record = copy.deepcopy(current_valid_record)
        current_invalid_record['files']['source-motion.npz'] = 'invalid'
        with self.assertRaisesRegex(ValueError, '해시'):
            validate_motion_reference_manifest(current_invalid_record)

    def test_manifest_schema_and_unknown_fields_rejected(self):
        current_valid_record = yaml.safe_load((MOTION_REFERENCE_ROOT/'manifest.yaml').read_text())
        for current_invalid_version in (True, 1.0, '1', None, 0, 2):
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record['schema_version'] = current_invalid_version
            with self.subTest(version=current_invalid_version), self.assertRaisesRegex(ValueError, 'schema_version'):
                validate_motion_reference_manifest(current_invalid_record)
        for current_unknown_key in ('frame', 99):
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record[current_unknown_key] = 35
            with self.subTest(key=current_unknown_key), self.assertRaisesRegex(ValueError, '알 수 없음'):
                validate_motion_reference_manifest(current_invalid_record)
        for current_missing_key in current_valid_record:
            current_invalid_record = copy.deepcopy(current_valid_record)
            del current_invalid_record[current_missing_key]
            with self.subTest(missing=current_missing_key), self.assertRaisesRegex(ValueError, current_missing_key):
                validate_motion_reference_manifest(current_invalid_record)

    def test_consumed_manifest_fields_fail_with_explicit_errors(self):
        current_valid_record = yaml.safe_load((MOTION_REFERENCE_ROOT/'manifest.yaml').read_text())
        validate_motion_reference_manifest(current_valid_record)
        for current_field_name,current_invalid_value,current_error_text in (
            ('frames',True,'frames'),('frames',34,'frames'),
            ('directions',['down_left']*4,'directions'),
            ('directions',[{}],'directions'),('files',None,'files'),('files',{},'해시')):
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record[current_field_name] = current_invalid_value
            with self.subTest(field=current_field_name,value=current_invalid_value),self.assertRaisesRegex(ValueError,current_error_text):
                validate_motion_reference_manifest(current_invalid_record)
        with self.assertRaisesRegex(ValueError,'객체'):
            validate_motion_reference_manifest(None)

    def test_source_frame_mapping_rejected_before_image_read(self):
        current_valid_record = yaml.safe_load((MOTION_REFERENCE_ROOT/'manifest.yaml').read_text())
        for current_invalid_frames in (None, {}, [], [1]*34, [1]*36, [True]*35, [1.0]*35, [0]*35, [-1]*35, ['1']*35):
            current_invalid_record = copy.deepcopy(current_valid_record)
            current_invalid_record['source_frames'] = current_invalid_frames
            with self.subTest(frames=current_invalid_frames), tempfile.TemporaryDirectory() as current_directory_name:
                current_manifest_root = Path(current_directory_name)
                (current_manifest_root/'manifest.yaml').write_text(yaml.safe_dump(current_invalid_record))
                with patch('tools.review.domains.image.pose_motion_reference.MOTION_REFERENCE_ROOT', current_manifest_root):
                    with self.assertRaisesRegex(ValueError, 'source_frames'):
                        load_motion_reference('down_left', 1)
        current_invalid_record = copy.deepcopy(current_valid_record)
        del current_invalid_record['source_frames']
        with self.assertRaisesRegex(ValueError, 'source_frames'):
            validate_motion_reference_manifest(current_invalid_record)

    def test_preview_error_clears_stale_candidate_and_disables_apply(self):
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        current_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8765', qwen21_mode_enabled=True, pose_transfer_enabled=True)
        current_preview_binding = next(current_binding for current_binding in current_interface_blocks.fns.values()
                                       if current_binding.fn and current_binding.fn.__name__ == 'preview_motion_reference')
        for current_reference_error in (ValueError('source_frames 오류'), OSError('참조 파일 없음')):
            with self.subTest(error=str(current_reference_error)), patch('tools.review.domains.image.pose_motion_reference.load_motion_reference', side_effect=current_reference_error):
                current_preview_result = current_preview_binding.fn('down_left', 1)
            self.assertIsNone(current_preview_result[0])
            self.assertEqual(current_preview_result[1], '')
            self.assertIn(str(current_reference_error), current_preview_result[2])
            self.assertIn('다시 선택', current_preview_result[2])
            self.assertFalse(current_preview_result[3]['interactive'])
        self.assertEqual(len(current_preview_binding.outputs), 4)

    def test_invalid_prompt_structure_and_template_have_explicit_errors(self):
        from tools.review.domains.image.pose_motion_reference import MOTION_PROMPT_CONFIG
        current_valid_prompt = yaml.safe_load(MOTION_PROMPT_CONFIG.read_text())
        current_invalid_records = [None, [], 1]
        for current_invalid_directions in (None, list(current_valid_prompt['directions']), 1):
            current_invalid_records.append({**current_valid_prompt, 'directions': current_invalid_directions})
        for current_invalid_record in current_invalid_records:
            with self.subTest(record=current_invalid_record), tempfile.TemporaryDirectory() as current_directory_name:
                current_prompt_path = Path(current_directory_name)/'prompts.yaml'
                current_prompt_path.write_text(yaml.safe_dump(current_invalid_record))
                with patch('tools.review.domains.image.pose_motion_reference.MOTION_PROMPT_CONFIG', current_prompt_path):
                    with self.assertRaisesRegex(ValueError, '보조 프롬프트 설정'):
                        load_motion_reference('down_left', 1)
        for current_template_text in ('{missing}', '{}', '{direction.missing}', '{'):
            with self.subTest(template=current_template_text), tempfile.TemporaryDirectory() as current_directory_name:
                current_prompt_path = Path(current_directory_name)/'prompts.yaml'
                current_prompt_path.write_text(yaml.safe_dump({**current_valid_prompt, 'template':current_template_text}))
                with patch('tools.review.domains.image.pose_motion_reference.MOTION_PROMPT_CONFIG', current_prompt_path):
                    with self.assertRaisesRegex(ValueError, 'template 치환 오류'):
                        load_motion_reference('down_left', 1)

    def test_yaml_syntax_error_names_source_file(self):
        from tools.review.domains.image.pose_motion_reference import read_motion_reference_yaml
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_yaml_path = Path(current_directory_name)/'manifest.yaml'
            current_yaml_path.write_text('frames: [')
            with self.assertRaisesRegex(ValueError, 'YAML 구문 오류.*manifest.yaml'):
                read_motion_reference_yaml(current_yaml_path)
