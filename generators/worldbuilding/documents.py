"""출처를 보존하는 문서 검색·엄격한 계약·변경 트랜잭션."""
from __future__ import annotations

import contextlib
from datetime import datetime
import difflib
import fcntl
import hashlib
import json
from pathlib import Path
import re
import uuid
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator

MAXIMUM_SOURCE_BYTES = 2_000_000
MAXIMUM_CHUNK_CHARACTERS = 2600
MAXIMUM_CONTEXT_CHARACTERS = 14000
WORKSPACE_CONFIG_FIELDS = {'workspace_schema_version','source_document_root','private_state_root','allowed_write_roots','required_source_paths','protected_document_paths','managed_catalog_path'}
REQUEST_INPUT_SCHEMA = {'type':'object','additionalProperties':False,'required':['requested_instruction_text','requested_operation_mode','requested_target_path'], 'properties':{'requested_instruction_text':{'type':'string','minLength':5,'maxLength':6000},'requested_operation_mode':{'enum':['create','append','replace']},'requested_target_path':{'type':'string','maxLength':300}}}
CHANGE_OUTPUT_SCHEMA = {'type':'object','additionalProperties':False,'required':['result_summary_text','document_change_entries','source_reference_ids','quality_warnings'], 'properties':{'result_summary_text':{'type':'string'},'source_reference_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'quality_warnings':{'type':'array','items':{'type':'string'}},'document_change_entries':{'type':'array','minItems':1,'maxItems':3,'items':{'type':'object','additionalProperties':False,'required':['document_relative_path','document_change_mode','existing_fragment_text','replacement_fragment_text'],'properties':{'document_relative_path':{'type':'string'},'document_change_mode':{'enum':['create','append','replace']},'existing_fragment_text':{'type':'string'},'replacement_fragment_text':{'type':'string','minLength':1}}}}}}


class StrictYamlLoader(yaml.SafeLoader):
    """중복 키를 금지한다."""


def construct_unique_mapping(current_yaml_loader, current_mapping_node, deep=False):
    current_mapping_result = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_key_value = current_yaml_loader.construct_object(current_key_node, deep=deep)
        if not isinstance(current_key_value, str) or current_key_value in current_mapping_result:
            raise ValueError('YAML 키는 중복 없는 문자열이어야 합니다.')
        current_mapping_result[current_key_value] = current_yaml_loader.construct_object(current_value_node, deep=deep)
    return current_mapping_result


StrictYamlLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def load_yaml_document(current_file_path):
    return yaml.load(current_file_path.read_text(encoding='utf-8'), Loader=StrictYamlLoader)


def parse_unique_json(current_source_text):
    def validate_json_pairs(current_pair_entries):
        current_result_mapping = {}
        for current_key_value, current_item_value in current_pair_entries:
            if current_key_value in current_result_mapping:
                raise ValueError(f'중복 JSON 키: {current_key_value}')
            current_result_mapping[current_key_value] = current_item_value
        return current_result_mapping
    return json.loads(current_source_text, object_pairs_hook=validate_json_pairs)


def calculate_text_digest(current_source_text):
    return hashlib.sha256(current_source_text.encode('utf-8')).hexdigest()


def write_atomic_document(current_target_path, current_document_text):
    current_target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output_path = current_target_path.with_name(current_target_path.name + '.' + uuid.uuid4().hex + '.partial')
    with temporary_output_path.open('x', encoding='utf-8') as current_output_stream:
        current_output_stream.write(current_document_text)
        current_output_stream.flush()
        import os
        os.fsync(current_output_stream.fileno())
    temporary_output_path.replace(current_target_path)


def save_yaml_document(current_target_path, current_document_value):
    write_atomic_document(current_target_path, yaml.safe_dump(current_document_value, allow_unicode=True, sort_keys=False))


def resolve_document_path(current_root_path, current_relative_path):
    parsed_relative_path = Path(current_relative_path)
    if not current_relative_path or parsed_relative_path.is_absolute() or any(current_path_part.startswith('.') for current_path_part in parsed_relative_path.parts):
        raise ValueError(f'허용되지 않는 상대 경로: {current_relative_path}')
    resolved_document_path = current_root_path / parsed_relative_path
    for current_parent_path in [resolved_document_path, *resolved_document_path.parents]:
        if current_parent_path == current_root_path:
            break
        if current_parent_path.is_symlink():
            raise ValueError(f'심볼릭 링크 경로 금지: {current_relative_path}')
    if not resolved_document_path.resolve().is_relative_to(current_root_path.resolve()):
        raise ValueError('문서 루트 이탈')
    return resolved_document_path


def load_workspace_config(current_config_path):
    current_config_values = load_yaml_document(current_config_path)
    if not isinstance(current_config_values, dict) or set(current_config_values) != WORKSPACE_CONFIG_FIELDS or current_config_values['workspace_schema_version'] != 1:
        raise ValueError('작업 공간 설정의 필드·버전이 올바르지 않습니다.')
    for current_path_field in ['source_document_root','private_state_root']:
        if not isinstance(current_config_values[current_path_field],str) or not Path(current_config_values[current_path_field]).is_absolute():
            raise ValueError(f'{current_path_field}: 절대 경로가 필요합니다.')
        current_config_values[current_path_field] = str(Path(current_config_values[current_path_field]).resolve())
    source_document_root = Path(current_config_values['source_document_root'])
    private_state_root = Path(current_config_values['private_state_root'])
    if not source_document_root.is_dir() or private_state_root == source_document_root:
        raise ValueError('문서 루트가 없거나 상태 경로와 같습니다.')
    for current_list_field in ['allowed_write_roots','required_source_paths','protected_document_paths']:
        if not isinstance(current_config_values[current_list_field],list) or not current_config_values[current_list_field] or len(set(current_config_values[current_list_field])) != len(current_config_values[current_list_field]):
            raise ValueError(f'{current_list_field}: 비어 있지 않은 고유 경로 목록이 필요합니다.')
        for current_path_value in current_config_values[current_list_field]:
            if not isinstance(current_path_value,str):
                raise ValueError('문서 경로는 문자열이어야 합니다.')
            resolve_document_path(source_document_root,current_path_value)
    if not isinstance(current_config_values['managed_catalog_path'], str):
        raise ValueError('managed_catalog_path는 문자열이어야 합니다.')
    if current_config_values['managed_catalog_path']:
        resolve_document_path(source_document_root,current_config_values['managed_catalog_path'])
    for current_required_path in current_config_values['required_source_paths']:
        if not resolve_document_path(source_document_root,current_required_path).is_file():
            raise ValueError(f'승계 필수 원본 누락: {current_required_path}')
    private_state_root.mkdir(parents=True,exist_ok=True)
    return current_config_values


@contextlib.contextmanager
def lock_document_workspace(current_state_root):
    with (current_state_root/'workspace.lock').open('a') as current_lock_stream:
        try:
            fcntl.flock(current_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:
            raise RuntimeError('다른 문서 작업이 실행 중입니다.') from current_lock_error
        try:
            yield
        finally:
            fcntl.flock(current_lock_stream,fcntl.LOCK_UN)


def scan_source_documents(current_config_values):
    source_document_root = Path(current_config_values['source_document_root'])
    private_state_root = Path(current_config_values['private_state_root'])
    source_document_entries = {}
    for current_document_path in sorted(source_document_root.rglob('*')):
        if current_document_path.suffix.lower() not in {'.md','.yaml','.yml'} or not current_document_path.is_file() or current_document_path.resolve().is_relative_to(private_state_root):
            continue
        current_relative_path = current_document_path.relative_to(source_document_root).as_posix()
        if any(current_path_part.startswith('.') for current_path_part in Path(current_relative_path).parts):
            continue
        resolve_document_path(source_document_root,current_relative_path)
        if current_document_path.stat().st_size > MAXIMUM_SOURCE_BYTES:
            raise ValueError(f'원본 크기 제한 초과: {current_relative_path}')
        current_document_text = current_document_path.read_text(encoding='utf-8')
        if current_document_path.suffix != '.md':
            load_yaml_document(current_document_path)
        source_document_entries[current_relative_path] = {'source_document_path':current_relative_path,'source_content_hash':calculate_text_digest(current_document_text),'source_document_body':current_document_text}
    return source_document_entries


def extract_search_terms(requested_instruction_text):
    search_token_values = re.findall(r'[가-힣A-Za-z0-9_-]{2,}',requested_instruction_text.lower())
    return set(re.sub(r'(에\s*대한|에|의|을|를|들을|들은|에서|으로|과|와|설정)$','',current_token_text) for current_token_text in search_token_values) - {'설정','설정들','추가','추가해줘','신규','새로운','하나','정의','정의한다','작성','수정','참고','참고하여','찾아','기존','대한','해줘','문서'}


def build_inherited_context(current_config_values, current_request_values, source_document_entries):
    """관련 원문 구간·필수 문단·해시를 보존하고 전체 검토와 구분한다."""
    Draft202012Validator(REQUEST_INPUT_SCHEMA).validate(current_request_values)
    search_term_values = extract_search_terms(current_request_values['requested_instruction_text'])
    required_source_paths = set(current_config_values['required_source_paths'])
    source_chunk_entries = []
    for source_relative_path, current_document_entry in source_document_entries.items():
        source_document_lines = current_document_entry['source_document_body'].splitlines(keepends=True)
        current_chunk_lines = []
        current_chunk_start = 1
        current_chunk_number = 0
        for current_line_number,current_line_text in enumerate([*source_document_lines,''],1):
            if current_chunk_lines and (sum(map(len,current_chunk_lines))+len(current_line_text)>MAXIMUM_CHUNK_CHARACTERS or current_line_number>len(source_document_lines)):
                current_chunk_text=''.join(current_chunk_lines)
                source_reference_id=f'{source_relative_path}:{current_chunk_start}-{current_line_number-1}'
                searchable_source_text=(source_relative_path+'\n'+current_chunk_text).lower()
                current_search_score=sum(min(searchable_source_text.count(current_term_text),5)*max(1,len(current_term_text)-1) for current_term_text in search_term_values if current_term_text)
                document_title_text=current_document_entry['source_document_body'].splitlines()[0].lower() if current_document_entry['source_document_body'] else ''
                current_search_score+=sum(20 for current_term_text in search_term_values if current_term_text and current_term_text in document_title_text)
                if current_search_score and source_relative_path.startswith(('world/','world-expansion/')):
                    current_search_score+=5
                    if any(current_title_term in document_title_text for current_title_term in ('설계','기준','원칙')):
                        current_search_score+=12
                    if current_chunk_number==0:
                        current_search_score+=3
                if source_relative_path.startswith('history/'):
                    current_search_score-=20
                current_required_flag=source_relative_path in required_source_paths and current_chunk_number==0
                if source_relative_path==current_request_values['requested_target_path']:
                    current_search_score+=20
                source_chunk_entries.append({'source_reference_id':source_reference_id,'source_document_path':source_relative_path,'source_content_hash':current_document_entry['source_content_hash'],'source_excerpt_text':current_chunk_text,'source_approval_state':'historical' if source_relative_path.startswith('history/') else 'mixed_or_unresolved','source_search_score':current_search_score,'source_required_flag':current_required_flag})
                current_chunk_lines=[]
                current_chunk_start=current_line_number
                current_chunk_number+=1
            current_chunk_lines.append(current_line_text)
    selected_chunk_entries=[]
    selected_character_count=0
    for current_chunk_entry in sorted(source_chunk_entries,key=lambda current_chunk_entry:(not current_chunk_entry['source_required_flag'],-current_chunk_entry['source_search_score'],current_chunk_entry['source_reference_id'])):
        current_excerpt_length=len(current_chunk_entry['source_excerpt_text'])
        if selected_character_count+current_excerpt_length>MAXIMUM_CONTEXT_CHARACTERS:
            if current_chunk_entry['source_required_flag']:
                raise ValueError('필수 승계 문맥이 예산을 초과했습니다.')
            continue
        if not current_chunk_entry['source_required_flag'] and current_chunk_entry['source_search_score']<=0:
            continue
        selected_chunk_entries.append(current_chunk_entry)
        selected_character_count+=current_excerpt_length
    if not selected_chunk_entries:
        raise ValueError('사용할 원문 컨텍스트가 없습니다.')
    return selected_chunk_entries


def validate_change_bundle(current_config_values,current_request_values,current_result_values,source_document_entries,selected_chunk_entries):
    Draft202012Validator(CHANGE_OUTPUT_SCHEMA).validate(current_result_values)
    allowed_reference_ids={current_chunk_entry['source_reference_id'] for current_chunk_entry in selected_chunk_entries}
    if not set(current_result_values['source_reference_ids']).issubset(allowed_reference_ids):
        raise ValueError('읽지 않은 출처를 인용했습니다.')
    source_document_root=Path(current_config_values['source_document_root'])
    seen_document_paths=set()
    planned_change_entries=[]
    for current_change_entry in current_result_values['document_change_entries']:
        current_relative_path=current_change_entry['document_relative_path']
        target_document_path=resolve_document_path(source_document_root,current_relative_path)
        if current_relative_path in seen_document_paths or target_document_path.suffix!='.md' or current_relative_path in current_config_values['protected_document_paths']:
            raise ValueError(f'중복·보호·미지원 대상: {current_relative_path}')
        seen_document_paths.add(current_relative_path)
        if not any(Path(current_relative_path).is_relative_to(Path(current_allowed_root)) for current_allowed_root in current_config_values['allowed_write_roots']):
            raise ValueError(f'쓰기 범위 밖: {current_relative_path}')
        current_change_mode=current_change_entry['document_change_mode']
        if current_change_mode!=current_request_values['requested_operation_mode']:
            raise ValueError('요청한 작업 종류와 모델 결과가 다릅니다.')
        if current_request_values['requested_target_path'] and current_relative_path!=current_request_values['requested_target_path']:
            raise ValueError('지정한 수정 대상과 다릅니다.')
        if current_change_mode!='create' and not current_request_values['requested_target_path']:
            raise ValueError('기존 문서 수정은 명시적 대상 경로가 필요합니다.')
        previous_document_text=source_document_entries.get(current_relative_path,{}).get('source_document_body')
        replacement_fragment_text=current_change_entry['replacement_fragment_text']
        if current_change_mode=='create':
            if previous_document_text is not None or target_document_path.exists() or current_change_entry['existing_fragment_text']:
                raise ValueError('신규 생성 대상이 존재하거나 기존 구간을 지정했습니다.')
            if not replacement_fragment_text.startswith('# '):
                raise ValueError('신규 Markdown은 제목으로 시작해야 합니다.')
            next_document_text=replacement_fragment_text.rstrip()+'\n'
        elif current_change_mode=='append':
            if previous_document_text is None or current_change_entry['existing_fragment_text']:
                raise ValueError('추가 대상이 없거나 기존 구간을 지정했습니다.')
            next_document_text=previous_document_text.rstrip()+'\n\n'+replacement_fragment_text.rstrip()+'\n'
        else:
            existing_fragment_text=current_change_entry['existing_fragment_text']
            if previous_document_text is None or not existing_fragment_text or previous_document_text.count(existing_fragment_text)!=1:
                raise ValueError('교체할 원문 구간이 없거나 유일하지 않습니다.')
            if not any(current_chunk_entry['source_document_path']==current_relative_path and existing_fragment_text in current_chunk_entry['source_excerpt_text'] for current_chunk_entry in selected_chunk_entries):
                raise ValueError('모델이 읽지 않은 구간을 교체할 수 없습니다.')
            next_document_text=previous_document_text.replace(existing_fragment_text,replacement_fragment_text,1)
        if current_change_mode in {'create','append'}:
            if '상태: 신규 제안' not in replacement_fragment_text:
                raise ValueError('새 내용에는 상태: 신규 제안 표시가 필요합니다.')
        planned_change_entries.append({'document_relative_path':current_relative_path,'previous_document_text':previous_document_text,'next_document_text':next_document_text,'previous_content_hash':calculate_text_digest(previous_document_text) if previous_document_text is not None else None,'next_content_hash':calculate_text_digest(next_document_text)})
    return planned_change_entries


def apply_document_changes(current_config_values,current_run_root,planned_change_entries):
    """원본 변경을 재확인하고 복구 가능한 저널을 남긴다."""
    source_document_root=Path(current_config_values['source_document_root'])
    for current_change_entry in planned_change_entries:
        current_target_path=resolve_document_path(source_document_root,current_change_entry['document_relative_path'])
        current_actual_hash=calculate_text_digest(current_target_path.read_text()) if current_target_path.exists() else None
        if current_actual_hash!=current_change_entry['previous_content_hash']:
            raise ValueError(f'생성 이후 원본이 변경되었습니다: {current_target_path}')
    save_yaml_document(current_run_root/'transaction.yaml',{'transaction_apply_state':'applying','document_change_entries':planned_change_entries})
    applied_change_entries=[]
    try:
        for current_change_entry in planned_change_entries:
            current_target_path=resolve_document_path(source_document_root,current_change_entry['document_relative_path'])
            current_actual_hash=calculate_text_digest(current_target_path.read_text()) if current_target_path.exists() else None
            if current_actual_hash!=current_change_entry['previous_content_hash']:
                raise ValueError(f'쓰기 직전 원본이 변경되었습니다: {current_target_path}')
            write_atomic_document(current_target_path,current_change_entry['next_document_text'])
            applied_change_entries.append(current_change_entry)
    except Exception:
        for current_change_entry in reversed(applied_change_entries):
            current_target_path=resolve_document_path(source_document_root,current_change_entry['document_relative_path'])
            if calculate_text_digest(current_target_path.read_text())!=current_change_entry['next_content_hash']:
                raise RuntimeError('실패 복구 중 외부 변경이 발견되었습니다. transaction.yaml을 확인하세요.')
            if current_change_entry['previous_document_text'] is None:
                current_target_path.unlink()
            else:
                write_atomic_document(current_target_path,current_change_entry['previous_document_text'])
        save_yaml_document(current_run_root/'transaction.yaml',{'transaction_apply_state':'rolled_back','document_change_entries':planned_change_entries})
        raise
    save_yaml_document(current_run_root/'transaction.yaml',{'transaction_apply_state':'applied','document_change_entries':planned_change_entries})


def rollback_document_changes(current_config_values,current_run_root):
    current_transaction_values=load_yaml_document(current_run_root/'transaction.yaml')
    if current_transaction_values['transaction_apply_state'] not in {'applying','applied'}:
        raise ValueError('복구할 적용 내역이 없습니다.')
    source_document_root=Path(current_config_values['source_document_root'])
    rollback_change_entries=[]
    for current_change_entry in current_transaction_values['document_change_entries']:
        current_target_path=resolve_document_path(source_document_root,current_change_entry['document_relative_path'])
        current_actual_hash=calculate_text_digest(current_target_path.read_text()) if current_target_path.exists() else None
        if current_actual_hash==current_change_entry['previous_content_hash']:
            continue
        if current_actual_hash!=current_change_entry['next_content_hash']:
            raise ValueError('적용 후 외부 수정이 있어 복구를 중단합니다.')
        rollback_change_entries.append(current_change_entry)
    for current_change_entry in rollback_change_entries:
        current_target_path=resolve_document_path(source_document_root,current_change_entry['document_relative_path'])
        if current_change_entry['previous_document_text'] is None:
            current_target_path.unlink()
        else:
            write_atomic_document(current_target_path,current_change_entry['previous_document_text'])
    current_transaction_values['transaction_apply_state']='rolled_back'
    save_yaml_document(current_run_root/'transaction.yaml',current_transaction_values)


def include_catalog_changes(current_config_values,source_document_entries,planned_change_entries):
    """기존 카탈로그의 해당 분류 표만 새 문서 목록에 맞춘다."""
    catalog_relative_path=current_config_values['managed_catalog_path']
    if not catalog_relative_path:
        return planned_change_entries
    if catalog_relative_path not in source_document_entries:
        raise ValueError('설정한 문서 카탈로그가 없습니다.')
    previous_catalog_text=source_document_entries[catalog_relative_path]['source_document_body']
    next_catalog_text=previous_catalog_text
    for current_change_entry in planned_change_entries:
        current_relative_path=current_change_entry['document_relative_path']
        current_title_match=re.search(r'^#\s+(.+)$',current_change_entry['next_document_text'],re.M)
        if not current_title_match:
            raise ValueError('문서 제목이 없습니다.')
        current_title_text=current_title_match.group(1).replace('|','\\|')
        catalog_row_text=f'| [{current_title_text}]({current_relative_path}) | `{current_relative_path}` |'
        catalog_sections=list(re.finditer(r'^## .+? \(\d+\)\n.*?(?=^## |\Z)',next_catalog_text,re.M|re.S))
        matching_catalog_section=None
        for current_section_match in catalog_sections:
            section_row_paths=re.findall(r'\| `([^`]+)` \|',current_section_match.group(0))
            if any(Path(current_row_path).parts[0]==Path(current_relative_path).parts[0] for current_row_path in section_row_paths):
                matching_catalog_section=current_section_match
                break
        if matching_catalog_section is None:
            raise ValueError('해당 문서 분류의 기존 카탈로그 표가 없습니다.')
        current_section_text=matching_catalog_section.group(0)
        section_line_values=current_section_text.splitlines()
        section_data_rows=[current_line_text for current_line_text in section_line_values if re.search(r'\| `[^`]+` \|',current_line_text)]
        section_data_rows=[current_row_text for current_row_text in section_data_rows if f'| `{current_relative_path}` |' not in current_row_text]+[catalog_row_text]
        section_data_rows.sort(key=lambda current_row_text: re.search(r'\| `([^`]+)` \|',current_row_text).group(1))
        current_header_text=re.sub(r'\(\d+\)$',f'({len(section_data_rows)})',section_line_values[0])
        next_section_text=current_header_text+'\n\n| 문서 | 경로 |\n|---|---|\n'+'\n'.join(section_data_rows)+'\n\n'
        next_catalog_text=next_catalog_text[:matching_catalog_section.start()]+next_section_text+next_catalog_text[matching_catalog_section.end():]
    if next_catalog_text!=previous_catalog_text:
        planned_change_entries.append({'document_relative_path':catalog_relative_path,'previous_document_text':previous_catalog_text,'next_document_text':next_catalog_text,'previous_content_hash':calculate_text_digest(previous_catalog_text),'next_content_hash':calculate_text_digest(next_catalog_text)})
    return planned_change_entries


def validate_document_links(current_config_values,planned_change_entries):
    """후보에 추가된 상대 문서 링크의 실제 대상을 검사한다."""
    from urllib.parse import unquote, urlsplit
    source_document_root=Path(current_config_values['source_document_root'])
    planned_document_paths={(source_document_root/current_change_entry['document_relative_path']).resolve() for current_change_entry in planned_change_entries}
    for current_change_entry in planned_change_entries:
        current_parent_path=(source_document_root/current_change_entry['document_relative_path']).parent
        current_body_text=re.sub(r'```.*?```','',current_change_entry['next_document_text'],flags=re.S)
        for current_link_value in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)',current_body_text):
            current_url_parts=urlsplit(current_link_value)
            if current_url_parts.scheme or current_link_value.startswith('#'):
                continue
            current_link_path=(current_parent_path/unquote(current_url_parts.path)).resolve()
            if not current_link_path.is_relative_to(source_document_root) or (not current_link_path.exists() and current_link_path not in planned_document_paths):
                raise ValueError(f'후보의 깨진 상대 링크: {current_change_entry["document_relative_path"]} → {current_link_value}')
