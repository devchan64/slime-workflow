"""학습·작성·중복 검토 작업을 실행별 경로에 기록한다."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from copy import deepcopy
import argparse
import json
import os
import re
import traceback
import uuid
from . import prepare,runtime
from .documents import DEFAULT_WORKSPACE_CONFIG,load_workspace_config,lock_workspace_state,read_yaml_document,save_yaml_document,snapshot_document_hashes,scan_workspace_documents,calculate_content_hash
from .index import learn_document_index,load_current_index,rank_document_chunks,find_duplicate_candidates
from .agent import (WRITER_SYSTEM_PROMPT,WRITER_OUTPUT_SCHEMA,DUPLICATE_SYSTEM_PROMPT,DUPLICATE_OUTPUT_SCHEMA,collect_writing_context,available_writing_folders,build_writing_proposal,build_duplicate_proposal,public_chunk_record)

JOB_IDENTIFIER_PATTERN=re.compile(r'^\d{8}-\d{6}-[a-f0-9]{8}$')
JOB_REQUEST_MODES={'learn','write','deduplicate'}

def validate_job_request(current_request_values):
    if not isinstance(current_request_values,dict) or set(current_request_values)!={'mode','prompt'}:raise ValueError('작업 요청 필드 오류')
    if current_request_values['mode'] not in JOB_REQUEST_MODES or not isinstance(current_request_values['prompt'],str) or len(current_request_values['prompt'])>6000:raise ValueError('작업 종류·프롬프트 오류')
    if current_request_values['mode']=='write' and not current_request_values['prompt'].strip():raise ValueError('작성 아이디어를 입력하세요.')
    if current_request_values['mode']=='learn' and current_request_values['prompt']:raise ValueError('학습에는 작성 프롬프트를 사용하지 않습니다.')
    return current_request_values

def resolve_job_directory(current_config_values,current_job_identifier):
    if not isinstance(current_job_identifier,str) or not JOB_IDENTIFIER_PATTERN.fullmatch(current_job_identifier):raise ValueError('작업 ID 오류')
    current_job_root=Path(current_config_values['state_root'])/'jobs'/current_job_identifier
    if current_job_root.is_symlink():raise ValueError('심볼릭 링크 작업 금지')
    return current_job_root

def update_job_status(current_job_root,current_stage_name,**current_detail_values):
    current_status_path=current_job_root/'status.yaml'
    current_status_values=read_yaml_document(current_status_path) if current_status_path.exists() else {}
    current_status_values.update(current_detail_values)
    current_status_values.update({'stage':current_stage_name,'updated_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat()})
    save_yaml_document(current_status_path,current_status_values)

def create_writer_job(current_config_values,current_request_values):
    validate_job_request(current_request_values)
    current_job_identifier=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
    current_job_root.mkdir(parents=True,exist_ok=False)
    save_yaml_document(current_job_root/'request.yaml',current_request_values)
    update_job_status(current_job_root,'queued',id=current_job_identifier,mode=current_request_values['mode'],created_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat())
    return current_job_identifier

def describe_writer_progress(current_job_root):
    current_status_values=read_yaml_document(current_job_root/'status.yaml')
    current_artifact_bytes=sum(current_file_path.stat().st_size for current_file_path in current_job_root.iterdir() if current_file_path.is_file())
    return f"상태={current_status_values['stage']} 진행={current_status_values.get('progress',{})} 산출바이트={current_artifact_bytes} 경로={current_job_root}"

def read_process_identity(current_process_identifier):
    current_process_path=Path('/proc')/str(current_process_identifier)
    try:
        current_process_fields=(current_process_path/'stat').read_text().rsplit(')',1)[1].split()
        return current_process_fields[19] if current_process_fields[0]!='Z' else None
    except FileNotFoundError:return None


def execute_writer_job(current_config_path,current_job_identifier):
    current_config_values=load_workspace_config(current_config_path)
    current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
    current_request_values=validate_job_request(read_yaml_document(current_job_root/'request.yaml'))
    if read_yaml_document(current_job_root/'status.yaml')['stage']!='queued':raise ValueError('이미 실행된 작업입니다.')
    update_job_status(current_job_root,'queued',process_id=os.getpid(),process_identity=read_process_identity(os.getpid()))
    prepare.RUNTIME_INSTALL_ROOT.mkdir(parents=True,exist_ok=True)
    prepare.CURRENT_LOG_PATH=current_job_root/'execution.log'
    try:
        with lock_workspace_state(current_config_values),prepare.lock_gpu_runtime(),prepare.trace_runtime_progress('working',lambda:describe_writer_progress(current_job_root)):
            update_job_status(current_job_root,'indexing' if current_request_values['mode']=='learn' else 'searching')
            prepare.emit_runtime_trace('start',f"mode={current_request_values['mode']} source={current_config_values['document_root']} output={current_job_root}")
            if current_request_values['mode']=='learn':
                with runtime.start_managed_server(current_job_root,'embedding'):
                    current_result_values=learn_document_index(current_config_values,runtime.request_document_embedding,lambda current_progress_values:update_job_status(current_job_root,'indexing',progress=current_progress_values))
                save_yaml_document(current_job_root/'result.yaml',current_result_values)
                update_job_status(current_job_root,'completed',summary=f"문서 {current_result_values['documents']}개 · 청크 {current_result_values['chunks']}개 학습 완료")
                return
            current_document_entries,current_chunk_entries=load_current_index(current_config_values)
            current_snapshot_hashes=snapshot_document_hashes(current_document_entries)
            if current_request_values['mode']=='write' or current_request_values['prompt'].strip():
                with runtime.start_managed_server(current_job_root,'embedding'):
                    current_query_vector=runtime.request_document_embedding('Instruct: Retrieve relevant documents for a writing request\nQuery: '+current_request_values['prompt'])
                current_ranked_entries=rank_document_chunks(current_chunk_entries,current_request_values['prompt'],current_query_vector,80 if current_request_values['mode']=='deduplicate' else 12)
            else:current_ranked_entries=[]
            save_yaml_document(current_job_root/'search.yaml',{'prompt':current_request_values['prompt'],'results':[public_chunk_record(current_chunk_entry) for current_chunk_entry in current_ranked_entries]})
            update_job_status(current_job_root,'reasoning')
            if current_request_values['mode']=='write':
                current_context_entries=collect_writing_context(current_document_entries,current_chunk_entries,current_ranked_entries)
                current_model_input={'instruction':current_request_values['prompt'],'sources':current_context_entries,'folders':available_writing_folders(current_config_values,current_document_entries)}
                save_yaml_document(current_job_root/'context.yaml',current_model_input)
                current_writer_schema=deepcopy(WRITER_OUTPUT_SCHEMA)
                current_writer_schema['properties']['source_ids']['items']={'type':'string','enum':[current_chunk_entry['id'] for current_chunk_entry in current_context_entries]}
                with runtime.start_managed_server(current_job_root):
                    current_model_result=runtime.request_structured_result(WRITER_SYSTEM_PROMPT,current_model_input,current_writer_schema)
                save_yaml_document(current_job_root/'model-result.yaml',current_model_result)
                current_proposal_values=build_writing_proposal(current_config_values,current_document_entries,current_context_entries,current_model_result)
            else:
                current_candidate_pairs,current_coverage_values=find_duplicate_candidates(current_document_entries,current_chunk_entries,current_ranked_entries if current_request_values['prompt'].strip() else None)
                current_review_entries=[]
                if current_candidate_pairs:
                    with runtime.start_managed_server(current_job_root):
                        for current_pair_number,current_candidate_values in enumerate(current_candidate_pairs,1):
                            current_model_input={'instruction':current_request_values['prompt'],'keep':public_chunk_record(current_candidate_values['keep']),'remove':public_chunk_record(current_candidate_values['remove'])}
                            current_verdict_values=runtime.request_structured_result(DUPLICATE_SYSTEM_PROMPT,current_model_input,DUPLICATE_OUTPUT_SCHEMA,600)
                            current_review_entries.append((current_candidate_values,current_verdict_values))
                            save_yaml_document(current_job_root/f'comparison-{current_pair_number:02d}.yaml',{'input':current_model_input,'verdict':current_verdict_values})
                            update_job_status(current_job_root,'reasoning',progress={'pairs_done':current_pair_number,'pairs_total':len(current_candidate_pairs)})
                current_proposal_values=build_duplicate_proposal(current_document_entries,current_review_entries,current_coverage_values)
            if snapshot_document_hashes(scan_workspace_documents(current_config_values))!=current_snapshot_hashes:raise ValueError('검토 중 원문이 변경되어 제안을 확정할 수 없습니다.')
            current_proposal_values['snapshot_hashes']=current_snapshot_hashes
            current_proposal_values['id']=current_job_identifier
            save_yaml_document(current_job_root/'proposal.yaml',current_proposal_values)
            current_proposal_digest=calculate_content_hash((current_job_root/'proposal.yaml').read_bytes())
            update_job_status(current_job_root,'review' if current_proposal_values['changes'] else 'completed',proposal_hash=current_proposal_digest,summary=f"변경 {len(current_proposal_values['changes'])}개 · 원본 적용 전 검토")
            prepare.emit_runtime_trace('complete',f'proposal={current_job_root/"proposal.yaml"}')
    except Exception as current_task_error:
        update_job_status(current_job_root,'failed',error=f'{type(current_task_error).__name__}: {current_task_error}')
        prepare.emit_runtime_trace('failed',traceback.format_exc())
        raise

if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser(description='작가 에이전트 등록 작업 실행')
    current_argument_parser.add_argument('--config',type=Path,default=DEFAULT_WORKSPACE_CONFIG)
    current_argument_parser.add_argument('--job-id',required=True)
    current_argument_values=current_argument_parser.parse_args()
    execute_writer_job(current_argument_values.config,current_argument_values.job_id)
