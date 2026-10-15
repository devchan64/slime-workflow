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
