"""Kimodo 참조 관절 편집과 다중 시점 검수에 쓰는 Python 함수."""
import base64
import hashlib
import json
from pathlib import Path


def load_reference_joint_editor(current_result_path,current_reference_paths):
    """완료된 참조 분석의 관절 원본과 이미지의 일치를 확인한다."""
    from tools.management.domains.image.three_reference_generation import decode_reference_image
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
    from generators.kimodo.multiview_review_report import build_multiview_review_report
    if not current_reference_path or not current_skeleton_path or not current_image_path:
        raise ValueError('참조 관절 JSON, 3D 골격 JSON, 참조 이미지를 모두 선택하세요.')
    current_reference=json.loads(Path(current_reference_path).read_text())
    current_skeleton=json.loads(Path(current_skeleton_path).read_text())
    current_heldout=json.loads(Path(current_heldout_path).read_text()) if current_heldout_path else None
    current_report=build_multiview_review_report(current_reference,current_skeleton,current_heldout)
    current_image_bytes=Path(current_image_path).read_bytes()
    current_preview,current_image_hash=render_bound_review_overlay(current_image_bytes,current_skeleton,current_report)
    current_report['review_binding_sha256']=calculate_review_source_binding(current_reference,current_skeleton,current_image_hash)
    current_notice='8방향 검수 기록을 불러왔습니다. 초록색: DWPose, 보라색: 3D 재투영. 적합 오차와 제외 관측 오차는 별개입니다.'
    if not current_heldout_path:
        current_notice+=' 제외 관측 기록을 선택하지 않아 미검증으로 표시합니다.'
    return current_report,current_preview,current_notice,select_multiview_review_rows(current_report,current_observation_number)


def render_bound_review_overlay(image_bytes, skeleton, report):
    from io import BytesIO
    from PIL import Image
    from generators.kimodo.multiview_review_report import render_multiview_review_overlay
    digest = hashlib.sha256(image_bytes).hexdigest()
    if skeleton.get("reference_image_sha256") != [digest]:
        raise ValueError("3D 골격의 참조 이미지 해시가 없거나 일치하지 않습니다.")
    with Image.open(BytesIO(image_bytes)) as image:
        return render_multiview_review_overlay(image, report), digest


def calculate_review_source_binding(current_reference_record,current_skeleton_record,current_image_hash):
    """검수 중인 입력의 변경 여부를 확인한다."""
    current_bytes=json.dumps({'reference':current_reference_record,'skeleton':current_skeleton_record,'image_sha256':current_image_hash},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(current_bytes).hexdigest()


def build_reviewed_bundle_from_review(current_review_record,current_reference_path,current_skeleton_path,current_image_path,current_generation_references):
    """검수한 출처 그대로 생성 참조에 사용할 후보 묶음을 구성한다."""
    from generators.kimodo.multiview_reviewed_bundle import REVIEWED_BUNDLE_SCHEMA_VERSION,validate_reviewed_multiview_bundle
    from tools.management.domains.image.three_reference_generation import decode_reference_image
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
