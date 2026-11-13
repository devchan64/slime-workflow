"""Kimodo NF4 실험 폼. 실행과 기록 수명은 공용 게이트웨이가 담당한다."""
import json
import gradio as gr
import yaml
import base64
import hashlib
import tempfile
from pathlib import Path
from tools.review.common.gradio_input_preview import build_input_preview
from generators.kimodo.contracts import KIMODO_JOB_STORAGE, KIMODO_MAXIMUM_SEED_VALUE
from generators.kimodo.contracts import KIMODO_CONFIG_ROOT, UniqueConfigLoader, KIMODO_DIRECTION_RECORDS
from tools.review.common.gradio_identifiers import build_generation_identifier
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS,normalize_kimodo_prompt,validate_kimodo_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor,render_video_generation_result
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


KIMODO_INPUT_MINIMUM_WIDTH = 320
KIMODO_POSE_PREVIEW_WIDTH = 240
KIMODO_POSE_PREVIEW_HEIGHT = 160


def load_reference_joint_editor(current_result_path,current_reference_paths):
    """완료된 참조 분석의 관절 원본과 이미지의 일치를 확인한다."""
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    if not current_result_path or not current_reference_paths:
        raise ValueError('참조 이미지와 검출 결과 JSON을 먼저 선택하세요.')
    current_result_record=json.loads(Path(current_result_path).read_text())
    current_hash_records=current_result_record.get('reference_image_sha256')
    if not isinstance(current_hash_records,list) or len(current_hash_records)!=len(current_reference_paths):
        raise ValueError('이미지 해시가 포함된 참조 검출 결과가 필요합니다. 최신 결과를 사용하세요.')
    for current_reference_path,current_expected_hash in zip(current_reference_paths,current_hash_records):
        current_image_bytes=decode_reference_image(base64.b64encode(Path(current_reference_path).read_bytes()).decode(),composite_transparent_background=True)
        if hashlib.sha256(current_image_bytes).hexdigest()!=current_expected_hash:
            raise ValueError('검출 결과와 참조 이미지가 일치하지 않습니다.')
    current_source_records=current_result_record['observation_sources']
    current_original_points=current_result_record.get('original_keypoints',current_result_record['keypoints'])
    if len(current_source_records)!=len(current_original_points):
        raise ValueError('참조 관절 검출 결과 형식 오류')
    current_editor_rows=[]
    for current_source_record,current_body_points,current_effective_points in zip(current_source_records,current_original_points,current_result_record['keypoints']):
        if len(current_body_points)!=18: raise ValueError('참조 관절 수 오류')
        for current_joint_index,current_point_record in enumerate(current_body_points):
            current_editor_rows.append([current_source_record['image'],current_source_record['person'],current_joint_index,current_point_record[0],current_point_record[1],current_effective_points[current_joint_index][0],current_effective_points[current_joint_index][1]])
    from PIL import Image,ImageDraw,ImageOps
    with Image.open(current_reference_paths[0]) as current_reference_image:
        current_preview_image=ImageOps.exif_transpose(current_reference_image).convert('RGB')
        current_preview_image.thumbnail((1536,1536))
    current_preview_draw=ImageDraw.Draw(current_preview_image)
    for current_source_record,current_body_points in zip(current_source_records,current_original_points):
        if current_source_record['image']!=1: continue
        for current_joint_index in (2,3,5,6):
            current_point_record=current_body_points[current_joint_index]
            current_x_value,current_y_value=current_point_record[:2]
            current_preview_draw.ellipse((current_x_value-4,current_y_value-4,current_x_value+4,current_y_value+4),fill='red',outline='white',width=1)
            current_preview_draw.text((current_x_value+5,current_y_value-8),f"{current_source_record['person']}:{current_joint_index}",fill='yellow',stroke_width=1,stroke_fill='black')
    return current_editor_rows,{'rows':current_editor_rows,'hashes':current_hash_records},f'관측 {len(current_source_records)}개를 불러왔습니다. 수정 X·Y를 입력하세요.',current_preview_image


def build_reference_joint_edit_payload(current_editor_rows,current_editor_state):
    if current_editor_state is None:
        return []
    if not isinstance(current_editor_rows,list) or len(current_editor_rows)!=len(current_editor_state['rows']):
        raise ValueError('관절 목록의 행을 추가하거나 삭제할 수 없습니다.')
    current_edit_records=[]
    for current_editor_row,current_original_row in zip(current_editor_rows,current_editor_state['rows']):
        if len(current_editor_row)!=7 or list(current_editor_row[:5])!=list(current_original_row[:5]):
            raise ValueError('관절 대상과 원본 좌표는 변경할 수 없습니다.')
        if list(current_editor_row[5:7])!=list(current_original_row[3:5]):
            current_image_index,current_person_index,current_joint_index=current_original_row[:3]
            current_edit_records.append({'image':current_image_index,'person':current_person_index,'joint':current_joint_index,'original':current_original_row[3:5],'edited':current_editor_row[5:7],'image_sha256':current_editor_state['hashes'][current_image_index-1]})
    return current_edit_records

def select_multiview_review_rows(current_review_record,current_observation_number):
    """선택한 방향의 관절별 가중치와 두 종류의 오차를 표시한다."""
    if current_review_record is None:
        return []
    if type(current_observation_number) is not int or not 1 <= current_observation_number <= 8:
        raise ValueError('검수할 관측 번호를 선택하세요.')
    current_view_record=current_review_record['views'][current_observation_number-1]
    current_rows=[]
    for current_joint_record in sorted(current_view_record['joints'],key=lambda current_row:current_row['joint']):
        current_heldout_record=current_joint_record['heldout']
        current_rows.append([str(current_joint_record['joint']),f"{current_joint_record['detector_score']:.3f}",f"{current_joint_record['declared_weight']:.3f}",f"{current_joint_record['effective_weight']:.3f}",current_joint_record['weight_reason'],f"{current_joint_record['fitted_error_px']:.2f}" if current_joint_record['fitted_error_px'] is not None else '제외',f"{current_heldout_record['error_px']:.2f}" if current_heldout_record and current_heldout_record.get('error_px') is not None else '미검증'])
    return current_rows


def load_multiview_review_files(current_reference_path,current_skeleton_path,current_image_path,current_heldout_path,current_observation_number):
    """같은 출처의 관절·3D·이미지만 8방향 겹침 검수로 불러온다."""
    from PIL import Image
    from generators.kimodo.multiview_review_report import build_multiview_review_report,render_multiview_review_overlay
    if not current_reference_path or not current_skeleton_path or not current_image_path:
        raise ValueError('참조 관절 JSON, 3D 골격 JSON, 참조 이미지를 모두 선택하세요.')
    current_reference=json.loads(Path(current_reference_path).read_text())
    current_skeleton=json.loads(Path(current_skeleton_path).read_text())
    current_heldout=json.loads(Path(current_heldout_path).read_text()) if current_heldout_path else None
    current_report=build_multiview_review_report(current_reference,current_skeleton,current_heldout)
    current_image_bytes=Path(current_image_path).read_bytes()
    current_image_hash=hashlib.sha256(current_image_bytes).hexdigest()
    if current_skeleton.get('reference_image_sha256') != [current_image_hash]:
        raise ValueError('3D 골격의 참조 이미지 해시가 없거나 일치하지 않습니다.')
    with Image.open(current_image_path) as current_image:
        current_preview=render_multiview_review_overlay(current_image,current_report)
    current_report['review_binding_sha256']=calculate_review_source_binding(current_reference,current_skeleton,current_image_hash)
    current_notice='8방향 검수 기록을 불러왔습니다. 초록색: DWPose, 보라색: 3D 재투영. 적합 오차와 제외 관측 오차는 별개입니다.'
    if not current_heldout_path:
        current_notice+=' 제외 관측 기록을 선택하지 않아 미검증으로 표시합니다.'
    return current_report,current_preview,current_notice,select_multiview_review_rows(current_report,current_observation_number)


