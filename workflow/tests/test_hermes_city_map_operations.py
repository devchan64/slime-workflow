"""도시 맵 접수의 중복과 응답 유실 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent import city_map_operations


class HermesCityMapOperationsTests(unittest.TestCase):
    def test_current_city_review_shows_changes_and_blocks_new_save(self):
        import json, os
        import subprocess
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_city_proposal
        proposal={'map':'stonewarm','generation':5,'revision':2,'changes':[{'path':['data','buildings',0,'name'],'before':'기존','after':'변경'}]}
        answer='HERMES_CITY_PROPOSAL\n'+json.dumps(proposal,ensure_ascii=False)+'\nEND_HERMES_CITY_PROPOSAL'
        self.assertEqual(parse_hermes_city_proposal(answer),proposal)
        gui=Path(__file__).resolve().parents[2]/'gui'
        with TemporaryDirectory() as directory:
            bundle=Path(directory)/'city.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'CityProposal.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const {CityProposalReview}=require(process.argv[1]);
              const proposal=JSON.parse(require('fs').readFileSync(0,'utf8'));
              const preview={source_alignment:{status:'matched'},source_plan:{status:'available',before_sha256:'a'.repeat(64),after_sha256:'b'.repeat(64)}};
              process.stdout.write(server.renderToStaticMarkup(React.createElement(CityProposalReview,{proposal,preview})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,input=json.dumps(proposal,ensure_ascii=False),text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        for value in ('stonewarm','data / buildings / 0 / name','기존','변경','신규 저장은 현재 지원되지 않습니다','저장 또는 복구 준비 완료를 뜻하지 않습니다'):
            self.assertIn(value,markup)
        self.assertNotIn('확인 후 저장',markup)

    def test_oversized_map_receipt_is_not_reported_as_missing(self):
        from workflow.domains.hermes_agent import field_map_operations
        from workflow.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        with TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            current_store_value=HermesDelegationStore(current_root_path)
            (current_root_path/'request_123.json').write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
            for current_module,current_reader in ((city_map_operations,city_map_operations.read_hermes_city_receipt),(field_map_operations,field_map_operations.read_hermes_field_receipt)):
                with self.subTest(module=current_module.__name__),patch.object(current_module,'HermesDelegationStore',return_value=current_store_value):
                    with self.assertRaises(ValueError):current_reader('request_123')

    def test_city_history_receipt_and_read_only_protocol(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--test',str(root/'workflow/tests/city_proposal_protocol.test.mjs')],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_city_session_and_preview_match_conversation_protocol(self):
        import json
        import subprocess
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        session='a'*32;job='2026-11-18_00-00-00-12345678'
        proposal={'map':'stonewarm','generation':5,'revision':2,'changes':[{'path':['data','buildings',0,'name'],'before':'old','after':'new'}]}
        source={'map':'stonewarm','generation':5,'revision':2,'document':{'data':{'buildings':[{'name':'old'}]}}}
        draft={**source,'document':{'data':{'buildings':[{'name':'new'}]}}}
        answer='HERMES_CITY_PROPOSAL\n'+json.dumps(proposal)+'\nEND_HERMES_CITY_PROPOSAL'
        with TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','도시 맵 변경');sessions.attach_session_job(session,'request_12345678',job)
            jobdir=root/'jobs'/job;jobdir.mkdir(parents=True)
            (jobdir/'request.json').write_text(json.dumps({'prompt':'도시 맵 변경'}))
            (jobdir/'status.json').write_text(json.dumps({'status':'completed'}))
            (jobdir/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':answer})+'\n')
            manager=HermesServiceManager(hermes_storage_root=root/'jobs',hermes_session_root=root/'sessions')
            token=city_map_operations.validate_hermes_city_draft(draft)
            editor_preview={'token':token,'cityId':'stonewarm','changed':True,'columns':5,'rows':5,'buildings':1,'objects':0,'source_plan':{'status':'available','before_sha256':'a'*64,'after_sha256':'b'*64}}
            with patch.object(city_map_operations,'call_field_map_editor',return_value=editor_preview),patch.object(city_map_operations,'load_hermes_city_map',return_value=source):
                preview=manager.execute_hermes_command('hermes-city-preview',{'draft':draft})
            view=manager.execute_hermes_command('hermes-session-view',{'session_id':session,'offset':0,'limit':6})
            parsed=manager.execute_hermes_command('hermes-city-proposal',{'id':job})
            script="""import {prepareCityProposal} from './gui/cityProposalProtocol.mjs';
              const [view,parsed,source,preview]=JSON.parse(process.argv[1]);let sent;
              const command=async(_,name,payload)=>{if(name==='hermes-session-view')return view;if(name==='hermes-city-proposal')return parsed;if(name==='hermes-city-receipt')return {state:'not_found'};if(name==='hermes-city-load')return source;if(name==='hermes-city-preview'){sent=payload.draft;return preview;}throw Error(name);};
              const result=await prepareCityProposal(command,view.id,parsed.job_id,view.snapshot,view.offset);
              if(sent.document.data.buildings[0].name!=='new' || source.document.data.buildings[0].name!=='old' || result.preview.save_available!==false)throw Error('review mismatch');"""
            repository=Path(__file__).resolve().parents[2]
            result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([view,parsed,source,preview],ensure_ascii=False)],cwd=repository,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_city_preview_reports_saving_unavailable(self):
        current_draft_record={'map':'stonewarm','generation':5,'revision':2,'document':{}}
        current_token_value=city_map_operations.validate_hermes_city_draft(current_draft_record)
        current_preview_record={'token':current_token_value,'cityId':'stonewarm','changed':True,'columns':5,'rows':5,'buildings':1,'objects':0}
        with patch.object(city_map_operations,'call_field_map_editor',return_value=current_preview_record):
            self.assertIs(city_map_operations.preview_hermes_city_map(current_draft_record)['save_available'],False)

    def test_city_preview_exposes_only_validated_source_plan_hashes(self):
        current_draft_record={'map':'stonewarm','generation':5,'revision':2,'document':{}}
        current_token_value=city_map_operations.validate_hermes_city_draft(current_draft_record)
        current_preview_record={'token':current_token_value,'cityId':'stonewarm','changed':True,'columns':5,'rows':5,'buildings':1,'objects':0,'source_plan':{'status':'available','before_sha256':'a'*64,'after_sha256':'b'*64}}
        with patch.object(city_map_operations,'call_field_map_editor',return_value=current_preview_record),patch.object(city_map_operations,'load_hermes_city_map',side_effect=ValueError('fixture')):
            current_result_record=city_map_operations.preview_hermes_city_map(current_draft_record)
            self.assertEqual(current_result_record['source_plan'],current_preview_record['source_plan'])
            self.assertIs(current_result_record['save_available'],False)
            current_preview_record['source_plan']={'status':'available','before_sha256':'invalid','after_sha256':'b'*64}
            with self.assertRaisesRegex(ValueError,'계획 해시 오류'):city_map_operations.preview_hermes_city_map(current_draft_record)

    def test_city_preview_compares_current_database_document_with_registered_source(self):
        current_draft_record={'map':'stonewarm','generation':5,'revision':2,'document':{'edited':True}}
        current_database_record={**current_draft_record,'document':{'original':True}}
        current_token_value=city_map_operations.validate_hermes_city_draft(current_draft_record)
        current_preview_record={'token':current_token_value,'cityId':'stonewarm','changed':True,'columns':5,'rows':5,'buildings':1,'objects':0}
        with patch.object(city_map_operations,'call_field_map_editor',return_value=current_preview_record),patch.object(city_map_operations,'load_hermes_city_map',return_value=current_database_record),patch('workflow.domains.map_assets.source_consistency.inspect_city_source_alignment',return_value={'status':'matched','note':'fixture'}) as current_alignment_mock:
            current_result_record=city_map_operations.preview_hermes_city_map(current_draft_record)
            self.assertEqual(current_result_record['source_alignment']['status'],'matched')
            self.assertEqual(current_alignment_mock.call_args.args[3],{'original':True})
            current_database_record['revision']=3
            current_alignment_mock.reset_mock()
            self.assertEqual(city_map_operations.preview_hermes_city_map(current_draft_record)['source_alignment']['status'],'unavailable')
            current_alignment_mock.assert_not_called()

    def test_city_preview_reports_unavailable_when_database_changes_during_comparison(self):
        current_draft_record={'map':'stonewarm','generation':5,'revision':2,'document':{}}
        current_token_value=city_map_operations.validate_hermes_city_draft(current_draft_record)
        current_preview_record={'token':current_token_value,'cityId':'stonewarm','changed':True,'columns':5,'rows':5,'buildings':1,'objects':0}
        current_initial_record={**current_draft_record,'document':{'original':True}}
        current_changed_record={**current_initial_record,'revision':3}
        with patch.object(city_map_operations,'call_field_map_editor',return_value=current_preview_record),patch.object(city_map_operations,'load_hermes_city_map',side_effect=[current_initial_record,current_changed_record]),patch('workflow.domains.map_assets.source_consistency.inspect_city_source_alignment',return_value={'status':'matched','note':'fixture'}):
            self.assertEqual(city_map_operations.preview_hermes_city_map(current_draft_record)['source_alignment']['status'],'unavailable')

    def test_city_save_blocks_new_dispatch_and_preserves_old_receipts(self):
        import json
        current_draft_value={'map':'stonewarm','generation':5,'revision':2,'document':{'name':'한글'}}
        current_token_value=city_map_operations.validate_hermes_city_draft(current_draft_value)
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            with patch.object(city_map_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(city_map_operations,'call_field_map_editor') as current_gateway_mock:
                with self.assertRaisesRegex(ValueError,'신규 저장'):
                    city_map_operations.save_hermes_city_map_once('city_unknown_123',current_draft_value,current_token_value)
                self.assertEqual(city_map_operations.read_hermes_city_receipt('city_unknown_123')['state'],'not_found')
                current_record_path=current_store_value.resolve_delegation_record_path('city_unknown_123')
                current_record_path.write_text(json.dumps({'version':5,'id':'city_unknown_123','token':current_token_value,'map':'stonewarm','state':'dispatching'}))
                self.assertEqual(city_map_operations.read_hermes_city_receipt('city_unknown_123')['state'],'unknown')
                self.assertTrue(city_map_operations.save_hermes_city_map_once('city_unknown_123',current_draft_value,current_token_value)['duplicate'])
                current_gateway_mock.assert_not_called()
                current_other_draft={**current_draft_value,'revision':3}
                with self.assertRaises(ValueError):
                    city_map_operations.save_hermes_city_map_once('city_unknown_123',current_other_draft,city_map_operations.validate_hermes_city_draft(current_other_draft))

    def test_map_save_does_not_overwrite_changed_receipt_or_retry(self):
        import json
        from workflow.domains.hermes_agent import field_map_operations
        current_city_draft={'map':'stonewarm','generation':5,'revision':2,'document':{'name':'한글'}}
        current_field_draft={'map':'moss-clearing','revision':'old','cells':[],'objects':[]}
        current_cases=((field_map_operations,'field',current_field_draft,field_map_operations.validate_field_map_draft(current_field_draft)),)
        for current_module_value,current_kind_name,current_draft_value,current_token_value in current_cases:
            with self.subTest(kind=current_kind_name),TemporaryDirectory() as current_root_name:
                current_store_value=HermesDelegationStore(Path(current_root_name))
                current_request_value=current_kind_name+'_changed_123'
                current_record_path=current_store_value.resolve_delegation_record_path(current_request_value)
                current_calls=[]
                def current_editor_response(current_command_name,current_payload_value):
                    current_calls.append(current_command_name)
                    if current_command_name=='city-edit-preview':return {'token':current_token_value,'changed':True,'cityId':'stonewarm','columns':5,'rows':5,'buildings':1,'objects':0}
                    if current_command_name=='map-edit-preview':return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0,'save_available':True}
                    current_changed_record=json.loads(current_record_path.read_text())
                    current_changed_record['external_change']='preserve'
                    current_record_path.write_text(json.dumps(current_changed_record))
                    return {'saved':True}
                current_save_function=city_map_operations.save_hermes_city_map_once if current_kind_name=='city' else field_map_operations.save_hermes_field_map_once
                with patch.object(current_module_value,'HermesDelegationStore',return_value=current_store_value),patch.object(current_module_value,'call_field_map_editor',side_effect=current_editor_response):
                    with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):current_save_function(current_request_value,current_draft_value,current_token_value)
                    self.assertEqual(current_save_function(current_request_value,current_draft_value,current_token_value)['state'],'unknown')
                self.assertEqual(len(current_calls),2)
                self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_stale_or_invalid_draft_never_saves(self):
        current_draft_value = {'map':'stonewarm','generation':5,'revision':2,'document':{}}
        with patch.object(city_map_operations,'call_field_map_editor',side_effect=ValueError('도시 원장이 변경되었습니다.')) as current_gateway_mock:
            with self.assertRaises(ValueError):
                city_map_operations.preview_hermes_city_map(current_draft_value)
            self.assertEqual(current_gateway_mock.call_args.args[0],'city-edit-preview')
        with self.assertRaises(ValueError):
            city_map_operations.validate_hermes_city_draft({**current_draft_value,'generation':True})
