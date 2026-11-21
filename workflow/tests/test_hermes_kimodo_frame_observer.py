import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent import kimodo_frame_observer


class HermesKimodoFrameObserverTests(unittest.TestCase):
    def test_reviewed_keyframe_save_rejects_changed_source_before_creating_storage(self):
        import numpy as np
        from workflow.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES,prepare_kimodo_keyframe_source,save_kimodo_keyframe_record
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_attempt_identifier='a'*32
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_storage_root=current_root_path/'jobs'
            current_keyframe_root=current_root_path/'keyframes'
            current_job_path=current_storage_root/current_job_identifier
            current_attempt_path=current_job_path/'attempts'/current_attempt_identifier
            current_attempt_path.mkdir(parents=True)
            current_preview_bytes=b'\x89PNG\r\n\x1a\nfixture'
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_attempt_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'fps':30,'frames':1,'frame_sha256':[hashlib.sha256(current_preview_bytes).hexdigest()]}))
            (current_attempt_path/'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','fps':30,'joint_names':list(range(77)),'parents':list(range(77))}))
            (current_attempt_path/'output-000.png').write_bytes(current_preview_bytes)
            current_motion_path=current_attempt_path/'motion.npz'
            current_arrays_map={current_name:np.zeros((1,*current_shape),dtype=np.float32) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()}
            np.savez_compressed(current_motion_path,**current_arrays_map)
            current_review_value=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)['review_sha256']
            for current_invalid_hash in ('bad','a'*63,None):
                if current_invalid_hash is None:continue
                with self.assertRaises(ValueError):save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root,current_keyframe_storage=current_keyframe_root,expected_review_sha256=current_invalid_hash)
            current_arrays_map['root_positions'][0,0]=1
            np.savez_compressed(current_motion_path,**current_arrays_map)
            with self.assertRaisesRegex(ValueError,'변경됐습니다'):
                save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root,current_keyframe_storage=current_keyframe_root,expected_review_sha256=current_review_value)
            self.assertFalse(current_keyframe_root.exists())
            current_new_review=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)['review_sha256']
            with self.assertRaisesRegex(ValueError,'변경됐습니다'):
                save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,1,'다른 태그',current_job_storage=current_storage_root,current_keyframe_storage=current_keyframe_root,expected_review_sha256=current_new_review)
            self.assertFalse(current_keyframe_root.exists())
            current_saved_record=save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root,current_keyframe_storage=current_keyframe_root,expected_review_sha256=current_new_review)
            self.assertTrue((current_keyframe_root/current_saved_record['id']/'record.json').is_file())
            with np.load(current_keyframe_root/current_saved_record['id']/'motion.npz',allow_pickle=False) as current_saved_arrays:self.assertEqual(current_saved_arrays['root_positions'][0,0],1)

    def test_keyframe_preparation_is_read_only_and_hashes_captured_source(self):
        import numpy as np
        from workflow.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES,prepare_kimodo_keyframe_source
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_attempt_identifier='a'*32
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_storage_root=current_root_path/'jobs'
            current_job_path=current_storage_root/current_job_identifier
            current_attempt_path=current_job_path/'attempts'/current_attempt_identifier
            current_attempt_path.mkdir(parents=True)
            current_preview_bytes=b'\x89PNG\r\n\x1a\nfixture'
            current_preview_hash=hashlib.sha256(current_preview_bytes).hexdigest()
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_attempt_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'fps':30,'frames':1,'frame_sha256':[current_preview_hash]}))
            current_skeleton_path=current_attempt_path/'skeleton.json'
            current_skeleton_record={'skeleton':'somaskel77','fps':30,'joint_names':list(range(77)),'parents':list(range(77))}
            current_skeleton_path.write_text(json.dumps(current_skeleton_record))
            (current_attempt_path/'output-000.png').write_bytes(current_preview_bytes)
            current_motion_path=current_attempt_path/'motion.npz'
            current_arrays_map={current_name:np.zeros((1,*current_shape),dtype=np.float32) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()}
            np.savez_compressed(current_motion_path,**current_arrays_map)
            current_before_paths=sorted(str(current_path.relative_to(current_root_path)) for current_path in current_root_path.rglob('*'))
            current_prepared_value=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)
            current_repeated_value=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)
            self.assertEqual(current_prepared_value['review_sha256'],current_repeated_value['review_sha256'])
            self.assertEqual(current_prepared_value['preview_bytes'],current_preview_bytes)
            self.assertEqual(current_before_paths,sorted(str(current_path.relative_to(current_root_path)) for current_path in current_root_path.rglob('*')))
            current_arrays_map['root_positions'][0,0]=1
            np.savez_compressed(current_motion_path,**current_arrays_map)
            current_changed_value=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)
            self.assertNotEqual(current_prepared_value['review_sha256'],current_changed_value['review_sha256'])
            current_skeleton_record['joint_names'][0]='changed'
            current_skeleton_path.write_text(json.dumps(current_skeleton_record))
            current_skeleton_value=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)
            self.assertNotEqual(current_changed_value['review_sha256'],current_skeleton_value['review_sha256'])
            current_invalid_arrays={**current_arrays_map,'root_positions':np.full((1,3),float('nan'))}
            np.savez_compressed(current_motion_path,**current_invalid_arrays)
            with self.assertRaises(ValueError):prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_storage_root)

    def test_frame_preview_crosses_real_mcp_stdio_and_gateway(self):
        import os
        import subprocess
        import threading
        from http.server import ThreadingHTTPServer
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[2]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_attempt_identifier='a'*32
        current_client_script=r"""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def inspect_frame_source():
 current_parameters=StdioServerParameters(command=sys.executable,args=['workflow/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
 async with stdio_client(current_parameters) as (current_input,current_output):
  async with ClientSession(current_input,current_output) as current_session:
   await current_session.initialize()
   current_tools={item.name:item for item in (await current_session.list_tools()).tools}
   if current_tools['inspect_hermes_kimodo_source_frame'].annotations.read_only_hint is not True:raise RuntimeError('읽기 표기 오류')
   current_request={'job_identifier_value':'2026-11-18_00-00-00-12345678','attempt_identifier_value':'a'*32,'frame_number_value':1}
   current_result=await current_session.call_tool('inspect_hermes_kimodo_source_frame',current_request)
   if current_result.is_error:raise RuntimeError(str(current_result.content))
   current_value=current_result.structured_content or json.loads(current_result.content[0].text)
   if current_value['frame']!=1 or not current_value['image'].endswith('/output-000.png'):raise RuntimeError('프레임 응답 오류')
   current_request['frame_number_value']=2
   if not (await current_session.call_tool('inspect_hermes_kimodo_source_frame',current_request)).is_error:raise RuntimeError('잘못된 프레임 허용')
asyncio.run(inspect_frame_source())
"""
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_storage_root=current_root_path/'kimodo'
            current_job_path=current_storage_root/current_job_identifier
            current_attempt_path=current_job_path/'attempts'/current_attempt_identifier
            current_attempt_path.mkdir(parents=True)
            current_image_bytes=b'\x89PNG\r\n\x1a\nfixture'
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier}))
            (current_attempt_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'fps':30,'frames':1,'frame_sha256':[hashlib.sha256(current_image_bytes).hexdigest()]}))
            (current_attempt_path/'output-000.png').write_bytes(current_image_bytes)
            current_manager_value=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL='http://127.0.0.1:'+str(current_server_value.server_port),PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
            try:
                with patch('workflow.domains.kimodo.generation.KIMODO_JOB_STORAGE',current_storage_root):
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                    self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
            finally:
                current_server_value.shutdown();current_server_value.server_close();current_thread_value.join(timeout=5)

    def test_preview_checks_current_attempt_frame_hash_and_changed_records(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_attempt_identifier='a'*32
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/current_job_identifier
            current_attempt_path=current_job_path/'attempts'/current_attempt_identifier
            current_attempt_path.mkdir(parents=True)
            current_status_record={'status':'completed'}
            current_root_result={'attempt':current_attempt_identifier}
            current_image_bytes=b'\x89PNG\r\n\x1a\nfixture'
            current_attempt_result={'attempt':current_attempt_identifier,'fps':30,'frames':1,'frame_sha256':[hashlib.sha256(current_image_bytes).hexdigest()]}
            (current_job_path/'status.json').write_text(json.dumps(current_status_record))
            (current_job_path/'result.json').write_text(json.dumps(current_root_result))
            (current_attempt_path/'result.json').write_text(json.dumps(current_attempt_result))
            current_image_path=current_attempt_path/'output-000.png'
            current_image_path.write_bytes(current_image_bytes)
            with patch('workflow.domains.kimodo.generation.KIMODO_JOB_STORAGE',current_root_path):
                current_response_value=kimodo_frame_observer.inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,1)
                self.assertEqual(current_response_value['image'],'/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/output-000.png')
                self.assertEqual(current_response_value['image_sha256'],hashlib.sha256(current_image_bytes).hexdigest())
                self.assertNotIn(str(current_root_path),str(current_response_value))
                for current_invalid_values in (('../bad',current_attempt_identifier,1),(current_job_identifier,'../bad',1),(current_job_identifier,current_attempt_identifier,True),(current_job_identifier,current_attempt_identifier,2)):
                    with self.assertRaises(ValueError):kimodo_frame_observer.inspect_kimodo_source_frame(*current_invalid_values)
                current_image_path.write_bytes(current_image_bytes+b'changed')
                with self.assertRaises(ValueError):kimodo_frame_observer.inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,1)
                current_image_path.unlink()
                current_image_path.symlink_to(current_job_path/'status.json')
                with self.assertRaises(OSError):kimodo_frame_observer.inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,1)
                current_image_path.unlink()
                current_image_path.write_bytes(current_image_bytes)
                with patch.object(kimodo_frame_observer,'read_bounded_delegation_record',side_effect=[current_status_record,current_root_result,current_attempt_result,current_status_record,{'attempt':'b'*32}]):
                    with self.assertRaisesRegex(ValueError,'조회 중 변경'):kimodo_frame_observer.inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,1)
                self.assertEqual(json.loads((current_job_path/'status.json').read_text()),current_status_record)