def calculate_review_source_binding(current_reference_record,current_skeleton_record,current_image_hash):
    """검수 중인 입력의 변경 여부를 확인한다."""
    current_bytes=json.dumps({'reference':current_reference_record,'skeleton':current_skeleton_record,'image_sha256':current_image_hash},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(current_bytes).hexdigest()


def build_reviewed_bundle_from_review(current_review_record,current_reference_path,current_skeleton_path,current_image_path,current_generation_references):
    """검수한 출처 그대로 생성 참조에 사용할 후보 묶음을 구성한다."""
    from generators.kimodo.multiview_reviewed_bundle import REVIEWED_BUNDLE_SCHEMA_VERSION,validate_reviewed_multiview_bundle
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    if current_review_record is None or not all((current_reference_path,current_skeleton_path,current_image_path,current_generation_references)):
        raise ValueError('8방향 검수 기록을 불러오고 생성 참조 이미지를 선택하세요.')
    current_reference=json.loads(Path(current_reference_path).read_text())
    current_skeleton=json.loads(Path(current_skeleton_path).read_text())
    current_image_hash=hashlib.sha256(Path(current_image_path).read_bytes()).hexdigest()
    if current_review_record.get('review_binding_sha256') != calculate_review_source_binding(current_reference,current_skeleton,current_image_hash):
        raise ValueError('검수 입력이 변경됐습니다. 8방향 검수를 다시 불러오세요.')
    current_hashes=[]
    for current_path in current_generation_references:
        current_png=decode_reference_image(base64.b64encode(Path(current_path).read_bytes()).decode(),composite_transparent_background=True)
        current_hashes.append(hashlib.sha256(current_png).hexdigest())
    return validate_reviewed_multiview_bundle({'schema':REVIEWED_BUNDLE_SCHEMA_VERSION,'reference_observations':current_reference,'skeleton':current_skeleton},current_hashes)


def handle_reviewed_bundle_from_review(current_review_record,current_reference_path,current_skeleton_path,current_image_path,current_generation_references):
    try:
        return build_reviewed_bundle_from_review(current_review_record,current_reference_path,current_skeleton_path,current_image_path,current_generation_references)
    except (ValueError,OSError,KeyError,TypeError) as current_error:
        raise gr.Error(str(current_error)) from current_error



def load_multiview_weight_editor(current_review_record,current_reference_path,current_skeleton_path,current_image_path):
    """검수 출처와 일치하는 8×18 판단 가중치를 편집 표로 만든다."""
    from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
    if current_review_record is None or not all((current_reference_path,current_skeleton_path,current_image_path)):
        raise gr.Error('먼저 같은 입력으로 8방향 검수를 불러오세요.')
    try:
        current_reference=json.loads(Path(current_reference_path).read_text())
        current_skeleton=json.loads(Path(current_skeleton_path).read_text())
        current_image_hash=hashlib.sha256(Path(current_image_path).read_bytes()).hexdigest()
        if current_review_record.get('review_binding_sha256')!=calculate_review_source_binding(current_reference,current_skeleton,current_image_hash):
            raise ValueError('검수 입력이 변경됐습니다. 8방향 검수를 다시 불러오세요.')
        current_table=current_skeleton['joint_weight_table']
        validate_multiview_joint_weights(current_table)
        current_rows=[[current_view['observation'],current_joint['joint'],current_joint['weight'],current_joint['reason']] for current_view in current_table['views'] for current_joint in current_view['joints']]
        return current_rows,{'binding':current_review_record['review_binding_sha256'],'targets':[[current_row[0],current_row[1]] for current_row in current_rows]},'8방향 × BODY18 관절 144개를 불러왔습니다. 수정 후 검증·파일 만들기를 누르세요.'
    except (ValueError,OSError,KeyError,TypeError) as current_error:
        raise gr.Error(str(current_error)) from current_error


def save_multiview_weight_editor(current_editor_rows,current_editor_state,current_review_record,current_reference_path,current_skeleton_path,current_image_path):
    """대상 순서를 보존하고 가중치·근거를 검증해 별도 JSON 파일을 만든다."""
    from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
    try:
        if not isinstance(current_editor_state,dict) or current_review_record is None or current_editor_state.get('binding')!=current_review_record.get('review_binding_sha256'):
            raise ValueError('검수 기록이 변경됐습니다. 가중치 표를 다시 불러오세요.')
        if not all((current_reference_path,current_skeleton_path,current_image_path)):
            raise ValueError('검수 입력을 다시 선택하세요.')
        current_reference=json.loads(Path(current_reference_path).read_text())
        current_skeleton=json.loads(Path(current_skeleton_path).read_text())
        current_image_hash=hashlib.sha256(Path(current_image_path).read_bytes()).hexdigest()
        if current_editor_state['binding']!=calculate_review_source_binding(current_reference,current_skeleton,current_image_hash):
            raise ValueError('검수 입력이 변경됐습니다. 가중치 표를 다시 불러오세요.')
        if hasattr(current_editor_rows,'tolist'):
            current_editor_rows=current_editor_rows.tolist()
        if not isinstance(current_editor_rows,list) or len(current_editor_rows)!=144:
            raise ValueError('8방향 × BODY18 관절 144개가 필요합니다.')
        current_views=[{'observation':current_view_index+1,'joints':[]} for current_view_index in range(8)]
        for current_index,current_row in enumerate(current_editor_rows):
            if not isinstance(current_row,(list,tuple)) or len(current_row)!=4 or list(current_row[:2])!=current_editor_state['targets'][current_index]:
                raise ValueError('관측 번호·관절 번호와 행 순서는 변경할 수 없습니다.')
            current_weight=current_row[2]
            if isinstance(current_weight,str):
                try:
                    current_weight=float(current_weight.strip())
                except ValueError as current_error:
                    raise ValueError('가중치는 0~1 숫자로 입력하세요.') from current_error
            if type(current_weight) not in (int,float):
                raise ValueError('가중치는 0~1 숫자로 입력하세요.')
            current_views[current_index//18]['joints'].append({'joint':current_index%18,'weight':current_weight,'reason':current_row[3]})
        current_table={'schema':'kimodo-body18-view-weights-v1','views':current_views}
        validate_multiview_joint_weights(current_table)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',prefix='kimodo-joint-weights-',suffix='.json',delete=False) as current_file:
            json.dump(current_table,current_file,ensure_ascii=False,indent=2,allow_nan=False)
        return current_file.name,'가중치 파일을 만들었습니다. 새 3D 추정과 검수 후에만 생성 참조로 선택할 수 있습니다.'
    except (ValueError,OSError,KeyError,TypeError) as current_error:
        raise gr.Error(str(current_error)) from current_error

def load_reviewed_multiview_bundle(current_bundle_path,current_reference_paths):
    """선택한 참조 이미지와 검수 골격의 출처를 확인한다."""
    from generators.kimodo.multiview_reviewed_bundle import REVIEWED_BUNDLE_MAXIMUM_BYTES,validate_reviewed_multiview_bundle
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    if not current_bundle_path or not current_reference_paths:
        raise ValueError('검수 골격 JSON과 참조 이미지를 먼저 선택하세요.')
    current_file_path=Path(current_bundle_path)
    if current_file_path.stat().st_size>REVIEWED_BUNDLE_MAXIMUM_BYTES:
        raise ValueError('검수 스켈레톤 묶음이 2MiB를 초과합니다.')
    current_bundle=json.loads(current_file_path.read_text())
    current_hashes=[]
    for current_path in current_reference_paths:
        current_png=decode_reference_image(base64.b64encode(Path(current_path).read_bytes()).decode(),composite_transparent_background=True)
        current_hashes.append(hashlib.sha256(current_png).hexdigest())
    return validate_reviewed_multiview_bundle(current_bundle,current_hashes)


def handle_reviewed_multiview_bundle(current_bundle_path,current_reference_paths):
    """관리 화면에서 입력 오류의 원인을 표시한다."""
    try:
        return load_reviewed_multiview_bundle(current_bundle_path,current_reference_paths)
    except (ValueError,OSError,KeyError,TypeError) as current_error:
        raise gr.Error(str(current_error)) from current_error


def describe_reviewed_multiview_bundle(current_bundle_record):
    if current_bundle_record is None:
        return '검수 3D 골격: 선택 안 됨. 파일을 선택한 뒤 불러오기를 누르세요.'
    return '검수 3D 골격 선택됨 · 생성 시 현재 참조 이미지와 출처를 다시 확인합니다. 새 3D 각도 추정·수동 관절 수정과 함께 사용할 수 없습니다.'



def load_face_anchor_calibration(current_calibration_path):
    """출처가 기록된 얼굴 앵커 교정을 불러온다."""
    from generators.kimodo.multiview_face_anchor_experiment import validate_face_calibration_format
    try:
        if not current_calibration_path:
            raise ValueError('얼굴 앵커 교정 JSON을 선택하세요.')
        current_path=Path(current_calibration_path)
        if current_path.stat().st_size>65536:
            raise ValueError('얼굴 앵커 교정 파일은 64KiB 이하여야 합니다.')
        current_record=json.loads(current_path.read_text())
        validate_face_calibration_format(current_record,current_require_source=True)
        return current_record
    except (ValueError,OSError,TypeError,KeyError) as current_error:
        raise gr.Error(str(current_error)) from current_error


def describe_face_anchor_calibration(current_calibration_record):
    if current_calibration_record is None:
        return '얼굴 앵커: 선택 안 됨'
    return f"얼굴 앵커 시험 선택됨 · 교정 프레임 {current_calibration_record['source']['frame']} (0부터) · 검수 골격과 SOMA 리그 결합을 생성 시 확인합니다. 앵커와 표면의 깊이 차이를 기록하지만 얼굴 가림은 판정하지 않습니다."

def load_proportion_examples():
    current_workspace_root=Path(__file__).resolve().parents[4]
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


def apply_proportion_example(current_example_identifier):
    current_example_mapping=load_proportion_examples()
    if current_example_identifier not in current_example_mapping:
        raise ValueError('신체 비율 예제를 선택하세요.')
    return True,current_example_mapping[current_example_identifier]['images']


def execute_kimodo_command(current_command_name,current_payload_record):
    return execute_remote_management_command('kimodo',current_command_name,current_payload_record)


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


def describe_kimodo_prompt(current_prompt_text,current_segment_text=""):
    if not current_prompt_text or not current_prompt_text.strip():
        return '원문 0단어 · 최종 0단어'
    try:
        current_final_prompt = "\n".join(normalize_kimodo_prompt(current_prompt_line) for current_prompt_line in current_prompt_text.splitlines() if current_prompt_line.strip()) if current_segment_text.strip() else normalize_kimodo_prompt(current_prompt_text)
        return f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_final_prompt.split())}단어 · 공식 공백·대소문자·문장부호 정규화\n\n최종 입력: {current_final_prompt}'
    except (OSError,ValueError) as current_prompt_error:
        return f'원문 {len(current_prompt_text.split())}단어 · 최종 확인 불가: {current_prompt_error}'


