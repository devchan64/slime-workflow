"""비공개 문서 스냅샷·경로·문단과 승인 전 변경을 엄격하게 관리한다."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote, urlsplit
import fcntl
import json
import os
import re
import tempfile
import yaml

WORKFLOW_REPOSITORY_ROOT=Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE_CONFIG=WORKFLOW_REPOSITORY_ROOT/'.local/writer-agent/workspace.yaml'
WORKSPACE_REQUIRED_FIELDS={'schema_version','document_root','state_root','write_roots','excluded_roots','protected_paths'}
MAXIMUM_DOCUMENT_BYTES=2_000_000
MAXIMUM_CHUNK_CHARACTERS=2400
MINIMUM_DUPLICATE_CHARACTERS=100
DOCUMENT_LINK_PATTERN=re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)\)')

class UniqueDocumentLoader(yaml.SafeLoader):
    pass

def construct_unique_mapping(current_yaml_loader,current_mapping_node):
    current_mapping_values={}
    for current_key_node,current_value_node in current_mapping_node.value:
        current_key_text=current_yaml_loader.construct_object(current_key_node,deep=True)
        if current_key_text in current_mapping_values:raise ValueError(f'중복 YAML 키: {current_key_text}')
        current_mapping_values[current_key_text]=current_yaml_loader.construct_object(current_value_node,deep=True)
    return current_mapping_values
UniqueDocumentLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,construct_unique_mapping)

def parse_unique_json(current_source_text):
    def collect_unique_fields(current_field_pairs):
        current_result_values={}
        for current_field_name,current_field_value in current_field_pairs:
            if current_field_name in current_result_values:raise ValueError(f'중복 JSON 필드: {current_field_name}')
            current_result_values[current_field_name]=current_field_value
        return current_result_values
    def reject_invalid_constant(current_constant_name):
        raise ValueError(f'유한수가 아닌 JSON 값: {current_constant_name}')
    return json.loads(current_source_text,object_pairs_hook=collect_unique_fields,parse_constant=reject_invalid_constant)

def calculate_content_hash(current_source_bytes):
    return sha256(current_source_bytes).hexdigest()

def read_yaml_document(current_document_path):
    return yaml.load(current_document_path.read_text(),Loader=UniqueDocumentLoader)

def write_atomic_bytes(current_document_path,current_source_bytes):
    current_document_path.parent.mkdir(parents=True,exist_ok=True)
    current_file_handle,current_temporary_name=tempfile.mkstemp(prefix='.writer-',dir=current_document_path.parent)
    try:
        with os.fdopen(current_file_handle,'wb') as current_output_stream:
            current_output_stream.write(current_source_bytes)
            current_output_stream.flush()
            os.fsync(current_output_stream.fileno())
        os.replace(current_temporary_name,current_document_path)
    finally:
        Path(current_temporary_name).unlink(missing_ok=True)

def save_yaml_document(current_document_path,current_document_values):
    write_atomic_bytes(current_document_path,yaml.safe_dump(current_document_values,allow_unicode=True,sort_keys=False).encode())

def resolve_document_path(current_root_path,current_relative_path):
    if not isinstance(current_relative_path,str) or not current_relative_path or '\\' in current_relative_path:raise ValueError('문서 상대 경로가 필요합니다.')
    current_relative_value=Path(current_relative_path)
    if current_relative_value.is_absolute() or any(current_part_value.startswith('.') for current_part_value in current_relative_value.parts):raise ValueError('숨김·상위·절대 경로 금지')
    current_target_path=current_root_path/current_relative_value
    for current_parent_path in [current_target_path,*current_target_path.parents]:
        if current_parent_path==current_root_path:break
        if current_parent_path.is_symlink():raise ValueError('심볼릭 링크 문서 금지')
    if not current_target_path.resolve().is_relative_to(current_root_path.resolve()):raise ValueError('문서 루트 이탈')
    return current_target_path

def load_workspace_config(current_config_path=DEFAULT_WORKSPACE_CONFIG):
    current_config_values=read_yaml_document(current_config_path)
    if not isinstance(current_config_values,dict) or set(current_config_values)!=WORKSPACE_REQUIRED_FIELDS or type(current_config_values['schema_version']) is not int or current_config_values['schema_version']!=1:raise ValueError('작업 공간 설정 필드·버전 오류')
    for current_field_name in ('document_root','state_root'):
        current_path_text=current_config_values[current_field_name]
        if not isinstance(current_path_text,str) or not Path(current_path_text).is_absolute():raise ValueError('문서·상태 루트에는 절대 경로가 필요합니다.')
        current_config_values[current_field_name]=str(Path(current_path_text).resolve())
    current_document_root=Path(current_config_values['document_root'])
    current_state_root=Path(current_config_values['state_root'])
    if not current_document_root.is_dir() or current_state_root==current_document_root or current_document_root.is_relative_to(current_state_root):raise ValueError('문서·상태 루트 분리 오류')
    for current_field_name in ('write_roots','excluded_roots','protected_paths'):
        current_path_values=current_config_values[current_field_name]
        if not isinstance(current_path_values,list) or any(not isinstance(current_path_value,str) for current_path_value in current_path_values) or len(set(current_path_values))!=len(current_path_values):raise ValueError('경로 목록 오류')
        for current_path_value in current_path_values:resolve_document_path(current_document_root,current_path_value)
    if not current_config_values['write_roots']:raise ValueError('쓰기 허용 루트가 필요합니다.')
    current_state_root.mkdir(parents=True,exist_ok=True)
    return current_config_values

def is_path_within(current_relative_path,current_root_values):
    return any(current_relative_path==current_root_value or current_relative_path.startswith(current_root_value.rstrip('/')+'/') for current_root_value in current_root_values)

def allow_document_write(current_config_values,current_relative_path):
    return (current_relative_path.endswith('.md') and Path(current_relative_path).name not in {'README.md','CATALOG.md','MANAGEMENT.md','SUMMARY.md'} and is_path_within(current_relative_path,current_config_values['write_roots']) and not is_path_within(current_relative_path,current_config_values['protected_paths']+current_config_values['excluded_roots']))

@contextmanager
def lock_workspace_state(current_config_values):
    with (Path(current_config_values['state_root'])/'workspace.lock').open('a') as current_lock_stream:
        try:fcntl.flock(current_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:raise RuntimeError('다른 학습·작성·적용 작업이 실행 중입니다.') from current_lock_error
        try:yield
        finally:fcntl.flock(current_lock_stream,fcntl.LOCK_UN)

def scan_workspace_documents(current_config_values):
    current_document_root=Path(current_config_values['document_root'])
    current_state_root=Path(current_config_values['state_root'])
    current_document_entries={}
    for current_document_path in sorted(current_document_root.rglob('*')):
        current_relative_path=current_document_path.relative_to(current_document_root).as_posix()
        if any(current_part_name.startswith('.') for current_part_name in Path(current_relative_path).parts) or current_document_path.resolve().is_relative_to(current_state_root) or is_path_within(current_relative_path,current_config_values['excluded_roots']):continue
        if current_document_path.suffix not in {'.md','.yaml','.yml'} or not current_document_path.is_file():continue
        resolve_document_path(current_document_root,current_relative_path)
        current_source_bytes=current_document_path.read_bytes()
        if len(current_source_bytes)>MAXIMUM_DOCUMENT_BYTES:raise ValueError(f'문서 크기 제한 초과: {current_relative_path}')
        current_source_text=current_source_bytes.decode('utf-8')
        if current_document_path.suffix!='.md':yaml.load(current_source_text,Loader=UniqueDocumentLoader)
        current_title_match=re.search(r'^# +(.+)',current_source_text,re.M)
        current_link_paths=[]
        for current_link_target in DOCUMENT_LINK_PATTERN.findall(current_source_text):
            current_url_parts=urlsplit(current_link_target)
            if current_url_parts.scheme or not current_url_parts.path:continue
            current_target_path=(current_document_path.parent/unquote(current_url_parts.path)).resolve()
            if current_target_path.is_relative_to(current_document_root):current_link_paths.append(current_target_path.relative_to(current_document_root).as_posix())
        current_document_entries[current_relative_path]={'path':current_relative_path,'hash':calculate_content_hash(current_source_bytes),'title':current_title_match.group(1) if current_title_match else current_document_path.stem,'text':current_source_text,'links':sorted(set(current_link_paths)),'writable':allow_document_write(current_config_values,current_relative_path),'incoming':0}
    if not current_document_entries:raise ValueError('학습할 Markdown·YAML 문서가 없습니다.')
    for current_document_entry in current_document_entries.values():
        for current_link_path in current_document_entry['links']:
            if current_link_path in current_document_entries:current_document_entries[current_link_path]['incoming']+=1
    return current_document_entries

def chunk_document_blocks(current_document_entry):
    """문단을 보존하고 긴 블록은 검색 청크만 분리한다. 삭제 후보는 일반 산문만 허용한다."""
    current_source_text=current_document_entry['text']
    current_block_ranges=[]
    current_block_start=0
    current_line_offset=0
    current_fence_marker=None
    for current_line_text in current_source_text.splitlines(keepends=True):
        current_fence_match=re.match(r'^\s*(`{3,}|~{3,})',current_line_text)
        if current_fence_match:
            if current_fence_marker is None:current_fence_marker=current_fence_match.group(1)[0]
            elif current_fence_match.group(1)[0]==current_fence_marker:current_fence_marker=None
        current_line_offset+=len(current_line_text)
        if not current_line_text.strip() and current_fence_marker is None:
            if current_source_text[current_block_start:current_line_offset].strip():current_block_ranges.append((current_block_start,current_line_offset))
            current_block_start=current_line_offset
    if current_source_text[current_block_start:].strip():current_block_ranges.append((current_block_start,len(current_source_text)))
    current_chunk_entries=[]
    current_heading_text=current_document_entry['title']
    for current_start_offset,current_end_offset in current_block_ranges:
        current_block_text=current_source_text[current_start_offset:current_end_offset]
        current_heading_match=re.match(r'^#{1,6} +(.+)',current_block_text)
        if current_heading_match:current_heading_text=current_heading_match.group(1)
        current_removable_flag=(current_document_entry['writable'] and MINIMUM_DUPLICATE_CHARACTERS<=len(current_block_text.strip())<=MAXIMUM_CHUNK_CHARACTERS and not re.search(r'^\s*(?:[#>|`~]|[-*+] |\d+[.)] )',current_block_text,re.M) and not re.search(r'확정|승인|SSOT|채택|상태:',current_heading_text+'\n'+current_block_text) and not DOCUMENT_LINK_PATTERN.search(current_block_text))
        for current_chunk_start in range(current_start_offset,current_end_offset,MAXIMUM_CHUNK_CHARACTERS):
            current_chunk_end=min(current_end_offset,current_chunk_start+MAXIMUM_CHUNK_CHARACTERS)
            current_chunk_text=current_source_text[current_chunk_start:current_chunk_end]
            current_chunk_identifier=sha256((current_document_entry['path']+':'+str(current_chunk_start)+':'+current_chunk_text).encode()).hexdigest()[:24]
            current_chunk_entries.append({'id':current_chunk_identifier,'path':current_document_entry['path'],'heading':current_heading_text,'start':current_chunk_start,'end':current_chunk_end,'text':current_chunk_text,'removable':current_removable_flag,'incoming':current_document_entry['incoming']})
    return current_chunk_entries

def snapshot_document_hashes(current_document_entries):
    return {current_path_text:current_document_entry['hash'] for current_path_text,current_document_entry in current_document_entries.items()}
