"""빌보드 위임의 검토 고정·중복 방지·응답 유실을 검사한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import billboard_operations
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesBillboardOperationTests(unittest.TestCase):
    def test_real_proposal_and_preview_match_conversation_protocol(self):
        import json
        import subprocess
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_billboard_proposal
        proposal={'texture':'grass-v1','expected':{'displayHeight':128},'values':{'displayHeight':130}}
        answer='HERMES_BILLBOARD_PROPOSAL\n'+json.dumps(proposal)+'\nEND_HERMES_BILLBOARD_PROPOSAL'
        parsed=parse_hermes_billboard_proposal(answer)
        draft={'revision':'abc','changes':[{'texture':'grass-v1','values':{'displayHeight':130}}]}
        token=billboard_operations.validate_billboard_edit_draft(draft)
        raw={'token':token,'changes':[{'texture':'grass-v1','before':{'displayHeight':128},'after':{'displayHeight':130}}],'maps':[],'map_warnings':[],'note':'검토'}
        with patch.object(billboard_operations,'call_field_map_editor',return_value=raw):
            preview=billboard_operations.preview_hermes_billboard_edit(draft)
        root=Path(__file__).resolve().parents[2]
        script="""import {prepareBillboardProposal} from './gui/billboardProposalProtocol.mjs';
          const [proposal,preview]=JSON.parse(process.argv[1]),session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
          const cmd=async(_,name)=>name==='hermes-session-view'?{id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BILLBOARD_PROPOSAL'}}]}:name==='hermes-billboard-proposal'?{job_id:job,proposal}:name==='hermes-billboard-receipt'?{state:'not_found'}:name==='hermes-billboard-load'?{texture:'grass-v1',revision:'abc',properties:{displayHeight:128}}:preview;
          const {review}=await prepareBillboardProposal(cmd,session,job,snapshot,0);
          if(review.draft.changes[0].values.displayHeight!==130)throw Error('draft');"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([parsed,preview])],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_current_billboard_review_displays_target_changes_and_warnings(self):
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'billboard.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BillboardProperties.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {BillboardReviewSummary}=require(process.argv[1]);
              const result={changes:[{texture:'tree-v1',before:{displayHeight:520},after:{displayHeight:500}}],maps:['meadow'],map_warnings:[{map:'meadow',message:'접지 확인'}],note:'맵 재확인'};
              process.stdout.write(server.renderToStaticMarkup(React.createElement(BillboardReviewSummary,{result})));"""
            html=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True)
        for value in ('tree-v1','표시 높이','520','500','meadow','접지 확인','맵 재확인'):
            self.assertIn(value,html)

    def test_unconfigured_file_asset_previews_all_initial_properties(self):
        catalog={'revision':'abc','assets':[{'texture':'grass-v1','properties':None}]}
        with patch.object(billboard_operations,'call_field_map_editor',return_value=catalog):
            source=billboard_operations.load_hermes_billboard_edit('grass-v1')
        self.assertTrue(source['initial'])
        self.assertEqual(source['properties']['displayHeight'],128)
        self.assertEqual(set(source['properties']),billboard_operations.EDITOR_MUTABLE_FIELDS-{'billboardPlacementAnchor'})

    def test_change_summary_shows_values_maps_and_warnings(self):
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'billboard.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BillboardProposal.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {BillboardProposalReview}=require(process.argv[1]);
              const preview={changes:[{texture:'tree-v1',before:{displayHeight:520},after:{displayHeight:500}}],maps:['assets/maps/field_tiles/meadow.yaml'],map_warnings:[{map:'assets/maps/field_tiles/meadow.yaml',message:'접지 확인'}],note:'맵은 다시 확인'};
              process.stdout.write(server.renderToStaticMarkup(React.createElement(BillboardProposalReview,{preview})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True)
        for value in ('tree-v1','표시 높이','520','500','assets/maps/field_tiles/meadow.yaml','접지 확인','맵은 다시 확인','확인 후 저장','취소'):
            self.assertIn(value,markup)

    def setUp(self):
        self.current_temporary_root=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temporary_root.cleanup)
        self.current_store_value=HermesDelegationStore(Path(self.current_temporary_root.name))
        self.current_draft_record={'revision':'abc','changes':[{'texture':'grass-v1','values':{'displayHeight':130}}]}
        self.current_token_value=billboard_operations.validate_billboard_edit_draft(self.current_draft_record)
        self.current_preview_record={'token':self.current_token_value,'changes':[{'texture':'grass-v1','before':{'displayHeight':128},'after':{'displayHeight':130}}],'maps':[],'map_warnings':[],'note':'검수'}
        self.current_store_patch=patch.object(billboard_operations,'HermesDelegationStore',return_value=self.current_store_value)
        self.current_store_patch.start()
        self.addCleanup(self.current_store_patch.stop)

    def test_history_asset_target_matching_and_legacy(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--test',str(root/'workflow/tests/billboard_proposal_protocol.test.mjs')],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_confirmed_save_and_duplicate_are_single_dispatch(self):
        def execute_test_editor(current_command_name,current_payload_record):
            return {'saved':True} if current_command_name=='asset-save-reviewed' else self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            self.assertTrue(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['saved'])
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['textures'],sorted(item['texture'] for item in self.current_draft_record['changes']))
            self.assertTrue(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['duplicate'])
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['state'],'completed')

    def test_database_ledger_status_survives_receipt_and_duplicate(self):
        def execute_test_editor(current_command_name,current_payload_record):
            return {'saved':True,'snapshot':'pending'} if current_command_name=='asset-save-reviewed' else self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor):
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            current_saved_record=billboard_operations.save_hermes_billboard_edit_once(*current_save_args)
            self.assertEqual(current_saved_record['ledger_status_at_save'],'pending')
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['ledger_status_at_save'],'pending')
            self.assertEqual(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['ledger_status_at_save'],'pending')

    def test_billboard_status_notice_distinguishes_pending_ledger(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        script="""import {billboardSaveNotice} from './gui/billboardSaveNotice.mjs';
          if(!billboardSaveNotice({saved:true,ledger_status_at_save:'pending'},'request').includes('저장 당시 원장 반영 대기'))throw Error('pending');
          if(billboardSaveNotice({saved:true},'request').includes('원장 반영'))throw Error('unknown');"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_changed_receipt_after_save_is_preserved_and_not_retried(self):
        import json
        current_record_path=self.current_store_value.resolve_delegation_record_path('request_123')
        def current_editor_response(current_command_name,current_payload_record):
            if current_command_name!='asset-save-reviewed':return self.current_preview_record
            current_changed_record=json.loads(current_record_path.read_text())
            current_changed_record['external_change']='preserve'
            current_record_path.write_text(json.dumps(current_changed_record))
            return {'saved':True}
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=current_editor_response) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):billboard_operations.save_hermes_billboard_edit_once(*current_save_args)
            self.assertEqual(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)
            self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_changed_warning_requires_new_review(self):
        with patch.object(billboard_operations,'call_field_map_editor',return_value=self.current_preview_record) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            self.current_preview_record['maps']=['assets/maps/field_tiles/meadow.yaml']
            self.current_preview_record['map_warnings']=[{'map':'assets/maps/field_tiles/meadow.yaml','message':'충돌'}]
            with self.assertRaisesRegex(ValueError,'다시 확인'):
                billboard_operations.save_hermes_billboard_edit_once('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            self.assertFalse(any(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list))

    def test_lost_save_response_is_not_retried(self):
        def execute_test_editor(current_command_name,current_payload_record):
            if current_command_name=='asset-save-reviewed':raise RuntimeError('응답 유실')
            return self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            with self.assertRaises(RuntimeError):billboard_operations.save_hermes_billboard_edit_once(*current_save_args)
            self.assertEqual(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)

    def test_disallowed_fields_and_nonfinite_values_rejected(self):
        for current_change_values in ({'image':'x'},{'displayHeight':float('nan')}):
            with self.subTest(values=current_change_values),self.assertRaises(ValueError):
                billboard_operations.validate_billboard_edit_draft({'revision':'abc','changes':[{'texture':'grass-v1','values':current_change_values}]})

    def test_real_gateway_dispatches_reviewed_save_under_editor_lock(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import json
        import threading
        from workflow.common.management_gateway import ManagementCommandGateway, execute_management_command
        from workflow.domains.map_assets import editor, resize
        current_call_order=[]
        def execute_test_preview(current_payload_record):
            current_call_order.append('preview')
            return self.current_preview_record
        def execute_test_save(current_payload_record):
            current_call_order.append('save')
            return {'saved':True}
        current_gateway_value=ManagementCommandGateway({'map-assets':resize.handle_map_resize_request})
        class GatewayTestHandler(BaseHTTPRequestHandler):
            def do_POST(current_handler_value):
                current_gateway_value.handle(current_handler_value)
            def log_message(current_handler_value,current_log_format,*current_log_values):
                pass
        current_server_value=ThreadingHTTPServer(('127.0.0.1',0),GatewayTestHandler)
        current_server_thread=threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_server_thread.start()
        try:
            current_preview_digest=editor.hash_billboard_review_result(self.current_preview_record)
            current_save_payload={**self.current_draft_record,'token':self.current_token_value,'review_sha256':current_preview_digest}
            with patch.dict('os.environ',{'SLIME_CONTENT_STORAGE':'file'}), patch.object(resize,'RESIZE_STORAGE_DIRECTORY',Path(self.current_temporary_root.name)/'locks'), patch.object(editor,'preview_editor_changes',side_effect=execute_test_preview), patch.object(editor,'save_editor_changes',side_effect=execute_test_save):
                current_response_record=execute_management_command('map-assets','asset-save-reviewed',current_save_payload,'http://127.0.0.1:'+str(current_server_value.server_port))
            self.assertTrue(current_response_record['saved'])
            self.assertEqual(current_call_order,['preview','save'])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join(timeout=5)