def restore_kimodo_inputs(current_history_record):
    current_request_record = current_history_record['request']
    if current_request_record.get('action')=='reference-analysis':
        current_request_record={**KIMODO_DEFAULT_SETTINGS,**current_request_record,'prompt':'','directions':list(KIMODO_DEFAULT_SETTINGS['directions'])}
    current_reference_paths=[]
    current_job_root=(KIMODO_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_root.parent!=KIMODO_JOB_STORAGE.resolve():
        raise ValueError('Kimodo 이력 경로 오류')
    for current_reference_name in current_request_record.get('references',[]):
        current_reference_path=(current_job_root/current_reference_name).resolve()
        if current_reference_path.parent!=current_job_root or not current_reference_path.is_file():
            raise ValueError('신체 비율 참조 사본 누락 또는 경로 오류')
        current_reference_paths.append(str(current_reference_path))
    current_keyframe_placements=current_request_record.get('keyframes',[])
    if current_request_record.get('endpoint_pose_id'):
        if current_request_record['endpoint_pose_id']!='relaxed-standing-v1' or current_keyframe_placements:
            raise ValueError('이전 양 끝 자세를 키프레임으로 변환할 수 없습니다.')
        current_keyframe_placements=[{'id':'b0000000000000000000000000000004','frame':1},{'id':'b0000000000000000000000000000004','frame':current_request_record['frames']}]
    return tuple(current_request_record[current_field_name] for current_field_name in ('prompt','frames','steps','seed','guidance_scale','heading_degrees','post_processing'))+(current_request_record.get('directions',['front_left']),current_request_record.get('remove_horizontal_motion',False),bool(current_reference_paths),current_reference_paths,current_request_record.get('openpose_scale_percent',100.0),current_request_record.get('pose_include_hands',False),current_request_record.get('pose_include_face',False),' '.join(map(str,current_request_record.get('segment_frames',[]))),None,[[current_placement['id'],current_placement['frame']] for current_placement in current_keyframe_placements],current_request_record.get('camera_elevation_degrees',0),' '.join(map(str,current_request_record.get('proportion_multiview_angles',[]))),current_request_record.get('proportion_reviewed_multiview'),current_request_record.get('proportion_projected_hip',False),current_request_record.get('proportion_face_anchor_calibration'),current_history_record['id'])


def restore_kimodo_inputs_with_joint_edits(current_history_record):
    current_input_values=restore_kimodo_inputs(current_history_record)
    if not current_history_record['request'].get('proportion_joint_edits'):
        return current_input_values+([],None,'관절점 수정 없음',None)
    current_job_root=(KIMODO_JOB_STORAGE/current_history_record['id']).resolve()
    current_attempt_identifier=json.loads((current_job_root/'current-attempt.json').read_text())['id']
    current_attempt_root=(current_job_root/'attempts'/current_attempt_identifier).resolve()
    if current_attempt_root.parent!=(current_job_root/'attempts').resolve():
        raise ValueError('참조 관절 수정 이력 경로 오류')
    current_result_path=current_attempt_root/'reference-proportions.json'
    if not current_result_path.is_file():
        raise ValueError('수동 관절 수정 이력을 복원할 검출 결과가 없습니다.')
    return current_input_values+load_reference_joint_editor(str(current_result_path),current_input_values[10])



def restore_kimodo_inputs_with_summary(current_history_record):
    """복원한 상태와 접힌 설정의 안내를 같은 응답으로 갱신한다."""
    current_values=restore_kimodo_inputs_with_joint_edits(current_history_record)
    current_summary=describe_kimodo_input_summary(*(current_values[current_index] for current_index in (9,10,16,6,8,3,1,7,17,19,20,21)))
    return current_values+(describe_reviewed_multiview_bundle(current_values[19]),describe_face_anchor_calibration(current_values[21]),current_summary)

def check_kimodo_readiness(current_model_ready,current_prompt_text,current_direction_names,current_proportions_enabled=False,current_reference_paths=None,current_keyframe_rows=None,current_postprocessing_enabled=False,current_segment_text='',current_endpoint_identifier=None,current_horizontal_removal=False,current_reviewed_bundle=None,current_projected_hip=False,current_face_calibration=None):
    current_keyframe_compatible = not current_keyframe_rows or (current_postprocessing_enabled and not current_endpoint_identifier and not current_horizontal_removal)
    return bool(current_model_ready and current_prompt_text and current_prompt_text.strip() and current_direction_names and (bool(current_proportions_enabled)==bool(current_reference_paths)) and current_keyframe_compatible and (not current_projected_hip or current_reviewed_bundle is not None) and (current_face_calibration is None or current_reviewed_bundle is not None))


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


def apply_kimodo_example(current_example_identifier):
    current_example_mapping = load_kimodo_examples()
    if current_example_identifier not in current_example_mapping:
        raise ValueError('불러올 동작 예시를 선택하세요.')
    current_example_record = current_example_mapping[current_example_identifier]
    current_settings_record = current_example_record.get('settings',{})
    return (current_example_record['prompt'],current_example_record['frames'])+tuple(current_settings_record[current_field_name] if current_field_name in current_settings_record else gr.skip() for current_field_name in ('steps','seed','guidance_scale','heading_degrees','post_processing','directions','remove_horizontal_motion'))


def apply_complete_kimodo_example(current_example_identifier):
    current_example_mapping=load_kimodo_examples()
    if current_example_identifier not in current_example_mapping:
        raise gr.Error('먼저 동작 예시를 선택하세요.')
    current_example_record=current_example_mapping[current_example_identifier]
    current_settings_record=current_example_record.get('settings',{})
    current_reference_identifier=current_example_record.get('reference_example')
    current_reference_values=apply_proportion_example(current_reference_identifier) if current_reference_identifier else (False,[])
    current_keyframe_rows = [[current_item['id'],current_item['frame']] for current_item in current_settings_record.get('keyframes',[])]
    return (*apply_kimodo_example(current_example_identifier),*current_reference_values,*(current_settings_record.get(current_field_name,gr.skip()) for current_field_name in ('openpose_scale_percent','pose_include_hands','pose_include_face')),' '.join(map(str,current_settings_record.get('segment_frames',[]))),None,current_keyframe_rows,current_settings_record.get('camera_elevation_degrees',0),'',None,False,None)


def describe_kimodo_duration(current_frame_count):
    if type(current_frame_count) not in (int,float) or not 30<=current_frame_count<=300 or not float(current_frame_count).is_integer():
        return '프레임 수를 30~300 사이의 정수로 입력하세요.'
    return f'모션 길이 **{current_frame_count/30:g}초** · {int(current_frame_count)}프레임 · 30fps'


def describe_kimodo_input_summary(current_proportions_enabled,current_reference_paths,current_keyframe_rows,current_postprocessing_enabled,current_horizontal_removal,current_seed_value=None,current_frame_count=None,current_direction_names=None,current_elevation_angle=None,current_reviewed_bundle=None,current_projected_hip=False,current_face_calibration=None):
    """접힌 설정을 열지 않아도 생성에 적용되는 상태를 확인한다."""
    current_reference_count = len(current_reference_paths or [])
    if current_proportions_enabled and current_reference_count:
        current_reference_text = f"적용 · {current_reference_count}장 · {', '.join(Path(current_reference_path).name for current_reference_path in current_reference_paths)}"
    elif current_proportions_enabled or current_reference_count:
        current_reference_text = '설정 확인 필요'
    else:
        current_reference_text = '꺼짐'
    current_direction_text = ", ".join(f"{KIMODO_DIRECTION_RECORDS[current_direction_name]['label']} {KIMODO_DIRECTION_RECORDS[current_direction_name]['angle']}°" for current_direction_name in (current_direction_names or []) if current_direction_name in KIMODO_DIRECTION_RECORDS) or "미선택"
    current_duration_text = describe_kimodo_duration(current_frame_count) if current_frame_count is not None else "미입력"
    return (f"**생성 전 설정** · 시드: {current_seed_value if current_seed_value is not None else '미입력'} · {current_duration_text} · 방향: {current_direction_text} · 고도: {current_elevation_angle if current_elevation_angle is not None else 0}°\n\n"
            f"신체 비율: {current_reference_text} · 가중 3D 골격: {'선택됨' if current_reviewed_bundle is not None else '없음'} · 3D 골반 시험: {'켜짐' if current_projected_hip else '꺼짐'} · 얼굴 앵커 시험: {'켜짐' if current_face_calibration is not None else '꺼짐'} · 키프레임: {len(current_keyframe_rows or [])}개"
            f" · 공식 후처리: {'켜짐' if current_postprocessing_enabled else '꺼짐'}"
            f" · 수평 이동 제거: {'켜짐' if current_horizontal_removal else '꺼짐'}")



def render_face_depth_summary(current_summary_record):
    """생성 이력에서 얼굴 앵커 깊이 차이와 미측정 수를 표시한다."""
    import html
    if not current_summary_record:
        return ''
    current_message=html.escape(str(current_summary_record.get('message','깊이 기록 상태를 확인할 수 없습니다.')))
    if current_summary_record.get('status')!='valid':
        return '<p><strong>얼굴 앵커 깊이 기록: 사용 불가</strong> · '+current_message+'</p>'
    current_rows=''
    for current_row in current_summary_record.get('rows',[]):
        current_values=[html.escape(str(current_row['direction'])),html.escape(str(current_row['label'])),f"{current_row['measured']}/{current_row['total']}"]
        for current_field in ('median_gap','min_gap','max_gap'):
            current_value=current_row.get(current_field)
            current_values.append(f'{current_value:.3f}' if current_value is not None else '미측정')
        current_rows+='<tr>'+''.join('<td>'+current_value+'</td>' for current_value in current_values)+'</tr>'
    return '<p><strong>얼굴 앵커 깊이 검수 · SOMA 좌표 단위</strong><br>'+current_message+' 전체 프레임 기록은 결과 ZIP에 포함됩니다.</p><table><thead><tr><th>방향</th><th>관절</th><th>측정 프레임</th><th>중앙값</th><th>최솟값</th><th>최댓값</th></tr></thead><tbody>'+current_rows+'</tbody></table>'

def render_kimodo_result(current_job_identifier,current_status_record,current_server_address):
    import html
    if current_status_record.get('reference_analysis_only'):
        return '<p>참조 신체 비율 추출 검증 · 모션 생성 아님. 추출 포즈 '+str(int(current_status_record.get('reference_observation_count',0)))+'개. 영상은 검출 인물별 포즈를 순서대로 보여줍니다. ZIP에 원시 점수·채택 근거·최종 비율을 포함합니다.</p>'+render_video_generation_result(current_job_identifier,current_status_record,current_server_address)
    if current_status_record.get('preprocess_videos'):
        from tools.review.common.gradio_video_results import render_condition_video_previews
        current_pose_status_html='<p>직접 포즈: '+('생성 완료' if current_status_record.get('direct_pose_status')=='completed' else '결과 기록 없음')+'</p>'
        if current_status_record.get('dwpose_status')=='warning':
            current_pose_status_html+='<p><strong>DWPose: 생성 오류 · 경고</strong> — '+html.escape(current_status_record.get('dwpose_error','상세 원인은 실행 로그를 확인하세요.'))+'<br>직접 포즈는 사용할 수 있으며 전체 모션 작업은 완료됐습니다.</p>'
        else:
            current_pose_status_html+='<p>DWPose: '+('생성 완료' if current_status_record.get('dwpose_status')=='completed' else '결과 기록 없음')+'</p>'
        current_pose_status_html+=render_face_depth_summary(current_status_record.get('face_anchor_depth_summary'))
        current_video_descriptions = {'SOMA 렌더':'원본 동작 검수용 영상입니다.', '직접 포즈':'SOMA 관절을 투영한 포즈입니다. Fun Control에 쓰는 30fps 결과는 16fps로 변환하세요.', 'DWPose 포즈':'렌더 영상에서 검출한 포즈입니다. Fun Control에 쓰는 30fps 결과는 16fps로 변환하세요.'}
        current_preview_html = ''
        for current_video_label,current_video_url in current_status_record['preprocess_videos'].items():
            current_video_kind = current_video_label.split(' · ',1)[0]
            current_video_description = current_video_descriptions.get(current_video_kind,'')
            current_preview_html += render_condition_video_previews({'preprocess_videos':{current_video_label:current_video_url}})
            if current_video_description:
                current_preview_html += '<p>'+html.escape(current_video_description)+'</p>'
        return current_pose_status_html+'<p>참조 비율은 포즈 출력에 적용하며 SOMA 원본은 유지합니다. 과거 결과의 프레임 속도는 생성 당시 기록을 확인하세요.</p><p><a href="#kimodo-history-keyframe-save">선택한 이력의 키프레임 저장 영역으로 이동</a></p>'+current_preview_html+'<p>전체 미리보기와 다운로드</p>'+render_video_generation_result(current_job_identifier,current_status_record,current_server_address)
    current_comparison_url = current_status_record.get('comparison_video')
    if not current_comparison_url:
        return render_video_generation_result(current_job_identifier,current_status_record,current_server_address)+'<p>이 결과에는 오픈포즈 비교 영상이 없습니다.</p>'
    current_comparison_html = render_video_generation_result(current_job_identifier,{**current_status_record,'video':current_comparison_url},current_server_address)
    current_pose_description = 'SOMA 원본(정면·측면) → SOMA 직접 투영 오픈포즈. 같은 프레임을 재생하며 카메라 높이·배율은 서로 다릅니다. 오픈포즈는 리타게팅 전 몸 관절이며 실제 눈 관절을 포함합니다. 코·귀는 대응 관절이 없어 생략하며 손 상세 점은 없습니다.' if current_status_record.get('pose_source')=='soma' else '이전 비교 결과: 오픈포즈는 리타게팅 후 ANNY 관절 투영입니다. SOMA 원본 패널은 결과에 따라 없을 수 있습니다.'
    if current_status_record.get('remove_horizontal_motion'):
        current_pose_description = '수평 이동 제거 적용: SOMA·오픈포즈는 보정본입니다. 원본 motion.npz와 보정 motion-in-place.npz는 ZIP에 포함됩니다.'
    if current_status_record.get('pose_schema')=='soma-body18-v2':
        current_pose_description += ' 이 과거 결과는 v2이며 Head를 코로 사용한 대리점이 포함됩니다. 신규 v3에서는 제거했습니다.'
    if current_status_record.get('reference_proportions'):
        current_pose_description += f" 참조 추출 포즈: {int(current_status_record.get('reference_observation_count',0))}개."
        current_pose_description += ' 참조 신체 비율 보정 적용: OpenPose의 너비·팔다리 길이만 조정했습니다. SOMA 원본과 체형이 다릅니다. ZIP의 reference-proportions.json에서 채택 관측·비율과 추출 포즈를 확인하세요.'
    current_pose_description += f" OpenPose 출력 크기: {current_status_record.get('openpose_scale_percent',100.0):g}%."
    return '<p>'+current_pose_description+'</p>'+current_comparison_html+f'<p><a href="{html.escape(current_status_record["video"],quote=True)}" target="_blank">SOMA MP4</a></p>'


def build_kimodo_interface(current_server_address,current_command_callback=None):
    current_execute_command = current_command_callback or execute_kimodo_command
    with gr.Blocks(title='Kimodo 모션 생성기') as current_interface_blocks:
        gr.Markdown('## Kimodo 모션 생성기 · NF4 실험\n텍스트로 SOMA 모션을 생성한 뒤 이 생성기에서 VideoX-Fun DWPose 검출과 선택 참조 관절 길이 보정을 수행합니다. Fun Control 입력에는 결과 포즈 영상을 16fps로 변환하세요. SOMA 렌더는 검수용입니다.')
        with gr.Accordion('고정 설정 · 모델 준비',open=False):
            gr.Markdown('고정: Kimodo-SOMA-RP-v1.2 · 모션 FP32 · LLM2Vec Llama 3 8B NF4 / BF16 연산 · CUDA · 30fps · 1개 샘플 · DDIM. 인코딩 후 인코더를 해제하고 모션을 생성합니다. 이후 모션 모델을 해제하고 SOMA 몸 관절을 512×512·30fps 정사영 포즈로 변환합니다. 모델 선택·부정 프롬프트는 제공하지 않습니다. 선택 이미지 참조는 모션 모델 입력이 아니라 OpenPose 출력 비율 보정에 사용합니다.')
        current_model_ready = gr.State(False)
        current_model_output = gr.Markdown('모델 상태 확인 중')
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        def refresh_kimodo_assets():
            try:
                current_asset_record = current_execute_command('model-status',{})
                return current_asset_record['message'],current_asset_record['ready']
            except Exception as current_asset_error:
                return f'모델 상태 확인 실패: {current_asset_error}',False
        current_refresh_event = current_refresh_button.click(refresh_kimodo_assets,outputs=[current_model_output,current_model_ready],queue=False)
        current_load_event = current_interface_blocks.load(refresh_kimodo_assets,outputs=[current_model_output,current_model_ready])
        gr.Markdown('### 모션 설정')
        current_example_mapping = load_kimodo_examples()
        with gr.Row():
            current_example_selector = gr.Dropdown(scale=3,choices=[(f"{current_example_record['label']} · 신체 비율 보정 {'켜짐' if current_example_record.get('reference_example') else '꺼짐'}",current_example_name) for current_example_name,current_example_record in current_example_mapping.items()],value=None,label='동작 예시',info='예제를 선택하고 불러오기를 눌러야 입력에 적용됩니다. 자동 생성하지 않습니다.')
            current_example_button = gr.Button('예시 불러오기',scale=1)
        current_prompt_control = gr.Textbox(label='동작 프롬프트',value=KIMODO_DEFAULT_SETTINGS['prompt'],lines=3,info='영문으로 주체와 신체 동작을 간결하게 작성하세요. 100단어·400토큰 이내.')
        current_direction_control = gr.CheckboxGroup(choices=[(f"{current_direction_record['label']} ({current_direction_record['angle']}°)",current_direction_name) for current_direction_name,current_direction_record in KIMODO_DIRECTION_RECORDS.items()],value=KIMODO_DEFAULT_SETTINGS['directions'],label='출력 방향 · 복수 선택',info='카메라 방향이며 동작은 회전하지 않습니다. 여러 방향 선택 시 렌더 시간과 저장 용량이 증가합니다.')
        current_elevation_control = gr.Radio(choices=[('수평 0°',0),('위에서 15°',15),('위에서 30°',30)],value=0,label='카메라 고도',info='양의 고도는 위에서 내려다보는 각도입니다. 모션 자체는 회전하지 않습니다.')
        current_prompt_summary = gr.Markdown(describe_kimodo_prompt(KIMODO_DEFAULT_SETTINGS['prompt']))
        current_frame_control = gr.Number(label='프레임 수',value=KIMODO_DEFAULT_SETTINGS['frames'],minimum=30,maximum=300,precision=0,info='30fps: 90프레임=3초, 150프레임=5초, 300프레임=10초. 8GB의 모든 길이를 보장하지 않습니다.')
        current_duration_output = gr.Markdown(describe_kimodo_duration(KIMODO_DEFAULT_SETTINGS['frames']))
        current_frame_control.change(describe_kimodo_duration,current_frame_control,current_duration_output,queue=False)
        with gr.Accordion('순차 생성 구간 · 선택',open=False):
            current_segment_control = gr.Textbox(label='구간별 프레임 수',value='',info='프롬프트를 동작별로 한 줄씩 작성하고 각 구간의 프레임 수를 공백으로 구분하세요. 예: 90 120 90. 합계는 전체 프레임 수와 같아야 합니다. 구간마다 설정한 스텝을 실행합니다.')
        current_seed_control = build_generation_seed(default_seed_value=KIMODO_DEFAULT_SETTINGS['seed'], maximum_seed_value=KIMODO_MAXIMUM_SEED_VALUE)
        with gr.Accordion('고급 설정',open=False):
            current_steps_control = gr.Number(label='샘플링 스텝',value=KIMODO_DEFAULT_SETTINGS['steps'],minimum=2,maximum=100,precision=0,info='공식 기본 100. 2스텝은 실행 연결 확인용이며 품질 평가에 사용하지 마세요.')
            current_guidance_control = gr.Number(label='텍스트 CFG',value=KIMODO_DEFAULT_SETTINGS['guidance_scale'],minimum=0,maximum=10,info='공식 기본 2. 텍스트 조건의 영향이며 원하는 동작의 성공을 보장하지 않습니다.')
            current_heading_control = gr.State(value=KIMODO_DEFAULT_SETTINGS['heading_degrees'])
            current_postprocessing_control = gr.Checkbox(label='공식 발 미끄러짐 후처리',value=KIMODO_DEFAULT_SETTINGS['post_processing'],info='기본 해제: 원본 동작 비교. 활성화하면 공식 후처리를 적용하고 실행 기록에 남깁니다.')
            gr.Markdown('[공식 모델카드](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2) · [NF4 인코더](https://huggingface.co/matbee/kimodo-llm2vec-nf4)\n\nANNY 리그 기능은 폐기되었습니다. SOMA 몸 포즈에는 실제 눈 관절이 포함됩니다. 코·귀는 대응 관절이 없어 생략하며 손 상세 점은 없습니다.\n\nNF4는 커뮤니티 양자화본입니다. BF16과 동작이 달라질 수 있으며 실제 품질은 결과를 검수하세요. 내부 30관절 추론을 공식 API가 77관절로 확장해 저장합니다.')
        current_endpoint_selector = gr.State(None)
        with gr.Accordion('저장한 키프레임 배치 · 선택',open=False):
            gr.Markdown('저장 목록을 새로고침하고 키프레임과 출력 프레임 번호를 골라 추가하세요. 1은 시작, 전체 프레임 수는 종료입니다. 공식 발 미끄러짐 후처리를 켜고 수평 이동 제거를 꺼야 하며 같은 출력 번호는 한 번만 지정합니다.')
            current_keyframe_refresh = gr.Button('저장 목록 새로고침')
            current_keyframe_selector = gr.Dropdown(choices=[],label='저장한 키프레임')
            current_keyframe_saved_preview = gr.Image(label='저장한 자세 미리보기',interactive=False,buttons=[])
            current_keyframe_target = gr.Number(label='배치할 출력 프레임 번호 · 1부터 시작',value=1,minimum=1,precision=0)
            with gr.Row():
                current_keyframe_add = gr.Button('배치 추가')
                current_keyframe_add_endpoints = gr.Button('선택 자세를 시작·종료에 배치')
                current_keyframe_remove = gr.Button('입력한 프레임 배치 삭제')
                current_keyframe_clear = gr.Button('배치 모두 지우기')
            current_keyframe_rows = gr.State([])
            current_keyframe_display = gr.Dataframe(headers=['키프레임 ID','출력 프레임'],datatype=['str','number'],interactive=False,label='현재 배치',value=[])
            current_keyframe_notice = gr.Markdown('배치 없음 · 목록을 새로고침해 키프레임을 선택하세요.')
            gr.Markdown('**저장 목록 관리** · 배치와 별도로 기존 항목을 교체하거나 폐기합니다.')
            with gr.Accordion('키프레임 교체',open=False):
                gr.Markdown('교체할 이전 항목과 새 항목을 선택하세요. 이전 항목은 목록에서 제외하고 보관하며, 기존 작업의 입력 사본은 유지됩니다. 아래 확인은 인라인 확인 영역입니다.')
                current_replace_old = gr.Dropdown(choices=[],label='목록에서 제외할 기존 키프레임')
                current_replace_new = gr.Dropdown(choices=[],label='사용할 새 키프레임')
                current_replace_prepare = gr.Button('교체 내용 확인')
                current_replace_state = gr.State(None)
                current_replace_message = gr.Markdown('두 항목을 선택하고 교체 내용을 확인하세요.')
                with gr.Row():
                    current_replace_confirm = gr.Button('교체 확인',interactive=False)
                    current_replace_cancel = gr.Button('취소',interactive=False)
            with gr.Accordion('사용자 키프레임 폐기',open=False):
                gr.Markdown('선택한 사용자 키프레임을 목록에서 제외하고 별도 보관합니다. 생성 작업의 입력 사본과 제작 기준 예제는 유지됩니다. 아래는 인라인 확인 영역입니다.')
                current_retire_selector=gr.Dropdown(choices=[],multiselect=True,label='폐기할 사용자 키프레임')
                current_retire_prepare=gr.Button('폐기 내용 확인',interactive=False)
                current_retire_state=gr.State(None)
                current_retire_message=gr.Markdown('저장 목록을 새로고침하고 폐기할 항목을 선택하세요.')
                with gr.Row():
                    current_retire_confirm=gr.Button('폐기 확인',interactive=False)
                    current_retire_cancel=gr.Button('폐기 취소',interactive=False)
            def refresh_retire_choices():
                from tools.review.domains.kimodo.keyframe_storage import KIMODO_EXAMPLE_KEYFRAME_IDENTIFIERS
                current_records=current_execute_command('keyframe-list',{})['records']
                current_choices=[(f"{current_record['tag']} · {current_record['source_job']} · {current_record['source_frame']}프레임 · {current_record['id'][:8]}",current_record['id']) for current_record in current_records if current_record['id'] not in KIMODO_EXAMPLE_KEYFRAME_IDENTIFIERS]
                return gr.update(choices=current_choices,value=[])
            def prepare_keyframe_retirement(current_identifiers):
                if not current_identifiers:
                    raise gr.Error('폐기할 사용자 키프레임을 선택하세요.')
                return list(current_identifiers),'다음 항목을 목록에서 제외하고 보관합니다: '+', '.join(current_identifiers),gr.update(interactive=True),gr.update(interactive=True)
            def confirm_keyframe_retirement(current_pending_identifiers,current_selected_identifiers):
                if not current_pending_identifiers or current_pending_identifiers!=current_selected_identifiers:
                    raise gr.Error('선택이 변경되었습니다. 폐기 내용을 다시 확인하세요.')
                current_response=current_execute_command('keyframe-retire',{'ids':current_pending_identifiers})
                return None,f"{current_response['retired_count']}개 폐기 완료. 저장 목록을 새로고침하세요.",gr.update(interactive=False),gr.update(interactive=False)
            current_keyframe_refresh.click(refresh_retire_choices,None,current_retire_selector,queue=False)
            current_retire_selector.change(lambda current_identifiers:(gr.update(interactive=bool(current_identifiers)),None,'항목을 선택한 뒤 폐기 내용을 확인하세요.',gr.update(interactive=False),gr.update(interactive=False)),current_retire_selector,[current_retire_prepare,current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel],queue=False)
            current_retire_prepare.click(prepare_keyframe_retirement,current_retire_selector,[current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel])
            current_retire_confirm.click(confirm_keyframe_retirement,[current_retire_state,current_retire_selector],[current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel])
            current_retire_cancel.click(lambda:(None,'폐기를 취소했습니다.',gr.update(interactive=False),gr.update(interactive=False)),None,[current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel])
            def refresh_replace_choices():
                current_records = current_execute_command('keyframe-list',{})['records']
                current_choices = [(f"{current_record['tag']} · {current_record['source_job']} · {current_record['source_frame']}프레임 · {current_record['id'][:8]}",current_record['id']) for current_record in current_records]
                return gr.update(choices=current_choices,value=None),gr.update(choices=current_choices,value=None)
            def prepare_keyframe_replacement(current_old_identifier,current_new_identifier):
                if not current_old_identifier or not current_new_identifier or current_old_identifier == current_new_identifier:
                    raise gr.Error('서로 다른 두 키프레임을 선택하세요.')
                return {'old_id':current_old_identifier,'new_id':current_new_identifier},f'기존 {current_old_identifier}을 목록에서 제외하고 {current_new_identifier}을 사용합니다.',gr.update(interactive=True),gr.update(interactive=True)
            def confirm_keyframe_replacement(current_pending_record,current_old_identifier,current_new_identifier):
                if current_pending_record != {'old_id':current_old_identifier,'new_id':current_new_identifier}:
                    raise gr.Error('선택이 변경되었습니다. 교체 내용을 다시 확인하세요.')
                current_execute_command('keyframe-replace',current_pending_record)
                return None,'교체 완료. 저장 목록을 새로고침하세요.',gr.update(interactive=False),gr.update(interactive=False)
            current_keyframe_refresh.click(refresh_replace_choices,None,[current_replace_old,current_replace_new],queue=False)
            current_replace_prepare.click(prepare_keyframe_replacement,[current_replace_old,current_replace_new],[current_replace_state,current_replace_message,current_replace_confirm,current_replace_cancel])
            current_replace_confirm.click(confirm_keyframe_replacement,[current_replace_state,current_replace_old,current_replace_new],[current_replace_state,current_replace_message,current_replace_confirm,current_replace_cancel])
            current_replace_cancel.click(lambda:(None,'교체를 취소했습니다.',gr.update(interactive=False),gr.update(interactive=False)),None,[current_replace_state,current_replace_message,current_replace_confirm,current_replace_cancel])
            def refresh_keyframe_choices():
                current_records = current_execute_command('keyframe-list',{})['records']
                return gr.update(choices=[(f"{current_record['tag']} · {current_record['source_job']} · {current_record['source_frame']}프레임 · {current_record['id'][:8]}",current_record['id']) for current_record in current_records],value=None)
            def preview_saved_keyframe(current_identifier):
                if not current_identifier:
                    return None
                from PIL import Image
                import io
                current_preview_record=current_execute_command('keyframe-preview',{'id':current_identifier})
                with Image.open(io.BytesIO(base64.b64decode(current_preview_record['image_base64'],validate=True))) as current_preview_image:
                    return current_preview_image.copy()
            def append_keyframe_placement(current_rows,current_identifier,current_target_number,current_total_frames,current_segment_text,current_endpoint_identifier):
                if not current_identifier or type(current_target_number) not in (int,float) or not float(current_target_number).is_integer():
                    raise gr.Error('키프레임과 정수 프레임 번호를 선택하세요.')
                if type(current_total_frames) not in (int,float) or not float(current_total_frames).is_integer() or current_total_frames < 1:
                    raise gr.Error('전체 프레임 수를 양의 정수로 입력하세요.')
                if current_endpoint_identifier:
                    raise gr.Error('키프레임을 추가하려면 양 끝 기준 자세 선택을 해제하세요.')
                current_new_rows = [*current_rows,[current_identifier,int(current_target_number)]]
                from tools.review.domains.kimodo.keyframe_storage import validate_kimodo_keyframe_placements
                current_validated_rows = validate_kimodo_keyframe_placements([{'id':current_row[0],'frame':current_row[1]} for current_row in current_new_rows],int(current_total_frames))
                current_new_rows = [[current_item['id'],current_item['frame']] for current_item in current_validated_rows]
                return current_new_rows,current_new_rows,f'{len(current_new_rows)}개 키프레임 배치됨 · 공식 후처리 켜짐',True
            current_keyframe_refresh.click(refresh_keyframe_choices,None,current_keyframe_selector,queue=False)
            current_keyframe_selector.change(preview_saved_keyframe,current_keyframe_selector,current_keyframe_saved_preview,queue=False)
            current_keyframe_add.click(append_keyframe_placement,[current_keyframe_rows,current_keyframe_selector,current_keyframe_target,current_frame_control,current_segment_control,current_endpoint_selector],[current_keyframe_rows,current_keyframe_display,current_keyframe_notice,current_postprocessing_control])
            def append_keyframe_endpoints(current_rows,current_identifier,current_total_frames):
                if not current_identifier or type(current_total_frames) not in (int,float) or not float(current_total_frames).is_integer() or current_total_frames < 30:
                    raise gr.Error('키프레임을 선택하고 전체 프레임 수를 30 이상의 정수로 입력하세요.')
                from tools.review.domains.kimodo.keyframe_storage import validate_kimodo_keyframe_placements
                current_proposed_rows=[*current_rows,[current_identifier,1],[current_identifier,int(current_total_frames)]]
                try:
                    current_placements=validate_kimodo_keyframe_placements([{'id':current_row[0],'frame':current_row[1]} for current_row in current_proposed_rows],int(current_total_frames))
                except ValueError as current_placement_error:
                    raise gr.Error(f'시작·종료 배치 실패: {current_placement_error}') from current_placement_error
                current_result_rows=[[current_item['id'],current_item['frame']] for current_item in current_placements]
                return current_result_rows,current_result_rows,f'{len(current_result_rows)}개 키프레임 배치됨 · 공식 후처리 켜짐',True
            current_keyframe_add_endpoints.click(append_keyframe_endpoints,[current_keyframe_rows,current_keyframe_selector,current_frame_control],[current_keyframe_rows,current_keyframe_display,current_keyframe_notice,current_postprocessing_control])
            def remove_keyframe_placement(current_rows,current_target_number):
                if type(current_target_number) not in (int,float) or not float(current_target_number).is_integer():
                    raise gr.Error('삭제할 출력 프레임 번호를 입력하세요.')
                current_remaining_rows = [current_row for current_row in current_rows if current_row[1] != int(current_target_number)]
                if len(current_remaining_rows) == len(current_rows):
                    raise gr.Error('입력한 프레임에 배치된 키프레임이 없습니다.')
                return current_remaining_rows,current_remaining_rows,f'{len(current_remaining_rows)}개 키프레임 배치됨'
            current_keyframe_remove.click(remove_keyframe_placement,[current_keyframe_rows,current_keyframe_target],[current_keyframe_rows,current_keyframe_display,current_keyframe_notice])
            current_keyframe_clear.click(lambda:([],[],'배치 없음'),None,[current_keyframe_rows,current_keyframe_display,current_keyframe_notice])
            current_keyframe_rows.change(lambda current_rows:current_rows,current_keyframe_rows,current_keyframe_display,queue=False)
        gr.Markdown('### 출력 설정')
        current_horizontal_control = gr.Checkbox(label='제자리 보행 보정 · 수평 이동 제거',value=KIMODO_DEFAULT_SETTINGS['remove_horizontal_motion'],info='골반의 X·Z 이동을 제거하고 상하 움직임·관절 회전을 유지합니다. 걷기 자체를 만들지는 않으며 발 미끄러짐을 검수하세요. 원본 모션은 ZIP에 보존합니다.')
        current_scale_control=gr.Slider(minimum=10,maximum=100,step=0.5,value=KIMODO_DEFAULT_SETTINGS['openpose_scale_percent'],label='OpenPose 출력 크기 (%)',info='기본 80%. 직접 포즈와 DWPose 모두 고정 카메라의 화면 중심을 기준으로 축소하여 사방 여백을 늘립니다.')
        with gr.Accordion('OpenPose 신체 비율 참조 · 선택',open=False):
            current_proportions_control=gr.Checkbox(value=False,label='참조 이미지의 신체 비율을 OpenPose 출력에 적용')
            current_reference_control=gr.File(file_count='multiple',file_types=['.png'],label='같은 캐릭터 PNG 참조 · 최대 8장 · 장당 8MiB')
            current_reference_control.upload(lambda current_reference_paths: bool(current_reference_paths),current_reference_control,current_proportions_control,queue=False)
            current_proportion_status=gr.Markdown('신체 비율 보정: 미적용 · 참조 이미지를 첨부하면 적용을 켭니다.')
            def describe_proportion_selection(current_enabled_value,current_reference_paths):
                if current_reference_paths and not current_enabled_value:
                    return '⚠ 참조가 있지만 적용이 꺼져 있습니다. 적용을 켜거나 참조를 제거해야 생성할 수 있습니다.'
                if current_enabled_value and current_reference_paths:
                    return f'신체 비율 보정: 적용 · 참조 {len(current_reference_paths)}장 · DWPose 출력 관절 길이에 반영'
                return '신체 비율 보정: 참조 이미지가 필요합니다.' if current_enabled_value else '신체 비율 보정: 미적용'
            for current_selection_control in (current_reference_control,current_proportions_control):
                current_selection_control.change(describe_proportion_selection,[current_proportions_control,current_reference_control],current_proportion_status,queue=False)
            current_proportion_examples=load_proportion_examples()
            with gr.Row():
                current_proportion_selector=gr.Dropdown(choices=[(current_example_record['label'],current_example_identifier) for current_example_identifier,current_example_record in current_proportion_examples.items()],label='신체 비율 참조 예제',value=None,info='불러오면 참조 목록을 교체하고 비율 적용을 켭니다. 생성은 실행하지 않습니다.')
                current_proportion_button=gr.Button('참조 예제 불러오기')
            current_proportion_button.click(apply_proportion_example,current_proportion_selector,[current_proportions_control,current_reference_control],queue=False)
            build_input_preview(current_reference_control,'신체 비율 참조 미리보기 · 입력 순서')
            with gr.Accordion('8방향 3D 비율 실험 · 선택',open=False):
                current_multiview_control=gr.Textbox(label='검출 관측 순서의 카메라 각도 8개 · 도',value='',placeholder='예: 45 0 135 90 225 315 180 270',info='비우면 기존 2D 보정입니다. 시험 시 검출 결과의 관측 순서와 방향 대응을 직접 확인하세요. 추정 결과와 미사용 관절 오차는 reference-proportions.json에 기록됩니다.')
            with gr.Accordion('검수 3D 골격을 비율 참조로 사용 · 실험',open=False):
                gr.Markdown('참조 이미지와 검수 골격의 출처가 같아야 합니다. 골격은 파일 선택 후 불러오기 버튼을 눌러야 적용되며, 파일 선택만으로 생성하지 않습니다.')
                current_reviewed_file=gr.File(label='검수 골격 묶음 JSON',file_types=['.json'],type='filepath')
                current_reviewed_bundle_state=gr.State(None)
                current_reviewed_notice=gr.Markdown(describe_reviewed_multiview_bundle(None))
                current_projected_hip_control=gr.Checkbox(value=False,label='DWPose 골반을 같은 프레임의 SOMA 투영으로 재구성 · 실험',info='검수 3D 골격이 필요합니다. 골반 좌표는 DWPose 검출 결과가 아니며 다른 누락 관절을 복원하지 않습니다.')
                with gr.Row():
                    current_reviewed_load=gr.Button('검수 골격 불러오기')
                    current_reviewed_clear=gr.Button('검수 골격 해제')
                current_reviewed_file_event=current_reviewed_file.change(lambda:None,None,current_reviewed_bundle_state,queue=False)
                current_reviewed_load_event=current_reviewed_load.click(handle_reviewed_multiview_bundle,[current_reviewed_file,current_reference_control],current_reviewed_bundle_state,queue=False)
                current_reviewed_clear_event=current_reviewed_clear.click(lambda:None,None,current_reviewed_bundle_state,queue=False)
                current_reviewed_bundle_state.change(describe_reviewed_multiview_bundle,current_reviewed_bundle_state,current_reviewed_notice,queue=False)
                current_face_calibration_file=gr.File(label='얼굴 앵커 교정 JSON · 실험',file_types=['.json'],type='filepath')
                current_face_calibration_state=gr.State(None)
                current_face_calibration_notice=gr.Markdown(describe_face_anchor_calibration(None))
                with gr.Row():
                    current_face_calibration_load=gr.Button('얼굴 앵커 불러오기')
                    current_face_calibration_clear=gr.Button('얼굴 앵커 해제')
                current_face_file_event=current_face_calibration_file.change(lambda:None,None,current_face_calibration_state,queue=False)
                current_face_load_event=current_face_calibration_load.click(load_face_anchor_calibration,current_face_calibration_file,current_face_calibration_state,queue=False)
                current_face_clear_event=current_face_calibration_clear.click(lambda:None,None,current_face_calibration_state,queue=False)
                current_face_calibration_state.change(describe_face_anchor_calibration,current_face_calibration_state,current_face_calibration_notice,queue=False)
            with gr.Accordion('8방향 DWPose·3D 골격 검수 · 실험',open=False):
                gr.Markdown('같은 참조 이미지의 관절·가중 3D 골격 기록을 비교합니다. 학습에 사용한 적합 오차는 독립 정확도 검증이 아닙니다. 검수 불러오기는 생성 설정을 바꾸지 않으며 후보 선택 버튼을 눌러야 생성 설정에 적용됩니다.')
                with gr.Row():
                    current_review_reference=gr.File(label='참조 DWPose 관절 JSON',file_types=['.json'],type='filepath')
                    current_review_skeleton=gr.File(label='가중 3D 골격 JSON',file_types=['.json'],type='filepath')
                with gr.Row():
                    current_review_image=gr.File(label='참조 이미지 PNG',file_types=['.png'],type='filepath')
                    current_review_heldout=gr.File(label='제외 관측 검증 JSON · 선택',file_types=['.json'],type='filepath')
                current_review_direction=gr.Dropdown(choices=[(f'{current_number}번 관측',current_number) for current_number in range(1,9)],value=1,label='검수할 참조 관측')
                current_review_button=gr.Button('8방향 검수 불러오기')
                current_review_state=gr.State(None)
                current_review_notice=gr.Markdown('검수 기록을 선택한 뒤 불러오세요.')
                current_review_preview=gr.Image(label='초록: DWPose · 보라: 공통 3D 재투영',type='pil',interactive=False)
                current_review_table=gr.Dataframe(headers=['관절','검출 점수','지정 가중치','실제 가중치','판단 근거','적합 오차 px','제외 관측 오차 px'],datatype=['str']*7,interactive=False,label='관절별 검수',value=[])
                current_review_button.click(load_multiview_review_files,[current_review_reference,current_review_skeleton,current_review_image,current_review_heldout,current_review_direction],[current_review_state,current_review_preview,current_review_notice,current_review_table],queue=False)
                with gr.Accordion('관절별 방향 가중치 수정 · 실험',open=False):
                    gr.Markdown('현재 검수 기록의 8방향 × BODY18 18개를 편집합니다. 관측·관절 번호는 고정하고 가중치 0~1과 판단 근거만 수정합니다. 얼굴의 별도 가시성 입력도 추정에 영향을 줍니다. 저장만으로 골격이나 생성 입력은 변경되지 않습니다.')
                    current_weight_editor=gr.Dataframe(headers=['관측','관절','가중치','판단 근거'],datatype=['number','number','number','str'],type='array',interactive=True,label='8방향 관절 가중치',value=[])
                    current_weight_editor_state=gr.State(None)
                    current_weight_editor_notice=gr.Markdown('8방향 검수 후 표를 불러오세요.')
                    current_weight_load=gr.Button('가중치 표 불러오기')
                    current_weight_output=gr.File(label='검증된 가중치 JSON',interactive=False)
                    current_weight_save=gr.Button('검증 후 가중치 파일 만들기')
                    current_weight_load_event=current_weight_load.click(load_multiview_weight_editor,[current_review_state,current_review_reference,current_review_skeleton,current_review_image],[current_weight_editor,current_weight_editor_state,current_weight_editor_notice],queue=False)
                    current_weight_load_event.success(lambda:None,None,current_weight_output,queue=False)
                    current_weight_save.click(save_multiview_weight_editor,[current_weight_editor,current_weight_editor_state,current_review_state,current_review_reference,current_review_skeleton,current_review_image],[current_weight_output,current_weight_editor_notice],queue=False)
                    current_weight_editor.input(lambda:(None,'표가 수정됐습니다. 다시 검증해 파일을 만드세요.'),None,[current_weight_output,current_weight_editor_notice],queue=False)
                current_review_use_button=gr.Button('검수 결과를 비율 참조 후보로 선택')
                current_review_use_event=current_review_use_button.click(handle_reviewed_bundle_from_review,[current_review_state,current_review_reference,current_review_skeleton,current_review_image,current_reference_control],current_reviewed_bundle_state,queue=False)
                current_review_direction.change(select_multiview_review_rows,[current_review_state,current_review_direction],current_review_table,queue=False)
                for current_review_input in (current_review_reference,current_review_skeleton,current_review_image,current_review_heldout):
                    current_review_input.change(lambda:(None,None,'입력이 변경되어 검수 기록을 다시 불러와야 합니다.',[]),None,[current_review_state,current_review_preview,current_review_notice,current_review_table],queue=False)
                    current_review_input.change(lambda:([],None,None,'검수 입력이 변경되어 가중치 표를 다시 불러와야 합니다.'),None,[current_weight_editor,current_weight_editor_state,current_weight_output,current_weight_editor_notice],queue=False)
            with gr.Accordion('참조 관절점 수동 수정 · 선택',open=False):
                gr.Markdown('완료된 생성 결과의 reference-proportions.json을 불러와 수정 X·Y를 입력합니다. 좌표는 정규화 참조 이미지의 픽셀 기준입니다. 수정 대상의 원본과 이미지가 일치하지 않으면 생성이 실패합니다.')
                current_joint_result_file=gr.File(label='참조 검출 결과 JSON',file_types=['.json'],type='filepath')
                current_joint_load_button=gr.Button('관절점 불러오기')
                current_joint_editor_state=gr.State(None)
                current_joint_editor=gr.Dataframe(headers=['이미지','인물','관절','원본 X','원본 Y','수정 X','수정 Y'],datatype=['number']*7,type='array',interactive=True,label='참조 관절점',value=[])
                current_joint_editor_notice=gr.Markdown('관절점 수정 없음')
                current_joint_preview_image=gr.Image(label='첫 번째 참조의 원본 위팔 검출점 · 인물:관절 번호',interactive=False)
                current_joint_load_button.click(load_reference_joint_editor,[current_joint_result_file,current_reference_control],[current_joint_editor,current_joint_editor_state,current_joint_editor_notice,current_joint_preview_image],queue=False)
                current_reference_control.upload(lambda:([],None,'참조가 변경되어 관절점을 다시 불러와야 합니다.',None),None,[current_joint_editor,current_joint_editor_state,current_joint_editor_notice,current_joint_preview_image],queue=False)
            gr.Markdown('얼굴과 전신 관절이 보이는 참조를 권장합니다. 시트의 모든 인물을 검출하며 포즈 출력에만 비율을 적용합니다. 적용을 끄려면 참조도 제거하세요.')
            with gr.Accordion('참조 비율 추출과 한계',open=False):
                gr.Markdown('투명 PNG는 흰 배경으로 합성합니다. 관절 점수는 확률이 아닌 검출 점수이며 원시값을 보존합니다. 몸통 대비 너비·팔다리 비율과 코·어깨·골반의 거리 관계로 어깨선을 보정합니다. 코는 목뼈 위치가 아닌 대리 지표이며 측면·고개 방향·가림·원근에 따라 차이가 생길 수 있습니다. 유효한 부위·얼굴 관측이 없으면 중단하고 안내합니다. SOMA 원본·동작 방향은 유지합니다.')
        with gr.Row():
            current_hands_control = gr.Checkbox(value=False,label='DWPose 손 상세 포함',info='현재 시험에서는 주먹을 쥔 손가락 자세가 표현되지 않았습니다. 손 상세 포함은 DWPose 검출 결과를 표시하는 옵션이며 주먹 자세를 보장하지 않습니다.')
            current_face_control = gr.Checkbox(value=False,label='DWPose 얼굴 상세 포함')
        gr.Markdown('SOMA 렌더 → VideoX-Fun DWPose → 선택 참조 관절 길이 보정 → 832×480 · 30fps 포즈 MP4. Fun Control의 현행 입력은 16fps이므로 별도 변환이 필요합니다. 몸 18점의 코·눈·귀는 유지합니다.')
        current_prompt_control.change(describe_kimodo_prompt,[current_prompt_control,current_segment_control],current_prompt_summary,queue=False)
        current_segment_control.change(describe_kimodo_prompt,[current_prompt_control,current_segment_control],current_prompt_summary,queue=False)
        current_input_controls = [current_prompt_control,current_frame_control,current_steps_control,current_seed_control,current_guidance_control,current_heading_control,current_postprocessing_control,current_direction_control,current_horizontal_control,current_proportions_control,current_reference_control,current_scale_control,current_hands_control,current_face_control,current_segment_control,current_endpoint_selector,current_keyframe_rows,current_elevation_control,current_multiview_control,current_reviewed_bundle_state,current_projected_hip_control,current_face_calibration_state]
        current_example_event=current_example_button.click(apply_complete_kimodo_example,current_example_selector,current_input_controls,queue=False)
        current_input_summary = gr.Markdown(describe_kimodo_input_summary(False,[],[],KIMODO_DEFAULT_SETTINGS['post_processing'],KIMODO_DEFAULT_SETTINGS['remove_horizontal_motion'],KIMODO_DEFAULT_SETTINGS['seed'],KIMODO_DEFAULT_SETTINGS['frames'],KIMODO_DEFAULT_SETTINGS['directions'],0))
        current_summary_inputs = [current_proportions_control,current_reference_control,current_keyframe_rows,current_postprocessing_control,current_horizontal_control,current_seed_control,current_frame_control,current_direction_control,current_elevation_control,current_reviewed_bundle_state,current_projected_hip_control,current_face_calibration_state]
        for current_summary_control in current_summary_inputs:
            current_summary_control.change(describe_kimodo_input_summary,current_summary_inputs,current_input_summary,queue=False)
        current_reviewed_events=[current_reviewed_file_event,current_reviewed_load_event,current_reviewed_clear_event,current_review_use_event,current_example_event]
        current_face_events=[current_face_file_event,current_face_load_event,current_face_clear_event,current_example_event]
        for current_event in current_reviewed_events:
            current_event.success(describe_reviewed_multiview_bundle,current_reviewed_bundle_state,current_reviewed_notice,queue=False)
        for current_event in current_face_events:
            current_event.success(describe_face_anchor_calibration,current_face_calibration_state,current_face_calibration_notice,queue=False)
        for current_event in [*current_reviewed_events,*current_face_events[:-1]]:
            current_event.success(describe_kimodo_input_summary,current_summary_inputs,current_input_summary,queue=False)
        gr.Markdown('예시는 시작점입니다. 생성된 동작의 자세와 움직임을 검수하세요.')
        current_generate_button = gr.Button('대기열에 추가',variant='primary',interactive=False)
        build_button_guidance(current_generate_button,'모델 자료와 전용 환경을 준비한 뒤 상태를 새로 확인하고 동작 프롬프트와 출력 방향을 한 개 이상 선택하세요. 신체 비율 참조 옵션을 켰다면 RGB PNG 이미지를 첨부하세요. 키프레임을 배치했다면 공식 후처리를 켜고 수평 이동 제거를 해제하세요. 3D 골반 또는 얼굴 앵커 시험을 쓰려면 검수 골격을 불러오세요.')
        with gr.Column() as current_confirmation_container:
            pass
        gr.Markdown('### 진행 상태 · 최신 결과\n접수한 작업의 진행률·예상 시간·VRAM과 완료 영상을 표시합니다. 이전 작업은 아래 생성 이력에서 조회하세요.')
        current_job_control = build_generation_identifier('접수한 생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        def enqueue_kimodo_generation(*current_input_values):
            current_request_record=build_kimodo_payload(*current_input_values[:-2])
            current_joint_edits=build_reference_joint_edit_payload(current_input_values[-2],current_input_values[-1])
            if current_joint_edits:
                current_request_record['proportion_joint_edits']=current_joint_edits
                validate_kimodo_request(current_request_record)
            current_job_record = current_execute_command('generate',current_request_record)
            return current_job_record['id'],'공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,enqueue_kimodo_generation,[*current_input_controls,current_joint_editor,current_joint_editor_state],[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_kimodo_readiness,generation_readiness_inputs=[current_model_ready,current_prompt_control,current_direction_control,current_proportions_control,current_reference_control,current_keyframe_rows,current_postprocessing_control,current_segment_control,current_endpoint_selector,current_horizontal_control,current_reviewed_bundle_state,current_projected_hip_control,current_face_calibration_state],generation_readiness_events=[current_refresh_event,current_load_event,*current_reviewed_events,*current_face_events])
        build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output,result_renderer_callback=render_kimodo_result)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_kimodo_inputs_with_summary,restore_output_components=[*current_input_controls,current_job_control,current_joint_editor,current_joint_editor_state,current_joint_editor_notice,current_joint_preview_image,current_reviewed_notice,current_face_calibration_notice,current_input_summary],result_renderer_callback=render_kimodo_result,record_folder_route='/kimodo',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
        with gr.Accordion('선택한 이력에서 키프레임 저장',open=False,elem_id='kimodo-history-keyframe-save'):
            gr.Markdown('위 생성 이력에서 완료된 작업을 선택하고 프레임을 불러오세요. 원본 SOMA 관절 미리보기는 30fps이며 첫 프레임은 1번입니다. 확인할 프레임으로 이동한 뒤 표시한 프레임 선택을 누르세요.')
            current_keyframe_number = gr.Number(label='원본 프레임 번호 · 1부터 시작',value=1,minimum=1,precision=0)
            current_keyframe_source = gr.State(None)
            current_keyframe_load_button = gr.Button('선택 이력 프레임 불러오기')
            from tools.review.common.gradio_frame_player import build_browser_frame_player
            current_keyframe_player = build_browser_frame_player('kimodo-keyframe-player',current_player_visible=True,defer_image_loading=False,current_selected_number_output=current_keyframe_number)
            current_keyframe_tag = gr.Textbox(label='키프레임 태그',max_lines=1,placeholder='예: 복싱 가드')
            current_keyframe_save = gr.Button('키프레임 저장',interactive=False)
            current_keyframe_status = gr.Markdown('이력 선택, 프레임 번호, 태그가 필요합니다.')
            current_keyframe_list_button = gr.Button('키프레임 목록 새로고침')
            current_keyframe_list_output = gr.JSON(label='저장된 키프레임 목록')
            def load_selected_keyframe_frames(current_job_identifier):
                if not current_job_identifier:
                    raise gr.Error('완료된 이력을 먼저 선택하세요.')
                current_job_status = current_execute_command('status',{'id':current_job_identifier})
                if current_job_status.get('status') != 'completed' or not current_job_status.get('attempt') or not current_job_status.get('image') or type(current_job_status.get('source_frame_count')) is not int:
                    raise gr.Error('완료된 모션 이력을 선택하세요.')
                current_frame_base = current_job_status['image'].rsplit('/',1)[0]
                current_frame_paths = [f'{current_frame_base}/output-{current_index:03d}.png' for current_index in range(current_job_status['source_frame_count'])]
                current_player_payload = {'frames':{'source':current_frame_paths},'directUrls':True,'panels':['원본 SOMA 관절 미리보기']}
                return json.dumps(current_player_payload,ensure_ascii=False),{'job_id':current_job_identifier,'attempt_id':current_job_status['attempt'],'frames':current_job_status['source_frame_count']},1,f"원본 {current_job_identifier} · {current_job_status['attempt']} · {len(current_frame_paths)}프레임을 불러왔습니다."
            current_keyframe_load_button.click(load_selected_keyframe_frames,current_history_outputs[0],[current_keyframe_player,current_keyframe_source,current_keyframe_number,current_keyframe_status])
            def update_keyframe_readiness(current_job_identifier,current_frame_value,current_tag_value,current_source_record):
                return gr.update(interactive=bool(current_source_record and current_source_record.get('job_id')==current_job_identifier and current_tag_value and current_tag_value.strip() and type(current_frame_value) in (int,float) and 1 <= current_frame_value <= current_source_record['frames'] and float(current_frame_value).is_integer()))
            for current_input_control in (current_history_outputs[0],current_keyframe_number,current_keyframe_tag,current_keyframe_source):
                current_input_control.change(update_keyframe_readiness,[current_history_outputs[0],current_keyframe_number,current_keyframe_tag,current_keyframe_source],current_keyframe_save,queue=False)
            def save_selected_keyframe(current_job_identifier,current_frame_value,current_tag_value,current_source_record):
                if not current_source_record or current_source_record.get('job_id') != current_job_identifier:
                    raise gr.Error('선택한 이력의 프레임을 다시 불러오세요.')
                current_job_status = current_execute_command('status',{'id':current_job_identifier})
                if current_job_status.get('status') != 'completed' or current_job_status.get('attempt') != current_source_record['attempt_id']:
                    raise gr.Error('작업 상태 또는 시도가 변경됐습니다. 프레임을 다시 불러오세요.')
                if type(current_frame_value) not in (int,float) or not float(current_frame_value).is_integer():
                    raise gr.Error('원본 프레임 번호는 정수여야 합니다.')
                current_saved_record = current_execute_command('keyframe-save',{'job_id':current_job_identifier,'attempt_id':current_source_record['attempt_id'],'frame':int(current_frame_value),'tag':current_tag_value})
                return f"저장 완료: {current_saved_record['id']} · {current_saved_record['tag']} · 원본 {current_saved_record['source_frame']}프레임"
            current_keyframe_save.click(save_selected_keyframe,[current_history_outputs[0],current_keyframe_number,current_keyframe_tag,current_keyframe_source],current_keyframe_status)
            current_keyframe_list_button.click(lambda:current_execute_command('keyframe-list',{})['records'],None,current_keyframe_list_output,queue=False)
    return current_interface_blocks
