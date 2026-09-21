"""AI 편집의 엄격한 배치 계약과 실제 원문 보존 산출물 흐름을 검증한다."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import runtime
import worldbuilding
from generators.worldbuilding.book_automation import execute_automated_book,validate_automated_placements
from generators.worldbuilding.documents import save_yaml_document,load_yaml_document


class AutomatedBookTests(unittest.TestCase):
    def test_rejects_missing_duplicate_and_invented_index(self):
        current_paragraph_entries=[{'paragraph_id':'first','paragraph_text':'도시 항구','source_document_path':'world/town.md'}]
        current_placement_entry={'paragraph_id':'first','index_terms':['항구'],'target_document_path':'world/town.md'}
        validate_automated_placements(current_paragraph_entries,[current_placement_entry])
        for current_placements in [[],[current_placement_entry,current_placement_entry],[dict(current_placement_entry,index_terms=['없는용어'])]]:
            with self.assertRaises(ValueError):
                validate_automated_placements(current_paragraph_entries,current_placements)

    def test_generates_book_from_strict_model_placements_without_source_writes(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_source_root=Path(current_temp_name)/'docs'
            (current_source_root/'world').mkdir(parents=True)
            current_source_path=current_source_root/'world/town.md'
            current_source_text='# 항구\n\n항구 주민은 바다를 살핀다.\n'
            current_source_path.write_text(current_source_text)
            current_run_root=Path(current_temp_name)/'state/jobs/20260921-235000-12345678'
            current_run_root.mkdir(parents=True)
            current_config_values={'source_document_root':str(current_source_root),'private_state_root':str(current_run_root.parents[1]),'allowed_write_roots':['world'],'protected_document_paths':[],'managed_catalog_path':'CATALOG.md'}
            save_yaml_document(current_run_root/'request.yaml',{'collection_id':'world','source_directory_paths':['world'],'book_title_text':'세계관','requested_instruction_text':'원문을 보존하며 도서로 정리한다.','task_kind_name':'book-edit'})
            save_yaml_document(current_run_root/'status.yaml',{'current_stage_name':'queued'})
            def request_model_response(current_endpoint_path,current_request_body):
                if current_endpoint_path=='/apply-template':
                    return {'prompt':'synthetic prompt'}
                if current_endpoint_path=='/tokenize':
                    return {'tokens':[1,2,3]}
                current_payload_values=json.loads(current_request_body['messages'][1]['content'])
                if 'paragraphs' not in current_payload_values:
                    current_result_values={'chapter_titles':['도시와 주민']}
                else:
                    current_result_values={'paragraph_placements':[{'paragraph_id':current_paragraph_entry['paragraph_id'],'chapter_title':'도시와 주민','order_number':current_paragraph_number,'target_document_path':'world/town.md','new_document_title':'','index_terms':['항구']} for current_paragraph_number,current_paragraph_entry in enumerate(current_payload_values['paragraphs'])]}
                return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(current_result_values,ensure_ascii=False)}}]}
            with patch.object(worldbuilding,'lock_gpu_runtime',contextlib.nullcontext),patch.object(runtime,'start_managed_server',lambda *current_arguments:contextlib.nullcontext()),patch.object(runtime,'request_local_model',request_model_response):
                execute_automated_book(current_config_values,current_run_root)
            current_result_values=load_yaml_document(current_run_root/'book-result.yaml')
            self.assertEqual(current_source_path.read_text(),current_source_text)
            self.assertEqual(current_result_values['preview_values']['document_change_entries'],[])
            self.assertEqual(load_yaml_document(current_run_root/'status.yaml')['current_stage_name'],'completed')
            current_book_path=current_run_root.parents[1]/'books'/current_result_values['book_values']['book_id']/'book.html'
            self.assertIn('도시와 주민',current_book_path.read_text())
            self.assertIn('항구 · 2',current_book_path.read_text())


if __name__=='__main__':
    unittest.main()
