"""등록된 제작 자산과 고정 프롬프트를 검증하고 실행 입력으로 고정한다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import math
import hashlib
import json
import yaml

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
ANIMATION_CONFIG_PATH = WORKFLOW_ROOT_DIRECTORY/'generators/animation/config/character_animation.yaml'
SUPPORTED_FRAME_STEPS = (1,2,4,8)
DIRECTION_PROMPT_LABELS = {'down_left':'forward-left, showing the front-left view','down_right':'forward-right, showing the front-right view','up_left':'back-left','up_right':'back-right'}
SUPPORTED_DIRECTION_NAMES = ('down_left','down_right','up_left','up_right')

def select_target_fps_frames(source_frame_count, source_frame_rate, target_frame_rate, generation_speed_ratio=1):
    if type(generation_speed_ratio) not in (int,float) or generation_speed_ratio not in (1,1.5,2,4):
        raise ValueError('생성 배속은 1·1.5·2·4 중 하나여야 합니다.')
    if type(target_frame_rate) is not int or target_frame_rate < 1 or target_frame_rate > source_frame_rate:
        raise ValueError(f'타겟 FPS는 1부터 원본 FPS({source_frame_rate})까지의 정수여야 합니다.')
    return [math.floor(frame_index_value * source_frame_rate * generation_speed_ratio / target_frame_rate) + 1
            for frame_index_value in range(math.ceil(source_frame_count * target_frame_rate / (source_frame_rate * generation_speed_ratio)))]

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
    if set(animation_config_record['prompts']) != {'base','auxiliary','auxiliary_rear'}:
        raise ValueError('기본·전방 보조·후방 보조 프롬프트 설정 필요')
    for animation_motion_record in animation_config_record['motions'].values():
        if set(animation_motion_record) != {'label','root','manifest','openpose','anny','target_fps'}:
            raise ValueError('모션 등록 형식 오류')
        if type(animation_motion_record['target_fps']) is not int or animation_motion_record['target_fps'] < 1:
            raise ValueError('기본 타겟 FPS 오류')
    for animation_character_record in animation_config_record['characters'].values():
        if set(animation_character_record) != {'label','root','manifest'}:
            raise ValueError('캐릭터 등록 형식 오류')
    return animation_config_record

def read_fixed_prompts(animation_config_record):
    fixed_prompt_values = {prompt_role_name:resolve_asset_path(prompt_file_name).read_text().strip() for prompt_role_name,prompt_file_name in animation_config_record['prompts'].items()}
    if not all(fixed_prompt_values.values()) or any(len((fixed_prompt_values['base']+' '+fixed_prompt_values[prompt_role_name]).split()) >= 100 for prompt_role_name in ('auxiliary','auxiliary_rear')):
        raise ValueError('고정 프롬프트는 비어 있지 않고 합계 100단어 미만이어야 합니다.')
    return fixed_prompt_values

def collect_catalog_asset_records(animation_config_record):
    """현재 사용할 수 있는 등록 자산과 제외 사유를 분리한다."""
    available_motion_records = []
    available_character_records = []
    unavailable_asset_records = []
    for motion_identifier_value, motion_config_record in animation_config_record['motions'].items():
        try:
            motion_manifest_path = resolve_asset_path(motion_config_record['root']+'/'+motion_config_record['manifest'])
            motion_manifest_record = read_asset_mapping(motion_manifest_path)
            if type(motion_manifest_record.get('frames')) is not int or motion_manifest_record['frames'] < 1 or type(motion_manifest_record.get('fps')) is not int or motion_manifest_record['fps'] < 1:
                raise ValueError('모션 manifest의 frames·fps 값이 올바르지 않습니다.')
        except (OSError, ValueError, yaml.YAMLError) as asset_error_value:
            unavailable_asset_records.append({'kind':'motion','id':motion_identifier_value,'label':motion_config_record['label'],'reason':str(asset_error_value)})
            continue
        available_motion_records.append({'id':motion_identifier_value,'label':motion_config_record['label'],'frames':motion_manifest_record['frames'],'fps':motion_manifest_record['fps'],'target_fps':motion_config_record['target_fps']})
    for character_identifier_value, character_config_record in animation_config_record['characters'].items():
        try:
            resolve_asset_path(character_config_record['root']+'/'+character_config_record['manifest'])
        except (OSError, ValueError, yaml.YAMLError) as asset_error_value:
            unavailable_asset_records.append({'kind':'character','id':character_identifier_value,'label':character_config_record['label'],'reason':str(asset_error_value)})
            continue
        available_character_records.append({'id':character_identifier_value,'label':character_config_record['label']})
    return available_motion_records, available_character_records, unavailable_asset_records

def build_animation_catalog():
    animation_config_record = load_animation_configuration()
    available_motion_records, available_character_records, unavailable_asset_records = collect_catalog_asset_records(animation_config_record)
    fixed_prompt_values = read_fixed_prompts(animation_config_record)
    return {'motions':available_motion_records,'characters':available_character_records,'unavailable_assets':unavailable_asset_records,'directions':list(SUPPORTED_DIRECTION_NAMES),'prompts':fixed_prompt_values,'direction_prompts':compose_direction_prompts(fixed_prompt_values)}

def prepare_animation_request(command_payload_value):
    if not {'motion','character','source','directions'} <= set(command_payload_value) or set(command_payload_value)-{'motion','character','source','directions','frame_step','target_fps','speed','steps','resolution','start_frame','end_frame'}:
        raise ValueError('motion·character·source·directions·start_frame·end_frame·target_fps·speed·steps·resolution·frame_step만 허용합니다. 프롬프트는 수정할 수 없습니다.')
    selected_output_resolution=command_payload_value.get('resolution',512)
    if type(selected_output_resolution) is not int or selected_output_resolution not in (512,768,1024,1280):raise ValueError('해상도는 512·768·1024·1280 중 선택하세요.')
    selected_inference_steps = command_payload_value.get('steps',4)
    if type(selected_inference_steps) is not int or selected_inference_steps not in (4,30):
        raise ValueError('생성 스텝은 4(Lightning) 또는 30이어야 합니다.')
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
    selected_frame_step = command_payload_value.get('frame_step',1)
    if type(selected_frame_step) is not int or selected_frame_step not in SUPPORTED_FRAME_STEPS:
        raise ValueError('프레임 간격은 1·2·4·8 중 하나여야 합니다.')
    animation_character_record = animation_config_record['characters'][command_payload_value['character']]
    motion_manifest_path = resolve_asset_path(animation_motion_record['root']+'/'+animation_motion_record['manifest'])
    character_manifest_path = resolve_asset_path(animation_character_record['root']+'/'+animation_character_record['manifest'])
    motion_manifest_record = read_asset_mapping(motion_manifest_path)
    character_manifest_record = read_asset_mapping(character_manifest_path)
    selected_start_frame = command_payload_value.get('start_frame',1)
    selected_end_frame = command_payload_value.get('end_frame',motion_manifest_record['frames'])
    if type(selected_start_frame) is not int or type(selected_end_frame) is not int or not 1 <= selected_start_frame <= selected_end_frame <= motion_manifest_record['frames']:
        raise ValueError(f"시작·종료 프레임은 1부터 {motion_manifest_record['frames']} 사이에서 시작값이 종료값보다 작거나 같아야 합니다.")
    if ('target_fps' in command_payload_value or 'speed' in command_payload_value) and 'frame_step' in command_payload_value:
        raise ValueError('타겟 FPS와 이전 프레임 간격은 함께 지정할 수 없습니다.')
    legacy_frame_sampling = 'frame_step' in command_payload_value
    selected_target_fps = command_payload_value.get('target_fps',animation_motion_record['target_fps'])
    selected_range_frame_count = selected_end_frame-selected_start_frame+1
    selected_frame_offsets = list(range(0,selected_range_frame_count,selected_frame_step)) if legacy_frame_sampling else [frame_number-1 for frame_number in select_target_fps_frames(selected_range_frame_count,motion_manifest_record['fps'],selected_target_fps,command_payload_value.get('speed',1))]
    selected_frame_numbers = [selected_start_frame+frame_offset for frame_offset in selected_frame_offsets]
    output_frame_rate = motion_manifest_record['fps'] if legacy_frame_sampling else selected_target_fps

    generation_frame_records = []
    for direction_name_value in selected_direction_names:
        character_file_path = resolve_asset_path(animation_character_record['root']+'/'+character_manifest_record['baseline_crops']['root']+'/'+direction_name_value+'.png')
        character_file_hash = hash_asset_file(character_file_path)
        if character_file_hash != character_manifest_record['baseline_crops']['files'][direction_name_value]:
            raise ValueError('캐릭터 레퍼런스 무결성 오류')
        for current_frame_number in selected_frame_numbers:
            pose_relative_path = animation_motion_record[command_payload_value['source']].format(direction=direction_name_value,frame=current_frame_number)
            pose_reference_path = resolve_asset_path(animation_motion_record['root']+'/'+pose_relative_path)
            pose_reference_hash = hash_asset_file(pose_reference_path)
            if pose_reference_hash != motion_manifest_record['files'][pose_relative_path]:
                raise ValueError(f'모션 프레임 무결성 오류: {pose_relative_path}')
            generation_frame_records.append({'direction':direction_name_value,'frame':current_frame_number,'character_path':str(character_file_path.relative_to(WORKFLOW_ROOT_DIRECTORY)),'character_sha256':character_file_hash,'pose_path':str(pose_reference_path.relative_to(WORKFLOW_ROOT_DIRECTORY)),'pose_sha256':pose_reference_hash})
    fixed_prompt_values = read_fixed_prompts(animation_config_record)
    combined_prompt_text = fixed_prompt_values['base']+'\n\n'+fixed_prompt_values['auxiliary']
    return {**command_payload_value,'resolution':selected_output_resolution,'speed':command_payload_value.get('speed',1),'frame_step':selected_frame_step,'start_frame':selected_start_frame,'end_frame':selected_end_frame,'source_frames_per_direction':motion_manifest_record['frames'],'selected_frame_numbers':selected_frame_numbers,'target_fps':None if legacy_frame_sampling else selected_target_fps,'source_fps':motion_manifest_record['fps'],'direction_prompts':compose_direction_prompts(fixed_prompt_values),'prompts':fixed_prompt_values,'prompt_sha256':hashlib.sha256(combined_prompt_text.encode()).hexdigest(),'prompt_words':len(combined_prompt_text.split()),'frames_per_direction':len(selected_frame_numbers),'fps':output_frame_rate,'motion_manifest_sha256':hash_asset_file(motion_manifest_path),'character_manifest_sha256':hash_asset_file(character_manifest_path),'frames':generation_frame_records,'sampling':('none' if selected_frame_step==1 else 'frame-step') if legacy_frame_sampling else 'target-fps','model':'Qwen/Qwen-Image-Edit-2511','steps':selected_inference_steps,'lightning':selected_inference_steps==4}

def resolve_motion_preview(selected_motion_name, selected_source_kind, selected_direction_name, selected_frame_number):
    """프롬프트·캐릭터·생성 이력 없이 등록 모션의 단일 프레임을 조회한다."""
    animation_config_record = load_animation_configuration()
    if selected_motion_name not in animation_config_record['motions'] or selected_source_kind not in ('openpose','anny') or selected_direction_name not in SUPPORTED_DIRECTION_NAMES:
        raise ValueError('등록되지 않은 모션·포즈 종류·방향입니다.')
    animation_motion_record = animation_config_record['motions'][selected_motion_name]
    motion_manifest_record = read_asset_mapping(resolve_asset_path(animation_motion_record['root']+'/'+animation_motion_record['manifest']))
    if type(selected_frame_number) is not int or not 1 <= selected_frame_number <= motion_manifest_record['frames']:
        raise ValueError('모션 프레임 범위를 벗어났습니다.')
    pose_relative_path = animation_motion_record[selected_source_kind].format(direction=selected_direction_name,frame=selected_frame_number)
    pose_reference_path = resolve_asset_path(animation_motion_record['root']+'/'+pose_relative_path)
    if hash_asset_file(pose_reference_path) != motion_manifest_record['files'][pose_relative_path]:
        raise ValueError('모션 프레임 무결성 오류')
    return pose_reference_path


def compose_direction_prompts(fixed_prompt_values):
    direction_prompt_records = {}
    for direction_name_value, direction_label_text in DIRECTION_PROMPT_LABELS.items():
        auxiliary_prompt_role = 'auxiliary_rear' if direction_name_value in ('up_left','up_right') else 'auxiliary'
        auxiliary_prompt_text = fixed_prompt_values[auxiliary_prompt_role].format(direction=direction_label_text)
        combined_prompt_text = fixed_prompt_values['base']+'\n\n'+auxiliary_prompt_text
        if len(combined_prompt_text.split()) >= 100:
            raise ValueError('방향별 프롬프트는 100단어 미만이어야 합니다.')
        direction_prompt_records[direction_name_value] = {'auxiliary':auxiliary_prompt_text,'text':combined_prompt_text,'sha256':hashlib.sha256(combined_prompt_text.encode()).hexdigest(),'words':len(combined_prompt_text.split())}
    return direction_prompt_records
