"""등록된 제작 자산과 고정 프롬프트를 검증하고 실행 입력으로 고정한다."""
from pathlib import Path
import hashlib
import json
import yaml

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
ANIMATION_CONFIG_PATH = WORKFLOW_ROOT_DIRECTORY/'generators/animation/config/character_animation.yaml'
SUPPORTED_DIRECTION_NAMES = ('down_left','down_right','up_left','up_right')

class UniqueMappingLoader(yaml.SafeLoader):
    pass

def construct_unique_mapping(mapping_yaml_loader, mapping_yaml_node):
    mapping_field_values = {}
    for mapping_key_node, mapping_value_node in mapping_yaml_node.value:
        mapping_field_name = mapping_yaml_loader.construct_object(mapping_key_node)
        if mapping_field_name in mapping_field_values:
            raise ValueError('중복 설정 필드')
        mapping_field_values[mapping_field_name] = mapping_yaml_loader.construct_object(mapping_value_node)
    return mapping_field_values

UniqueMappingLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)

def read_asset_mapping(asset_record_path):
    return yaml.load(asset_record_path.read_text(), Loader=UniqueMappingLoader)

def resolve_asset_path(relative_asset_path):
    resolved_asset_path = (WORKFLOW_ROOT_DIRECTORY/relative_asset_path).resolve()
    if not resolved_asset_path.is_relative_to(WORKFLOW_ROOT_DIRECTORY) or not resolved_asset_path.is_file():
        raise ValueError(f'등록 파일을 찾을 수 없습니다: {relative_asset_path}')
    return resolved_asset_path

def hash_asset_file(asset_file_path):
    return hashlib.sha256(asset_file_path.read_bytes()).hexdigest()

def load_animation_configuration():
    animation_config_record = read_asset_mapping(ANIMATION_CONFIG_PATH)
    if set(animation_config_record) != {'schema_version','prompts','motions','characters'} or animation_config_record['schema_version'] != 1:
        raise ValueError('애니메이션 설정 형식 오류')
    if set(animation_config_record['prompts']) != {'base','auxiliary'}:
        raise ValueError('기본·보조 프롬프트 설정 필요')
    for animation_motion_record in animation_config_record['motions'].values():
        if set(animation_motion_record) != {'label','root','manifest','openpose','anny'}:
            raise ValueError('모션 등록 형식 오류')
    for animation_character_record in animation_config_record['characters'].values():
        if set(animation_character_record) != {'label','root','manifest'}:
            raise ValueError('캐릭터 등록 형식 오류')
    return animation_config_record

def read_fixed_prompts(animation_config_record):
    fixed_prompt_values = {prompt_role_name:resolve_asset_path(prompt_file_name).read_text().strip() for prompt_role_name,prompt_file_name in animation_config_record['prompts'].items()}
    if not all(fixed_prompt_values.values()) or len(' '.join(fixed_prompt_values.values()).split()) >= 100:
        raise ValueError('고정 프롬프트는 비어 있지 않고 합계 100단어 미만이어야 합니다.')
    return fixed_prompt_values

def build_animation_catalog():
    animation_config_record = load_animation_configuration()
    animation_motion_records = []
    for animation_motion_identifier, animation_motion_record in animation_config_record['motions'].items():
        motion_manifest_record = read_asset_mapping(resolve_asset_path(animation_motion_record['root']+'/'+animation_motion_record['manifest']))
        animation_motion_records.append({'id':animation_motion_identifier,'label':animation_motion_record['label'],'frames':motion_manifest_record['frames'],'fps':motion_manifest_record['fps']})
    return {'motions':animation_motion_records,'characters':[{'id':animation_character_identifier,'label':animation_character_record['label']} for animation_character_identifier,animation_character_record in animation_config_record['characters'].items()], 'directions':list(SUPPORTED_DIRECTION_NAMES),'prompts':read_fixed_prompts(animation_config_record)}

def prepare_animation_request(command_payload_value):
    if set(command_payload_value) != {'motion','character','source','directions'}:
        raise ValueError('motion·character·source·directions만 허용합니다. 프롬프트는 수정할 수 없습니다.')
    animation_config_record = load_animation_configuration()
    for selection_field_name, selection_group_name in (('motion','motions'),('character','characters')):
        if not isinstance(command_payload_value[selection_field_name],str) or command_payload_value[selection_field_name] not in animation_config_record[selection_group_name]:
            raise ValueError(f'등록되지 않은 {selection_field_name}')
    selected_direction_names = command_payload_value['directions']
    if not isinstance(selected_direction_names,list) or not selected_direction_names or any(not isinstance(direction_name_value,str) or direction_name_value not in SUPPORTED_DIRECTION_NAMES for direction_name_value in selected_direction_names) or len(set(selected_direction_names)) != len(selected_direction_names):
        raise ValueError('중복 없이 하나 이상의 방향을 선택하세요.')
    if command_payload_value['source'] not in ('openpose','anny'):
        raise ValueError('포즈 입력은 openpose 또는 anny입니다.')
    animation_motion_record = animation_config_record['motions'][command_payload_value['motion']]
    animation_character_record = animation_config_record['characters'][command_payload_value['character']]
    motion_manifest_path = resolve_asset_path(animation_motion_record['root']+'/'+animation_motion_record['manifest'])
    character_manifest_path = resolve_asset_path(animation_character_record['root']+'/'+animation_character_record['manifest'])
    motion_manifest_record = read_asset_mapping(motion_manifest_path)
    character_manifest_record = read_asset_mapping(character_manifest_path)
    generation_frame_records = []
    for direction_name_value in selected_direction_names:
        character_file_path = resolve_asset_path(animation_character_record['root']+'/'+character_manifest_record['baseline_crops']['root']+'/'+direction_name_value+'.png')
        character_file_hash = hash_asset_file(character_file_path)
        if character_file_hash != character_manifest_record['baseline_crops']['files'][direction_name_value]:
            raise ValueError('캐릭터 레퍼런스 무결성 오류')
        for current_frame_number in range(1,motion_manifest_record['frames']+1):
            pose_relative_path = animation_motion_record[command_payload_value['source']].format(direction=direction_name_value,frame=current_frame_number)
            pose_reference_path = resolve_asset_path(animation_motion_record['root']+'/'+pose_relative_path)
            pose_reference_hash = hash_asset_file(pose_reference_path)
            if pose_reference_hash != motion_manifest_record['files'][pose_relative_path]:
                raise ValueError(f'모션 프레임 무결성 오류: {pose_relative_path}')
            generation_frame_records.append({'direction':direction_name_value,'frame':current_frame_number,'character_path':str(character_file_path.relative_to(WORKFLOW_ROOT_DIRECTORY)),'character_sha256':character_file_hash,'pose_path':str(pose_reference_path.relative_to(WORKFLOW_ROOT_DIRECTORY)),'pose_sha256':pose_reference_hash})
    fixed_prompt_values = read_fixed_prompts(animation_config_record)
    combined_prompt_text = '\n\n'.join(fixed_prompt_values.values())
    return {**command_payload_value,'prompts':fixed_prompt_values,'prompt_sha256':hashlib.sha256(combined_prompt_text.encode()).hexdigest(),'prompt_words':len(combined_prompt_text.split()),'frames_per_direction':motion_manifest_record['frames'],'fps':motion_manifest_record['fps'],'motion_manifest_sha256':hash_asset_file(motion_manifest_path),'character_manifest_sha256':hash_asset_file(character_manifest_path),'frames':generation_frame_records,'sampling':'none','model':'Qwen/Qwen-Image-Edit-2511','steps':4}
