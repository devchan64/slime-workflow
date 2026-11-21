import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from tools.management.domains.hermes_agent.capture_delegation import prepare_capture_delegation_once
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesCaptureDelegationTests(unittest.TestCase):
    def test_normalized_defaults_deduplicate_and_conflicts_reject(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_store_value=HermesDelegationStore(Path(current_directory_name))
            current_submit_mock=Mock(return_value={'id':'2026-11-19_12-00-00-12345678'})
            current_first_result=prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},current_submit_mock)
            current_second_result=prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge','edges':False},current_submit_mock)
            self.assertEqual(current_first_result['state'],'accepted')
            self.assertTrue(current_second_result['duplicate'])
            self.assertEqual(current_submit_mock.call_count,1)
            with self.assertRaises(ValueError):prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge','edges':True},current_submit_mock)
            with self.assertRaises(ValueError):prepare_capture_delegation_once(current_store_value,'request_123','character-review',{},current_submit_mock)
            self.assertEqual(current_submit_mock.call_count,1)

    def test_delegation_lock_rejects_special_files_without_dispatch(self):
        import os
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            current_store_value=HermesDelegationStore(current_root_path)
            current_lock_path=current_root_path/'.delegations.lock'
            current_submit_mock=Mock()
            os.mkfifo(current_lock_path)
            with self.assertRaises((OSError,ValueError)):
                prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},current_submit_mock)
            current_lock_path.unlink()
            (current_root_path/'target').write_text('')
            current_lock_path.symlink_to(current_root_path/'target')
            with self.assertRaises((OSError,ValueError)):
                prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},current_submit_mock)
            current_submit_mock.assert_not_called()
            current_lock_path.unlink()
            with current_store_value.hold_delegation_storage_lock():
                self.assertTrue(current_lock_path.is_file())

    def test_unreadable_existing_receipt_never_resubmits(self):
        import os
        from tools.management.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path)
            current_record_path=current_root_path/'request_123.json'
            current_submit_mock=Mock()
            for current_kind_value in ('oversized','fifo'):
                with self.subTest(kind=current_kind_value):
                    if current_kind_value=='oversized':current_record_path.write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
                    else:os.mkfifo(current_record_path)
                    with self.assertRaises(ValueError):current_store_value.read_service_delegation('request_123','map-review')
                    with self.assertRaises(ValueError):prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},current_submit_mock)
                    current_submit_mock.assert_not_called()
                    current_record_path.unlink()

    def test_response_loss_remains_unknown_and_invalid_input_never_submits(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_store_value=HermesDelegationStore(Path(current_directory_name))
            current_submit_mock=Mock(side_effect=OSError('response lost'))
            with self.assertRaises(ValueError):prepare_capture_delegation_once(current_store_value,'request_bad','map-review',{'map':'../invalid'},current_submit_mock)
            current_submit_mock.assert_not_called()
            with self.assertRaises(OSError):prepare_capture_delegation_once(current_store_value,'request_lost','character-review',{},current_submit_mock)
            current_result_value=prepare_capture_delegation_once(current_store_value,'request_lost','character-review',{},current_submit_mock)
            self.assertEqual(current_result_value['state'],'unknown')
            self.assertTrue(current_result_value['duplicate'])
            self.assertEqual(current_submit_mock.call_count,1)
