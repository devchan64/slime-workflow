"""건물 앵커 위임의 검토·충돌·응답 유실을 검사한다."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from workflow.domains.hermes_agent import building_operations
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesBuildingOperationsTests(unittest.TestCase):
    def test_real_session_and_receipt_reach_current_history_protocol(self):
        import hashlib
        import json
        import subprocess
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        session='a'*32;job='2026-11-18_00-00-00-12345678'
        request_id='chat_'+hashlib.sha256((session+':'+job+':building').encode()).hexdigest()
        draft={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        answer='HERMES_BUILDING_PROPOSAL\n'+json.dumps(draft)+'\nEND_HERMES_BUILDING_PROPOSAL'
        catalog={'generation':3,'assets':[{'texture':draft['texture'],'properties':draft['expected'],'maps':[{'map':'test-city'}]}]}
        with TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','건물 앵커 변경');sessions.attach_session_job(session,'request_12345678',job)
            jobdir=root/'jobs'/job;jobdir.mkdir(parents=True)
            (jobdir/'request.json').write_text(json.dumps({'prompt':'건물 앵커 변경'}))
            (jobdir/'status.json').write_text(json.dumps({'status':'completed'}))
            (jobdir/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':answer})+'\n')
            manager=HermesServiceManager(hermes_storage_root=root/'jobs',hermes_session_root=root/'sessions')
            store=HermesDelegationStore(root/'receipts')
            with patch.object(building_operations,'HermesDelegationStore',return_value=store),patch.object(building_operations,'call_field_map_editor',side_effect=lambda command,_:catalog if command=='building-list' else {'saved':True,'generation':4,'snapshot':'pending'}):
                review=building_operations.preview_hermes_building_anchor(draft)
                building_operations.save_hermes_building_anchor(request_id,draft,review['review_sha256'])
                view=manager.execute_hermes_command('hermes-session-view',{'session_id':session,'offset':0,'limit':6})
                proposal=manager.execute_hermes_command('hermes-building-proposal',{'id':job})
                receipt=manager.execute_hermes_command('hermes-building-receipt',{'request_id':request_id})
            script="""import {readBuildingSessionReceipts,verifyBuildingProposalBeforeSave} from './gui/buildingProposalProtocol.mjs';
              const [view,proposal,receipt]=JSON.parse(process.argv[1]);
              const command=async(_,name)=>name==='hermes-session-view'?view:name==='hermes-building-proposal'?proposal:receipt;
              const result=await readBuildingSessionReceipts(command,view.id);
              if(result.rows.length!==1 || !result.rows[0][1].includes('town-test-v1') || !result.rows[0][1].includes('원장 반영 대기'))throw Error(JSON.stringify(result.rows));
              await verifyBuildingProposalBeforeSave(command,view.id,proposal.job_id,{snapshot:view.snapshot,offset:view.offset,draft:proposal.proposal});"""
            repository=Path(__file__).resolve().parents[2]
            result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([view,proposal,receipt],ensure_ascii=False)],cwd=repository,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_oversized_asset_edit_receipts_are_not_missing(self):
        from workflow.domains.hermes_agent import billboard_operations,sprite_operations
        from workflow.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        with TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            current_store_value=HermesDelegationStore(current_root_path)
            (current_root_path/'request_123.json').write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
            current_receipt_readers=((building_operations,building_operations.read_hermes_building_receipt),(billboard_operations,billboard_operations.read_hermes_billboard_edit_receipt),(sprite_operations,sprite_operations.read_hermes_sprite_anchor_receipt))
            for current_module,current_reader in current_receipt_readers:
                with self.subTest(module=current_module.__name__),patch.object(current_module,'HermesDelegationStore',return_value=current_store_value):
                    with self.assertRaises(ValueError):current_reader('request_123')

    def test_conversation_receipt_history_identifies_database_and_no_gpu(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--test',str(root/'workflow/tests/building_proposal_membership.test.mjs')],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_history_distinguishes_legacy_and_mismatched_building_target(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        script="""import {buildingReceiptStatus} from './gui/buildingProposalProtocol.mjs';
          const id='chat_1',texture='town-test-v1';
          if(!buildingReceiptStatus({request_id:id,state:'completed',saved:true},id,texture).includes('대상 미확인'))throw Error('legacy');
          let rejected=false;try{buildingReceiptStatus({request_id:id,state:'completed',saved:true,texture:'town-other-v1'},id,texture)}catch{rejected=true}
          if(!rejected)throw Error('target');
          if(buildingReceiptStatus({request_id:id,state:'unknown'},id,texture)!=='접수 확인 필요')throw Error('unknown');"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_building_preview_rechecks_catalog_generation_and_properties(self):
        draft={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        catalog={'generation':3,'assets':[{'texture':'town-test-v1','properties':draft['expected'].copy(),'maps':[{'map':'test-city'}]}]}
        with patch.object(building_operations,'call_field_map_editor',return_value=catalog):
            review=building_operations.preview_hermes_building_anchor(draft)
            self.assertEqual(review['maps'],['test-city'])
            self.assertEqual(review['before'],draft['expected'])
            self.assertEqual(review['after'],draft['properties'])
            catalog['generation']=4
            with self.assertRaises(ValueError):building_operations.preview_hermes_building_anchor(draft)
            catalog['generation']=3
            catalog['assets'][0]['properties']['anchorX']=0.4
            with self.assertRaises(ValueError):building_operations.preview_hermes_building_anchor(draft)

    def test_conversation_proposal_rechecks_current_building_before_save(self):
        import json
        import subprocess
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_building_proposal
        current_draft={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_answer='HERMES_BUILDING_PROPOSAL\n'+json.dumps(current_draft)+'\nEND_HERMES_BUILDING_PROPOSAL'
        self.assertEqual(parse_hermes_building_proposal(current_answer),current_draft)
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--test',str(root/'workflow/tests/building_proposal_membership.test.mjs')],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        current_draft['properties']['anchorY']=float('nan')
        with self.assertRaises(ValueError):parse_hermes_building_proposal('HERMES_BUILDING_PROPOSAL\n'+json.dumps(current_draft)+'\nEND_HERMES_BUILDING_PROPOSAL')

    def test_saved_building_status_describes_historical_ledger_state(current_test_case):
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with TemporaryDirectory() as directory:
            bundle=Path(directory)/'building.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BuildingProposal.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {BuildingProposalReceipt}=require(process.argv[1]);
              const render=receipt=>server.renderToStaticMarkup(React.createElement(BuildingProposalReceipt,{receipt}));
              process.stdout.write(JSON.stringify([render({state:'completed',saved:true,generation:4,ledger_status_at_save:'pending'}),render({state:'completed',saved:true})]));"""
            import json
            current_message,without_pending=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True))
        current_test_case.assertIn('저장 당시 원장 반영 대기',current_message)
        current_test_case.assertIn('DB 세대 4',current_message)
        current_test_case.assertIn('현재 원장 동기화',current_message)
        current_test_case.assertNotIn('반영 대기',without_pending)
        current_test_case.assertIn('건물 대상 미확인',current_message)

    def test_current_building_review_shows_values_and_explicit_actions(self):
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with TemporaryDirectory() as directory:
            bundle=Path(directory)/'building.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BuildingProposal.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {BuildingProposalReview}=require(process.argv[1]);
              const preview={texture:'town-test-v1',generation:3,before:{anchorX:0.5,anchorY:1},after:{anchorX:0.6,anchorY:1},maps:['test-city']};
              const render=busy=>server.renderToStaticMarkup(React.createElement(BuildingProposalReview,{preview,busy}));
              process.stdout.write(JSON.stringify([render(false),render(true)]));"""
            import json
            html,busy_html=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True))
        for text in ('town-test-v1','앵커 X','0.5','0.6','test-city','확인 후 저장','취소','GPU 생성 작업은 실행하지 않습니다'):
            self.assertIn(text,html)
        self.assertEqual(html.count('disabled='),0)
        self.assertEqual(busy_html.count('disabled='),2)

    def test_review_save_duplicate_and_response_loss(self):
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog_value={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft_value['expected'],'maps':[{'map':'test-city'}],'image':'/private'}]}
        with TemporaryDirectory() as current_directory_name, patch.object(building_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory_name))), patch.object(building_operations,'call_field_map_editor') as current_gateway_mock:
            current_gateway_mock.side_effect=lambda current_command_name,current_payload_value: current_catalog_value if current_command_name=='building-list' else {'saved':True,'generation':4,'snapshot':'pending'}
            current_preview_value=building_operations.preview_hermes_building_anchor(current_draft_value)
            self.assertEqual(current_preview_value['maps'],['test-city'])
            self.assertNotIn('/private',str(current_preview_value))
            current_saved_value=building_operations.save_hermes_building_anchor('building_123',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(current_saved_value['state'],'completed')
            self.assertEqual(current_saved_value['texture'],'town-test-v1')
            self.assertEqual((current_saved_value['generation'],current_saved_value['ledger_status_at_save']),(4,'pending'))
            self.assertEqual(building_operations.read_hermes_building_receipt('building_123')['generation'],4)
            self.assertEqual(building_operations.read_hermes_building_receipt('building_123')['texture'],'town-test-v1')
            self.assertTrue(building_operations.save_hermes_building_anchor('building_123',current_draft_value,current_preview_value['review_sha256'])['duplicate'])
            self.assertEqual(sum(current_call.args[0]=='building-save' for current_call in current_gateway_mock.call_args_list),1)
            current_gateway_mock.side_effect=lambda current_command_name,current_payload_value: current_catalog_value if current_command_name=='building-list' else (_ for _ in ()).throw(OSError('lost'))
            with self.assertRaises(OSError):building_operations.save_hermes_building_anchor('building_456',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(building_operations.read_hermes_building_receipt('building_456')['state'],'unknown')
            self.assertEqual(building_operations.save_hermes_building_anchor('building_456',current_draft_value,current_preview_value['review_sha256'])['state'],'unknown')

    def test_mismatched_building_response_remains_unknown(current_test_case):
        current_draft={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft['expected'],'maps':[]}]}
        with TemporaryDirectory() as current_directory,patch.object(building_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory))),patch.object(building_operations,'call_field_map_editor') as current_editor:
            current_editor.side_effect=lambda current_command,current_payload:current_catalog if current_command=='building-list' else {'saved':True,'asset':'town-other-v1','generation':4,'snapshot':'pending'}
            current_review=building_operations.preview_hermes_building_anchor(current_draft)
            with current_test_case.assertRaisesRegex(ValueError,'결과 확인 필요'):
                building_operations.save_hermes_building_anchor('building_wrong_123',current_draft,current_review['review_sha256'])
            current_test_case.assertEqual(building_operations.read_hermes_building_receipt('building_wrong_123')['state'],'unknown')
            current_test_case.assertEqual(building_operations.save_hermes_building_anchor('building_wrong_123',current_draft,current_review['review_sha256'])['state'],'unknown')
            current_test_case.assertEqual(sum(item.args[0]=='building-save' for item in current_editor.call_args_list),1)

    def test_changed_receipt_after_building_save_is_not_overwritten(self):
        import json
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog_value={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft_value['expected'],'maps':[]}]}
        with TemporaryDirectory() as current_directory_name:
            current_store_value=HermesDelegationStore(Path(current_directory_name))
            current_record_path=current_store_value.resolve_delegation_record_path('building_123')
            def current_editor_response(current_command_name,current_payload_value):
                if current_command_name=='building-list':return current_catalog_value
                current_receipt_value=json.loads(current_record_path.read_text())
                current_receipt_value['external_change']='preserve'
                current_record_path.write_text(json.dumps(current_receipt_value))
                return {'saved':True}
            with patch.object(building_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(building_operations,'call_field_map_editor',side_effect=current_editor_response) as current_editor_mock:
                current_preview_value=building_operations.preview_hermes_building_anchor(current_draft_value)
                current_save_args=('building_123',current_draft_value,current_preview_value['review_sha256'])
                with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):building_operations.save_hermes_building_anchor(*current_save_args)
                self.assertEqual(building_operations.save_hermes_building_anchor(*current_save_args)['state'],'unknown')
                self.assertEqual(sum(item.args[0]=='building-save' for item in current_editor_mock.call_args_list),1)
                self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_changed_state_or_non_anchor_change_is_rejected(self):
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1,'displayWidthAdjustment':0,'displayHeightAdjustment':0},'properties':{'anchorX':0.6,'anchorY':1,'displayWidthAdjustment':0,'displayHeightAdjustment':0}}
        with patch.object(building_operations,'call_field_map_editor',return_value={'generation':4,'assets':[]}):
            with self.assertRaisesRegex(ValueError,'세대'):building_operations.preview_hermes_building_anchor(current_draft_value)
        current_draft_value['properties']['displayWidthAdjustment']=1
        with self.assertRaisesRegex(ValueError,'앵커'):building_operations.inspect_hermes_building_draft(current_draft_value)
