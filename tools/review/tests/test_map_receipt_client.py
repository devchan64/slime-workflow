"""맵 DB 접수는 저장 요청을 보내지 않고 원래 입력으로 확인한다."""
import hashlib
import json
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
from tools.review.domains.map_assets.database_client import read_content_map_change_receipt


class MapReceiptClientTests(unittest.TestCase):
    def test_content_api_error_is_bounded_and_closed(current_test_case):
        from io import BytesIO
        from urllib.error import HTTPError
        from tools.review.domains.map_assets.database_client import execute_content_api_request
        for current_error_bytes,current_expected_marker in ((b'not found','not found'),(b'x'*5000,'오류 응답 일부만 표시')):
            current_error_stream=BytesIO(current_error_bytes)
            current_http_error=HTTPError('http://127.0.0.1',404,'missing',{},current_error_stream)
            with current_test_case.subTest(size=len(current_error_bytes)), patch.dict('os.environ',{'SLIME_CONTENT_SERVICE_ORIGIN':'http://127.0.0.1'},clear=True), patch('tools.review.domains.map_assets.database_client.build_opener') as current_opener_mock:
                current_opener_mock.return_value.open.side_effect=current_http_error
                with current_test_case.assertRaisesRegex(ValueError,current_expected_marker):
                    execute_content_api_request('GET','/internal/v1/content/map-change-receipt')
                current_test_case.assertTrue(current_error_stream.closed)

    def test_original_request_hash_and_read_only_transport(current_test_case):
        current_payload_value={'requestId':'test id&한글','expectedGeneration':3,'documents':[{'path':'test.yaml','revision':1,'document':{'data':'한글'}}]}
        current_expected_hash=hashlib.sha256(json.dumps(current_payload_value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        with patch('tools.review.domains.map_assets.database_client.execute_content_api_request',return_value={'state':'matched'}) as current_request_mock:
            current_result_record=read_content_map_change_receipt(current_payload_value)
        current_test_case.assertEqual(current_result_record['state'],'matched')
        current_test_case.assertEqual(current_result_record['request_sha256'],current_expected_hash)
        current_call_arguments=current_request_mock.call_args.args
        current_test_case.assertEqual(current_call_arguments[0],'GET')
        current_test_case.assertEqual(urlsplit(current_call_arguments[1]).path,'/internal/v1/content/map-change-receipt')
        current_test_case.assertEqual(parse_qs(urlsplit(current_call_arguments[1]).query),{'requestId':['test id&한글'],'requestSha256':[current_expected_hash]})
        current_test_case.assertEqual(len(current_call_arguments),2)

    def test_hermes_command_reads_receipt_and_validates_inputs(current_test_case):
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.common.management_gateway import resolve_management_command
        current_payload_value={'database_request_id':'request id','request_sha256':'a'*64}
        current_test_case.assertEqual(resolve_management_command('hermes-agent','hermes-map-database-receipt',current_payload_value)[1],'/hermes-agent/hermes-map-database-receipt')
        with patch('tools.review.domains.map_assets.database_client.execute_content_api_request',return_value={'state':'not_found'}) as current_request_mock:
            current_result_value=HermesServiceManager().execute_hermes_command('hermes-map-database-receipt',current_payload_value)
            current_test_case.assertEqual(current_result_value['state'],'not_found')
            current_test_case.assertIn('보장하지 않습니다',current_result_value['note'])
            current_test_case.assertEqual(current_request_mock.call_args.args[0],'GET')
        for current_invalid_payload in ({}, {**current_payload_value,'request_sha256':'INVALID'}, {**current_payload_value,'unexpected':True}):
            with current_test_case.assertRaises(ValueError):
                HermesServiceManager().execute_hermes_command('hermes-map-database-receipt',current_invalid_payload)

    def test_receipt_discovery_documents_inputs_and_limits(current_test_case):
        from tools.review.domains.hermes_agent.capabilities import list_hermes_capability_catalog,search_management_service_registration
        current_capability_record=next(current_record for current_record in list_hermes_capability_catalog()['records'] if current_record['command']=='hermes-map-database-receipt')
        current_test_case.assertEqual(set(current_capability_record['required']),{'database_request_id','request_sha256'})
        current_test_case.assertEqual(set(current_capability_record['interfaces']),{'gui','mcp','isolated_fixed_bridge'})
        current_test_case.assertEqual(current_capability_record['effect'],'read')
        current_test_case.assertIn('재접수 안전',current_capability_record['note'])
        current_service_records=search_management_service_registration({'query':'맵 DB 변경 접수','limit':10})['services']
        current_test_case.assertIn('map-assets',[current_record['service'] for current_record in current_service_records])

    def test_bad_input_or_response_fails_closed(current_test_case):
        current_payload_value={'requestId':'id','expectedGeneration':1,'documents':[{}]}
        for current_response_record in ({}, {'state':'unknown'}, {'state':'matched','extra':True}, {'state':None}):
            with current_test_case.subTest(response=current_response_record), patch('tools.review.domains.map_assets.database_client.execute_content_api_request',return_value=current_response_record):
                with current_test_case.assertRaises(ValueError):read_content_map_change_receipt(current_payload_value)
        for current_invalid_payload in ({}, {**current_payload_value,'expectedGeneration':True}, {**current_payload_value,'documents':[]}, {**current_payload_value,'documents':[float('nan')]}):
            with current_test_case.subTest(payload=current_invalid_payload), patch('tools.review.domains.map_assets.database_client.execute_content_api_request') as current_request_mock:
                with current_test_case.assertRaises(ValueError):read_content_map_change_receipt(current_invalid_payload)
                current_request_mock.assert_not_called()
        for current_state_name in ('not_found','mismatch'):
            with patch('tools.review.domains.map_assets.database_client.execute_content_api_request',return_value={'state':current_state_name}):
                current_test_case.assertEqual(read_content_map_change_receipt(current_payload_value)['state'],current_state_name)


if __name__=='__main__':unittest.main()
