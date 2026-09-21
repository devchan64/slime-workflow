"""최신 원문만 검색하는 로컬 임베딩 색인. SQLite는 재생성 가능한 산출물이다."""
import hashlib
import math
import sqlite3
import struct

EMBEDDING_VECTOR_DIMENSIONS = 1024
RAG_INDEX_VERSION = 'qwen3-embedding-q8-v1'
EMBEDDING_MODEL_DIGEST = '06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439'
SEMANTIC_RESULT_LIMIT = 20


def normalize_embedding_vector(current_vector_values):
    if not isinstance(current_vector_values,list) or len(current_vector_values)!=EMBEDDING_VECTOR_DIMENSIONS or any(type(current_vector_value) not in {int,float} or not math.isfinite(current_vector_value) for current_vector_value in current_vector_values):
        raise ValueError('임베딩 차원·자료형·유한값 계약 위반')
    current_vector_length=math.sqrt(sum(current_vector_value**2 for current_vector_value in current_vector_values))
    if current_vector_length<=0 or not math.isfinite(current_vector_length):
        raise ValueError('임베딩 벡터의 크기가 올바르지 않습니다.')
    return [current_vector_value/current_vector_length for current_vector_value in current_vector_values]


class DocumentVectorIndex:
    """문서별 원자적 갱신과 해시 검증으로 오래된 검색 근거를 차단한다."""
    def __init__(self,current_database_path,source_document_root):
        self.database_connection_handle=sqlite3.connect(current_database_path)
        self.database_connection_handle.execute('PRAGMA foreign_keys=ON')
        self.database_connection_handle.executescript('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS documents (path TEXT PRIMARY KEY,hash TEXT NOT NULL); CREATE TABLE IF NOT EXISTS chunks (reference TEXT PRIMARY KEY,path TEXT NOT NULL REFERENCES documents(path) ON DELETE CASCADE,excerpt_hash TEXT NOT NULL,vector BLOB NOT NULL);')
        expected_metadata_values={'version':RAG_INDEX_VERSION,'model':EMBEDDING_MODEL_DIGEST,'root':str(source_document_root),'dimensions':str(EMBEDDING_VECTOR_DIMENSIONS)}
        actual_metadata_values=dict(self.database_connection_handle.execute('SELECT key,value FROM metadata'))
        if actual_metadata_values and actual_metadata_values!=expected_metadata_values:
            self.database_connection_handle.close()
            raise ValueError('RAG 색인의 모델·버전·문서 루트가 다릅니다.')
        if not actual_metadata_values:
            with self.database_connection_handle:
                self.database_connection_handle.executemany('INSERT INTO metadata VALUES (?,?)',expected_metadata_values.items())

    def close(self):
        self.database_connection_handle.close()

    def refresh_document_vectors(self,current_document_map,source_document_entries,embedding_request_function,source_validate_function,progress_report_function):
        current_document_records=current_document_map['document_records']
        existing_document_hashes=dict(self.database_connection_handle.execute('SELECT path,hash FROM documents'))
        with self.database_connection_handle:
            for removed_document_path in set(existing_document_hashes)-set(source_document_entries):
                self.database_connection_handle.execute('DELETE FROM documents WHERE path=?',(removed_document_path,))
        total_document_count=len(source_document_entries)
        for current_document_number,(current_document_path,current_source_entry) in enumerate(source_document_entries.items(),1):
            current_section_entries=current_document_records[current_document_path]['document_section_entries']
            if not current_section_entries:
                raise ValueError(f'색인할 원문이 없는 문서: {current_document_path}')
            if existing_document_hashes.get(current_document_path)==current_source_entry['source_content_hash']:
                existing_reference_values={current_row_value[0] for current_row_value in self.database_connection_handle.execute('SELECT reference FROM chunks WHERE path=?',(current_document_path,))}
                if existing_reference_values!={current_section_entry['source_reference_id'] for current_section_entry in current_section_entries}:
                    raise ValueError('RAG 청크 계약이 변경되었습니다. 색인 버전을 갱신하세요.')
                progress_report_function(current_document_number,total_document_count,current_document_path,True)
                continue
            current_source_lines=current_source_entry['source_document_body'].splitlines(keepends=True)
            next_chunk_rows=[]
            for current_section_entry in current_section_entries:
                source_validate_function(current_source_entry)
                current_excerpt_text=''.join(current_source_lines[current_section_entry['source_start_line']-1:current_section_entry['source_end_line']])
                embedding_input_text=current_document_records[current_document_path]['document_title_text']+'\n'+current_excerpt_text
                current_vector_values=normalize_embedding_vector(embedding_request_function(embedding_input_text))
                next_chunk_rows.append((current_section_entry['source_reference_id'],current_document_path,hashlib.sha256(current_excerpt_text.encode()).hexdigest(),struct.pack('<'+'f'*EMBEDDING_VECTOR_DIMENSIONS,*current_vector_values)))
            source_validate_function(current_source_entry)
            with self.database_connection_handle:
                self.database_connection_handle.execute('DELETE FROM documents WHERE path=?',(current_document_path,))
                self.database_connection_handle.execute('INSERT INTO documents VALUES (?,?)',(current_document_path,current_source_entry['source_content_hash']))
                self.database_connection_handle.executemany('INSERT INTO chunks VALUES (?,?,?,?)',next_chunk_rows)
            progress_report_function(current_document_number,total_document_count,current_document_path,False)

    def search_document_vectors(self,current_query_vector,source_document_entries):
        normalized_query_vector=normalize_embedding_vector(current_query_vector)
        current_result_entries=[]
        for current_reference_id,current_document_path,current_document_hash,current_vector_blob in self.database_connection_handle.execute('SELECT chunks.reference,chunks.path,documents.hash,chunks.vector FROM chunks JOIN documents ON chunks.path=documents.path'):
            if current_document_path not in source_document_entries or source_document_entries[current_document_path]['source_content_hash']!=current_document_hash:
                continue
            if len(current_vector_blob)!=EMBEDDING_VECTOR_DIMENSIONS*4:
                raise ValueError('저장된 임베딩 차원이 올바르지 않습니다.')
            current_stored_vector=normalize_embedding_vector(list(struct.unpack('<'+'f'*EMBEDDING_VECTOR_DIMENSIONS,current_vector_blob)))
            current_similarity_score=sum(current_query_value*current_stored_value for current_query_value,current_stored_value in zip(normalized_query_vector,current_stored_vector))
            current_result_entries.append({'source_reference_id':current_reference_id,'similarity_score':current_similarity_score})
        return sorted(current_result_entries,key=lambda current_result_entry:(-current_result_entry['similarity_score'],current_result_entry['source_reference_id']))[:SEMANTIC_RESULT_LIMIT]
