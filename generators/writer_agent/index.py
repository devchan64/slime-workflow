"""문단 벡터·원문 해시·참조 그래프를 원자적으로 학습하고 혼합 검색한다."""
from collections import Counter
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import json
import math
import re
import sqlite3
import struct
import uuid
from .documents import chunk_document_blocks,snapshot_document_hashes,scan_workspace_documents

EMBEDDING_VECTOR_DIMENSIONS=1024
INDEX_SCHEMA_VERSION='writer-rag-v1-qwen3-embedding-q8'
SEARCH_RESULT_LIMIT=12
DUPLICATE_PAIR_LIMIT=12
DUPLICATE_SIMILARITY_THRESHOLD=0.93

def normalize_embedding_vector(current_vector_values):
    if not isinstance(current_vector_values,list) or len(current_vector_values)!=EMBEDDING_VECTOR_DIMENSIONS or any(type(current_vector_value) not in {int,float} or not math.isfinite(current_vector_value) for current_vector_value in current_vector_values):raise ValueError('임베딩 차원·수치 계약 오류')
    current_vector_length=math.sqrt(sum(current_vector_value**2 for current_vector_value in current_vector_values))
    if not math.isfinite(current_vector_length) or current_vector_length<=0:raise ValueError('0 또는 비유한 임베딩 벡터')
    return [current_vector_value/current_vector_length for current_vector_value in current_vector_values]

def tokenize_search_terms(current_query_text):
    return set(re.findall(r'[가-힣a-z0-9]{2,}',current_query_text.lower()))

def learn_document_index(current_config_values,current_embedding_function,current_progress_function):
    current_document_entries=scan_workspace_documents(current_config_values)
    current_snapshot_hashes=snapshot_document_hashes(current_document_entries)
    current_index_path=Path(current_config_values['state_root'])/'rag.sqlite3'
    current_vector_cache={}
    if current_index_path.exists():
        with closing(sqlite3.connect(f'file:{current_index_path}?mode=ro',uri=True)) as current_previous_database:
            current_metadata_values=dict(current_previous_database.execute('SELECT key,value FROM metadata'))
            if current_metadata_values.get('version')!=INDEX_SCHEMA_VERSION:raise ValueError('기존 색인의 모델·스키마 버전 불일치')
            current_vector_cache=dict(current_previous_database.execute('SELECT text_hash,vector FROM chunks'))
    current_temporary_path=current_index_path.with_name('learning-'+uuid.uuid4().hex+'.sqlite3')
    current_chunk_count=0
    current_cached_count=0
    try:
        with closing(sqlite3.connect(current_temporary_path)) as current_database_handle:
            current_database_handle.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE documents(path TEXT PRIMARY KEY,hash TEXT NOT NULL,record TEXT NOT NULL);CREATE TABLE chunks(id TEXT PRIMARY KEY,path TEXT NOT NULL,text_hash TEXT NOT NULL,record TEXT NOT NULL,vector BLOB NOT NULL);CREATE INDEX chunk_document_path ON chunks(path);')
            current_database_handle.executemany('INSERT INTO metadata VALUES (?,?)',[('version',INDEX_SCHEMA_VERSION),('root',current_config_values['document_root'])])
            for current_document_number,(current_document_path,current_document_entry) in enumerate(current_document_entries.items(),1):
                current_database_handle.execute('INSERT INTO documents VALUES (?,?,?)',(current_document_path,current_document_entry['hash'],json.dumps({current_field_key:current_field_value for current_field_key,current_field_value in current_document_entry.items() if current_field_key!='text'},ensure_ascii=False)))
                for current_chunk_entry in chunk_document_blocks(current_document_entry):
                    current_embedding_text=current_document_entry['title']+'\n'+current_chunk_entry['heading']+'\n'+current_chunk_entry['text']
                    current_embedding_hash=sha256(current_embedding_text.encode()).hexdigest()
                    if current_embedding_hash in current_vector_cache:
                        current_vector_blob=current_vector_cache[current_embedding_hash]
                        if len(current_vector_blob)!=EMBEDDING_VECTOR_DIMENSIONS*4:raise ValueError('저장된 임베딩 차원 오류')
                        current_cached_count+=1
                    else:
                        current_vector_values=normalize_embedding_vector(current_embedding_function(current_embedding_text))
                        current_vector_blob=struct.pack('<'+'f'*EMBEDDING_VECTOR_DIMENSIONS,*current_vector_values)
                        current_vector_cache[current_embedding_hash]=current_vector_blob
                    current_database_handle.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',(current_chunk_entry['id'],current_document_path,current_embedding_hash,json.dumps(current_chunk_entry,ensure_ascii=False),current_vector_blob))
                    current_chunk_count+=1
                    current_progress_function({'document':current_document_path,'documents_done':current_document_number,'documents_total':len(current_document_entries),'chunks':current_chunk_count,'reused_chunks':current_cached_count})
            if snapshot_document_hashes(scan_workspace_documents(current_config_values))!=current_snapshot_hashes:raise ValueError('학습 중 원문이 변경되었습니다. 다시 학습하세요.')
            current_database_handle.commit()
        current_temporary_path.replace(current_index_path)
    finally:current_temporary_path.unlink(missing_ok=True)
    return {'documents':len(current_document_entries),'chunks':current_chunk_count,'reused_chunks':current_cached_count,'index_path':str(current_index_path),'snapshot_hashes':current_snapshot_hashes}

