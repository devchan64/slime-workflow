"""명시적으로 전달된 격리 API에 공용 게이트웨이·CLI HTTP를 연결한다."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import threading
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from tools.management.common.management_gateway import ManagementCommandGateway, execute_gateway_cli
from tools.management.domains.map_assets.resize import handle_map_resize_request
from tools.management.domains.map_assets.database_client import execute_content_api_request


@unittest.skipUnless(os.environ.get('ASSET_HTTP_ISOLATED_TEST') == '1', '격리 API 실행기가 필요합니다.')
class AssetServiceHttpTests(unittest.TestCase):
    def test_hermes_effect_and_billboard_save_over_real_database(current_test_case):
        from tools.management.domains.hermes_agent import billboard_operations, effect_operations
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        from tools.management.domains.map_assets import database_editor, resize
        current_gateway_service=ManagementCommandGateway({'map-assets':handle_map_resize_request})
        class IsolatedGatewayHandler(BaseHTTPRequestHandler):
            def do_POST(current_http_handler):
                current_gateway_service.handle(current_http_handler)
            def log_message(current_http_handler,current_log_format,*current_log_arguments):
                pass
        current_http_server=ThreadingHTTPServer(('127.0.0.1',0),IsolatedGatewayHandler)
        current_server_thread=threading.Thread(target=current_http_server.serve_forever,daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_temp_path=Path(current_directory_name)
                current_store_value=HermesDelegationStore(current_temp_path/'receipts')
                current_gateway_origin='http://127.0.0.1:'+str(current_http_server.server_port)
                with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database','SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}), patch.object(resize,'RESIZE_STORAGE_DIRECTORY',current_temp_path/'locks'), patch.object(database_editor,'EDITOR_STORAGE_DIRECTORY',current_temp_path/'previews'), patch.object(effect_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(billboard_operations,'HermesDelegationStore',return_value=current_store_value):
                    current_effect_source=effect_operations.read_hermes_effect_detail('firefly-swarm-v1')
                    current_alignment_record=current_effect_source['alignment']
                    current_effect_draft={'id':'firefly-swarm-v1','revision':current_effect_source['revision'],'target':current_alignment_record['target'],'alpha':0.8,'frames':current_alignment_record['frames']}
                    current_effect_preview=effect_operations.preview_hermes_effect_edit(current_effect_draft)
                    current_effect_result=effect_operations.save_hermes_effect_edit_once('isolated_effect_123',current_effect_draft,current_effect_preview['token'])
                    current_test_case.assertTrue(current_effect_result['saved'])
                    current_test_case.assertEqual(execute_content_api_request('GET','/internal/v1/content/effects')['effects'][0]['alignment']['alpha'],0.8)
                    current_test_case.assertTrue(effect_operations.save_hermes_effect_edit_once('isolated_effect_123',current_effect_draft,current_effect_preview['token'])['duplicate'])
                    with current_test_case.assertRaises(ValueError):effect_operations.preview_hermes_effect_edit(current_effect_draft)
                    current_billboard_source=billboard_operations.load_hermes_billboard_edit('test-grass')
                    current_billboard_draft={'revision':current_billboard_source['revision'],'changes':[{'texture':'test-grass','values':{'displayHeight':130,'groundFootprintColumns':2}}]}
                    current_billboard_preview=billboard_operations.preview_hermes_billboard_edit(current_billboard_draft)
                    current_test_case.assertEqual(current_billboard_preview['maps'],['assets/maps/field_tiles/test-field.yaml'])
                    current_test_case.assertIn('점유 영역 충돌',current_billboard_preview['map_warnings'][0]['message'])
                    current_map_bundle=execute_content_api_request('GET','/internal/v1/content/review-bundle?map=test-field')
                    current_map_document=current_map_bundle['documents']['field_tiles/test-field.yaml']
                    current_map_document['data']['objects'][1]['position']={'column':3,'row':1}
                    execute_content_api_request('POST','/internal/v1/content/map-changes',{'requestId':'isolated-map-move-123','expectedGeneration':current_map_bundle['generation'],'documents':[{'path':'field_tiles/test-field.yaml','revision':current_map_bundle['revisions']['field_tiles/test-field.yaml'],'document':current_map_document}]})
                    with current_test_case.assertRaisesRegex(ValueError,'검수 결과가 변경'):
                        billboard_operations.save_hermes_billboard_edit_once('isolated_billboard_123',current_billboard_draft,current_billboard_preview['token'],current_billboard_preview['review_sha256'])
                    current_billboard_preview=billboard_operations.preview_hermes_billboard_edit(current_billboard_draft)
                    current_test_case.assertEqual(current_billboard_preview['map_warnings'],[])
                    current_billboard_result=billboard_operations.save_hermes_billboard_edit_once('isolated_billboard_123',current_billboard_draft,current_billboard_preview['token'],current_billboard_preview['review_sha256'])
                    current_test_case.assertTrue(current_billboard_result['saved'])
                    current_test_case.assertEqual(execute_content_api_request('GET','/internal/v1/content/billboards/test-grass')['properties']['displayHeight'],130)
                    current_test_case.assertTrue(billboard_operations.save_hermes_billboard_edit_once('isolated_billboard_123',current_billboard_draft,current_billboard_preview['token'],current_billboard_preview['review_sha256'])['duplicate'])
                    with current_test_case.assertRaises(ValueError):billboard_operations.preview_hermes_billboard_edit(current_billboard_draft)
                    current_fog_value={'id':'isolated-fog-v1','name':'격리 안개','image':'assets/sprites/effects/terrain/lake-fog-sheet-v2.png','renderer':'fog','columns':4,'rows':2,'frames':8,'alignment':{'key':'isolated-fog','texture':'isolated-fog','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
                    current_fog_preview=effect_operations.preview_hermes_effect_registration(current_fog_value)
                    current_fog_result=effect_operations.register_hermes_effect_once('isolated_fog_123',current_fog_value,current_fog_preview['review_sha256'])
                    current_test_case.assertEqual(current_fog_result['state'],'completed')
                    current_test_case.assertIn(current_fog_value,execute_content_api_request('GET','/internal/v1/content/effects')['effects'])
                    current_glow_value={'id':'isolated-glow-v1','name':'격리 발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'isolated-glow','texture':'test-grass','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
                    current_glow_preview=effect_operations.preview_hermes_effect_registration(current_glow_value)
                    current_test_case.assertEqual(current_glow_preview['linked_billboard']['revision'],2)
                    current_glow_result=effect_operations.register_hermes_effect_once('isolated_glow_123',current_glow_value,current_glow_preview['review_sha256'])
                    current_test_case.assertEqual(current_glow_result['state'],'completed')
                    current_test_case.assertIn(current_glow_value,execute_content_api_request('GET','/internal/v1/content/effects')['effects'])
                    current_waypoint_value={'id':'waypoint-test-old','name':'격리 웨이포인트','image':'assets/sprites/effects/waypoint/waypoint-guide-v4.png','animation':'assets/sprites/effects/waypoint/waypoint-guide-v4.animation.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
                    current_register_preview=effect_operations.preview_hermes_effect_registration(current_waypoint_value)
                    current_register_args=('isolated_register_123',current_waypoint_value,current_register_preview['review_sha256'])
                    current_register_result=effect_operations.register_hermes_effect_once(*current_register_args)
                    current_test_case.assertEqual(current_register_result['state'],'completed')
                    current_test_case.assertTrue(effect_operations.register_hermes_effect_once(*current_register_args)['duplicate'])
                    current_waypoint_source=effect_operations.read_hermes_effect_detail('waypoint-test-old')
                    current_replacement_value={**current_waypoint_value,'id':'waypoint-test-new','name':'격리 새 웨이포인트'}
                    current_replacement_draft={'id':'waypoint-test-old','revision':current_waypoint_source['revision'],'effect':current_replacement_value}
                    current_replacement_preview=effect_operations.preview_hermes_waypoint_replacement(current_replacement_draft)
                    current_replacement_args=('isolated_replace_123',current_replacement_draft,current_replacement_preview['review_sha256'])
                    current_replace_result=effect_operations.replace_hermes_waypoint_once(*current_replacement_args)
                    current_test_case.assertEqual((current_replace_result['state'],current_replace_result['id']),('completed','waypoint-test-new'))
                    current_test_case.assertTrue(effect_operations.replace_hermes_waypoint_once(*current_replacement_args)['duplicate'])
                    current_effect_ids={item['id'] for item in execute_content_api_request('GET','/internal/v1/content/effects')['effects']}
                    current_test_case.assertIn('waypoint-test-new',current_effect_ids)
                    current_test_case.assertNotIn('waypoint-test-old',current_effect_ids)
        finally:
            current_http_server.shutdown()
            current_http_server.server_close()
            current_server_thread.join(timeout=5)

    def test_gateway_envelope_cli_and_authentication(current_test_case):
        current_gateway_service = ManagementCommandGateway({'map-assets':handle_map_resize_request})

        class IsolatedGatewayHandler(BaseHTTPRequestHandler):
            def do_POST(current_http_handler):
                current_gateway_service.handle(current_http_handler)

            def log_message(current_http_handler, current_log_format, *current_log_arguments):
                pass

        current_http_server = ThreadingHTTPServer(('127.0.0.1',0),IsolatedGatewayHandler)
        current_server_thread = threading.Thread(target=current_http_server.serve_forever,daemon=True)
        current_server_thread.start()
        try:
            current_server_origin = 'http://127.0.0.1:'+str(current_http_server.server_port)
            current_request_record = Request(current_server_origin+'/management/command',
                data=json.dumps({'service':'map-assets','command':'database-status','payload':{}}).encode(),
                headers={'Origin':current_server_origin,'Content-Type':'application/json'})
            with urlopen(current_request_record,timeout=10) as current_http_response:
                current_envelope_result=json.load(current_http_response)
            current_test_case.assertTrue(current_envelope_result['pending'])
            current_output_buffer=io.StringIO()
            with tempfile.TemporaryDirectory() as current_directory_name, contextlib.redirect_stdout(current_output_buffer):
                current_payload_path=Path(current_directory_name)/'payload.json'
                current_payload_path.write_text('{}')
                execute_gateway_cli(['command','map-assets','--server-url',current_server_origin,'database-status','--payload-file',str(current_payload_path)])
            current_test_case.assertEqual(json.loads(current_output_buffer.getvalue()),current_envelope_result)
            current_test_case.assertIn('types',execute_content_api_request('GET','/internal/v1/content/types'))
            with patch.dict(os.environ,{'SLIME_CONTENT_SERVICE_SECRET_FILE':os.environ['ASSET_HTTP_WRONG_TOKEN_FILE']}):
                with current_test_case.assertRaisesRegex(ValueError,'401'):
                    execute_content_api_request('GET','/internal/v1/content/status')
        finally:
            current_http_server.shutdown()
            current_http_server.server_close()
            current_server_thread.join(timeout=5)


@unittest.skipUnless(os.environ.get('ASSET_HTTP_LEGACY_TEST') == '1', '격리 기존 콘텐츠 API가 필요합니다.')
class LegacyAssetServiceHttpTests(unittest.TestCase):
    def test_waypoint_registration_and_replacement_with_legacy_backend(current_test_case):
        from tools.management.domains.hermes_agent import effect_operations
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_gateway_service=ManagementCommandGateway({'map-assets':handle_map_resize_request})
        class IsolatedGatewayHandler(BaseHTTPRequestHandler):
            def do_POST(current_handler):
                current_gateway_service.handle(current_handler)
            def log_message(current_handler,*current_arguments):
                pass
        current_http_server=ThreadingHTTPServer(('127.0.0.1',0),IsolatedGatewayHandler)
        current_server_thread=threading.Thread(target=current_http_server.serve_forever,daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_temp_name:
                current_root_path=Path(current_temp_name)
                current_gateway_origin='http://127.0.0.1:'+str(current_http_server.server_port)
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin,'SLIME_CONTENT_STORAGE':'database'}),patch.object(effect_operations,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_effect_value={'id':'legacy-waypoint-old','name':'기존','image':'assets/sprites/effects/waypoint/waypoint-guide-v4.png','animation':'assets/sprites/effects/waypoint/waypoint-guide-v4.animation.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
                    current_preview_value=effect_operations.preview_hermes_effect_registration(current_effect_value)
                    current_result_value=effect_operations.register_hermes_effect_once('legacy_register_123',current_effect_value,current_preview_value['review_sha256'])
                    current_test_case.assertEqual(current_result_value['state'],'completed')
                    current_detail_value=effect_operations.read_hermes_effect_detail('legacy-waypoint-old')
                    current_replacement_value={**current_effect_value,'id':'legacy-waypoint-new','name':'새 웨이포인트'}
                    current_draft_value={'id':'legacy-waypoint-old','revision':current_detail_value['revision'],'effect':current_replacement_value}
                    current_review_value=effect_operations.preview_hermes_waypoint_replacement(current_draft_value)
                    current_replace_args=('legacy_replace_123',current_draft_value,current_review_value['review_sha256'])
                    current_test_case.assertEqual(effect_operations.replace_hermes_waypoint_once(*current_replace_args)['state'],'completed')
                    current_test_case.assertTrue(effect_operations.replace_hermes_waypoint_once(*current_replace_args)['duplicate'])
                    current_test_case.assertEqual(execute_content_api_request('GET','/internal/v1/content/effects')['effects'],[current_replacement_value])
                    current_fog_value={'id':'legacy-fog','name':'안개','image':'assets/sprites/effects/terrain/lake-fog-sheet-v2.png','renderer':'fog','columns':4,'rows':2,'frames':8,'alignment':{'key':'legacy-fog-key','texture':'legacy-fog-texture','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
                    current_fog_preview=effect_operations.preview_hermes_effect_registration(current_fog_value)
                    current_test_case.assertEqual(effect_operations.register_hermes_effect_once('legacy_fog_123',current_fog_value,current_fog_preview['review_sha256'])['state'],'completed')
                    current_generation_before=execute_content_api_request('GET','/internal/v1/content/status')['generation']
                    with current_test_case.assertRaises(ValueError):
                        execute_content_api_request('POST','/internal/v1/content/effects',{**current_fog_value,'id':'legacy-fog-duplicate'})
                    current_key_collision={**current_fog_value,'id':'legacy-fog-key-duplicate','alignment':{**current_fog_value['alignment'],'texture':'different-texture'}}
                    with current_test_case.assertRaises(ValueError):
                        execute_content_api_request('POST','/internal/v1/content/effects',current_key_collision)
                    current_test_case.assertEqual(execute_content_api_request('GET','/internal/v1/content/status')['generation'],current_generation_before)
                    current_effect_values=execute_content_api_request('GET','/internal/v1/content/effects')['effects']
                    current_test_case.assertEqual({record['id'] for record in current_effect_values},{'legacy-waypoint-new','legacy-fog'})
                    current_glow_value={'id':'legacy-glow','name':'발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'legacy-glow-key','texture':'test-grass','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
                    current_glow_preview=effect_operations.preview_hermes_effect_registration(current_glow_value)
                    with current_test_case.assertRaises(ValueError):
                        execute_content_api_request('POST','/internal/v1/content/effects/reviewed',{'effect':current_glow_value,'expectedBillboardRevision':2})
                    current_test_case.assertEqual(execute_content_api_request('GET','/internal/v1/content/status')['generation'],current_generation_before)
                    current_test_case.assertEqual(effect_operations.register_hermes_effect_once('legacy_glow_123',current_glow_value,current_glow_preview['review_sha256'])['state'],'completed')
                    from concurrent.futures import ThreadPoolExecutor
                    from threading import Barrier
                    current_start_barrier=Barrier(2)
                    def submit_concurrent_effect(current_effect_identifier):
                        current_concurrent_value={**current_fog_value,'id':current_effect_identifier,'alignment':{**current_fog_value['alignment'],'texture':'legacy-race-texture','key':current_effect_identifier}}
                        current_start_barrier.wait(timeout=5)
                        try:
                            execute_content_api_request('POST','/internal/v1/content/effects',current_concurrent_value)
                            return 'created'
                        except ValueError:
                            return 'rejected'
                    with ThreadPoolExecutor(max_workers=2) as current_executor_pool:
                        current_outcomes_value=list(current_executor_pool.map(submit_concurrent_effect,['legacy-race-one','legacy-race-two']))
                    current_test_case.assertEqual(sorted(current_outcomes_value),['created','rejected'])
        finally:
            current_http_server.shutdown()
            current_http_server.server_close()
            current_server_thread.join(timeout=5)
