"""Kimodo 입력과 예제 카탈로그의 공통 검증."""
import base64
from pathlib import Path

import yaml

from .contracts import KIMODO_CONFIG_ROOT, KIMODO_DEFAULT_SETTINGS, UniqueConfigLoader, validate_kimodo_request


def load_proportion_examples():
    current_workspace_root=Path(__file__).resolve().parents[2]
    current_config_record=yaml.load((KIMODO_CONFIG_ROOT/'proportion-examples.yaml').read_text(),Loader=UniqueConfigLoader)
    if not isinstance(current_config_record,dict) or set(current_config_record)!={'schema_version','examples'} or current_config_record['schema_version']!=1 or not isinstance(current_config_record['examples'],list):
        raise ValueError('신체 비율 예제 목록 계약 오류')
    current_example_mapping={}
    for current_example_record in current_config_record['examples']:
        if not isinstance(current_example_record,dict) or set(current_example_record)!={'id','label','images'} or any(not isinstance(current_example_record[current_field_name],str) or not current_example_record[current_field_name].strip() for current_field_name in ('id','label')):
            raise ValueError('신체 비율 예제 필드 오류')
        if current_example_record['id'] in current_example_mapping:
            raise ValueError('신체 비율 예제 ID 중복')
        current_image_paths=current_example_record['images']
        if not isinstance(current_image_paths,list) or not 1<=len(current_image_paths)<=8:
            raise ValueError('신체 비율 예제는 이미지 1~8장이 필요합니다.')
        current_resolved_paths=[]
        for current_image_path in current_image_paths:
            if not isinstance(current_image_path,str):
                raise ValueError('신체 비율 예제 경로는 문자열이어야 합니다.')
            current_resolved_path=(current_workspace_root/current_image_path).resolve()
            if not any(current_resolved_path.is_relative_to(current_workspace_root/current_allowed_directory) for current_allowed_directory in ('assets','baseline')) or not current_resolved_path.is_file():
                raise ValueError(f'신체 비율 예제 이미지 경로 오류: {current_image_path}')
            current_resolved_paths.append(str(current_resolved_path))
        current_example_mapping[current_example_record['id']]={'label':current_example_record['label'],'images':current_resolved_paths}
    return current_example_mapping


def build_kimodo_payload(current_prompt_text,current_frame_count,current_step_count,current_seed_value,current_guidance_value,current_heading_value,current_postprocessing_value,current_direction_names=None,current_horizontal_removal=False,current_proportions_enabled=False,current_reference_paths=None,current_scale_percent=KIMODO_DEFAULT_SETTINGS['openpose_scale_percent'],current_include_hands=False,current_include_face=False,current_segment_text="",current_endpoint_identifier=None,current_keyframe_rows=None,current_elevation_angle=0,current_multiview_text='',current_reviewed_bundle=None,current_projected_hip=False,current_face_calibration=None):
    for current_integer_value in (current_frame_count,current_step_count,current_seed_value):
        if type(current_integer_value) not in (int,float) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·스텝·시드는 정수로 입력하세요.')
    current_request_record = {'pose_include_hands':current_include_hands,'pose_include_face':current_include_face,'openpose_scale_percent':current_scale_percent,'remove_horizontal_motion':current_horizontal_removal,'action':'generate','prompt':current_prompt_text,'frames':int(current_frame_count),'steps':int(current_step_count),'seed':int(current_seed_value),'guidance_scale':current_guidance_value,'heading_degrees':current_heading_value,'post_processing':current_postprocessing_value,'directions':list(KIMODO_DEFAULT_SETTINGS['directions']) if current_direction_names is None else current_direction_names}
    if current_elevation_angle != 0:
        current_request_record['camera_elevation_degrees']=current_elevation_angle
    if current_endpoint_identifier:
        current_request_record['endpoint_pose_id']=current_endpoint_identifier
    if current_keyframe_rows:
        current_request_record['keyframes'] = [{'id':current_row_value[0],'frame':current_row_value[1]} for current_row_value in current_keyframe_rows]
    if current_segment_text.strip():
        current_frame_tokens=current_segment_text.split()
        if any(not current_frame_token.isdigit() for current_frame_token in current_frame_tokens):
            raise ValueError('구간 프레임은 공백으로 구분한 정수로 입력하세요.')
        current_request_record['segment_frames']=[int(current_frame_token) for current_frame_token in current_frame_tokens]
    if current_reference_paths and not current_proportions_enabled:
        raise ValueError('신체 비율 참조 이미지가 있지만 비율 적용이 꺼져 있습니다. 적용을 켜거나 참조 이미지를 제거하세요. 참조를 무시한 채 생성하지 않습니다.')
    if current_proportions_enabled:
        if not current_reference_paths:
            raise ValueError('신체 비율 맞춤을 켰다면 참조 이미지를 첨부하세요.')
        current_request_record['proportion_images']=[base64.b64encode(Path(current_reference_path).read_bytes()).decode() for current_reference_path in current_reference_paths]
    if current_multiview_text.strip():
        try:
            current_request_record['proportion_multiview_angles']=[float(current_angle_value) for current_angle_value in current_multiview_text.split()]
        except ValueError as current_input_error:
            raise ValueError('다중 시점 각도는 공백으로 구분한 숫자 8개가 필요합니다.') from current_input_error
    if current_reviewed_bundle is not None:
        current_request_record['proportion_reviewed_multiview']=current_reviewed_bundle
    if type(current_projected_hip) is not bool:
        raise ValueError('3D 투영 골반 시험 여부는 참/거짓이어야 합니다.')
    if current_projected_hip:
        current_request_record['proportion_projected_hip']=True
    if current_face_calibration is not None:
        current_request_record['proportion_face_anchor_calibration']=current_face_calibration
    current_validated_request=validate_kimodo_request(current_request_record)
    if current_proportions_enabled:
        current_request_record['proportion_images']=current_validated_request['images']
    return current_request_record


