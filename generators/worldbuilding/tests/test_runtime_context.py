"""입력 예산 절약이 출처·원문·승인 정보와 검증 메타데이터를 보존하는지 확인한다."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime import build_generation_messages, build_generation_schema


class GenerationContextTests(unittest.TestCase):
    def test_preserves_source_and_request_without_internal_metadata(self):
        current_source_entries=[{'source_reference_id':'world/town.md:1-3','source_document_path':'world/town.md','source_excerpt_text':'# 작은 도시\n상태: 신규 제안\n상인은 “별빛”을 판다.\n','source_approval_state':'mixed_or_unresolved','source_content_hash':'a'*64,'source_search_score':42,'source_required_flag':True}]
        original_source_entries=copy.deepcopy(current_source_entries)
        current_request_values={'requested_instruction_text':'시장 정보를 추가한다','requested_operation_mode':'append','requested_target_path':'world/town.md'}
        current_message_entries=build_generation_messages({'allowed_write_roots':['world']},current_request_values,current_source_entries)
        current_payload_values=json.loads(current_message_entries[1]['content'])
        self.assertEqual(current_payload_values['task_instruction_data'],current_request_values)
        self.assertEqual(current_payload_values['allowed_output_roots'],['world'])
        current_prompt_source=current_payload_values['inherited_source_entries'][0]
        self.assertEqual(set(current_prompt_source),{'source_reference_id','source_document_path','source_excerpt_text','source_approval_state'})
        for current_field_name in current_prompt_source:
            self.assertEqual(current_prompt_source[current_field_name],original_source_entries[0][current_field_name])
        self.assertEqual(current_source_entries,original_source_entries)

    def test_uses_standard_json_string_grammar_for_markdown(self):
        current_request_values={'requested_operation_mode':'append','requested_target_path':'world/town.md'}
        current_schema_values=build_generation_schema(current_request_values,[{'source_reference_id':'world/town.md:1-3'}])
        current_fragment_schema=current_schema_values['properties']['document_change_entries']['items']['properties']['replacement_fragment_text']
        self.assertEqual(current_fragment_schema,{'type':'string','minLength':1})


if __name__=='__main__':
    unittest.main()
