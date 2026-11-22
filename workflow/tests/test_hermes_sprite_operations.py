"""격리 에셋에서 Hermes 앵커 검토와 실제 편집기 저장을 검증한다."""
import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from PIL import Image
from workflow.domains.character_animation import sprite_sheet_editor
from workflow.domains.hermes_agent import sprite_operations
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesSpriteOperationsTests(unittest.TestCase):
    def test_actual_sprite_proposal_and_receipt_match_session_history(self):
        import subprocess
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_sprite_proposal
        session='a'*32;job='2026-11-18_00-00-00-12345678'
        request_id='chat_'+hashlib.sha256((session+':'+job+':sprite').encode()).hexdigest()
        answer='HERMES_SPRITE_PROPOSAL\n'+json.dumps(self.current_draft_record)+'\nEND_HERMES_SPRITE_PROPOSAL'
        proposal=parse_hermes_sprite_proposal(answer)
        receipt=sprite_operations.inspect_hermes_sprite_receipt({'version':9,'id':request_id,'state':'completed','saved':True,'job_id':'sprite-job','path':self.current_path_value},request_id)
        script="""import {readBuildingSessionReceipts} from './gui/buildingProposalProtocol.mjs';
          const [proposal,receipt]=JSON.parse(process.argv[1]),session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
          const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_SPRITE_PROPOSAL'}}]};
          const command=async(_,name)=>name==='hermes-session-view'?page:name==='hermes-sprite-proposal'?{job_id:job,proposal}:receipt;
          const result=await readBuildingSessionReceipts(command,session);
          if(result.rows.length!==1 || !result.rows[0][1].includes(proposal.path))throw Error(JSON.stringify(result.rows));"""
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([proposal,receipt])],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def setUp(self):
        current_temp_directory=tempfile.TemporaryDirectory();self.addCleanup(current_temp_directory.cleanup)
        self.current_root_path=Path(current_temp_directory.name)
        self.current_asset_root=self.current_root_path/'slime-assets'
        current_sprite_directory=self.current_asset_root/'assets/characters/default/animations/test'
        current_sprite_directory.mkdir(parents=True)
        self.current_frontend_root=self.current_root_path/'slime-frontend';self.current_frontend_root.mkdir()
        self.current_image_path=current_sprite_directory/'sheet.png'
        current_image_value=Image.new('RGBA',(8,4),(10,20,30,255));current_image_value.paste((210,30,40,255),(4,0,8,4));current_image_value.save(self.current_image_path)
        self.current_metadata_path=current_sprite_directory/'sheet.animation.json'
        self.current_animation_record={'animationId':'character.test','version':'v1','sheet':{'width':8,'height':4},'frames':[{'frameId':'idle.0','rect':{'x':0,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':3}},{'frameId':'idle.1','rect':{'x':4,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':3}}],'clips':[{'clipId':'idle','loop':True,'nextClipId':None,'frames':[{'frameId':'idle.0','durationMs':167},{'frameId':'idle.1','durationMs':166}]}]}
        self.current_metadata_path.write_text(json.dumps(self.current_animation_record))
        current_records=[{'managementId':current_file_path.name,'version':'v1','path':current_file_path.relative_to(self.current_asset_root).as_posix(),'sha256':hashlib.sha256(current_file_path.read_bytes()).hexdigest(),'source':{}} for current_file_path in (self.current_image_path,self.current_metadata_path)]
        (self.current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':current_records}))
        (self.current_frontend_root/'sprite-assets.lock.yaml').write_text(yaml.safe_dump({'files':[{'path':current_record['path'],'source_path':current_record['path'],'sha256':current_record['sha256']} for current_record in current_records]}))
        self.current_path_value=current_records[0]['path']
        current_image_hash=current_records[0]['sha256'];current_metadata_hash=current_records[1]['sha256']
        current_snapshot_digest=hashlib.sha256((current_image_hash+':'+current_metadata_hash).encode()).hexdigest()
        self.current_draft_record={'path':self.current_path_value,'snapshot':current_snapshot_digest,'columns':2,'anchors':[{'frame_id':'idle.0','x':2,'y':3}]}
        self.current_store_value=HermesDelegationStore(self.current_root_path/'receipts')
        current_environment_patch=patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(self.current_asset_root)});current_environment_patch.start();self.addCleanup(current_environment_patch.stop)
        current_jobs_patch=patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',self.current_root_path/'jobs');current_jobs_patch.start();self.addCleanup(current_jobs_patch.stop)
        current_store_patch=patch.object(sprite_operations,'HermesDelegationStore',return_value=self.current_store_value);current_store_patch.start();self.addCleanup(current_store_patch.stop)
        def execute_test_editor(current_command_name,current_payload_record):
            if current_command_name=='sheet-image':return sprite_sheet_editor.execute_sprite_asset_command('sheet-image',current_payload_record)
            if current_command_name=='sheet-export':return sprite_sheet_editor.execute_sprite_sheet_export(current_payload_record)
            if current_command_name=='sheet-gif':return sprite_sheet_editor.execute_sprite_gif_export(current_payload_record)
            if current_command_name=='sheet-update':return sprite_sheet_editor.update_registered_sprite_sheet(current_payload_record)
            raise ValueError('unexpected command')
        current_editor_patch=patch.object(sprite_operations,'call_hermes_sprite_editor',side_effect=execute_test_editor);current_editor_patch.start();self.addCleanup(current_editor_patch.stop)

    def test_registered_sprite_update_restores_originals_on_metadata_replace_error(self):
        import os
        current_update_payload,_=sprite_operations.prepare_hermes_sprite_anchor_edit(self.current_draft_record)
        current_paths_value=(self.current_image_path,self.current_metadata_path,self.current_asset_root/'asset-registry.yaml',self.current_frontend_root/'sprite-assets.lock.yaml')
        current_previous_files={current_file_path:current_file_path.read_bytes() for current_file_path in current_paths_value}
        current_original_replace=os.replace
        def fail_metadata_replace(current_source_path,current_target_path):
            if Path(current_target_path)==self.current_metadata_path:raise OSError('모의 좌표맵 교체 실패')
            return current_original_replace(current_source_path,current_target_path)
        with patch('os.replace',side_effect=fail_metadata_replace):
            with self.assertRaisesRegex(OSError,'모의 좌표맵 교체 실패'):
                sprite_sheet_editor.update_registered_sprite_sheet(current_update_payload)
        for current_file_path,current_file_bytes in current_previous_files.items():self.assertEqual(current_file_path.read_bytes(),current_file_bytes)

    def test_sprite_transaction_restores_all_changed_files_after_write_error(self):
        import os
        current_paths_value=[self.current_root_path/('file'+str(current_index_value)) for current_index_value in range(4)]
        for current_index_value,current_file_path in enumerate(current_paths_value):
            current_file_path.write_bytes(('old'+str(current_index_value)).encode())
        current_previous_files={current_file_path:current_file_path.read_bytes() for current_file_path in current_paths_value}
        current_pending_files={current_file_path:b'updated' for current_file_path in current_paths_value}
        current_original_replace=os.replace
        def replace_with_write_failure(current_source_path,current_target_path):
            if Path(current_target_path)==current_paths_value[3]:raise OSError('모의 교체 실패')
            return current_original_replace(current_source_path,current_target_path)
        with patch('os.replace',side_effect=replace_with_write_failure):
            with self.assertRaisesRegex(OSError,'모의 교체 실패'):
                sprite_sheet_editor.write_sprite_asset_transaction(current_pending_files,current_previous_files)
        for current_file_path,current_file_bytes in current_previous_files.items():self.assertEqual(current_file_path.read_bytes(),current_file_bytes)
        self.assertEqual(list(self.current_root_path.glob('.*.sprite-*.tmp')),[])

    def test_sprite_transaction_continues_restoring_after_one_rollback_failure(self):
        import os
        current_paths_value=[self.current_root_path/('file'+str(current_index_value)) for current_index_value in range(4)]
        for current_file_path in current_paths_value:current_file_path.write_bytes(b'old')
        current_previous_files={current_file_path:b'old' for current_file_path in current_paths_value}
        current_pending_files={current_file_path:b'updated' for current_file_path in current_paths_value}
        current_original_replace=os.replace
        current_target_counts={current_file_path:0 for current_file_path in current_paths_value}
        def replace_with_rollback_failure(current_source_path,current_target_path):
            current_target_path=Path(current_target_path)
            current_target_counts[current_target_path]+=1
            if current_target_path==current_paths_value[3] or (current_target_path==current_paths_value[2] and current_target_counts[current_target_path]==2):raise OSError('모의 교체 실패')
            return current_original_replace(current_source_path,current_target_path)
        with patch('os.replace',side_effect=replace_with_rollback_failure):
            with self.assertRaisesRegex(RuntimeError,'일부 파일 복원 실패'):
                sprite_sheet_editor.write_sprite_asset_transaction(current_pending_files,current_previous_files)
        self.assertEqual(current_paths_value[0].read_bytes(),b'old')
        self.assertEqual(current_paths_value[1].read_bytes(),b'old')
        self.assertEqual(current_paths_value[2].read_bytes(),b'updated')
        self.assertEqual(current_paths_value[3].read_bytes(),b'old')
        self.assertEqual(list(self.current_root_path.glob('.*.sprite-*.tmp')),[])

    def test_sprite_pending_observer_compares_backup_and_hides_local_paths(self):
        from workflow.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
        self.assertEqual(inspect_hermes_sprite_pending_status()['state'],'clear')
        with sprite_sheet_editor.hold_sprite_asset_update_lock():
            self.assertEqual(inspect_hermes_sprite_pending_status()['state'],'busy')
        current_before_bytes=self.current_image_path.read_bytes()
        current_lock_path=self.current_frontend_root/'sprite-assets.lock.yaml'
        current_lock_value=yaml.safe_load(current_lock_path.read_text())
        current_lock_path.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':current_lock_value['files']}))
        current_backup_root=self.current_root_path/'jobs'/'sample'/'before'
        current_backup_root.mkdir(parents=True)
        (current_backup_root/'0').write_bytes(current_before_bytes)
        (current_backup_root/'paths.json').write_text(json.dumps([str(self.current_image_path)]))
        current_marker_path=self.current_asset_root/'.local/content-ledger/sprite-update-pending.json'
        current_marker_value={'version':1,'backup_root':str(current_backup_root),'files':[{'path':str(self.current_image_path),'before_sha256':hashlib.sha256(current_before_bytes).hexdigest(),'after_sha256':hashlib.sha256(b'future').hexdigest(),'backup_index':0}]}
        current_marker_path.write_text(json.dumps(current_marker_value))
        current_marker_bytes=current_marker_path.read_bytes()
        current_result_value=inspect_hermes_sprite_pending_status()
        self.assertEqual(current_result_value['state'],'pending')
        self.assertEqual(current_result_value['backup_manifest'],'valid')
        self.assertEqual(current_result_value['files'],[{'path':self.current_image_path.relative_to(self.current_asset_root).as_posix(),'current':'before','backup':'valid','registry_lock':'matched'}])
        (current_backup_root/'paths.json').write_text(json.dumps(['/unexpected/path']))
        current_mismatch_value=inspect_hermes_sprite_pending_status()
        self.assertEqual(current_mismatch_value['backup_manifest'],'invalid')
        self.assertEqual(current_mismatch_value['files'][0]['backup'],'unavailable')
        (current_backup_root/'paths.json').write_text(json.dumps([str(self.current_image_path)]))
        self.assertNotIn(str(self.current_root_path),str(current_result_value))
        self.assertEqual(current_marker_path.read_bytes(),current_marker_bytes)
        current_marker_value['files'][0]['after_sha256']=current_marker_value['files'][0]['before_sha256']
        current_marker_path.write_text(json.dumps(current_marker_value))
        self.assertEqual(inspect_hermes_sprite_pending_status()['files'][0]['current'],'unchanged')
        current_marker_value['files'][0]['after_sha256']=hashlib.sha256(b'future').hexdigest()
        current_marker_path.write_text(json.dumps(current_marker_value))
        self.current_image_path.write_bytes(b'future')
        (current_backup_root/'0').write_bytes(b'bad backup')
        current_result_value=inspect_hermes_sprite_pending_status()
        self.assertEqual(current_result_value['files'][0]['current'],'after')
        self.assertEqual(current_result_value['files'][0]['backup'],'invalid')
        self.assertEqual(current_result_value['files'][0]['registry_lock'],'mismatch')
        current_lock_path.write_text('invalid: [')
        self.assertEqual(inspect_hermes_sprite_pending_status()['files'][0]['registry_lock'],'unavailable')
        current_marker_value['files'][0]['path']='/etc/passwd'
        current_marker_path.write_text(json.dumps(current_marker_value))
        self.assertEqual(inspect_hermes_sprite_pending_status()['state'],'unavailable')

    def test_unreadable_sprite_marker_blocks_observation_and_write(self):
        from workflow.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
        with sprite_sheet_editor.hold_sprite_asset_update_lock():pass
        current_marker_path=self.current_asset_root/'.local/content-ledger/sprite-update-pending.json'
        current_original_bytes=self.current_image_path.read_bytes()
        current_lstat_method=Path.lstat
        current_exists_method=Path.exists
        def reject_marker_stat(current_path_value,*current_arguments,**current_keywords):
            if current_path_value==current_marker_path:raise PermissionError('unreadable')
            return current_lstat_method(current_path_value,*current_arguments,**current_keywords)
        def hide_marker_exists(current_path_value,*current_arguments,**current_keywords):
            if current_path_value==current_marker_path:return False
            return current_exists_method(current_path_value,*current_arguments,**current_keywords)
        with patch.object(Path,'exists',autospec=True,side_effect=hide_marker_exists),patch.object(Path,'lstat',autospec=True,side_effect=reject_marker_stat):
            self.assertEqual(inspect_hermes_sprite_pending_status()['state'],'unavailable')
            with self.assertRaises(PermissionError):
                with sprite_sheet_editor.hold_sprite_asset_update_lock():pass
            with self.assertRaises(PermissionError):
                sprite_sheet_editor.write_sprite_asset_transaction({self.current_image_path:b'changed'},{self.current_image_path:current_original_bytes},current_transaction_marker=current_marker_path,current_backup_root=self.current_root_path/'backup')
        self.assertEqual(self.current_image_path.read_bytes(),current_original_bytes)

    def test_sprite_pending_hash_rejects_file_modified_during_read(self):
        import os
        from workflow.domains.hermes_agent.sprite_pending_observer import read_sprite_pending_file_hash
        current_test_path=self.current_root_path/'changed-file'
        current_test_path.write_bytes(b'original')
        current_original_fstat=os.fstat
        current_fstat_calls=[]
        def change_after_first_stat(current_descriptor_value):
            current_stat_value=current_original_fstat(current_descriptor_value)
            current_fstat_calls.append(True)
            if len(current_fstat_calls)==1:current_test_path.write_bytes(b'changed content')
            return current_stat_value
        with patch('os.fstat',side_effect=change_after_first_stat):
            with self.assertRaisesRegex(ValueError,'변경되었습니다'):
                read_sprite_pending_file_hash(current_test_path)

    def test_sprite_pending_observer_rejects_invalid_ledger_and_marker(self):
        from workflow.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
        current_local_path=self.current_asset_root/'.local'
        current_local_path.mkdir()
        (current_local_path/'content-ledger').write_text('not a directory')
        self.assertEqual(inspect_hermes_sprite_pending_status()['state'],'unavailable')
        (current_local_path/'content-ledger').unlink()
        with sprite_sheet_editor.hold_sprite_asset_update_lock():pass
        current_marker_path=current_local_path/'content-ledger/sprite-update-pending.json'
        current_marker_path.write_text('{')
        self.assertEqual(inspect_hermes_sprite_pending_status()['state'],'unavailable')
        self.assertTrue(current_marker_path.is_file())

    def test_sprite_interrupted_process_leaves_marker_and_blocks_next_writer(self):
        import subprocess
        import sys
        current_first_path=self.current_asset_root/'first.bin'
        current_second_path=self.current_asset_root/'second.bin'
        current_first_path.write_bytes(b'old first')
        current_second_path.write_bytes(b'old second')
        current_backup_root=self.current_root_path/'backup'
        current_backup_root.mkdir()
        (current_backup_root/'0').write_bytes(b'old first')
        (current_backup_root/'1').write_bytes(b'old second')
        current_child_code="""
import os
from pathlib import Path
from workflow.domains.character_animation.sprite_sheet_editor import hold_sprite_asset_update_lock,write_sprite_asset_transaction
current_root_path=Path(os.environ['SLIME_ASSETS_ROOT'])
current_first_path=current_root_path/'first.bin'
current_second_path=current_root_path/'second.bin'
current_original_replace=os.replace
def stop_after_first_replace(current_source_path,current_target_path):
    current_original_replace(current_source_path,current_target_path)
    if Path(current_target_path)==current_first_path:os._exit(37)
os.replace=stop_after_first_replace
with hold_sprite_asset_update_lock():
    write_sprite_asset_transaction({current_first_path:b'new first',current_second_path:b'new second'},{current_first_path:b'old first',current_second_path:b'old second'},current_transaction_marker=current_root_path/'.local/content-ledger/sprite-update-pending.json',current_backup_root=Path(os.environ['TEST_SPRITE_BACKUP_ROOT']))
"""
        current_environment_values=dict(os.environ,SLIME_ASSETS_ROOT=str(self.current_asset_root),TEST_SPRITE_BACKUP_ROOT=str(current_backup_root),PYTHONPATH=str(Path(__file__).resolve().parents[2]))
        current_child_process=subprocess.run([sys.executable,'-c',current_child_code],env=current_environment_values,capture_output=True,text=True,timeout=10)
        self.assertEqual(current_child_process.returncode,37,current_child_process.stderr)
        self.assertEqual(current_first_path.read_bytes(),b'new first')
        self.assertEqual(current_second_path.read_bytes(),b'old second')
        current_marker_path=self.current_asset_root/'.local/content-ledger/sprite-update-pending.json'
        current_marker_value=json.loads(current_marker_path.read_text())
        self.assertEqual(current_marker_value['backup_root'],str(current_backup_root))
        self.assertEqual(current_marker_value['files'][0]['before_sha256'],hashlib.sha256(b'old first').hexdigest())
        with self.assertRaisesRegex(ValueError,'완료되지 않은 스프라이트 저장'):
            with sprite_sheet_editor.hold_sprite_asset_update_lock():pass
        self.assertTrue(current_marker_path.is_file())

    def test_sprite_failed_write_with_successful_rollback_clears_marker(self):
        import os
        current_first_path=self.current_asset_root/'first.bin'
        current_second_path=self.current_asset_root/'second.bin'
        current_first_path.write_bytes(b'old first')
        current_second_path.write_bytes(b'old second')
        current_backup_root=self.current_root_path/'backup'
        current_backup_root.mkdir()
        current_original_replace=os.replace
        def fail_second_replace(current_source_path,current_target_path):
            if Path(current_target_path)==current_second_path:raise OSError('모의 오류')
            return current_original_replace(current_source_path,current_target_path)
        with sprite_sheet_editor.hold_sprite_asset_update_lock():
            current_marker_path=self.current_asset_root/'.local/content-ledger/sprite-update-pending.json'
            with patch('os.replace',side_effect=fail_second_replace),self.assertRaisesRegex(OSError,'모의 오류'):
                sprite_sheet_editor.write_sprite_asset_transaction({current_first_path:b'new first',current_second_path:b'new second'},{current_first_path:b'old first',current_second_path:b'old second'},current_transaction_marker=current_marker_path,current_backup_root=current_backup_root)
            self.assertFalse(current_marker_path.exists())
        self.assertEqual(current_first_path.read_bytes(),b'old first')
        self.assertEqual(current_second_path.read_bytes(),b'old second')

    def test_sprite_asset_lock_serializes_separate_processes(self):
        import select
        import subprocess
        import sys
        current_child_code="""
from workflow.domains.character_animation.sprite_sheet_editor import hold_sprite_asset_update_lock
print('ready',flush=True)
with hold_sprite_asset_update_lock():
    print('acquired',flush=True)
"""
        current_environment_values=dict(os.environ,SLIME_ASSETS_ROOT=str(self.current_asset_root),PYTHONPATH=str(Path(__file__).resolve().parents[2]))
        with sprite_sheet_editor.hold_sprite_asset_update_lock():
            current_child_process=subprocess.Popen([sys.executable,'-u','-c',current_child_code],env=current_environment_values,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(current_child_process.stdout.readline().strip(),'ready')
                current_readable_streams,_,_=select.select([current_child_process.stdout],[],[],0.25)
                self.assertEqual(current_readable_streams,[],'다른 프로세스가 잠금 해제 전에 진입했습니다.')
            except BaseException:
                current_child_process.kill()
                current_child_process.communicate(timeout=5)
                raise
        current_output_text,current_error_text=current_child_process.communicate(timeout=5)
        self.assertEqual(current_child_process.returncode,0,current_error_text)
        self.assertEqual(current_output_text.strip(),'acquired')

    def test_sprite_asset_lock_rejects_symlinked_ledger(self):
        current_local_root=self.current_asset_root/'.local'
        current_local_root.mkdir()
        (current_local_root/'content-ledger').symlink_to(self.current_root_path,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
            with sprite_sheet_editor.hold_sprite_asset_update_lock():pass
        self.assertFalse((self.current_root_path/'sprite-asset-update.lock').exists())

    def test_registered_sprite_update_rejects_missing_or_duplicate_consumer_lock(self):
        current_update_payload,_=sprite_operations.prepare_hermes_sprite_anchor_edit(self.current_draft_record)
        current_registry_path=self.current_asset_root/'asset-registry.yaml'
        current_lock_path=self.current_frontend_root/'sprite-assets.lock.yaml'
        current_lock_record=yaml.safe_load(current_lock_path.read_text())
        current_original_files={current_path:current_path.read_bytes() for current_path in (self.current_image_path,self.current_metadata_path,current_registry_path)}
        for current_target_path in (self.current_image_path,self.current_metadata_path):
            current_relative_path=current_target_path.relative_to(self.current_asset_root).as_posix()
            for current_test_case in ('missing','duplicate'):
                with self.subTest(current_relative_path=current_relative_path,current_test_case=current_test_case):
                    current_entries=[dict(current_item) for current_item in current_lock_record['files']]
                    if current_test_case=='missing':current_entries=[current_item for current_item in current_entries if current_item['source_path']!=current_relative_path]
                    else:current_entries.append(dict(next(current_item for current_item in current_entries if current_item['source_path']==current_relative_path)))
                    current_lock_path.write_text(yaml.safe_dump({'files':current_entries}))
                    current_before_lock=current_lock_path.read_bytes()
                    with self.assertRaisesRegex(ValueError,'각각 하나'):
                        sprite_sheet_editor.update_registered_sprite_sheet(current_update_payload)
                    for current_file_path,current_file_bytes in current_original_files.items():self.assertEqual(current_file_path.read_bytes(),current_file_bytes)
                    self.assertEqual(current_lock_path.read_bytes(),current_before_lock)

    def test_sprite_preflight_blocks_without_receipt_and_allows_retry_after_clear(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_save_args=('sprite_blocked_123',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
        current_original_paths=(self.current_image_path,self.current_metadata_path,self.current_asset_root/'asset-registry.yaml',self.current_frontend_root/'sprite-assets.lock.yaml')
        current_original_files={current_path:current_path.read_bytes() for current_path in current_original_paths}
        for current_state_name in ('pending','busy','unavailable'):
            with self.subTest(current_state_name=current_state_name),patch('workflow.domains.hermes_agent.sprite_pending_observer.inspect_hermes_sprite_pending_status',return_value={'state':current_state_name,'files':[]}):
                current_result_value=sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)
                self.assertEqual((current_result_value['state'],current_result_value['reason']),('blocked',current_state_name))
                self.assertFalse(current_result_value['saved'])
                self.assertEqual(sprite_operations.read_hermes_sprite_anchor_receipt('sprite_blocked_123')['state'],'not_found')
                for current_file_path,current_file_bytes in current_original_files.items():self.assertEqual(current_file_path.read_bytes(),current_file_bytes)
        with patch('workflow.domains.hermes_agent.sprite_pending_observer.inspect_hermes_sprite_pending_status',return_value={'state':'clear','files':[]}):
            self.assertTrue(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['saved'])

    def test_conversation_review_preserves_sprite_changes(self):
        import subprocess
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'sprite.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SpriteProposal.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {SpriteProposalReview}=require(process.argv[1]);
              const preview=JSON.parse(require('fs').readFileSync(0,'utf8'));
              process.stdout.write(server.renderToStaticMarkup(React.createElement(SpriteProposalReview,{preview,busy:true})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,input=json.dumps(current_preview_record),text=True)
        for value in ('앵커 변경','프레임 배치',current_preview_record['output_sha256'],current_preview_record['clips'][0]['id'],str(current_preview_record['clips'][0]['frames'][0]['duration_ms'])+'ms','확인 후 저장','취소','disabled'):
            self.assertIn(value,markup)

    def test_preview_and_save_update_registry_and_lock_once(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        self.assertEqual(current_preview_record['changed_anchors'][0]['after'],{'x':2,'y':3})
        self.assertEqual(current_preview_record['output_sheet'],{'width':8,'height':4})
        self.assertEqual(hashlib.sha256(base64.b64decode(current_preview_record['preview_image'])).hexdigest(),current_preview_record['output_sha256'])
        self.assertEqual(len(current_preview_record['frame_layout']),2)
        self.assertEqual(current_preview_record['frame_layout'][1]['after'],{'x':4,'y':0,'width':4,'height':4})
        current_save_args=('sprite_request_123',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
        self.assertTrue(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['saved'])
        self.assertEqual(sprite_operations.read_hermes_sprite_anchor_receipt('sprite_request_123')['path'],self.current_draft_record['path'])
        self.assertTrue(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['duplicate'])
        current_animation_value=json.loads(self.current_metadata_path.read_text())
        self.assertEqual(current_animation_value['frames'][0]['anchor'],{'x':2,'y':3})
        self.assertEqual(current_animation_value['clips'],self.current_animation_record['clips'])
        current_registry_records={current_record['path']:current_record for current_record in yaml.safe_load((self.current_asset_root/'asset-registry.yaml').read_text())['assets']}
        for current_lock_record in yaml.safe_load((self.current_frontend_root/'sprite-assets.lock.yaml').read_text())['files']:
            self.assertEqual(current_lock_record['sha256'],current_registry_records[current_lock_record['source_path']]['sha256'])
        with self.assertRaisesRegex(ValueError,'원본이 변경'):sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        self.assertEqual(self.current_store_value.list_delegation_receipts()['records'],[])

    def test_changed_receipt_after_sprite_save_is_not_overwritten(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_save_args=('sprite_request_123',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
        current_record_path=self.current_store_value.resolve_delegation_record_path('sprite_request_123')
        current_original_editor=sprite_operations.call_hermes_sprite_editor.side_effect
        def current_editor_response(current_command_name,current_payload_value):
            current_result_value=current_original_editor(current_command_name,current_payload_value)
            if current_command_name=='sheet-update':
                current_receipt_value=json.loads(current_record_path.read_text())
                current_receipt_value['external_change']='preserve'
                current_record_path.write_text(json.dumps(current_receipt_value))
            return current_result_value
        with patch.object(sprite_operations,'call_hermes_sprite_editor',side_effect=current_editor_response) as current_editor_mock:
            with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)
            self.assertEqual(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(item.args[0]=='sheet-update' for item in current_editor_mock.call_args_list),1)
            self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_registered_clip_playback_preserves_order_and_timing(self):
        from io import BytesIO
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_playback_record=sprite_operations.render_hermes_sprite_clip_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],'idle')
        current_gif_bytes=base64.b64decode(current_playback_record['gif'],validate=True)
        self.assertEqual(hashlib.sha256(current_gif_bytes).hexdigest(),current_playback_record['sha256'])
        self.assertEqual(current_playback_record['durations_ms'],[170,160])
        self.assertTrue(current_playback_record['loop'])
        with Image.open(BytesIO(current_gif_bytes)) as current_gif_image:
            self.assertEqual(current_gif_image.n_frames,2)
            self.assertEqual(current_gif_image.info['duration'],170)
            current_first_pixel=current_gif_image.convert('RGB').getpixel((2,2))
            current_gif_image.seek(1)
            self.assertEqual(current_gif_image.info['duration'],160)
            self.assertNotEqual(current_first_pixel,current_gif_image.convert('RGB').getpixel((2,2)))
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_clip_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],'missing')
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_clip_playback(self.current_draft_record,current_preview_record['token'],'0'*64,'idle')

    def test_clip_duration_rounding_preserves_cycle_length(self):
        current_frame_values=[{'duration_ms':current_duration_value} for current_duration_value in (167,166,167)*4]
        current_duration_values=sprite_operations.quantize_hermes_sprite_clip_durations(current_frame_values)
        self.assertEqual(current_duration_values[:3],[170,160,170])
        self.assertEqual(sum(current_duration_values),2000)
        self.assertTrue(all(current_duration_value>=10 and current_duration_value%10==0 for current_duration_value in current_duration_values))

    def test_reviewed_playback_uses_real_gif_and_rejects_mismatch(self):
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_playback_record=sprite_operations.render_hermes_sprite_anchor_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],8)
        current_gif_bytes=base64.b64decode(current_playback_record['gif'],validate=True)
        self.assertTrue(current_gif_bytes.startswith((b'GIF87a',b'GIF89a')))
        self.assertEqual(hashlib.sha256(current_gif_bytes).hexdigest(),current_playback_record['sha256'])
        self.assertEqual(current_playback_record['frame_count'],2)
        self.assertIn('균일 FPS',current_playback_record['note'])
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_anchor_playback(self.current_draft_record,current_preview_record['token'],'0'*64,8)
        with self.assertRaises(ValueError):sprite_operations.render_hermes_sprite_anchor_playback(self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'],7)
        self.assertEqual(self.current_image_path.read_bytes(),base64.b64decode(sprite_sheet_editor.execute_sprite_asset_command('sheet-image',{'path':self.current_path_value})['image']))

    def test_stale_source_invalid_frame_and_unknown_response(self):
        with self.assertRaises(ValueError):sprite_operations.preview_hermes_sprite_anchor_edit({**self.current_draft_record,'anchors':[{'frame_id':'missing','x':0,'y':0}]})
        current_preview_record=sprite_operations.preview_hermes_sprite_anchor_edit(self.current_draft_record)
        current_original_editor=sprite_operations.call_hermes_sprite_editor
        def execute_lost_editor(current_command_name,current_payload_record):
            if current_command_name=='sheet-update':raise OSError('lost response')
            return current_original_editor(current_command_name,current_payload_record)
        with patch.object(sprite_operations,'call_hermes_sprite_editor',side_effect=execute_lost_editor) as current_editor_mock:
            current_save_args=('sprite_request_456',self.current_draft_record,current_preview_record['token'],current_preview_record['review_sha256'])
            with self.assertRaises(OSError):sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)
            self.assertEqual(sprite_operations.read_hermes_sprite_anchor_receipt('sprite_request_456')['state'],'unknown')
            self.assertEqual(sprite_operations.save_hermes_sprite_anchor_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(current_call.args[0]=='sheet-update' for current_call in current_editor_mock.call_args_list),1)
