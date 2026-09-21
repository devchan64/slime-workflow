"""세계관·시스템 설계 두 도서의 원본 루트 폴더를 관리한다."""
from pathlib import Path
from jsonschema import Draft202012Validator
from .documents import load_yaml_document,save_yaml_document,resolve_document_path,lock_document_workspace

DOCUMENT_COLLECTION_NAMES={'world':'세계관','system-design':'시스템 설계'}
DEFAULT_COLLECTION_ROOTS={'world':['world'],'system-design':['gameplay','backend','frontend','ssot','workflow']}
COLLECTION_ROOTS_SCHEMA={'type':'array','maxItems':50,'uniqueItems':True,'items':{'type':'string','minLength':1,'maxLength':300}}
COLLECTION_SETTINGS_SCHEMA={'type':'object','additionalProperties':False,'required':['schema_version','collection_roots'],'properties':{'schema_version':{'const':1},'collection_roots':{'type':'object','additionalProperties':False,'required':list(DOCUMENT_COLLECTION_NAMES),'properties':{current_collection_id:COLLECTION_ROOTS_SCHEMA for current_collection_id in DOCUMENT_COLLECTION_NAMES}}}}
COLLECTION_UPDATE_SCHEMA={'type':'object','additionalProperties':False,'required':['collection_id','source_directory_paths'],'properties':{'collection_id':{'enum':list(DOCUMENT_COLLECTION_NAMES)},'source_directory_paths':COLLECTION_ROOTS_SCHEMA}}


def validate_collection_roots(current_config_values,current_settings_values):
    Draft202012Validator(COLLECTION_SETTINGS_SCHEMA).validate(current_settings_values)
    current_source_root=Path(current_config_values['source_document_root'])
    current_private_root=Path(current_config_values['private_state_root'])
    current_seen_roots=[]
    for current_collection_id,current_directory_paths in current_settings_values['collection_roots'].items():
        for current_directory_path in current_directory_paths:
            if current_directory_path=='.' or Path(current_directory_path).as_posix()!=current_directory_path:
                raise ValueError('문서 루트 아래의 폴더를 지정하세요. 전체 루트는 등록할 수 없습니다.')
            current_target_path=resolve_document_path(current_source_root,current_directory_path)
            if not current_target_path.is_dir() or current_target_path.resolve().is_relative_to(current_private_root):
                raise ValueError('등록할 수 없는 원본 폴더: '+current_directory_path)
            for previous_collection_id,previous_directory_path in current_seen_roots:
                if current_directory_path.startswith(previous_directory_path+'/') or previous_directory_path.startswith(current_directory_path+'/') or current_directory_path==previous_directory_path:
                    raise ValueError('이미 포함된 폴더와 범위가 겹칩니다: '+previous_collection_id+'/'+previous_directory_path)
            current_seen_roots.append((current_collection_id,current_directory_path))


def load_document_collections(current_config_values):
    current_settings_path=Path(current_config_values['private_state_root'])/'document-collections.yaml'
    if current_settings_path.exists():
        current_settings_values=load_yaml_document(current_settings_path)
    else:
        current_settings_values={'schema_version':1,'collection_roots':{current_collection_id:[current_directory_path for current_directory_path in current_default_paths if (Path(current_config_values['source_document_root'])/current_directory_path).is_dir()] for current_collection_id,current_default_paths in DEFAULT_COLLECTION_ROOTS.items()}}
    validate_collection_roots(current_config_values,current_settings_values)
    return [{'collection_id':current_collection_id,'book_title_text':current_collection_title,'source_directory_paths':current_settings_values['collection_roots'][current_collection_id]} for current_collection_id,current_collection_title in DOCUMENT_COLLECTION_NAMES.items()]


def update_document_collection(current_config_values,current_request_values):
    Draft202012Validator(COLLECTION_UPDATE_SCHEMA).validate(current_request_values)
    with lock_document_workspace(Path(current_config_values['private_state_root'])):
        current_collection_entries=load_document_collections(current_config_values)
        current_settings_values={'schema_version':1,'collection_roots':{current_collection_entry['collection_id']:current_collection_entry['source_directory_paths'] for current_collection_entry in current_collection_entries}}
        current_settings_values['collection_roots'][current_request_values['collection_id']]=current_request_values['source_directory_paths']
        validate_collection_roots(current_config_values,current_settings_values)
        save_yaml_document(Path(current_config_values['private_state_root'])/'document-collections.yaml',current_settings_values)
    return {'collection_entries':load_document_collections(current_config_values)}


def resolve_collection_request(current_config_values,current_request_values):
    current_collection_id=current_request_values.get('collection_id')
    current_collection_entry=next((current_collection_entry for current_collection_entry in load_document_collections(current_config_values) if current_collection_entry['collection_id']==current_collection_id),None)
    if current_collection_entry is None:
        raise ValueError('세계관 또는 시스템 설계 도서를 선택하세요.')
    if not current_collection_entry['source_directory_paths']:
        raise ValueError('이 도서에는 루트 폴더가 없습니다. 루트 폴더 설정에서 추가하세요.')
    if current_request_values['source_directory_paths']!=current_collection_entry['source_directory_paths']:
        raise ValueError('도서의 루트 폴더가 변경되었습니다. 문서를 다시 불러오세요.')
    if 'book_title_text' in current_request_values and current_request_values['book_title_text']!=current_collection_entry['book_title_text']:
        raise ValueError('도서 제목은 세계관 또는 시스템 설계로 고정됩니다.')
    return current_collection_entry
