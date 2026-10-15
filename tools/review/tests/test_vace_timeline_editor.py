"""배치 항목 삭제 시 프레임과 마스크의 대응을 검증한다."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools.review.ui.gradio.vace_timeline_app import remove_timeline_image


class VaceTimelineEditorTests(unittest.TestCase):
    def test_selection_readiness_rejects_empty_and_stale_items(self):
        from tools.review.ui.gradio.vace_timeline_app import update_timeline_selection_readiness
        for current_file_paths,current_selected_items,current_expected_values in (
            ([],[],(False,False)),(['1.png'],[],(True,False)),
            (['1.png'],[(0,'1.png')],(True,True)),
            ([],[(0,'1.png')],(False,False)),
            (['2.png'],[(0,'1.png')],(True,False)),
        ):
            self.assertEqual(tuple(current_update_value['interactive'] for current_update_value in update_timeline_selection_readiness(current_file_paths,current_selected_items)),current_expected_values)


    def test_required_input_readiness_tracks_loading_and_deletion(self):
        from tools.review.ui.gradio.vace_timeline_app import check_timeline_input_readiness
        for current_file_paths, current_table_rows, current_prompt_text in (
            ([], [], 'walk'), (['1.png'], [], 'walk'),
            (['1.png'], [[1, True]], '  '), (['1.png'], [[1, True]], None),
            ([], [[1, True]], 'walk'),
        ):
            self.assertFalse(check_timeline_input_readiness(current_file_paths, current_table_rows, current_prompt_text))
        self.assertTrue(check_timeline_input_readiness(['1.png'], [[1, True]], 'walk'))

    def test_restore_rejects_job_path_escape_before_reading(self):
        from tools.review.ui.gradio import vace_timeline_app
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_storage_directory = Path(current_temporary_directory)/'jobs'
            current_storage_directory.mkdir()
            current_external_directory = Path(current_temporary_directory)/'outside'
            current_external_directory.mkdir()
            current_job_identifier = '2026-10-15_13-00-00-1234abcd'
            (current_storage_directory/current_job_identifier).symlink_to(current_external_directory, target_is_directory=True)
            with patch.object(vace_timeline_app, 'VACE_TIMELINE_STORAGE_ROOT', current_storage_directory), patch('generators.vace.timeline.verify_timeline_request') as current_verify_mock:
                for current_invalid_identifier in ('../outside', str(current_external_directory), None, current_job_identifier):
                    with self.subTest(identifier=current_invalid_identifier), self.assertRaisesRegex(vace_timeline_app.gr.Error, 'ID 형식|심볼릭 링크'):
                        vace_timeline_app.restore_timeline_inputs({'id': current_invalid_identifier})
                current_verify_mock.assert_not_called()

    def test_observed_state_updates_use_event_queue(self):
        from tools.review.ui.gradio.vace_timeline_app import build_timeline_interface
        from tools.review.ui.gradio.management_menu_app import compose_management_interface
        current_tool_interface = build_timeline_interface('http://127.0.0.1:8798')
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_menu_source = Path(current_temporary_directory)/'manager-source.json'
            current_menu_source.write_text(json.dumps({'pages': []}))
            current_menu_interface = compose_management_interface(current_tool_interface, 8798, current_menu_source)
        current_observed_identifiers = {
            current_target_identifier
            for current_event_function in current_menu_interface.fns.values()
            for current_target_identifier, current_event_name in current_event_function.targets
            if current_event_name == 'change'
        }
        current_checked_functions = []
        for current_event_function in current_menu_interface.fns.values():
            if any(current_output_component.stateful and current_output_component._id in current_observed_identifiers for current_output_component in current_event_function.outputs):
                current_checked_functions.append(current_event_function.name)
                self.assertTrue(current_event_function.queue, current_event_function.name)
        self.assertIn('restore_selected_inputs', current_checked_functions)
        self.assertIn('remove_timeline_image', current_checked_functions)
        self.assertIn('select_all_timeline_images', current_checked_functions)

    def test_restore_uses_verified_disk_request(self):
        from tools.review.ui.gradio import vace_timeline_app
        from tools.review.tests.test_vace_timeline import VaceTimelineContractTests
        from generators.vace.timeline import validate_timeline_request
        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_storage_directory = Path(current_temporary_directory)
            current_job_identifier = '2026-10-15_13-00-00-1234abcd'
            current_job_directory = current_storage_directory/current_job_identifier
            current_job_directory.mkdir()
            current_request_record = validate_timeline_request(VaceTimelineContractTests().build_valid_payload())
            current_saved_record = {**{current_field_name: current_field_value for current_field_name, current_field_value in current_request_record.items() if current_field_name != 'images'}, **save_three_reference_inputs(current_job_directory, current_request_record)}
            (current_job_directory/'request.json').write_text(json.dumps(current_saved_record))
            current_stale_record = {**current_saved_record, 'prompt': 'stale', 'seed': 999, 'references': ['wrong.png']}
            with patch.object(vace_timeline_app, 'VACE_TIMELINE_STORAGE_ROOT', current_storage_directory):
                current_restored_values = vace_timeline_app.restore_timeline_inputs({'id': current_job_identifier, 'request': current_stale_record})
            self.assertEqual(current_restored_values[0], [str(current_job_directory/'reference-1.png')])
            self.assertEqual(current_restored_values[2], current_saved_record['prompt'])
            self.assertEqual(current_restored_values[5], current_saved_record['seed'])

    def test_remove_middle_preserves_frame_numbers_and_masks(self):
        self.assertEqual(remove_timeline_image(['a','b','c'],[[1,False],[13,True],[35,False]],[(1,'b')]),
                         (['a','c'],[[1,False],[35,False]],['a','c']))

    def test_remove_last_clears_inputs(self):
        self.assertEqual(remove_timeline_image(['a'],[[1,True]],[(0,'a')]),([],[],None))

    def test_stale_selection_is_rejected(self):
        with self.assertRaises(Exception):
            remove_timeline_image(['b'],[[18,True]],[(0,'a')])

    def test_remove_all_items(self):
        self.assertEqual(remove_timeline_image(['a','b'],[[1,True],[18,False]],[(0,'a'),(1,'b')]),([],[],None))