def load_current_index(current_config_values):
    current_index_path=Path(current_config_values['state_root'])/'rag.sqlite3'
    if not current_index_path.is_file():raise ValueError('먼저 학습 명령으로 문서 RAG를 구성하세요.')
    with closing(sqlite3.connect(f'file:{current_index_path}?mode=ro',uri=True)) as current_database_handle:
        current_metadata_values=dict(current_database_handle.execute('SELECT key,value FROM metadata'))
        if current_metadata_values!={'version':INDEX_SCHEMA_VERSION,'root':current_config_values['document_root']}:raise ValueError('색인 버전·문서 루트 오류. 올바른 색인으로 학습하세요.')
        current_snapshot_hashes=dict(current_database_handle.execute('SELECT path,hash FROM documents'))
        current_document_entries=scan_workspace_documents(current_config_values)
        if snapshot_document_hashes(current_document_entries)!=current_snapshot_hashes:raise ValueError('문서 추가·수정·삭제 이후 색인이 오래되었습니다. 학습 갱신이 필요합니다.')
        current_chunk_entries=[]
        for current_chunk_json,current_vector_blob in current_database_handle.execute('SELECT record,vector FROM chunks ORDER BY path,id'):
            current_chunk_entry=json.loads(current_chunk_json)
            current_chunk_entry['vector']=normalize_embedding_vector(list(struct.unpack('<'+'f'*EMBEDDING_VECTOR_DIMENSIONS,current_vector_blob)))
            current_chunk_entries.append(current_chunk_entry)
    return current_document_entries,current_chunk_entries

def rank_document_chunks(current_chunk_entries,current_query_text,current_query_vector,current_result_limit=SEARCH_RESULT_LIMIT):
    current_normalized_query=normalize_embedding_vector(current_query_vector)
    current_query_terms=tokenize_search_terms(current_query_text)
    current_ranked_entries=[]
    for current_chunk_entry in current_chunk_entries:
        current_similarity_score=sum(current_query_value*current_chunk_value for current_query_value,current_chunk_value in zip(current_normalized_query,current_chunk_entry['vector']))
        current_chunk_terms=tokenize_search_terms(current_chunk_entry['path']+' '+current_chunk_entry['heading']+' '+current_chunk_entry['text'])
        current_lexical_score=len(current_query_terms&current_chunk_terms)/max(1,len(current_query_terms))
        current_ranked_entries.append({**current_chunk_entry,'score':round(current_similarity_score*.8+current_lexical_score*.2,6)})
    current_ranked_entries.sort(key=lambda current_entry:(-current_entry['score'],current_entry['path'],current_entry['start']))
    return current_ranked_entries[:current_result_limit]

