"""경로를 모르는 요청의 문서 탐색·색인 갱신·읽기 경계를 검증한다."""
import copy
import hashlib
import unittest
from generators.worldbuilding.retrieval import (refresh_document_map,search_document_map,read_document_sections,discover_document_context,validate_discovery_decision,build_discovery_schema)


class DocumentDiscoveryTests(unittest.TestCase):
    def setUp(self):
        current_source_texts={'world/guide.md':'# 도시 안내\n[항구의 수장](people.md)을 확인한다.\n','world/people.md':'# 자치회 인물\n## 해풍 대표\n별칭: 바람지기\n**은빛** 항구는 자치회가 운영한다. 대표는 라온이다.\n','world/rules.md':'# 지역 규칙\n대표는 주민 투표로 선출한다.\n'}
        self.source_document_entries={current_source_path:{'source_document_path':current_source_path,'source_document_body':current_source_text,'source_content_hash':hashlib.sha256(current_source_text.encode()).hexdigest()} for current_source_path,current_source_text in current_source_texts.items()}
        self.current_document_map,self.current_index_changes=refresh_document_map(self.source_document_entries)
        self.current_config_values={'source_document_root':'/private/docs','allowed_write_roots':['world'],'required_source_paths':['world/guide.md'],'protected_document_paths':['world/rules.md']}
        self.current_request_values={'requested_instruction_text':'바람지기의 성격을 추가해줘','requested_operation_mode':'append','requested_target_path':''}

    def test_yaml_can_be_read_but_cannot_be_a_write_target(self):
        from jsonschema import Draft202012Validator
        from generators.worldbuilding.documents import REQUEST_INPUT_SCHEMA
        current_yaml_reference={'source_reference_id':'world/profiles.yaml:1-3','source_document_path':'world/profiles.yaml'}
        current_markdown_reference={'source_reference_id':'world/people.md:1-4','source_document_path':'world/people.md'}
        current_read_lookup={current_markdown_reference['source_reference_id']:current_markdown_reference}
        current_schema_values=build_discovery_schema(self.current_request_values,[current_yaml_reference],current_read_lookup,self.current_config_values)
        current_read_schema=next(current_variant_entry for current_variant_entry in current_schema_values['anyOf'] if current_variant_entry['properties']['action_name']['const']=='read')
        self.assertIn(current_yaml_reference['source_reference_id'],current_read_schema['properties']['source_reference_ids']['items']['enum'])
        current_read_lookup[current_yaml_reference['source_reference_id']]=current_yaml_reference
        current_schema_values=build_discovery_schema(self.current_request_values,[],current_read_lookup,self.current_config_values)
        current_finish_schema=next(current_variant_entry for current_variant_entry in current_schema_values['anyOf'] if current_variant_entry['properties']['action_name']['const']=='finish')
        self.assertEqual(current_finish_schema['properties']['resolved_target_path']['enum'],['world/people.md'])
        self.assertEqual(current_finish_schema['properties']['source_reference_ids']['const'],list(current_read_lookup))
        self.assertFalse(Draft202012Validator(REQUEST_INPUT_SCHEMA).is_valid(dict(self.current_request_values,requested_target_path='world/profiles.yaml')))
        self.assertTrue(Draft202012Validator(REQUEST_INPUT_SCHEMA).is_valid(self.current_request_values))

    def test_finds_alias_and_incoming_link_label(self):
        for current_query_text in ['바람지기','항구의 수장']:
            self.assertEqual(search_document_map(self.current_document_map,current_query_text)[0]['source_document_path'],'world/people.md')

    def test_refreshes_renamed_deleted_and_changed_documents(self):
        previous_document_map=copy.deepcopy(self.current_document_map)
        self.source_document_entries['world/renamed.md']=self.source_document_entries.pop('world/people.md')
        self.source_document_entries['world/renamed.md']['source_document_path']='world/renamed.md'
        self.source_document_entries['world/rules.md'].update(source_document_body='# 변경된 규칙\n',source_content_hash='updated-hash')
        next_document_map,current_index_changes=refresh_document_map(self.source_document_entries,previous_document_map)
        self.assertIn('world/people.md',current_index_changes['removed_document_paths'])
        self.assertEqual(set(current_index_changes['changed_document_paths']),{'world/renamed.md','world/rules.md'})
        self.assertEqual(next_document_map['document_records']['world/rules.md']['document_title_text'],'변경된 규칙')
        self.assertIs(next_document_map['document_records']['world/guide.md'],previous_document_map['document_records']['world/guide.md'])

    def test_reads_exact_lines_and_rejects_stale_hash(self):
        current_reference_id=search_document_map(self.current_document_map,'바람지기')[0]['source_reference_id']
        current_read_entry=read_document_sections(self.current_document_map,self.source_document_entries,[current_reference_id])[0]
        self.assertIn('라온',current_read_entry['source_excerpt_text'])
        self.source_document_entries['world/people.md']['source_content_hash']='changed'
        with self.assertRaises(ValueError):
            read_document_sections(self.current_document_map,self.source_document_entries,[current_reference_id])

    def test_agent_searches_reads_and_resolves_unknown_target(self):
        recorded_decision_entries=[]
        def request_decision_function(current_payload_values,current_schema_values):
            self.assertEqual(current_payload_values['primary_document_roots'],['/private/docs/world'])
            if current_payload_values['round_number']==1:
                return {'action_name':'search','search_query_text':'자치회 대표','source_reference_ids':[],'resolved_target_path':'','decision_reason_text':'직책을 기준으로 찾는다.'}
            if current_payload_values['round_number']==2:
                current_candidate_entry=next(current_candidate_entry for current_candidate_entry in current_payload_values['search_results'] if current_candidate_entry['section_heading_text']=='해풍 대표')
                return {'action_name':'read','search_query_text':'','source_reference_ids':[current_candidate_entry['source_reference_id']],'resolved_target_path':'','decision_reason_text':'별칭과 실제 인물을 읽는다.'}
            return {'action_name':'finish','search_query_text':'','source_reference_ids':[current_payload_values['read_source_entries'][0]['source_reference_id']],'resolved_target_path':'world/people.md','decision_reason_text':'별칭에 해당하는 인물의 소유 문서를 확인했다.'}
        selected_source_entries,resolved_request_values=discover_document_context(self.current_config_values,self.current_request_values,self.current_document_map,self.source_document_entries,request_decision_function,lambda *current_record_values:recorded_decision_entries.append(current_record_values))
        self.assertEqual(resolved_request_values['requested_target_path'],'world/people.md')
        self.assertEqual(self.current_request_values['requested_target_path'],'')
        self.assertIn('라온',selected_source_entries[0]['source_excerpt_text'])
        self.assertEqual(len(recorded_decision_entries),3)

    def test_rejects_unread_finish_and_invented_read(self):
        for current_action_name in ['finish','read']:
            with self.assertRaises(ValueError):
                validate_discovery_decision({'action_name':current_action_name,'search_query_text':'','source_reference_ids':['world/unknown.md:1-3'],'resolved_target_path':'','decision_reason_text':'없는 원문'},set(),set())

    def test_agent_cannot_change_explicit_target(self):
        self.current_request_values['requested_target_path']='world/guide.md'
        def request_decision_function(current_payload_values,current_schema_values):
            if current_payload_values['round_number']==1:
                return {'action_name':'read','search_query_text':'','source_reference_ids':[next(current_candidate_entry['source_reference_id'] for current_candidate_entry in current_payload_values['search_results'] if current_candidate_entry['source_document_path']=='world/people.md')],'resolved_target_path':'','decision_reason_text':'인물을 읽는다.'}
            return {'action_name':'finish','search_query_text':'','source_reference_ids':[current_payload_values['read_source_entries'][0]['source_reference_id']],'resolved_target_path':'world/people.md','decision_reason_text':'대상을 바꾼다.'}
        with self.assertRaises(Exception):
            discover_document_context(self.current_config_values,self.current_request_values,self.current_document_map,self.source_document_entries,request_decision_function,lambda *current_record_values:None)

    def test_search_loop_stops_without_writing(self):
        def request_decision_function(current_payload_values,current_schema_values):
            return {'action_name':'search','search_query_text':'없는자료','source_reference_ids':[],'resolved_target_path':'','decision_reason_text':'근거가 없다.'}
        with self.assertRaises(Exception):
            discover_document_context(self.current_config_values,self.current_request_values,self.current_document_map,self.source_document_entries,request_decision_function,lambda *current_record_values:None)
