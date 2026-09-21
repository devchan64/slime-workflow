"""문단 원문을 재작성하지 않고 파일 분리·이동을 미리보기, 반영, 복구한다."""
from collections import Counter
import contextlib
from datetime import datetime
import difflib
from pathlib import Path, PurePosixPath
import posixpath
import re
import threading
import traceback
from urllib.parse import unquote,urlsplit
import uuid
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator
from markdown_it import MarkdownIt

from .bookbinding import plan_document_book,scan_book_documents,normalize_heading_anchor,BOOK_IDENTIFIER_PATTERN
from .documents import (calculate_text_digest,load_yaml_document,save_yaml_document,resolve_document_path,
    lock_document_workspace,apply_document_changes,rollback_document_changes,include_catalog_changes)

REORGANIZATION_REQUEST_SCHEMA={'type':'object','additionalProperties':False,'required':['source_directory_paths','paragraph_placements','new_document_titles'],'properties':{'source_directory_paths':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string'}},'paragraph_placements':{'type':'array','minItems':1,'maxItems':15000,'items':{'type':'object','additionalProperties':False,'required':['paragraph_id','target_document_path'],'properties':{'paragraph_id':{'type':'string'},'target_document_path':{'type':'string','minLength':1,'maxLength':300}}}},'new_document_titles':{'type':'object','additionalProperties':{'type':'string','minLength':1,'maxLength':120,'pattern':r'^[^\r\n]+$'}}}}

REORGANIZATION_REQUEST_SCHEMA['properties']['collection_id']={'enum':['world','system-design']}

@contextlib.contextmanager
def trace_reorganization_steps(current_run_root,current_stage_name):
    current_stop_event=threading.Event()
    current_log_lock=threading.Lock()
    def record_trace_message(current_message_text):
        current_log_line=f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/document-structure/{current_stage_name} {current_message_text}'
        with current_log_lock,(current_run_root/'execution.log').open('a') as current_log_stream:
            current_log_stream.write(current_log_line+'\n')
        print(current_log_line,flush=True)
    def record_trace_heartbeat():
        while not current_stop_event.wait(4):
            record_trace_message('문서 구조 처리 중 · 결과 검증 대기')
    current_heartbeat_thread=threading.Thread(target=record_trace_heartbeat,daemon=True)
    record_trace_message('시작')
    current_heartbeat_thread.start()
    try:
        yield
        record_trace_message('완료')
    except Exception:
        record_trace_message(traceback.format_exc())
        print('\n'.join((current_run_root/'execution.log').read_text().splitlines()[-20:]),flush=True)
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join(timeout=1)


def inspect_markdown_links(current_document_path,current_document_text,current_reference_values=None):
    current_markdown_parser=MarkdownIt('commonmark',{'html':False}).enable('table')
    current_environment_values={} if current_reference_values is None else current_reference_values
    current_document_tokens=current_markdown_parser.parse(current_document_text,current_environment_values)
    current_heading_counts={}
    current_heading_anchors=set()
    current_link_targets=[]
    for current_token_index,current_parser_token in enumerate(current_document_tokens):
        if current_parser_token.type=='heading_open':
            current_heading_slug=normalize_heading_anchor(current_document_tokens[current_token_index+1].content)
            current_heading_count=current_heading_counts.get(current_heading_slug,0)
            current_heading_counts[current_heading_slug]=current_heading_count+1
            current_heading_anchors.add(current_heading_slug+('-'+str(current_heading_count) if current_heading_count else ''))
        for current_child_token in current_parser_token.children or []:
            if current_child_token.type not in {'link_open','image'}:
                continue
            current_link_text=current_child_token.attrGet('href' if current_child_token.type=='link_open' else 'src') or ''
            current_parsed_url=urlsplit(current_link_text)
            if current_parsed_url.scheme or current_parsed_url.netloc:
                current_link_targets.append(('external',current_link_text,''))
            else:
                current_link_path=posixpath.normpath(posixpath.join(str(PurePosixPath(current_document_path).parent),unquote(current_parsed_url.path))) if current_parsed_url.path else current_document_path
                current_link_targets.append(('local',current_link_path,unquote(current_parsed_url.fragment)))
    return current_link_targets,current_heading_anchors,current_environment_values


def prepare_reorganization_changes(current_config_values,current_request_values):
    Draft202012Validator(REORGANIZATION_REQUEST_SCHEMA).validate(current_request_values)
    if 'collection_id' in current_request_values:
        from .book_collections import resolve_collection_request
        current_collection_entry=resolve_collection_request(current_config_values,current_request_values)
        current_config_values={**current_config_values,'allowed_write_roots':current_collection_entry['source_directory_paths']}
    current_plan_values=plan_document_book(current_config_values,{'book_title_text':'문서 구조 편집','source_directory_paths':current_request_values['source_directory_paths']})
    current_paragraph_lookup={current_paragraph_entry['paragraph_id']:current_paragraph_entry for current_paragraph_entry in current_plan_values['paragraph_entries']}
    current_placement_ids=[current_placement_entry['paragraph_id'] for current_placement_entry in current_request_values['paragraph_placements']]
    if len(current_placement_ids)!=len(set(current_placement_ids)) or set(current_placement_ids)!=set(current_paragraph_lookup):
        raise ValueError('문단 누락·중복 또는 원문 변경: 배치안을 다시 불러오세요.')
    current_source_entries=scan_book_documents(current_config_values)
    for current_paragraph_entry in current_paragraph_lookup.values():
        if current_paragraph_entry['source_document_path'] not in current_source_entries or current_source_entries[current_paragraph_entry['source_document_path']]['source_content_hash']!=current_paragraph_entry['source_content_hash']:
            raise ValueError('문단 수집 중 원문이 변경되었습니다. 배치안을 다시 불러오세요.')
    selected_source_paths={current_paragraph_entry['source_document_path'] for current_paragraph_entry in current_paragraph_lookup.values()}
    current_target_paragraphs={current_source_path:[] for current_source_path in sorted(selected_source_paths)}
    for current_placement_entry in current_request_values['paragraph_placements']:
        current_paragraph_entry=current_paragraph_lookup[current_placement_entry['paragraph_id']]
        current_target_path=current_placement_entry['target_document_path']
        resolve_document_path(Path(current_config_values['source_document_root']),current_target_path)
        if current_target_path in current_source_entries and current_target_path not in selected_source_paths:
            raise ValueError('이동 대상 기존 파일도 원본 선택 범위에 포함해야 합니다: '+current_target_path)
        if current_target_path!=current_paragraph_entry['source_document_path'] and (not current_target_path.endswith('.md') or not current_paragraph_entry['source_document_path'].endswith('.md')):
            raise ValueError('파일 간 문단 이동은 Markdown에만 지원합니다. YAML은 원본 위치를 유지하세요.')
        current_target_paragraphs.setdefault(current_target_path,[]).append(current_paragraph_entry)
    current_new_paths=set(current_target_paragraphs)-set(current_source_entries)
    if set(current_request_values['new_document_titles'])!=current_new_paths:
        raise ValueError('새 파일 각각에 제목을 지정해야 합니다. 사용하지 않는 제목도 제거하세요.')
    current_next_documents={current_source_path:current_source_entry['source_document_body'] for current_source_path,current_source_entry in current_source_entries.items()}
    current_change_entries=[]
    for current_target_path,current_paragraph_entries in current_target_paragraphs.items():
        current_previous_text=current_next_documents.get(current_target_path)
        current_next_text=''
        if current_target_path in current_new_paths:
            current_next_text='# '+current_request_values['new_document_titles'][current_target_path].strip()+'\n\n'
        for current_paragraph_entry in current_paragraph_entries:
            if current_next_text and not current_next_text.endswith(('\n\n','\r\n\r\n')):
                current_next_text+='\n\n'
            current_next_text+=current_paragraph_entry['paragraph_text']
        # 이동하지 않은 파일은 줄바꿈을 포함해 완전히 동일하게 유지한다.
        if [current_paragraph_entry['paragraph_id'] for current_paragraph_entry in current_paragraph_entries]==[current_paragraph_entry['paragraph_id'] for current_paragraph_entry in sorted(current_paragraph_lookup.values(),key=lambda current_paragraph_entry:current_paragraph_entry['source_start_line']) if current_paragraph_entry['source_document_path']==current_target_path]:
            current_next_text=current_previous_text
        if current_next_text==current_previous_text:
            continue
        if current_target_path in current_config_values['protected_document_paths'] or not any(current_target_path.startswith(current_write_root.rstrip('/')+'/') for current_write_root in current_config_values['allowed_write_roots']):
            raise ValueError('수정할 수 없는 문서입니다: '+current_target_path)
        if not current_next_text or not re.match(r'^#\s+\S',current_next_text):
            raise ValueError('각 파일의 제목과 내용을 유지하세요. 비워진 파일은 자동 삭제하지 않습니다: '+current_target_path)
        current_next_documents[current_target_path]=current_next_text
        current_change_entries.append({'document_relative_path':current_target_path,'previous_document_text':current_previous_text,'next_document_text':current_next_text,'previous_content_hash':calculate_text_digest(current_previous_text) if current_previous_text is not None else None,'next_content_hash':calculate_text_digest(current_next_text)})
    if not current_change_entries:
        raise ValueError('파일 배치에 변경이 없습니다. 대상 파일 또는 문단 순서를 변경하세요.')
    current_before_links={current_source_path:inspect_markdown_links(current_source_path,current_source_entry['source_document_body']) for current_source_path,current_source_entry in current_source_entries.items() if current_source_path.endswith('.md')}
    current_after_links={current_source_path:inspect_markdown_links(current_source_path,current_source_text) for current_source_path,current_source_text in current_next_documents.items() if current_source_path.endswith('.md')}
    for current_target_path,current_paragraph_entries in current_target_paragraphs.items():
        if not current_target_path.endswith('.md'):
            continue
        for current_paragraph_entry in current_paragraph_entries:
            current_original_path=current_paragraph_entry['source_document_path']
            previous_link_targets=inspect_markdown_links(current_original_path,current_paragraph_entry['paragraph_text'],dict(current_before_links[current_original_path][2]))[0]
            next_link_targets=inspect_markdown_links(current_target_path,current_paragraph_entry['paragraph_text'],dict(current_after_links[current_target_path][2]))[0]
            if Counter(previous_link_targets)!=Counter(next_link_targets):
                raise ValueError('문단 이동으로 상대 링크 또는 참조 정의의 의미가 달라집니다. 참조를 함께 정리한 뒤 이동하세요: '+current_original_path+' → '+current_target_path)
    for current_source_path,(current_link_targets,_,_) in current_before_links.items():
        for current_link_kind,current_link_path,current_link_fragment in current_link_targets:
            if current_link_kind=='local' and current_link_fragment and current_link_path in current_before_links and current_link_fragment in current_before_links[current_link_path][1] and current_link_fragment not in current_after_links[current_link_path][1]:
                raise ValueError('기존 문서가 참조하는 절을 옮기면 링크가 끊어집니다: '+current_source_path+' → '+current_link_path+'#'+current_link_fragment)
    current_change_entries=include_catalog_changes(current_config_values,current_source_entries,current_change_entries)
    return current_change_entries,current_source_entries


def preview_document_reorganization(current_config_values,current_request_values):
    current_reorganization_id=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
    current_run_root=Path(current_config_values['private_state_root'])/'reorganizations'/current_reorganization_id
    current_run_root.mkdir(parents=True,mode=0o700)
    with trace_reorganization_steps(current_run_root,'preview'),lock_document_workspace(Path(current_config_values['private_state_root'])):
        current_change_entries,current_source_entries=prepare_reorganization_changes(current_config_values,current_request_values)
        current_preview_values={'reorganization_id':current_reorganization_id,'current_stage_name':'preview','source_hash_mapping':{current_source_path:current_source_entry['source_content_hash'] for current_source_path,current_source_entry in current_source_entries.items()},'document_change_entries':current_change_entries,'request_values':current_request_values}
        save_yaml_document(current_run_root/'preview.yaml',current_preview_values)
        return {'reorganization_id':current_reorganization_id,'document_change_entries':[{'document_relative_path':current_change_entry['document_relative_path'],'change_diff_text':''.join(difflib.unified_diff((current_change_entry['previous_document_text'] or '').splitlines(keepends=True),current_change_entry['next_document_text'].splitlines(keepends=True),fromfile='이전/'+current_change_entry['document_relative_path'],tofile='이후/'+current_change_entry['document_relative_path']))} for current_change_entry in current_change_entries]}


def execute_document_reorganization(current_config_values,current_reorganization_id,current_operation_name):
    if not re.fullmatch(BOOK_IDENTIFIER_PATTERN,current_reorganization_id) or current_operation_name not in {'apply','rollback'}:
        raise ValueError('지원하지 않는 문서 구조 작업입니다.')
    current_run_root=resolve_document_path(Path(current_config_values['private_state_root'])/'reorganizations',current_reorganization_id)
    with trace_reorganization_steps(current_run_root,current_operation_name),lock_document_workspace(Path(current_config_values['private_state_root'])):
        current_preview_values=load_yaml_document(current_run_root/'preview.yaml')
        if current_operation_name=='apply':
            if current_preview_values['current_stage_name']!='preview' or (current_run_root/'transaction.yaml').exists():
                raise ValueError('이미 처리한 배치안입니다.')
            current_source_entries=scan_book_documents(current_config_values)
            if {current_source_path:current_source_entry['source_content_hash'] for current_source_path,current_source_entry in current_source_entries.items()}!=current_preview_values['source_hash_mapping']:
                raise ValueError('미리보기 이후 원문이 변경되었습니다. 미리보기를 다시 만드세요.')
            current_verified_changes,_=prepare_reorganization_changes(current_config_values,current_preview_values['request_values'])
            if current_verified_changes!=current_preview_values['document_change_entries']:
                raise ValueError('설정 또는 배치안이 변경되었습니다. 미리보기를 다시 만드세요.')
            apply_document_changes(current_config_values,current_run_root,current_verified_changes)
            current_preview_values['current_stage_name']='applied'
        else:
            rollback_document_changes(current_config_values,current_run_root)
            current_preview_values['current_stage_name']='rolled_back'
        save_yaml_document(current_run_root/'preview.yaml',current_preview_values)
        return {'reorganization_id':current_reorganization_id,'current_stage_name':current_preview_values['current_stage_name']}


def list_document_reorganizations(current_config_values):
    current_result_entries=[]
    for current_preview_path in sorted((Path(current_config_values['private_state_root'])/'reorganizations').glob('*/preview.yaml'),reverse=True)[:30]:
        current_preview_values=load_yaml_document(current_preview_path)
        current_transaction_path=current_preview_path.parent/'transaction.yaml'
        current_transaction_state=load_yaml_document(current_transaction_path)['transaction_apply_state'] if current_transaction_path.exists() else 'preview'
        current_result_entries.append({'reorganization_id':current_preview_values['reorganization_id'],'collection_id':current_preview_values['request_values'].get('collection_id','world' if current_preview_values['request_values']['source_directory_paths']==['world'] else None),'current_stage_name':current_transaction_state,'document_paths':[current_change_entry['document_relative_path'] for current_change_entry in current_preview_values['document_change_entries']],'can_rollback_flag':current_transaction_state in {'applying','applied'}})
    return current_result_entries
