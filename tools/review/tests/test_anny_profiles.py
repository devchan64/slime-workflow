import unittest
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.anny import anny_attributes
from tools.review.domains.anny.anny_attributes import load_active_profile, load_profile_by_identifier, load_profile_attribute_defaults
from tools.review.ui_assets import resolve_review_ui_asset


class AnnyProfileTests(unittest.TestCase):
    def test_baseline_rejects_duplicate_keys_and_invalid_types(self):
        current_original_text=anny_attributes.BASELINE_SELECTION_PATH.read_text()
        current_invalid_records=[current_original_text+'schema_version: 1\n',current_original_text.replace('schema_version: 1','schema_version: true'),current_original_text.replace('schema_version: 1','schema_version: 1.0'),'schema_version: 1\nactive_profile_path: null\n','schema_version: 1\nactive_profile_path: ""\n']
        for current_invalid_text in current_invalid_records:
            with self.subTest(source=current_invalid_text), patch.object(anny_attributes,'BASELINE_SELECTION_PATH') as current_selection_mock:
                current_selection_mock.read_text.return_value=current_invalid_text
                with self.assertRaises(ValueError):
                    load_active_profile()

    def test_profile_rejects_duplicate_fields_and_boolean_version(self):
        current_original_text=(anny_attributes.PROFILE_DIRECTORY_PATH/'neutral.yaml').read_text()
        current_invalid_records=[current_original_text+'schema_version: 1\n',current_original_text.replace('schema_version: 1','schema_version: true'),current_original_text.replace('attribute_overrides: {}','attribute_overrides:\n  head-scale-horiz-incr: 0\n  head-scale-horiz-incr: 1')]
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_profile_directory=Path(current_directory_name)
            current_profile_path=current_profile_directory/'test.yaml'
            with patch.object(anny_attributes,'PROFILE_DIRECTORY_PATH',current_profile_directory):
                for current_invalid_text in current_invalid_records:
                    with self.subTest(source=current_invalid_text):
                        current_profile_path.write_text(current_invalid_text)
                        with self.assertRaises(ValueError):
                            anny_attributes.load_profile_record(current_profile_path)
                current_profile_path.write_text(current_original_text)
                self.assertEqual(anny_attributes.load_profile_record(current_profile_path)['profile_id'],'neutral_v4')

    def test_attribute_json_rejects_duplicate_and_nonfinite_values(self):
        current_profile_record=load_active_profile()
        current_attribute_text=(anny_attributes.ROOT/current_profile_record['attributes_path']).read_text()
        current_invalid_records=['{"phenotype_kwargs":{},"phenotype_kwargs":{}}', '{"phenotype_kwargs":{"age":0,"age":1}}', '{"phenotype_kwargs":{"age":NaN}}', '{"phenotype_kwargs":{"age":Infinity}}']
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attribute_path=Path(current_directory_name)/'attributes.json'
            current_test_profile={**current_profile_record,'attributes_path':str(current_attribute_path)}
            for current_invalid_text in current_invalid_records:
                with self.subTest(source=current_invalid_text):
                    current_attribute_path.write_text(current_invalid_text)
                    with self.assertRaises(ValueError):
                        load_profile_attribute_defaults(current_test_profile)
            current_attribute_path.write_text(current_attribute_text)
            self.assertEqual(load_profile_attribute_defaults(current_test_profile),load_profile_attribute_defaults(current_profile_record))

    def test_attribute_structure_rejects_malformed_model_inputs(self):
        from generators.animation.anny_attribute_contract import validate_anny_attribute_structure
        current_valid_record=load_profile_attribute_defaults(load_active_profile())
        current_invalid_records=[]
        for current_field_name,current_invalid_value in [('phenotype_kwargs',[]),('pose_parameters',{}),('pose_parameterization','world')]:
            current_invalid_record=copy.deepcopy(current_valid_record)
            current_invalid_record[current_field_name]=current_invalid_value
            current_invalid_records.append(current_invalid_record)
        for current_invalid_value in (True,2,float('inf')):
            current_invalid_record=copy.deepcopy(current_valid_record)
            current_invalid_record['phenotype_kwargs']['age']=current_invalid_value
            current_invalid_records.append(current_invalid_record)
        for current_matrix_value in ([[1,0]],[[True]*4]*4,[[float('inf')]*4]*4):
            current_invalid_record=copy.deepcopy(current_valid_record)
            current_invalid_record['pose_parameters']['root']=current_matrix_value
            current_invalid_records.append(current_invalid_record)
        current_invalid_records.extend([None,[],{**current_valid_record,'unknown':0}])
        for current_invalid_record in current_invalid_records:
            with self.subTest(record=str(current_invalid_record)[:80]),self.assertRaises(ValueError):
                validate_anny_attribute_structure(current_invalid_record)
        current_original_record=copy.deepcopy(current_valid_record)
        validate_anny_attribute_structure(current_valid_record)
        self.assertEqual(current_valid_record,current_original_record)

    def test_renderer_rejects_invalid_structure_before_model_import(self):
        current_renderer_path=anny_attributes.ROOT/'generators/animation/render_anny_attribute_preview.py'
        current_valid_record=load_profile_attribute_defaults(load_active_profile())
        current_valid_record['pose_parameters']['root']=[[1,0]]
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_input_path=Path(current_directory_name)/'attributes.json'
            current_output_path=Path(current_directory_name)/'render'
            current_input_path.write_text(json.dumps(current_valid_record))
            current_process_script="""
import importlib.abc,runpy,sys
class RejectModelImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('torch','anny'):
            raise RuntimeError('MODEL_IMPORT_REACHED')
sys.meta_path.insert(0,RejectModelImport())
current_renderer_path=sys.argv[1]
sys.path.insert(0,str(__import__('pathlib').Path(current_renderer_path).parent))
sys.argv=sys.argv[1:]
runpy.run_path(current_renderer_path,run_name='__main__')
"""
            current_process_result=subprocess.run([sys.executable,'-c',current_process_script,str(current_renderer_path),'--attributes',str(current_input_path),'--output-dir',str(current_output_path)],capture_output=True,text=True,timeout=15)
            self.assertNotEqual(current_process_result.returncode,0)
            self.assertIn('ANNY 포즈 행렬 형식 오류',current_process_result.stderr)
            self.assertNotIn('MODEL_IMPORT_REACHED',current_process_result.stderr)
            self.assertFalse((current_output_path/'anny-rest-rig.npz').exists())

    def test_neutral_is_the_active_default_profile(self):
        active_profile_record=load_active_profile()
        self.assertEqual(active_profile_record['profile_id'],'neutral_v4')
        self.assertEqual(active_profile_record['label'],'중성형 v4')
        self.assertEqual(active_profile_record['source_asset_id'],'anny-neutral-v4')

    def test_retired_profiles_are_unavailable(self):
        for profile_identifier in ('female_type_a_v1','female_type_a_v2','male_type_a_v1'):
            with self.assertRaises(ValueError):
                load_profile_by_identifier(profile_identifier)

    def test_attribute_editor_has_direct_input_modal(self):
        rendered_page_text=resolve_review_ui_asset('anny-attributes.html').read_text()
        self.assertIn('attribute-direct-input-dialog',rendered_page_text)
        self.assertIn('직접 입력',rendered_page_text)
        self.assertIn('openDirectAttributeInput',rendered_page_text)
        self.assertIn('baseline-profile',rendered_page_text)


if __name__=='__main__':
    unittest.main()