def calculate_dependency_score(current_chunk_entry,current_document_entry):
    current_ownership_bonus=50 if not current_document_entry['writable'] or re.search('SSOT|원본|확정',current_document_entry['title']) else 0
    current_document_terms=tokenize_search_terms(current_document_entry['title']+' '+current_chunk_entry['heading'])
    current_relevance_score=len(current_document_terms&tokenize_search_terms(current_chunk_entry['text']))
    return current_ownership_bonus+current_document_entry['incoming']*3+min(10,current_relevance_score)

def find_duplicate_candidates(current_document_entries,current_chunk_entries,current_scope_entries=None):
    """유사도는 후보 탐색, 참조·소유 점수는 삭제 방향 제약에만 쓴다."""
    current_scope_ids={current_chunk_entry['id'] for current_chunk_entry in current_scope_entries} if current_scope_entries is not None else None
    current_candidate_entries=[]
    current_eligible_entries=[current_chunk_entry for current_chunk_entry in current_chunk_entries if current_chunk_entry['path'].endswith('.md') and 100<=len(current_chunk_entry['text'].strip())<=2400]
    current_term_lookup={current_chunk_entry['id']:tokenize_search_terms(current_chunk_entry['text']) for current_chunk_entry in current_eligible_entries}
    current_compared_pairs=0
    for current_left_number,current_left_entry in enumerate(current_eligible_entries):
        for current_right_entry in current_eligible_entries[current_left_number+1:]:
            if current_scope_ids is not None and current_left_entry['id'] not in current_scope_ids and current_right_entry['id'] not in current_scope_ids:continue
            if not current_left_entry['removable'] and not current_right_entry['removable']:continue
            current_left_terms=current_term_lookup[current_left_entry['id']]
            current_right_terms=current_term_lookup[current_right_entry['id']]
            current_term_overlap=len(current_left_terms&current_right_terms)/max(1,len(current_left_terms|current_right_terms))
            if current_term_overlap<.35:continue
            current_compared_pairs+=1
            current_similarity_score=sum(current_left_value*current_right_value for current_left_value,current_right_value in zip(current_left_entry['vector'],current_right_entry['vector']))
            if current_similarity_score<DUPLICATE_SIMILARITY_THRESHOLD:continue
            current_left_score=calculate_dependency_score(current_left_entry,current_document_entries[current_left_entry['path']])
            current_right_score=calculate_dependency_score(current_right_entry,current_document_entries[current_right_entry['path']])
            if current_left_score==current_right_score:
                if current_left_entry['path']!=current_right_entry['path']:continue
                current_keep_entry,current_remove_entry=sorted((current_left_entry,current_right_entry),key=lambda current_entry:current_entry['start'])
            else:current_keep_entry,current_remove_entry=(current_left_entry,current_right_entry) if current_left_score>current_right_score else (current_right_entry,current_left_entry)
            if not current_remove_entry['removable']:continue
            current_candidate_entries.append({'keep':current_keep_entry,'remove':current_remove_entry,'similarity':round(current_similarity_score,6),'keep_dependency':max(current_left_score,current_right_score),'remove_dependency':min(current_left_score,current_right_score)})
    current_candidate_entries.sort(key=lambda current_pair_entry:(-current_pair_entry['similarity'],current_pair_entry['remove']['path']))
    return current_candidate_entries[:DUPLICATE_PAIR_LIMIT],{'eligible_chunks':len(current_eligible_entries),'compared_pairs':current_compared_pairs,'candidate_pairs':len(current_candidate_entries),'reviewed_pairs':min(len(current_candidate_entries),DUPLICATE_PAIR_LIMIT),'limited':len(current_candidate_entries)>DUPLICATE_PAIR_LIMIT}