def load_kimodo_examples():
    current_example_record = yaml.load((KIMODO_CONFIG_ROOT/'prompt-examples.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_example_record,dict) or set(current_example_record)!={'schema_version','examples'} or current_example_record['schema_version']!=1 or not isinstance(current_example_record['examples'],list) or not current_example_record['examples']:
        raise ValueError('Kimodo 프롬프트 예시 계약 오류')
    current_example_mapping = {}
    for current_example_value in current_example_record['examples']:
        if not isinstance(current_example_value,dict) or set(current_example_value)-{'reference_example'} not in ({'id','label','prompt','frames'},{'id','label','prompt','frames','settings'}) or any(not isinstance(current_example_value[current_field_name],str) or not current_example_value[current_field_name].strip() for current_field_name in ('id','label','prompt')):
            raise ValueError('Kimodo 예시 필드 오류')
        if current_example_value['id'] in current_example_mapping:
            raise ValueError('Kimodo 예시 ID 중복')
        build_kimodo_payload(current_example_value['prompt'],current_example_value['frames'],KIMODO_DEFAULT_SETTINGS['steps'],KIMODO_DEFAULT_SETTINGS['seed'],KIMODO_DEFAULT_SETTINGS['guidance_scale'],KIMODO_DEFAULT_SETTINGS['heading_degrees'],KIMODO_DEFAULT_SETTINGS['post_processing'])
        if 'settings' in current_example_value:
            current_settings_record = current_example_value['settings']
            if not isinstance(current_settings_record,dict) or set(current_settings_record)-{'segment_frames','openpose_scale_percent','pose_include_hands','pose_include_face','keyframes','camera_elevation_degrees'}!={'steps','seed','guidance_scale','heading_degrees','post_processing','directions','remove_horizontal_motion'}:
                raise ValueError('Kimodo 예시 설정 필드 오류')
            validate_kimodo_request({'action':'generate','prompt':current_example_value['prompt'],'frames':current_example_value['frames'],**current_settings_record})
        if 'reference_example' in current_example_value and current_example_value['reference_example'] not in load_proportion_examples():
            raise ValueError('등록되지 않은 신체 비율 참조 예제')
        current_example_mapping[current_example_value['id']] = current_example_value
    return current_example_mapping
