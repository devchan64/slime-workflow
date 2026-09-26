"""생성 시트의 레이아웃에 따라 프레임별 수동 앵커 검수 페이지를 만든다."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.ui_assets import read_review_shared_styles
from datetime import datetime
import argparse
import hashlib
import json
import traceback
from PIL import Image

WORKFLOW_REPO_ROOT=Path(__file__).resolve().parents[2]
DIRECTION_NAME_VALUES={'down_left','down_right','up_left','up_right'}

def reject_duplicate_fields(object_field_pairs):
    parsed_object_record={}
    for current_field_name,current_field_value in object_field_pairs:
        if current_field_name in parsed_object_record: raise ValueError(f'중복 필드: {current_field_name}')
        parsed_object_record[current_field_name]=current_field_value
    return parsed_object_record

def build_animation_anchors(parsed_argument_values):
    review_run_directory=parsed_argument_values.root.resolve()
    if not review_run_directory.is_relative_to(WORKFLOW_REPO_ROOT/'.tmp'): raise ValueError('워크플로우 .tmp 실행 폴더를 지정하세요.')
    execution_log_path=review_run_directory/'build-anchors.log'
    def emit_anchor_trace(trace_stage_name,trace_message_text):
        trace_output_line=f'{datetime.now().isoformat()}/animation-anchors/{trace_stage_name} {trace_message_text}'
        print(trace_output_line,flush=True)
        with execution_log_path.open('a') as execution_log_stream: execution_log_stream.write(trace_output_line+'\n')
    try:
        emit_anchor_trace('start',str(review_run_directory))
        result_manifest_data=json.loads((review_run_directory/'result.json').read_text(),object_pairs_hook=reject_duplicate_fields)
        sheet_column_count,sheet_row_count=result_manifest_data['layout']
        if any(type(current_size_value)is not int or current_size_value<1 for current_size_value in (sheet_column_count,sheet_row_count)): raise ValueError('양의 정수 열·행이 필요합니다.')
        frame_duration_value=result_manifest_data['frame_duration_ms']
        if type(frame_duration_value)is not int or frame_duration_value<1: raise ValueError('양의 정수 프레임 시간이 필요합니다.')
        source_output_records=result_manifest_data['outputs']
        if len(source_output_records)!=4 or {current_output_record['direction'] for current_output_record in source_output_records}!=DIRECTION_NAME_VALUES: raise ValueError('고유한 4방향 시트가 필요합니다.')
        review_frame_records=[]
        source_sheet_records=[]
        for current_output_record in source_output_records:
            source_image_name=current_output_record['image']
            if Path(source_image_name).name!=source_image_name: raise ValueError('시트는 실행 폴더의 파일명이어야 합니다.')
            source_sheet_path=review_run_directory/source_image_name
            with Image.open(source_sheet_path) as current_sheet_image:
                actual_sheet_width,actual_sheet_height=current_sheet_image.size
            if [actual_sheet_width,actual_sheet_height]!=current_output_record['size']: raise ValueError('기록과 이미지 크기가 다릅니다.')
            if actual_sheet_width<sheet_column_count or actual_sheet_height<sheet_row_count: raise ValueError('셀보다 작은 시트입니다.')
            current_direction_name=current_output_record['direction']
            source_sheet_records.append({'direction':current_direction_name,'image':source_image_name,'sha256':hashlib.sha256(source_sheet_path.read_bytes()).hexdigest()})
            for frame_sequence_index in range(sheet_column_count*sheet_row_count):
                cell_column_index=frame_sequence_index%sheet_column_count
                cell_row_index=frame_sequence_index//sheet_column_count
                cell_left_position=cell_column_index*actual_sheet_width//sheet_column_count
                cell_top_position=cell_row_index*actual_sheet_height//sheet_row_count
                cell_width_value=(cell_column_index+1)*actual_sheet_width//sheet_column_count-cell_left_position
                cell_height_value=(cell_row_index+1)*actual_sheet_height//sheet_row_count-cell_top_position
                initial_anchor_point={'x':cell_width_value//2,'y':cell_height_value-1}
                review_frame_records.append({'frameId':f'{current_direction_name}.{frame_sequence_index}','direction':current_direction_name,'image':source_image_name,'rect':{'x':cell_left_position,'y':cell_top_position,'width':cell_width_value,'height':cell_height_value},'contacts':[dict(initial_anchor_point),dict(initial_anchor_point)],'endpoints':[],'anchor':initial_anchor_point})
        source_identity_record={'animationId':parsed_argument_values.animation_id,'animationVersion':parsed_argument_values.animation_version,'sheets':source_sheet_records}
        if parsed_argument_values.coordinates:
            imported_artifact_data=json.loads(parsed_argument_values.coordinates.read_text(),object_pairs_hook=reject_duplicate_fields)
            if set(imported_artifact_data)!={'schemaVersion','artifactType','description','coordinateMode','source','frames'} or type(imported_artifact_data['schemaVersion'])is not int or imported_artifact_data['schemaVersion']!=1 or imported_artifact_data['artifactType']!='character-animation-anchor-review' or imported_artifact_data['coordinateMode']!='anchor' or imported_artifact_data['source']!=source_identity_record or not isinstance(imported_artifact_data['description'],str) or not imported_artifact_data['description'].strip(): raise ValueError('좌표 스키마·대상 애니메이션·시트 해시 불일치')
            imported_frame_records=imported_artifact_data['frames']
            if not isinstance(imported_frame_records,list) or len(imported_frame_records)!=len(review_frame_records): raise ValueError('좌표 프레임 수 불일치')
            imported_frame_lookup={current_frame_record['frameId']:current_frame_record for current_frame_record in imported_frame_records}
            if len(imported_frame_lookup)!=len(review_frame_records): raise ValueError('중복 프레임')
            for current_frame_record in review_frame_records:
                imported_frame_record=imported_frame_lookup[current_frame_record['frameId']]
                if set(imported_frame_record)!={'frameId','direction','image','rect','points','anchor'} or any(imported_frame_record[current_field_name]!=current_frame_record[current_field_name] for current_field_name in ('direction','image','rect')): raise ValueError('프레임 셀·방향 불일치')
                imported_anchor_point=imported_frame_record['anchor']
                if not isinstance(imported_anchor_point,dict) or set(imported_anchor_point)!={'x','y'} or any(type(current_coordinate_value)is not int for current_coordinate_value in imported_anchor_point.values()) or not 0<=imported_anchor_point['x']<current_frame_record['rect']['width'] or not 0<=imported_anchor_point['y']<current_frame_record['rect']['height'] or imported_frame_record['points']!=[imported_anchor_point]: raise ValueError('셀 내부 정수 앵커가 필요합니다.')
                current_frame_record.update(anchor=imported_anchor_point,contacts=[dict(imported_anchor_point),dict(imported_anchor_point)])
        review_source_metadata={'coordinateMode':'anchor','animationId':parsed_argument_values.animation_id,'animationVersion':parsed_argument_values.animation_version,'artifactType':'character-animation-anchor-review','exportFilename':'character-animation-anchor-review.json','frameDurationMs':frame_duration_value,'sheets':source_sheet_records,'description':f"{parsed_argument_values.animation_id} / {parsed_argument_values.animation_version}의 프레임별 수동 지면 앵커. 셀 좌상 원점, x 오른쪽·y 아래, 원본 정수 픽셀. points는 anchor 한 점. 떠 있는 발의 중심과 다르며 초기 셀 하단 중앙은 편집 시작점일 뿐 검수 완료 좌표가 아니다."}
        template_source_text=(WORKFLOW_REPO_ROOT/'generators/animation/review_standing_anchors.html').read_text()
        template_source_text=template_source_text.replace('</style>', '</style><style>'+read_review_shared_styles()+'</style>',1)
        rendered_page_text=template_source_text.replace('__FRAME_RECORDS__',json.dumps(review_frame_records).replace('<','\\u003c')).replace('__SOURCE_METADATA__',json.dumps(review_source_metadata,ensure_ascii=False).replace('<','\\u003c'))
        (review_run_directory/'anchors.html').write_text(rendered_page_text)
        emit_anchor_trace('complete',f'{len(review_frame_records)}프레임: {review_run_directory}/anchors.html')
    except Exception:
        emit_anchor_trace('failure',traceback.format_exc())
        print('\n'.join(execution_log_path.read_text().splitlines()[-20:]),flush=True)
        raise

if __name__=='__main__':
    argument_value_parser=argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--root',type=Path,required=True)
    argument_value_parser.add_argument('--animation-id',required=True)
    argument_value_parser.add_argument('--animation-version',required=True)
    argument_value_parser.add_argument('--coordinates',type=Path)
    build_animation_anchors(argument_value_parser.parse_args())
