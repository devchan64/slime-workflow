import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.management.domains.hermes_agent.capture_queue import submit_capture_queue_request
from tools.management.domains.hermes_agent.capture_status import read_capture_delegation_status
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesCaptureStatusTests(unittest.TestCase):
    def test_character_result_requires_expected_dimensions_and_visible_pixels(self):
        from PIL import Image
        from tools.management.domains.hermes_agent.capture_status import verify_capture_result_files
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_capture_path=current_root_path/'.tmp'/'test'/'character-review-capture'/'fixture-capture'
            current_capture_path.mkdir(parents=True)
            current_settings_value={'width':256,'height':256}
            current_image_values={current_name:str(current_capture_path/(current_name+'.png')) for current_name in ('baseline','adjusted','comparison')}
            current_result_value={'status':'completed','directory':str(current_capture_path),'settings':current_settings_value,'images':current_image_values}
            (current_capture_path/'result.yaml').write_text(json.dumps(current_result_value))
            for current_name,current_size in (('baseline',(512,512)),('adjusted',(512,512)),('comparison',(1024,512))):
                Image.new('RGBA',current_size,(1,2,3,255)).save(current_image_values[current_name],format='PNG')
            self.assertTrue(verify_capture_result_files(current_result_value,'character-review',current_root_path,current_settings_value))
            Image.new('RGBA',(2,2),(1,2,3,255)).save(current_image_values['adjusted'],format='PNG')
            self.assertFalse(verify_capture_result_files(current_result_value,'character-review',current_root_path,current_settings_value))

    def test_status_requires_matching_receipt_request_command_and_result(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_root=current_root_path/'.tmp'/'test'/'review-capture'
            current_job_root.mkdir(parents=True)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            with patch('tools.management.domains.hermes_agent.capture_queue.CAPTURE_QUEUE_EXECUTION_VERIFIED',True),patch('tools.management.common.gpu_job_queue.GPU_MEMORY_REQUIREMENTS',{'review-capture':1234}),patch('tools.management.common.gpu_job_queue.GPU_EXCLUSIVE_SERVICES',frozenset({'review-capture'})),patch('tools.management.common.gpu_job_queue.launch_gpu_process'):
                current_receipt_value=submit_capture_queue_request(current_store_value,current_job_root,'request_123','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
            current_job_path=current_job_root/current_receipt_value['job_id']
            current_reader=lambda:read_capture_delegation_status(current_store_value,'request_123','map-review',current_root_path)
            self.assertEqual(current_reader()['job']['status'],'unknown')
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'review-capture','command':['python','-m','tools.management.domains.hermes_agent.capture_worker','--job-dir',str(current_job_path)]}))
            (current_job_path/'status.json').write_text('{"status":"running"}')
            self.assertEqual(current_reader()['job'],{'status':'running','result_available':False})
            from tools.management.domains.hermes_agent.capture_status import find_verified_capture_request_identity
            self.assertEqual(find_verified_capture_request_identity(current_store_value,current_receipt_value['job_id'],current_root_path),{'request_id':'request_123','capture_service':'map-review'})
            self.assertIsNone(find_verified_capture_request_identity(current_store_value,'../invalid',current_root_path))
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            self.assertFalse(current_reader()['job']['result_available'])
            from PIL import Image
            current_capture_path=current_root_path/'.tmp'/'test'/'character-review-capture'/'fixture-capture'
            current_capture_path.mkdir(parents=True)
            current_image_path=current_capture_path/'map.png'
            current_settings_value=json.loads((current_job_path/'request.json').read_text())['settings']
            current_result_value={'status':'completed','directory':str(current_capture_path),'settings':current_settings_value,'images':{'map':str(current_image_path)}}
            (current_capture_path/'result.yaml').write_text(json.dumps(current_result_value))
            (current_job_path/'capture-result.json').write_text(json.dumps(current_result_value))
            self.assertFalse(current_reader()['job']['result_available'])
            Image.new('RGBA',(2,2),(1,2,3,0)).save(current_image_path,format='PNG')
            self.assertFalse(current_reader()['job']['result_available'])
            Image.new('RGB',(2,2),(1,2,3)).save(current_image_path,format='PNG')
            self.assertFalse(current_reader()['job']['result_available'])
            Image.new('RGBA',(2,2),(1,2,3,255)).save(current_image_path,format='PNG')
            self.assertTrue(current_reader()['job']['result_available'])
            (current_capture_path/'result.yaml').write_text('{"status":"failed"}')
            self.assertFalse(current_reader()['job']['result_available'])
            (current_capture_path/'result.yaml').write_text(json.dumps(current_result_value))
            current_image_path.unlink()
            current_image_path.symlink_to(current_job_path/'request.json')
            self.assertFalse(current_reader()['job']['result_available'])
            current_request_path=current_job_path/'request.json'
            current_request_value=json.loads(current_request_path.read_text())
            current_request_value['request_id']='request_other'
            current_request_path.write_text(json.dumps(current_request_value))
            self.assertEqual(current_reader()['job']['status'],'unknown')
            self.assertIsNone(find_verified_capture_request_identity(current_store_value,current_receipt_value['job_id'],current_root_path))
            current_request_value['request_id']='request_123'
            current_request_value['settings']['edges']=True
            current_request_path.write_text(json.dumps(current_request_value))
            self.assertEqual(current_reader()['job']['status'],'unknown')
            current_request_value['settings']['edges']=False
            current_request_path.write_text(json.dumps(current_request_value))
            self.assertEqual(current_reader()['job']['status'],'completed')
            (current_job_path/'gpu-command.json').write_text('[]')
            self.assertEqual(current_reader()['job']['status'],'unknown')

    def test_capture_record_reader_rejects_oversized_and_nonregular_files(self):
        import os
        from tools.management.domains.hermes_agent.capture_status import CAPTURE_RECORD_MAXIMUM_BYTES,read_bounded_capture_record
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_record_path=current_root_path/'record.json'
            current_record_path.write_bytes(b'a'*(CAPTURE_RECORD_MAXIMUM_BYTES+1))
            with self.assertRaises(ValueError):read_bounded_capture_record(current_record_path)
            current_record_path.unlink()
            os.mkfifo(current_record_path)
            with self.assertRaises(ValueError):read_bounded_capture_record(current_record_path)
            current_record_path.unlink()
            current_record_path.symlink_to(current_root_path/'other')
            with self.assertRaises(OSError):read_bounded_capture_record(current_record_path)

    def test_missing_receipt_never_reads_job(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_result_value=read_capture_delegation_status(current_store_value,'request_123','map-review',current_root_path)
            self.assertEqual(current_result_value['receipt']['state'],'not_found')
            self.assertIsNone(current_result_value['job'])
