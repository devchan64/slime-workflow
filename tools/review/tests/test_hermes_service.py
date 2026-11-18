import json
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from tools.review.domains.hermes_agent.service import HermesServiceManager
from tools.review.common.management_gateway import resolve_management_command, identify_management_command


class HermesServiceTests(unittest.TestCase):
    def setUp(self):
        self.hermes_temporary_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.hermes_temporary_root.cleanup)
        self.hermes_service_manager = HermesServiceManager(Path(self.hermes_temporary_root.name) / 'jobs', Path(self.hermes_temporary_root.name) / 'sessions')

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_duplicate_submission_is_single_queue_job(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'same-request-1234', 'prompt':'작은 테스트'}
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_result_values = list(hermes_thread_pool.map(lambda _: self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record), range(4)))
        self.assertEqual(hermes_launch_mock.call_count, 1)
        self.assertEqual(len({hermes_result_record['id'] for hermes_result_record in hermes_result_values}), 1)
        self.assertEqual(sum(hermes_result_record['duplicate'] for hermes_result_record in hermes_result_values), 3)
        with self.assertRaisesRegex(ValueError, '다른 지시'):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'same-request-1234', 'prompt':'다른 테스트'})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_unknown_acceptance_is_not_relaunched(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'unknown-request-1234', 'prompt':'테스트'}
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)
        hermes_job_status = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertEqual(hermes_job_status['status']['status'], 'unknown')
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)['duplicate'])
        hermes_launch_mock.assert_called_once()

    def test_read_only_management_observation_preserves_unknown_and_filters_fields(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('tools.review.common.gpu_status.read_gpu_status', return_value={'status':'busy', 'processes':[{'command':'private'}], 'gtt_free_mib':123, 'vram_free_mib':456, 'unexpected':'private'}), patch('tools.review.common.gpu_job_queue.list_waiting_gpu_jobs', return_value={'jobs':[{'id':'job-1', 'service':'kimodo', 'path':'private'}]}):
            hermes_observation_record = read_hermes_management_snapshot()
        self.assertEqual(hermes_observation_record['gpu']['status'], 'busy')
        self.assertIn('Kimodo 활성 상태는 기록 기준',hermes_observation_record['detail'])
        self.assertEqual(hermes_observation_record['gpu']['process_count'], 1)
        self.assertEqual(hermes_observation_record['queue']['jobs'], [{'id':'job-1', 'service':'kimodo'}])
        self.assertNotIn('private', str(hermes_observation_record))
        with patch('tools.review.common.gpu_status.read_gpu_status', side_effect=OSError('unavailable')), patch('tools.review.common.gpu_job_queue.list_waiting_gpu_jobs', side_effect=OSError('unavailable')):
            hermes_observation_record = read_hermes_management_snapshot()
        self.assertEqual(hermes_observation_record['gpu']['status'], 'unavailable')
        self.assertEqual(hermes_observation_record['queue']['status'], 'unavailable')

    def test_management_status_uses_shared_observation_and_rejects_input(self):
        from tools.review.domains.hermes_agent import management_observer
        current_snapshot_value = {'model': {'status': 'unavailable'}, 'gpu': {'status': 'busy'}, 'queue': {'status': 'available', 'jobs': []}}
        with patch.object(management_observer, 'read_hermes_management_snapshot', return_value=current_snapshot_value):
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-management-status', {}), current_snapshot_value)
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-management-status', {}), ('POST', '/hermes-agent/hermes-management-status'))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-management-status', {'command':'prepare'})

    def test_model_inventory_filters_paths_and_handles_invalid_responses(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_model_inventory
        current_response_record = {'models': {'kimodo': {'count':2, 'total_bytes':123, 'incomplete':False, 'files':[{'path':'private/path'}]}}}
        with patch('tools.review.common.management_gateway.execute_management_command', return_value=current_response_record) as current_gateway_mock:
            current_inventory_result = read_hermes_model_inventory()
        self.assertEqual(current_inventory_result['models'], [{'service':'kimodo', 'file_count':2, 'total_bytes':123, 'incomplete':False}])
        self.assertNotIn('private', str(current_inventory_result))
        self.assertEqual(current_gateway_mock.call_args.args[:3], ('model-downloads', 'download-inventory', {}))
        with patch('tools.review.common.management_gateway.execute_management_command', return_value={'models': {'kimodo': {'count':True, 'total_bytes':3, 'incomplete':False}}}):
            self.assertEqual(read_hermes_model_inventory()['status'], 'unavailable')
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-model-inventory', {'path':'other'})
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-model-inventory', {}), ('POST', '/hermes-agent/hermes-model-inventory'))

    def test_service_registration_exposes_new_services_without_granting_execution(self):
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        with patch.dict(MANAGEMENT_SERVICE_COMMANDS, {'future-service': ('future-command',)}):
            current_catalog_record = self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_future_record = next(item for item in current_catalog_record['services'] if item['service'] == 'future-service')
        self.assertEqual(current_future_record['commands'], ['future-command'])
        self.assertEqual(current_future_record['availability'], 'unverified')
        self.assertEqual(current_future_record['gateway_blocked'],[])
        self.assertEqual(current_future_record['known_service_blocked'],[])
        self.assertEqual(current_future_record['conditional_limitations'],[])
        current_vace_record=next(item for item in current_catalog_record['services'] if item['service']=='wan22-vace')
        self.assertTrue(any(item['command']=='resume' and 'official-bf16-resident-v1' in item['note'] for item in current_vace_record['conditional_limitations']))
        current_fun_record=next(item for item in current_catalog_record['services'] if item['service']=='wan22-fun-control')
        self.assertEqual({item['command'] for item in current_fun_record['conditional_limitations']},{'generate','resume'})
        current_music_record=next(item for item in current_catalog_record['services'] if item['service']=='music-magenta')
        current_music_blocks={item['command']:item['reason'] for item in current_music_record['known_service_blocked']}
        self.assertIn('generate',current_music_blocks)
        self.assertIn('resume',current_music_blocks)
        self.assertNotIn('history',current_music_blocks)
        current_animation_record=next(item for item in current_catalog_record['services'] if item['service']=='character-animation')
        current_animation_blocks={item['command']:item['reason'] for item in current_animation_record['known_service_blocked']}
        self.assertEqual(set(current_animation_blocks),{'generate','resume','record-alpha-vnccs'})
        self.assertIn('sheet-update',current_animation_record['commands'])
        from tools.review.domains.character_animation.character_animation_jobs import execute_animation_command
        for current_command_name,current_reason_text in current_animation_blocks.items():
            with self.assertRaises(ValueError) as current_error_value:
                execute_animation_command(current_command_name,{})
            self.assertEqual(str(current_error_value.exception),current_reason_text)
        from tools.review.domains.music.generation import MusicGenerationManager
        current_music_manager=MusicGenerationManager('music-magenta')
        for current_command_name in ('generate','resume'):
            with self.assertRaises(ValueError) as current_error_value:
                current_music_manager.execute_music_command(current_command_name,{})
            self.assertEqual(str(current_error_value.exception),current_music_blocks[current_command_name])
        current_retired_record=next(item for item in current_catalog_record['services'] if item['service']=='momask')
        self.assertEqual({item['command'] for item in current_retired_record['gateway_blocked']},set(current_retired_record['commands']))
        current_qwen_record=next(item for item in current_catalog_record['services'] if item['service']=='qwen-21')
        self.assertIn('generate',{item['command'] for item in current_qwen_record['gateway_blocked']})
        self.assertNotIn('history',{item['command'] for item in current_qwen_record['gateway_blocked']})
        for current_service_record in current_catalog_record['services']:
            for current_blocked_record in current_service_record['gateway_blocked']:
                with self.assertRaises(ValueError) as current_error_value:
                    resolve_management_command(current_service_record['service'],current_blocked_record['command'],{})
                self.assertEqual(str(current_error_value.exception),current_blocked_record['reason'])
        self.assertIn('실행 가능 여부', current_catalog_record['note'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {'service':'future-service'})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('future-command', {})
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-service-registration', {}), ('POST', '/hermes-agent/hermes-service-registration'))

    def test_service_registration_search_uses_shared_catalog(self):
        current_search_result=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'query':'음악','offset':0,'limit':10})
        self.assertTrue({'music-heartmula','sfx-dasheng-audiogen'} <= {current_record['service'] for current_record in current_search_result['services']})
        self.assertIsNone(current_search_result['next_offset'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'limit':11})

    def test_kimodo_build_status_sanitizes_existing_service(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_kimodo_build_status
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'status':'completed','cache_status':'unverified','id':'2026-11-18_00-00-00-12345678','error':'private path'}) as current_gateway_mock:
            current_status_value=self.hermes_service_manager.execute_hermes_command('hermes-kimodo-build-status',{})
        self.assertEqual(current_status_value['status'],'completed')
        self.assertEqual(current_status_value['build_status'],'completed')
        self.assertEqual(current_status_value['cache_status'],'unverified')
        self.assertNotIn('private',str(current_status_value))
        self.assertEqual(current_gateway_mock.call_args.args[:3],('kimodo','migraphx-build-observe',{}))
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'status':'completed','cache_status':'unverified','id':'../private'}):
            self.assertEqual(read_hermes_kimodo_build_status()['status'],'unavailable')
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-kimodo-build-status',{'extra':True})

    def test_field_commands_require_exact_payloads(self):
        with patch('tools.review.domains.hermes_agent.field_map_operations.load_hermes_field_map', return_value={'map':'moss-clearing'}) as current_load_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-field-load', {'map':'moss-clearing'})['map'],'moss-clearing')
            current_load_mock.assert_called_once_with('moss-clearing')
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-field-load', {'map':'moss-clearing','path':'other'})
        self.assertEqual(resolve_management_command('hermes-agent','hermes-field-preview',{'draft':{}}), ('POST','/hermes-agent/hermes-field-preview'))

    def test_content_database_status_sanitizes_and_rejects_inconsistent_data(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_content_database_status
        current_database_value = {'generation':9, 'snapshotGeneration':7, 'pending':True, 'latestSnapshot':{'generation':8,'state':'failed','leaseExpired':False,'error':'private secret','runId':'private'}}
        with patch('tools.review.common.management_gateway.execute_management_command', return_value=current_database_value) as current_gateway_mock:
            current_result_value = self.hermes_service_manager.execute_hermes_command('hermes-content-database-status', {})
        self.assertEqual(current_result_value['ledger_generation'], 7)
        self.assertTrue(current_result_value['pending'])
        self.assertEqual(current_result_value['latest']['state'], 'failed')
        self.assertNotIn('private', str(current_result_value))
        self.assertEqual(current_gateway_mock.call_args.args[:3], ('map-assets','database-status',{}))
        with patch('tools.review.common.management_gateway.execute_management_command', return_value={**current_database_value,'pending':False}):
            self.assertEqual(read_hermes_content_database_status()['status'], 'unavailable')
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=RuntimeError('secret')):
            self.assertNotIn('secret',str(read_hermes_content_database_status()))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-content-database-status', {'command':'database-restore'})
        self.assertEqual(resolve_management_command('hermes-agent','hermes-content-database-status',{}), ('POST','/hermes-agent/hermes-content-database-status'))

    def test_model_preparation_respects_existing_policy_and_keeps_receipt(self):
        from tools.review.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        current_store_value = HermesModelPreparationStore(Path(self.hermes_temporary_root.name) / 'receipts')
        current_request_value = {'request_id':'request_prepare_123', 'service':'flux-image'}
        with patch('tools.review.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore', return_value=current_store_value), patch('tools.review.common.management_gateway.execute_management_command', return_value={'preparation_status':'running', 'path':'private'}) as current_gateway_mock:
            current_result_value = self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', current_request_value)
            self.assertEqual(current_result_value['state'], 'accepted')
            self.assertNotIn('private', str(current_result_value))
            self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', current_request_value)['duplicate'])
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-model-prepare-status', current_request_value)['state'], 'accepted')
            current_gateway_mock.assert_called_once()
            self.assertEqual(current_gateway_mock.call_args.args[:3], ('flux-image','prepare',{'action':'prepare'}))
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_blocked_123','service':'expression-lora'})
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_blocked_123','service':'flux-image', 'url':'private'})
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_blocked_123','service':[]})
        self.assertEqual(resolve_management_command('hermes-agent','hermes-model-prepare',current_request_value), ('POST','/hermes-agent/hermes-model-prepare'))

    def test_audio_model_preparation_uses_download_command(self):
        from tools.review.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        current_store_value = HermesModelPreparationStore(Path(self.hermes_temporary_root.name) / 'receipts')
        with patch('tools.review.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore', return_value=current_store_value), patch('tools.review.common.management_gateway.execute_management_command', return_value={'ready':False,'preparation_status':'running'}) as current_gateway_mock:
            self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_audio_123','service':'music-heartmula'})
        self.assertEqual(current_gateway_mock.call_args.args[:3], ('music-heartmula','download-model',{}))

    def test_model_readiness_accepts_only_registered_service_and_filters_response(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_model_readiness
        with patch('tools.review.common.management_gateway.execute_management_command', return_value={'ready':True,'generation_ready':True,'preparation_status':'completed','path':'private','secret':'private'}) as current_gateway_mock:
            current_status = read_hermes_model_readiness('flux-image')
            self.assertTrue(current_status['ready'])
            self.assertTrue(current_status['generation_ready'])
            self.assertNotIn('private',str(current_status))
            current_gateway_mock.assert_called_once()
            self.assertEqual(current_gateway_mock.call_args.args[:3],('flux-image','model-status',{}))
            with self.assertRaises(ValueError):
                read_hermes_model_readiness('unregistered-service')
            current_gateway_mock.assert_called_once()
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[{'ready':True,'preparation_status':'running','path':'private'},{'ready':False,'artifacts_ready':True}]):
            current_status = read_hermes_model_readiness('music-heartmula')
            self.assertFalse(current_status['ready'])
            self.assertTrue(current_status['artifacts_ready'])
            self.assertIsNone(current_status['generation_ready'])
            self.assertEqual(current_status['download'],{'ready':True,'preparation_status':'running'})
            self.assertNotIn('private',str(current_status))
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[OSError('private'),{'ready':False}]):
            current_status = read_hermes_model_readiness('music-heartmula')
            self.assertEqual(current_status['status'],'available')
            self.assertIsNone(current_status['download'])
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[{'ready':False,'preparation_status':'running'},OSError('private')]):
            current_status = read_hermes_model_readiness('music-heartmula')
            self.assertEqual(current_status['status'],'unavailable')
            self.assertEqual(current_status['download'],{'ready':False,'preparation_status':'running'})
            self.assertNotIn('private',str(current_status))
        with patch('tools.review.common.management_gateway.execute_management_command', return_value={'ready':True}):
            current_status = read_hermes_model_readiness('flux-image')
            self.assertIsNone(current_status['generation_ready'])
            self.assertEqual(current_status['preparation_status'],'unknown')
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=OSError('private path')):
            current_status = read_hermes_model_readiness('flux-image')
            self.assertEqual(current_status['status'],'unavailable')
            self.assertNotIn('private',str(current_status))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-model-readiness', {'service':'flux-image','extra':'prepare'})

    def test_building_catalog_uses_generation_and_filters_paths(self):
        from tools.review.domains.hermes_agent.asset_observer import read_hermes_building_catalog
        current_asset_record={'texture':'town-iseulon-guild-v1','image':'/private/image.png','width':512,'height':256,'properties':{'anchorX':0.5,'anchorY':1.0,'private':'secret'},'maps':[{'map':'iseulon','name':'길드','width':2,'height':3,'facing':'front','contentWidth':2}]}
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'generation':7,'assets':[current_asset_record]}) as current_gateway_mock:
            current_result=read_hermes_building_catalog({'query':'길드','limit':1})
        self.assertEqual(current_result['generation'],7)
        self.assertEqual(current_result['items'][0]['uses'][0]['map'],'iseulon')
        self.assertEqual(current_result['items'][0]['image_pixels'],{'width':512,'height':256})
        self.assertNotIn('/private',str(current_result))
        self.assertNotIn('secret',str(current_result))
        current_gateway_mock.assert_called_once()
        self.assertEqual(current_gateway_mock.call_args.args[:3],('map-assets','building-list',{}))
        for current_invalid_record in ({'limit':31},{'offset':True},{'query':'a\nb'},{'command':'building-save'}):
            with self.subTest(request=current_invalid_record),self.assertRaises(ValueError):
                read_hermes_building_catalog(current_invalid_record)
        with patch('tools.review.common.management_gateway.execute_management_command',side_effect=ValueError('/private')):
            with self.assertRaisesRegex(ValueError,'콘텐츠 서비스 연결') as current_error:
                read_hermes_building_catalog({})
            self.assertNotIn('/private',str(current_error.exception))

    def test_building_pages_reject_changed_generation_data_and_query(self):
        from tools.review.domains.hermes_agent.asset_observer import read_hermes_building_catalog
        current_assets_list=[{'texture':'town-test-'+str(index)+'-v1','width':2,'height':2,'properties':{'anchorX':0.5,'anchorY':1},'maps':[]} for index in range(3)]
        current_catalog_value={'generation':5,'assets':current_assets_list}
        with patch('tools.review.common.management_gateway.execute_management_command',return_value=current_catalog_value):
            current_first_page=read_hermes_building_catalog({'limit':1})
            current_second_page=read_hermes_building_catalog({'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            self.assertNotEqual(current_first_page['items'][0]['id'],current_second_page['items'][0]['id'])
            with self.assertRaisesRegex(ValueError,'변경'):
                read_hermes_building_catalog({'query':'town','limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            current_catalog_value['generation']=6
            with self.assertRaisesRegex(ValueError,'변경'):
                read_hermes_building_catalog({'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            current_catalog_value['generation']=5
            current_assets_list[1]['properties']['anchorX']=1
            with self.assertRaisesRegex(ValueError,'변경'):
                read_hermes_building_catalog({'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            with self.assertRaises(ValueError):read_hermes_building_catalog({'snapshot':'bad'})

    def test_world_map_uses_validated_source_and_omits_private_paths(self):
        from tools.review.domains.hermes_agent.asset_observer import read_hermes_world_map_catalog
        current_catalog = {'maps':[{'id':'town','name':'마을','safeTown':True,'column':0,'row':1,'connections':[{'id':'gate','target':'field','direction':'north','targetWaypointId':'return','path':'/private'}], 'thumbnail':{'url':'/private'}}], 'provenance':[{'managementId':'map.example','version':'v1','sha256':'a'*64,'source':'/private'}]}
        with patch('tools.review.domains.world_map.catalog.load_world_review_catalog',return_value=current_catalog) as current_source_mock:
            current_result = read_hermes_world_map_catalog()
        current_source_mock.assert_called_once_with()
        self.assertEqual(current_result['maps'][0]['connections'][0]['target'],'field')
        self.assertEqual(current_result['provenance'][0]['sha256'],'a'*64)
        self.assertNotIn('/private',str(current_result))
        current_catalog['provenance'][0]['source'] = 'assets/maps/map_names/town.yaml'
        with patch('tools.review.domains.world_map.catalog.load_world_review_catalog',return_value=current_catalog):
            current_selected = read_hermes_world_map_catalog('town')
        self.assertEqual(current_selected['provenance_scope'],'selected_map')
        self.assertEqual(current_selected['provenance'][0]['managementId'],'map.example')
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-world-map', {'map':None})
        with patch('tools.review.domains.world_map.catalog.load_world_review_catalog',side_effect=ValueError('/private')):
            with self.assertRaisesRegex(ValueError,'원본을 검증') as current_error:
                read_hermes_world_map_catalog()
            self.assertNotIn('/private',str(current_error.exception))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-world-map', {'command':'save'})

    def test_billboard_catalog_filters_paths_and_paginates(self):
        from tools.review.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog
        current_asset_record = {'texture':'tree-v1','name':'나무','category':'large-trees','image':'/private/image.png','properties':{'displayHeight':42,'anchorX':0.5,'private':'secret'},'maps':[{'path':'assets/maps/field_tiles/a.yaml','texture_key_occurrences':2},{'path':'/private/path','texture_key_occurrences':1}], 'modeling':{'purpose':'그늘','basis':'등록 이름 기준','visual_review':{'status':'확인 필요','source_sha256':'secret'}}, 'metadata':['private']}
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'revision':'a'*64,'assets':[current_asset_record,{**current_asset_record,'texture':'tree-v2'}]}) as current_gateway_mock:
            current_result = read_hermes_billboard_catalog({'category':'large-trees','query':'나무','limit':1})
        self.assertEqual(current_result['total'],2)
        self.assertEqual(current_result['next_offset'],1)
        self.assertEqual(current_result['items'][0]['maps'],[{'map':'a','source_path':'assets/maps/field_tiles/a.yaml','occurrences':2}])
        self.assertEqual(current_result['items'][0]['display_properties']['displayHeight'],42)
        self.assertEqual(current_result['items'][0]['modeling']['visual_review_status'],'확인 필요')
        self.assertNotIn('private',str(current_result))
        self.assertNotIn('secret',str(current_result))
        self.assertEqual(current_gateway_mock.call_args.args[:3],('map-assets','asset-list',{'category':'large-trees'}))
        for current_bad_request in ({'limit':31},{'offset':True},{'query':'line\nbreak'},{'category':'../../x'},{'command':'asset-save'}):
            with self.subTest(request=current_bad_request), self.assertRaises(ValueError):
                read_hermes_billboard_catalog(current_bad_request)
        with patch('tools.review.common.management_gateway.execute_management_command',side_effect=OSError('/private')):
            with self.assertRaisesRegex(ValueError,'확인할 수 없습니다') as current_error:
                read_hermes_billboard_catalog({})
            self.assertNotIn('/private',str(current_error.exception))

    def test_kimodo_recorded_active_observation_never_recovers_jobs(self):
        from tools.review.domains.kimodo.generation import KimodoGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_manager_value=KimodoGenerationManager()
            current_manager_value.job_storage_root=Path(current_temp_root)/'jobs'
            self.assertEqual(current_manager_value.read_kimodo_recorded_active_status()['count'],0)
            current_running_path=current_manager_value.job_storage_root/'2026-11-17_10-00-00-12345678'
            current_running_path.mkdir(parents=True)
            current_status_path=current_running_path/'status.json'
            current_status_bytes=b'{"status":"running"}\n'
            current_status_path.write_bytes(current_status_bytes)
            current_result_value=current_manager_value.read_kimodo_recorded_active_status()
            self.assertTrue(current_result_value['running'])
            self.assertEqual(current_result_value['id'],current_running_path.name)
            self.assertIn('프로세스 생존',current_result_value['note'])
            self.assertEqual(current_status_path.read_bytes(),current_status_bytes)
            self.assertFalse((current_running_path/'resume.lock').exists())
            current_status_path.unlink()
            current_unknown_value=current_manager_value.read_kimodo_recorded_active_status()
            self.assertFalse(current_unknown_value['running'])
            self.assertEqual(current_unknown_value['unknown_count'],1)
            current_status_path.write_bytes(current_status_bytes)
            current_corrupt_path=current_manager_value.job_storage_root/'2026-11-17_11-00-00-87654321'
            current_corrupt_path.mkdir()
            (current_corrupt_path/'status.json').write_text('{broken')
            current_partial_value=current_manager_value.read_kimodo_recorded_active_status()
            self.assertEqual(current_partial_value['count'],1)
            self.assertEqual(current_partial_value['unknown_count'],1)
            self.assertEqual(current_status_path.read_bytes(),current_status_bytes)
        self.assertEqual(resolve_management_command('kimodo','active-observe',{}),('GET','/kimodo/active-observe'))

    def test_generator_observation_uses_only_fixed_read_commands(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_generator_snapshot
        current_job_id = '2026-11-17_10-00-00-12345678'
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[{'ready':True, 'preparation_status':'idle', 'private':'secret'}, {'running':True, 'id':current_job_id, 'count':2, 'unknown_count':1, 'private':'secret'}]) as current_gateway_mock:
            current_generator_value = read_hermes_generator_snapshot()['kimodo']
        self.assertEqual(current_generator_value['model'], {'status':'available', 'ready':True, 'preparation_status':'idle'})
        self.assertEqual(current_generator_value['active'], {'status':'available', 'running':True, 'id':current_job_id, 'count':2, 'unknown_count':1})
        self.assertEqual([current_call.args[:3] for current_call in current_gateway_mock.call_args_list], [('kimodo', 'model-status', {}), ('kimodo', 'active-observe', {})])
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[ValueError('offline'), {'running':True, 'id':'../../bad'}]):
            current_generator_value = read_hermes_generator_snapshot()['kimodo']
        self.assertEqual(current_generator_value['model']['status'], 'unavailable')
        self.assertEqual(current_generator_value['active']['status'], 'unavailable')
        for current_bad_record in ({'running':False,'id':None,'count':1,'unknown_count':0},{'running':True,'id':current_job_id,'count':True,'unknown_count':0},{'running':False,'id':current_job_id,'count':0,'unknown_count':0},{'running':False,'id':None,'count':0,'unknown_count':True}):
            with self.subTest(response=current_bad_record),patch('tools.review.common.management_gateway.execute_management_command',side_effect=[{'ready':True},current_bad_record]):
                self.assertEqual(read_hermes_generator_snapshot()['kimodo']['active']['status'],'unavailable')

    def test_model_observation_reports_failure_without_ready_claim(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('tools.review.domains.hermes_agent.management_observer.inspect_hermes_model_status', side_effect=OSError('unavailable')):
            current_observation_record = read_hermes_management_snapshot()
        self.assertEqual(current_observation_record['model'], {'status': 'unavailable'})

    def test_reservation_observation_is_filtered_and_conservative(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_root_path = Path(current_temp_root)
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'], [])
            current_active_path = current_root_path / 'active'
            current_active_path.mkdir()
            current_job_id = '2026-11-18_00-00-00-12345678'
            (current_active_path / 'one.json').write_text(json.dumps({'service':'hermes-agent','required_memory_mib':32768,'path':'/private/' + current_job_id,'worker_process_token':'secret','pid':123}))
            (current_active_path / 'two.json').write_text('bad json')
            current_result_value = read_hermes_gpu_reservation_snapshot(current_root_path)
            self.assertEqual(current_result_value['status'], 'available')
            self.assertEqual(current_result_value['records'][0], {'state':'recorded','service':'hermes-agent','job_id':current_job_id,'required_memory_mib':32768})
            self.assertEqual(current_result_value['records'][1]['state'], 'unknown')
            self.assertNotIn('secret', str(current_result_value))
            self.assertNotIn('/private/', str(current_result_value))
            (current_active_path / 'two.json').unlink()
            (current_active_path / 'two.json').symlink_to(current_active_path / 'one.json')
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'][1]['state'], 'unknown')
            with patch('os.scandir', side_effect=PermissionError('denied')):
                self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['status'], 'unavailable')

    def test_recent_job_observation_filters_fields_and_handles_missing_status(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_recent_job_snapshot
        current_job_root = self.hermes_service_manager.hermes_storage_root
        current_job_root.mkdir(parents=True, exist_ok=True)
        for current_index in range(12):
            current_job_path = current_job_root / ('2026-11-18_00-00-' + f'{current_index:02d}' + '-12345678')
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text('{"prompt":"secret"}')
            if current_index != 11:
                (current_job_path / 'status.json').write_text('{"status":"completed","error":"private"}')
        current_result_value = read_hermes_recent_job_snapshot(self.hermes_service_manager)
        self.assertEqual(current_result_value['status'], 'available')
        self.assertEqual(len(current_result_value['jobs']), 10)
        self.assertTrue(current_result_value['truncated'])
        self.assertEqual(current_result_value['jobs'][0]['status'], 'unknown')
        self.assertNotIn('secret', str(current_result_value))
        self.assertNotIn('private', str(current_result_value))
        self.assertNotIn(str(current_job_root), str(current_result_value))
        with patch.object(self.hermes_service_manager, 'list_hermes_job_paths', side_effect=OSError('unavailable')):
            self.assertEqual(read_hermes_recent_job_snapshot(self.hermes_service_manager)['status'], 'unavailable')

    def test_writer_reservation_preview_rejects_unverified_or_ambiguous_targets(self):
        import os
        from tools.review.common import gpu_job_queue
        from tools.review.domains.hermes_agent.writer_reservation import preview_writer_reservation_recovery
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_active_path=current_root_path/'active'
            current_active_path.mkdir()
            current_job_identifier='20261118-120000-12345678'
            current_reservation_value={'service':'writer-agent','path':'/private/jobs/'+current_job_identifier,'pid':os.getpid(),'pid_start_token':'different'}
            (current_active_path/'one.json').write_text(json.dumps(current_reservation_value))
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_root_path),patch.object(gpu_job_queue,'open_verified_hermes_process_group',return_value=None):
                current_preview_value=preview_writer_reservation_recovery(current_job_identifier)
                self.assertFalse(current_preview_value['recoverable'])
                self.assertNotIn('/private',str(current_preview_value))
                (current_active_path/'two.json').write_text(json.dumps(current_reservation_value))
                with self.assertRaisesRegex(ValueError,'둘 이상'):preview_writer_reservation_recovery(current_job_identifier)
                with self.assertRaises(ValueError):preview_writer_reservation_recovery('../private')

    def test_unverified_writer_cleanup_reservation_is_visible(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_active_path=current_root_path/'active'
            current_active_path.mkdir()
            (current_active_path/'writer.json').write_text(json.dumps({'service':'writer-agent','path':'/private/jobs/20261118-120000-12345678','required_memory_mib':16384,'cleanup_unverified':True,'worker_pgid':123}))
            current_result_value=read_hermes_gpu_reservation_snapshot(current_root_path)
            self.assertEqual(current_result_value['records'][0]['state'],'cleanup_unverified')
            self.assertEqual(current_result_value['records'][0]['job_id'],'20261118-120000-12345678')
            self.assertNotIn('/private',str(current_result_value))
            (current_active_path/'writer.json').write_text(json.dumps({'service':'writer-agent','required_memory_mib':16384,'cleanup_unverified':'yes'}))
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'][0]['state'],'unknown')

    def test_capabilities_use_registered_gateway_and_strict_empty_input(self):
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES
        current_catalog_value = self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        self.assertEqual(current_catalog_value['version'], 1)
        self.assertTrue(current_catalog_value['records'])
        self.assertEqual(current_catalog_value['unlisted_commands'],[])
        current_capabilities_by_name={current_record['command']:current_record for current_record in current_catalog_value['records']}
        for current_command_name in ('hermes-video-proposal','hermes-kimodo-proposal','hermes-diff','hermes-delegation-status','hermes-flux-delegation-history'):
            self.assertEqual(current_capabilities_by_name[current_command_name]['effect'],'local_bookkeeping')
        self.assertEqual(current_capabilities_by_name['hermes-management-status']['effect'],'local_bookkeeping')
        self.assertEqual(current_capabilities_by_name['hermes-kimodo-build-status']['gpu'],'none')
        self.assertIn('캐시 유효성',current_capabilities_by_name['hermes-kimodo-build-status']['note'])
        current_command_list=MANAGEMENT_SERVICE_COMMANDS['hermes-agent']
        with patch.dict(MANAGEMENT_SERVICE_COMMANDS, {'hermes-agent':[*current_command_list,'hermes-new-command']}):
            current_drift_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        self.assertEqual(current_drift_value['unlisted_commands'],['hermes-new-command'])
        for current_record_value in current_catalog_value['records']:
            self.assertIn(current_record_value['command'], MANAGEMENT_SERVICE_COMMANDS['hermes-agent'])
            self.assertEqual(current_record_value['method'], MANAGEMENT_COMMAND_ROUTES[current_record_value['command']][0])
            self.assertIn(current_record_value['effect'], ('read', 'write', 'enqueue', 'recovery_possible', 'cancel_request', 'local_bookkeeping'))
            self.assertEqual(current_record_value['payload_schema']['required'], current_record_value['required'])
            self.assertEqual(set(current_record_value['payload_schema']['properties']), set(current_record_value['required'] + current_record_value['optional']), current_record_value['command'])
            self.assertFalse(current_record_value['payload_schema']['additionalProperties'])
        for current_command_name in ('hermes-video-proposal','hermes-audio-proposal'):
            self.assertNotIn('service',current_capabilities_by_name[current_command_name]['payload_schema']['properties'])
        self.assertIn('service',current_capabilities_by_name['hermes-delegate-video']['payload_schema']['properties'])
        self.assertIn('service',current_capabilities_by_name['hermes-delegate-audio']['payload_schema']['properties'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {'extra':True})

    def test_keyframe_capability_schema_matches_batch_contract(self):
        from jsonschema import Draft202012Validator
        from tools.review.domains.kimodo.keyframe_storage import KIMODO_KEYFRAME_LIMIT
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_record_value=next(record for record in current_catalog_value['records'] if record['command']=='hermes-kimodo-keyframe-validate')
        current_schema_value=current_record_value['payload_schema']
        self.assertEqual(current_schema_value['properties']['keyframes']['maxItems'],KIMODO_KEYFRAME_LIMIT)
        current_validator_value=Draft202012Validator(current_schema_value)
        self.assertTrue(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'a'*32,'frame':1}]}))
        self.assertFalse(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'invalid','frame':1}]}))
        self.assertFalse(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'a'*32,'frame':1,'extra':True}]}))
        self.assertFalse(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'a'*32,'frame':1}]*(KIMODO_KEYFRAME_LIMIT+1)}))

    def test_capability_schema_describes_pagination_and_optional_filters(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        current_schemas_by_command={record['command']:record['payload_schema'] for record in current_catalog_value['records']}
        current_keyframe_validator=Draft202012Validator(current_schemas_by_command['hermes-kimodo-keyframes'])
        self.assertTrue(current_keyframe_validator.is_valid({'snapshot':None}))
        self.assertTrue(current_keyframe_validator.is_valid({'snapshot':'a'*64}))
        self.assertFalse(current_keyframe_validator.is_valid({'snapshot':'invalid'}))
        current_sprite_validator=Draft202012Validator(current_schemas_by_command['hermes-sprite-detail'])
        self.assertTrue(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':0,'snapshot':None}))
        self.assertFalse(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':1}))
        self.assertFalse(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':1,'snapshot':None}))
        self.assertTrue(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':1,'snapshot':'a'*64}))
        current_world_validator=Draft202012Validator(current_schemas_by_command['hermes-world-map'])
        self.assertTrue(current_world_validator.is_valid({}))
        self.assertTrue(current_world_validator.is_valid({'map':'forest'}))
        self.assertFalse(current_world_validator.is_valid({'map':None}))
        self.assertTrue(Draft202012Validator(current_schemas_by_command['hermes-billboard-catalog']).is_valid({'category':None}))
        self.assertFalse(Draft202012Validator(current_schemas_by_command['hermes-sprite-catalog']).is_valid({'query':'first\nsecond'}))
        current_field_validator=Draft202012Validator(current_schemas_by_command['hermes-field-region'])
        self.assertTrue(current_field_validator.is_valid({'map':'forest','revision':None}))
        self.assertFalse(current_field_validator.is_valid({'map':'forest','revision':''}))

    def test_building_anchor_capability_describes_strict_draft(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schema_value=next(item['payload_schema'] for item in current_catalog_value['records'] if item['command']=='hermes-building-preview')
        current_validator_value=Draft202012Validator(current_schema_value)
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        self.assertTrue(current_validator_value.is_valid({'draft':current_draft_value}))
        for current_invalid_value in ({**current_draft_value,'generation':True},{**current_draft_value,'texture':'bad'}, {**current_draft_value,'unknown':1},{**current_draft_value,'properties':{'anchorX':17,'anchorY':1}},{**current_draft_value,'properties':{'anchorX':0.5,'anchorY':1,'displayWidthAdjustment':1}},{**current_draft_value,'properties':{'anchorX':0.5,'anchorY':1,'shadowShape':'circle'}}):
            with self.subTest(draft=current_invalid_value):self.assertFalse(current_validator_value.is_valid({'draft':current_invalid_value}))

    def test_source_history_catalog_matches_routes_and_capabilities(self):
        from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS,resolve_management_command
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={record['service']:record for record in current_service_catalog['services']}
        for current_service_name in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES):
            with self.subTest(service=current_service_name):
                current_source_command='writer-history-observe' if current_service_name=='writer-agent' else 'history-observe'
                self.assertIn(current_source_command,MANAGEMENT_SERVICE_COMMANDS[current_service_name])
                self.assertEqual(resolve_management_command(current_service_name,current_source_command,{})[0],'POST')
                current_expected_link='hermes-audio-source-history' if current_service_name in SOURCE_HISTORY_AUDIO_SERVICES else 'hermes-generator-source-history'
                self.assertIn(current_expected_link,current_service_records[current_service_name]['hermes_links'])
        self.assertEqual(len(SOURCE_HISTORY_GENERATOR_SERVICES),len(set(SOURCE_HISTORY_GENERATOR_SERVICES)))
        self.assertFalse(set(SOURCE_HISTORY_GENERATOR_SERVICES)&set(SOURCE_HISTORY_AUDIO_SERVICES))

    def test_service_registration_links_to_existing_hermes_capabilities(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_capability_catalog=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_capability_names={record['command'] for record in current_capability_catalog['records']}
        current_service_records={record['service']:record for record in current_service_catalog['services']}
        for current_service_name,current_expected_command in (('music-heartmula','hermes-delegate-audio'),('wan22-vace','hermes-delegate-video'),('flux-building','hermes-delegate-flux-profile'),('kimodo','hermes-delegate-kimodo'),('writer-agent','hermes-delegate-writer'),('prompt-translation','hermes-delegate-translation'),('map-assets','hermes-city-save'),('map-assets','hermes-effect-register'),('character-animation','hermes-sprite-save'),('character-animation','hermes-sprite-catalog'),('kimodo','hermes-kimodo-keyframes'),('model-downloads','hermes-model-inventory')):
            self.assertIn(current_expected_command,current_service_records[current_service_name]['hermes_links'])
        for current_service_name,current_expected_commands in {
            'flux-image':{'hermes-delegate-flux-image','hermes-flux-delegation-status','hermes-flux-delegation-history','hermes-flux-delegation-cancel','hermes-flux-proposal'},
            'map-assets':{'hermes-billboard-receipt','hermes-effect-receipt','hermes-effect-register-receipt','hermes-waypoint-receipt','hermes-field-receipt','hermes-field-history','hermes-city-receipt','hermes-city-history'},
            'character-animation':{'hermes-sprite-proposal','hermes-sprite-receipt'},
            'writer-agent':{'hermes-writer-apply-status','hermes-writer-apply-history'},
            'prompt-translation':{'hermes-translation-proposal'},
        }.items():
            self.assertTrue(current_expected_commands <= set(current_service_records[current_service_name]['hermes_links']))
        for current_service_record in current_service_catalog['services']:
            self.assertTrue(set(current_service_record['hermes_links']) <= current_capability_names)
            self.assertEqual(len(current_service_record['hermes_links']),len(set(current_service_record['hermes_links'])))
        from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation
        for _,current_service_name in MODEL_PREPARATION_SERVICES:
            current_links_value=current_service_records[current_service_name]['hermes_links']
            self.assertIn('hermes-model-readiness',current_links_value)
            self.assertIn('hermes-model-prepare-status',current_links_value)
            current_prepare_allowed=inspect_registered_model_operation(current_service_name,MANAGEMENT_SERVICE_COMMANDS[current_service_name],'prepare') is not None
            self.assertEqual('hermes-model-prepare' in current_links_value,current_prepare_allowed)

    def test_known_flux_seamless_limitations_match_service_validator(self):
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_service_value=next(record for record in current_catalog_value['services'] if record['service']=='flux-seamless')
        current_note_value=next(record['note'] for record in current_service_value['conditional_limitations'] if record['command']=='generate')
        for current_expected_text in ('512×512','참조 이미지 없음','global-periodic-v1','16스텝'):
            self.assertIn(current_expected_text,current_note_value)
        current_manager_value=FluxImageGenerationManager('flux-seamless')
        current_request_value={'action':'generate','prompt':'grass','images':[],'width':512,'height':512,'steps':16,'seed':42}
        self.assertEqual(current_manager_value.validate_generation_request(current_request_value)['seamless_method'],'global-periodic-v1')
        for current_change_value in ({'width':768},{'steps':20},{'seamless_method':'edge-blend'}):
            with self.subTest(change=current_change_value),self.assertRaises(ValueError):
                current_manager_value.validate_generation_request({**current_request_value,**current_change_value})

    def test_flux_profile_reference_limits_match_service_validators(self):
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        from tools.review.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_records_by_service={record['service']:record for record in current_catalog_value['services']}
        current_request_value={'action':'generate','prompt':'grass','images':[],'width':768,'height':768,'steps':16,'seed':42}
        for current_profile_name,current_profile_values in FLUX_IMAGE_PROFILE_RECORDS.items():
            if current_profile_name=='flux-seamless':
                continue
            current_note_value=next(record['note'] for record in current_records_by_service[current_profile_name]['conditional_limitations'] if record['command']=='generate')
            self.assertIn('최대 2장',current_note_value)
            self.assertIn('16스텝',current_note_value)
            current_manager_value=FluxImageGenerationManager(current_profile_name)
            if current_profile_values[4]:
                self.assertIn('첫 참조 이미지가 필요',current_note_value)
                with self.subTest(profile=current_profile_name),self.assertRaises(ValueError):
                    current_manager_value.validate_generation_request(current_request_value)
        current_note_value=next(record['note'] for record in current_records_by_service['flux-expression']['conditional_limitations'] if record['command']=='generate')
        self.assertIn('얼굴 참조 이미지 1장',current_note_value)
        with self.assertRaises(ValueError):
            FluxExpressionGenerationManager().validate_generation_request(current_request_value)

    def test_known_video_limitations_match_service_validators(self):
        from generators.wan_fun.contracts import reject_retired_rgb_input, validate_fun_request
        from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_records_by_service={record['service']:record for record in current_catalog_value['services']}
        current_fun_notes=' '.join(item['note'] for item in current_records_by_service['wan22-fun-control']['conditional_limitations'])
        for current_request_value in ({'start_image':'image'},{'end_image':'image'},{'input_mode':'reference-only'},{'input_mode':'rgb-video'}):
            with self.subTest(request=current_request_value),self.assertRaises(ValueError):
                reject_retired_rgb_input(current_request_value)
        self.assertIn('타일 VAE',current_fun_notes)
        current_tiled_request={'action':'generate','prompt':'walk','negative_prompt':'','images':[],'width':832,'height':480,'frames':5,'steps':20,'seed':42,'flow_shift':5,'guidance_scale':6,'switch_ratio':0.5,'control_type':'pose','pose_video':'video','use_regular_vae':False}
        with self.assertRaisesRegex(ValueError,'타일 VAE'):
            validate_fun_request(current_tiled_request)
        current_vace_notes=' '.join(item['note'] for item in current_records_by_service['wan22-vace']['conditional_limitations'])
        self.assertIn('official-bf16-resident-v1',current_vace_notes)
        with patch('tools.review.domains.wan_vace.generation.validate_vace_assets') as current_asset_validator:
            current_manager_value=VaceVideoGenerationManager()
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_runtime({'model_profile':'retired-q4'})
            current_asset_validator.assert_not_called()
            current_manager_value.validate_generation_runtime({'model_profile':'official-bf16-resident-v1'})
            current_asset_validator.assert_called_once()

    def test_tool_activity_is_bounded_and_reports_command_exit(self):
        from tools.review.domains.hermes_agent.service import read_hermes_tool_activity
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_path = Path(current_temp_root)
            current_events = [{'type':'tool_use','name':'terminal','tool_call_id':'call1','input':{'command':'echo test'},'timestamp':1794929185434}, {'type':'tool_result','name':'terminal','tool_call_id':'call1','output':json.dumps({'exit_code':2,'output':'private full text'}),'is_error':False}]
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(current_event) for current_event in current_events))
            current_activity_record = read_hermes_tool_activity(current_job_path)
            self.assertEqual(current_activity_record['events'][0]['target'], 'echo test')
            self.assertEqual(current_activity_record['events'][1]['result'], 'error')
            self.assertNotIn('private full text', str(current_activity_record))
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(current_events[0]) for _ in range(12)))
            current_activity_record = read_hermes_tool_activity(current_job_path)
            self.assertEqual(len(current_activity_record['events']), 8)
            self.assertTrue(current_activity_record['truncated'])

    def test_memory_capacity_distinguishes_vram_from_host_gtt(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_memory_capacity
        current_gpu_value = {'status':'idle', 'vram_total_mib':98304, 'vram_free_mib':90000, 'gtt_total_mib':15000, 'gtt_free_mib':14000}
        with patch('tools.review.common.gpu_job_queue.read_host_available_memory', return_value=20000), patch('tools.review.common.gpu_memory_history.estimate_required_memory', return_value={'required_memory_mib':32768}):
            current_capacity_value = read_hermes_memory_capacity(current_gpu_value)
            self.assertEqual(current_capacity_value['domain'], 'vram')
            self.assertTrue(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'], 90000)
            current_gpu_value.update(vram_total_mib=1000, gtt_total_mib=100000, gtt_free_mib=90000)
            current_capacity_value = read_hermes_memory_capacity(current_gpu_value)
            self.assertEqual(current_capacity_value['domain'], 'gtt')
            self.assertFalse(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'], 20000 - current_capacity_value['host_reserve_mib'])
        with patch('tools.review.common.gpu_job_queue.read_host_available_memory', return_value=5000), patch('tools.review.common.gpu_memory_history.estimate_required_memory', return_value={'required_memory_mib':32768}):
            current_gpu_value.update(vram_total_mib=98304, gtt_total_mib=15000)
            self.assertEqual(read_hermes_memory_capacity(current_gpu_value)['pool_available_mib'], 0)
        self.assertEqual(read_hermes_memory_capacity({'status':'unavailable'})['status'], 'unavailable')
        current_gpu_value.update(vram_total_mib=1000,gtt_total_mib=100000,gtt_free_mib=90000)
        from tools.review.common.host_memory_guard import HOST_MEMORY_RESERVE_KIB
        current_host_reserve=HOST_MEMORY_RESERVE_KIB//1024
        with patch('tools.review.common.gpu_job_queue.read_host_available_memory',side_effect=[current_host_reserve+32767,current_host_reserve+32768]),patch('tools.review.common.gpu_memory_history.estimate_required_memory',return_value={'required_memory_mib':32768}):
            self.assertFalse(read_hermes_memory_capacity(current_gpu_value)['capacity_sufficient'])
            current_capacity_value=read_hermes_memory_capacity(current_gpu_value)
            self.assertTrue(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'],32768)
            self.assertIn('다른 예약과 작업 순서는 반영하지 않습니다',current_capacity_value['detail'])

    def test_session_requests_are_idempotent_and_survive_reopen(self):
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore
        hermes_store_path = Path(self.hermes_temporary_root.name) / 'sessions'
        hermes_session_store = HermesSessionStore(hermes_store_path)
        hermes_session_identifier = hermes_session_store.create_session_record()['id']
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_result_values = list(hermes_thread_pool.map(lambda _: HermesSessionStore(hermes_store_path).append_session_request(hermes_session_identifier, 'session-request-1234', '상태를 확인해 줘'), range(4)))
        self.assertEqual(sum(not hermes_result_record['duplicate'] for hermes_result_record in hermes_result_values), 1)
        with self.assertRaisesRegex(ValueError, '다른 메시지'):
            hermes_session_store.append_session_request(hermes_session_identifier, 'session-request-1234', '다른 지시')
        hermes_job_identifier = '2026-11-17_10-00-00-12345678'
        hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', hermes_job_identifier)
        hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', hermes_job_identifier)
        with self.assertRaisesRegex(ValueError, '다른 작업'):
            hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', '2026-11-17_10-00-01-12345678')
        hermes_session_record = HermesSessionStore(hermes_store_path).read_session_record(hermes_session_identifier)
        self.assertEqual(len(hermes_session_record['messages']), 1)
        self.assertEqual(hermes_session_record['messages'][0]['job_id'], hermes_job_identifier)
        with self.assertRaises(ValueError):
            hermes_session_store.read_session_record('../outside')

    def test_session_creation_and_read_are_gateway_compatible_and_idempotent(self):
        hermes_session_identifier = 'a' * 32
        hermes_session_payload = {'session_id': hermes_session_identifier}
        for hermes_command_name in ('hermes-session-create', 'hermes-session-read'):
            hermes_method_value, hermes_route_value = resolve_management_command('hermes-agent', hermes_command_name, hermes_session_payload)
            self.assertEqual(identify_management_command(hermes_route_value, hermes_method_value, hermes_session_payload), ('hermes-agent', hermes_command_name, hermes_session_payload))
        hermes_first_record = self.hermes_service_manager.execute_hermes_command('hermes-session-create', hermes_session_payload)
        self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-session-create', hermes_session_payload), hermes_first_record)
        self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-session-read', hermes_session_payload), hermes_first_record)
        hermes_session_list = self.hermes_service_manager.execute_hermes_command('hermes-session-list', {})
        self.assertEqual(hermes_session_list['sessions'][0]['id'], hermes_session_identifier)
        self.assertEqual(hermes_session_list['sessions'][0]['message_count'], 0)
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-list', {'extra': 1})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': '../outside'})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': None})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': hermes_session_identifier, 'extra': 1})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_session_submit_retries_and_includes_completed_context(self, hermes_launch_mock, hermes_ready_mock):
        hermes_session_identifier = 'b' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': hermes_session_identifier})
        hermes_first_payload = {'session_id': hermes_session_identifier, 'request_id': 'first-request-1234', 'prompt': '첫 질문'}
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_first_results = list(hermes_thread_pool.map(lambda _: self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_first_payload), range(4)))
        self.assertEqual(hermes_launch_mock.call_count, 1)
        self.assertEqual(len({current_result['job_id'] for current_result in hermes_first_results}), 1)
        self.assertEqual(sum(not current_result['duplicate'] for current_result in hermes_first_results), 1)
        hermes_second_payload = {'session_id': hermes_session_identifier, 'request_id': 'second-request-1234', 'prompt': '그 답을 이어서'}
        with self.assertRaisesRegex(ValueError, '종료된 후'):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_second_payload)
        hermes_first_job_path = self.hermes_service_manager.hermes_storage_root / hermes_first_results[0]['job_id']
        (hermes_first_job_path / 'status.json').write_text('{"status":"completed"}')
        (hermes_first_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':'첫 답변'}, ensure_ascii=False))
        hermes_second_result = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_second_payload)
        hermes_second_request = json.loads((self.hermes_service_manager.hermes_storage_root / hermes_second_result['job_id'] / 'request.json').read_text())
        self.assertIn('첫 질문', hermes_second_request['prompt'])
        self.assertIn('첫 답변', hermes_second_request['prompt'])
        hermes_view_record = self.hermes_service_manager.execute_hermes_command('hermes-session-view', {'session_id': hermes_session_identifier})
        self.assertEqual(hermes_view_record['messages'][0]['job']['final_response'], '첫 답변')
        self.assertEqual(hermes_view_record['messages'][1]['job']['status']['status'], 'unknown')
        self.assertEqual(hermes_view_record['message_count'], 2)
        self.assertIn('그 답을 이어서', hermes_second_request['prompt'])
        self.assertEqual(hermes_launch_mock.call_count, 2)
        with self.assertRaisesRegex(ValueError, '다른 메시지'):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {**hermes_first_payload, 'prompt':'다른 질문'})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_session_retry_after_job_accepted_but_link_failed(self, hermes_launch_mock, hermes_ready_mock):
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore
        hermes_session_identifier = 'c' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': hermes_session_identifier})
        hermes_request_record = {'session_id': hermes_session_identifier, 'request_id': 'retry-request-1234', 'prompt': '테스트'}
        with patch.object(HermesSessionStore, 'attach_session_job', side_effect=OSError('저장 중단')):
            with self.assertRaises(OSError):
                self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_request_record)
        hermes_retry_record = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_request_record)
        self.assertTrue(hermes_retry_record['duplicate'])
        hermes_launch_mock.assert_called_once()
        hermes_saved_record = self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': hermes_session_identifier})
        self.assertEqual(hermes_saved_record['messages'][0]['job_id'], hermes_retry_record['job_id'])

    def test_gateway_command_round_trip(self):
        hermes_payload_record = {'request_id':'test-request-1234', 'prompt':'테스트'}
        hermes_method_value, hermes_route_value = resolve_management_command('hermes-agent', 'hermes-submit', hermes_payload_record)
        self.assertEqual(identify_management_command(hermes_route_value, hermes_method_value, hermes_payload_record), ('hermes-agent', 'hermes-submit', hermes_payload_record))

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_detail_includes_agent_response_and_tool_result(self, hermes_launch_mock, hermes_ready_mock):
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'trace-request-1234', 'prompt':'테스트'})
        hermes_job_path = self.hermes_service_manager.hermes_storage_root / hermes_job_result['id']
        hermes_event_values = [{'type':'tool_use','name':'terminal','input':{'command':'python -m unittest'}}, {'type':'tool_result','output':'OK'}, {'type':'result','text':'검사 완료'}]
        (hermes_job_path / 'hermes-events.jsonl').write_text(''.join(json.dumps(hermes_event_record, ensure_ascii=False) + '\n' for hermes_event_record in hermes_event_values))
        hermes_detail_record = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertIn('python -m unittest', hermes_detail_record['log'])
        self.assertIn('검사 완료', hermes_detail_record['log'])
        self.assertEqual(hermes_detail_record['final_response'], '검사 완료')
        self.assertFalse(hermes_detail_record['final_response_truncated'])
        (hermes_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':'가' * 8001}, ensure_ascii=False))
        hermes_detail_record = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertEqual(len(hermes_detail_record['final_response']), 8000)
        self.assertTrue(hermes_detail_record['final_response_truncated'])

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_diff_chunks_preserve_unicode_bytes_and_require_completion(self, hermes_launch_mock, hermes_ready_mock):
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'diff-request-1234', 'prompt':'테스트'})
        hermes_job_path = self.hermes_service_manager.hermes_storage_root / hermes_job_result['id']
        hermes_diff_bytes = '가나다'.encode('utf-8')
        (hermes_job_path / 'change.diff').write_bytes(hermes_diff_bytes)
        hermes_chunk_request = {'id':hermes_job_result['id'], 'offset':0, 'limit':2}
        with self.assertRaisesRegex(ValueError, '종료된 뒤'):
            self.hermes_service_manager.execute_hermes_command('hermes-diff', hermes_chunk_request)
        (hermes_job_path / 'status.json').write_text('{"status":"completed"}')
        hermes_collected_bytes = bytearray()
        while hermes_chunk_request['offset'] is not None:
            hermes_chunk_record = self.hermes_service_manager.execute_hermes_command('hermes-diff', hermes_chunk_request)
            hermes_collected_bytes.extend(base64.b64decode(hermes_chunk_record['data_base64']))
            hermes_chunk_request['offset'] = hermes_chunk_record['next_offset']
        self.assertEqual(bytes(hermes_collected_bytes), hermes_diff_bytes)
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-diff', {'id':hermes_job_result['id'], 'offset':0, 'limit':999999})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_verification_modules_are_allowlisted_and_idempotent(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'verify-request-1234', 'prompt':'테스트', 'verification_modules':['tools.review.tests.test_hermes_service']}
        hermes_first_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)
        self.assertFalse(hermes_first_result['duplicate'])
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)['duplicate'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'verify-request-1234', 'prompt':'테스트'})
        with self.assertRaisesRegex(ValueError, '등록된 검증 모듈'):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'bad-module-1234', 'prompt':'테스트', 'verification_modules':['os.system']})
        hermes_launch_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
