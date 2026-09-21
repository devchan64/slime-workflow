"""RAG 캐시의 재사용·원본 변경·오염 벡터·검색 결합을 검증한다."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from generators.worldbuilding.rag import DocumentVectorIndex,normalize_embedding_vector
from generators.worldbuilding.retrieval import refresh_document_map,retrieve_candidate_sections


class DocumentRagTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory_handle=tempfile.TemporaryDirectory()
        self.current_database_path=Path(self.temporary_directory_handle.name)/'index.sqlite3'
        self.current_vector_index=DocumentVectorIndex(self.current_database_path,'/private/docs')
        self.current_source_entries={}
        self.update_source_document('world/people.md','# 대표\n항구 대표는 주민 투표로 뽑는다.\n')
        self.update_source_document('world/land.md','# 지형\n산에는 나무가 많다.\n')
        self.current_embedding_calls=[]

    def tearDown(self):
        self.current_vector_index.close()
        self.temporary_directory_handle.cleanup()

    def update_source_document(self,current_document_path,current_body_text):
        self.current_source_entries[current_document_path]={'source_document_path':current_document_path,'source_document_body':current_body_text,'source_content_hash':hashlib.sha256(current_body_text.encode()).hexdigest()}

    def request_test_embedding(self,current_source_text):
        self.current_embedding_calls.append(current_source_text)
        return [1.0,0.0]+[0.0]*1022 if '투표' in current_source_text else [0.0,1.0]+[0.0]*1022

    def refresh_test_index(self,current_embedding_function=None):
        current_document_map,_=refresh_document_map(self.current_source_entries)
        self.current_vector_index.refresh_document_vectors(current_document_map,self.current_source_entries,current_embedding_function or self.request_test_embedding,lambda current_source_entry:None,lambda *current_progress_values:None)
        return current_document_map

    def test_reuses_unchanged_document_embeddings(self):
        self.refresh_test_index()
        previous_call_count=len(self.current_embedding_calls)
        self.refresh_test_index()
        self.assertEqual(len(self.current_embedding_calls),previous_call_count)

    def test_invalidates_changed_and_deleted_sources(self):
        self.refresh_test_index()
        self.update_source_document('world/people.md','# 대표\n대표 선거를 중단한다.\n')
        self.current_source_entries.pop('world/land.md')
        current_results=self.current_vector_index.search_document_vectors([1.0]+[0.0]*1023,self.current_source_entries)
        self.assertEqual(current_results,[])
        self.refresh_test_index()
        self.assertEqual(self.current_vector_index.database_connection_handle.execute('SELECT COUNT(*) FROM documents').fetchone()[0],1)

    def test_failed_embedding_never_publishes_partial_document(self):
        self.refresh_test_index()
        self.update_source_document('world/people.md','# 대표\n새로운 대표 규칙이다.\n')
        def reject_embedding_request(current_source_text):
            raise RuntimeError('GPU 오류')
        with self.assertRaises(RuntimeError):
            self.refresh_test_index(reject_embedding_request)
        current_results=self.current_vector_index.search_document_vectors([1.0]+[0.0]*1023,self.current_source_entries)
        self.assertFalse(any(current_result_entry['source_reference_id'].startswith('world/people.md:') for current_result_entry in current_results))

    def test_rejects_invalid_or_zero_vector(self):
        for current_vector_values in [[0.0]*1024,[float('nan')]+[0.0]*1023,[1.0],[True]+[0.0]*1023]:
            with self.assertRaises(ValueError):
                normalize_embedding_vector(current_vector_values)

    def test_refuses_index_from_another_source_root(self):
        with self.assertRaises(ValueError):
            DocumentVectorIndex(self.current_database_path,'/another/docs')

    def test_semantic_candidates_reach_agent_without_keyword_overlap(self):
        current_document_map=self.refresh_test_index()
        current_results=retrieve_candidate_sections(current_document_map,'선거',[],['world'],lambda current_query_text:self.current_vector_index.search_document_vectors([1.0]+[0.0]*1023,self.current_source_entries))
        self.assertTrue(current_results[0]['source_reference_id'].startswith('world/people.md:'))
        self.assertEqual(current_results[0]['semantic_similarity_score'],1.0)
