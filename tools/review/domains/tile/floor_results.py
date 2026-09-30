"""검은 배경의 바닥 표면 사각형을 검출하고 정사각형으로 원근 보정한다."""
import hashlib
import json
import logging
from pathlib import Path
import cv2
import numpy as np

FLOOR_BACKGROUND_THRESHOLD = 32
FLOOR_MINIMUM_AREA_RATIO = 0.2
FLOOR_POLYGON_TOLERANCES = (0.015, 0.02, 0.03, 0.04, 0.05)
FLOOR_MINIMUM_FILL_RATIO = 0.80
FLOOR_MINIMUM_HULL_RATIO = 0.85
FLOOR_GRID_SIDE_COUNT = 3
FLOOR_GRID_IMAGE_SIZE = 1024
FLOOR_GRID_MINIMUM_AREA = 0.025
FLOOR_GRID_MAXIMUM_AREA = 0.15
FLOOR_GRID_ALIGNMENT_TOLERANCE = 0.03
FLOOR_GRID_RECTIFY_SETTINGS = {"version":2,"grid_rows":3,"grid_columns":3,"selected_row":2,"selected_column":2}


def detect_floor_quadrilateral(original_image_value):
    image_height_value, image_width_value = original_image_value.shape[:2]
    foreground_mask_value = (original_image_value.max(axis=2) > FLOOR_BACKGROUND_THRESHOLD).astype('uint8') * 255
    kernel_width_value = max(3, round(min(image_height_value,image_width_value)*0.007) | 1)
    foreground_mask_value = cv2.morphologyEx(foreground_mask_value,cv2.MORPH_CLOSE,np.ones((kernel_width_value,kernel_width_value),dtype='uint8'))
    detected_contour_values, _ = cv2.findContours(foreground_mask_value,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not detected_contour_values: raise ValueError('검은 배경에서 바닥 표면을 찾지 못했습니다.')
    largest_contour_value = max(detected_contour_values,key=cv2.contourArea)
    contour_area_value = cv2.contourArea(largest_contour_value)
    if contour_area_value < image_height_value*image_width_value*FLOOR_MINIMUM_AREA_RATIO: raise ValueError('바닥 표면이 이미지의 20%보다 작습니다.')
    convex_hull_value = cv2.convexHull(largest_contour_value)
    for polygon_tolerance_value in FLOOR_POLYGON_TOLERANCES:
        polygon_corner_values = cv2.approxPolyDP(convex_hull_value,polygon_tolerance_value*cv2.arcLength(convex_hull_value,True),True)
        if len(polygon_corner_values)==4: break
    else: raise ValueError('바닥 표면의 네 꼭짓점을 검출하지 못했습니다.')
    polygon_area_value = cv2.contourArea(polygon_corner_values)
    if not cv2.isContourConvex(polygon_corner_values) or contour_area_value/polygon_area_value < FLOOR_MINIMUM_FILL_RATIO or polygon_area_value/cv2.contourArea(convex_hull_value) < FLOOR_MINIMUM_HULL_RATIO: raise ValueError('검출한 사각형과 바닥 표면이 충분히 일치하지 않습니다.')
    ordered_corner_values = polygon_corner_values.reshape(4,2).astype('float32')
    # 윤곽선 순서를 유지하고 왼쪽 위에서 시작한다. 합/차 기반 중복 꼭짓점을 피한다.
    ordered_corner_values = np.roll(ordered_corner_values,-np.argmin(ordered_corner_values.sum(axis=1)),axis=0)
    first_edge_value = ordered_corner_values[1]-ordered_corner_values[0]
    second_edge_value = ordered_corner_values[2]-ordered_corner_values[0]
    if first_edge_value[0]*second_edge_value[1]-first_edge_value[1]*second_edge_value[0] < 0:
        ordered_corner_values = ordered_corner_values[[0,3,2,1]]
    if np.any(ordered_corner_values[:,0]<=1) or np.any(ordered_corner_values[:,1]<=1) or np.any(ordered_corner_values[:,0]>=image_width_value-2) or np.any(ordered_corner_values[:,1]>=image_height_value-2):
        raise ValueError('바닥 사각형이 이미지 가장자리에 닿습니다. 검은 배경 여백이 필요합니다.')
    return ordered_corner_values


def extract_center_tile(original_image_value):
    """독립된 윤곽 9개를 확인하고 1부터 세는 2행 2열을 원본 픽셀로 분리한다."""
    image_height_value, image_width_value = original_image_value.shape[:2]
    if (image_height_value,image_width_value) != (FLOOR_GRID_IMAGE_SIZE,FLOOR_GRID_IMAGE_SIZE):
        raise ValueError('9칸 바닥 타일 원본은 1024×1024여야 합니다.')
    foreground_mask_value = (original_image_value.max(axis=2)>FLOOR_BACKGROUND_THRESHOLD).astype('uint8')*255
    detected_contour_values,_ = cv2.findContours(foreground_mask_value,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    tile_contour_values = [current_contour_value for current_contour_value in detected_contour_values if cv2.contourArea(current_contour_value)>=image_width_value*image_height_value*FLOOR_GRID_MINIMUM_AREA]
    if len(tile_contour_values)!=9: raise ValueError(f'분리된 타일 9개가 필요합니다. 검출: {len(tile_contour_values)}개')
    selected_cell_records = {}
    detected_image_value = original_image_value.copy()
    for current_contour_value in tile_contour_values:
        if cv2.contourArea(current_contour_value)>image_width_value*image_height_value*FLOOR_GRID_MAXIMUM_AREA:
            raise ValueError('여러 칸이 연결된 표면입니다. 검은 간격으로 분리된 9칸이 필요합니다.')
        column_start_value,row_start_value,tile_width_value,tile_height_value = cv2.boundingRect(current_contour_value)
        column_index_value = int((column_start_value+tile_width_value/2)*3/image_width_value)
        row_index_value = int((row_start_value+tile_height_value/2)*3/image_height_value)
        grid_cell_position = (row_index_value,column_index_value)
        if grid_cell_position in selected_cell_records: raise ValueError('동일 격자 칸에 여러 타일이 검출됐습니다.')
        cell_alignment_margin = image_width_value/FLOOR_GRID_SIDE_COUNT*FLOOR_GRID_ALIGNMENT_TOLERANCE
        if column_start_value < column_index_value*image_width_value/3-cell_alignment_margin or column_start_value+tile_width_value > (column_index_value+1)*image_width_value/3+cell_alignment_margin or row_start_value < row_index_value*image_height_value/3-cell_alignment_margin or row_start_value+tile_height_value > (row_index_value+1)*image_height_value/3+cell_alignment_margin:
            raise ValueError('타일이 3행 3열 셀 경계를 넘습니다. 생성 배열을 확인하세요.')
        selected_cell_records[grid_cell_position] = [column_start_value,row_start_value,tile_width_value,tile_height_value]
        cv2.rectangle(detected_image_value,(column_start_value,row_start_value),(column_start_value+tile_width_value-1,row_start_value+tile_height_value-1),(0,255,255) if grid_cell_position==(1,1) else (255,180,0),2)
        cv2.putText(detected_image_value,f'{row_index_value+1},{column_index_value+1}',(column_start_value,row_start_value+22),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2)
    if set(selected_cell_records)!={(row_index_value,column_index_value) for row_index_value in range(3) for column_index_value in range(3)}: raise ValueError('3행 3열 배열에 빈 칸이 있습니다.')
    column_start_value,row_start_value,tile_width_value,tile_height_value = selected_cell_records[(1,1)]
    # 원근 보정 검출에 필요한 검은 여백을 원본에서 포함한다.
    crop_left_value = column_start_value-2
    crop_top_value = row_start_value-2
    cropped_image_value = original_image_value[crop_top_value:row_start_value+tile_height_value+2,crop_left_value:column_start_value+tile_width_value+2].copy()
    extraction_record_value = {'grid_rows':3,'grid_columns':3,'selected_row':2,'selected_column':2,'index_base':1,'crop_box':[crop_left_value,crop_top_value,column_start_value+tile_width_value+2,row_start_value+tile_height_value+2],'detected_cells':[{'row':current_cell_position[0]+1,'column':current_cell_position[1]+1,'bounds':current_cell_bounds} for current_cell_position,current_cell_bounds in sorted(selected_cell_records.items())]}
    return cropped_image_value,detected_image_value,extraction_record_value


def save_floor_rectification(current_job_root,current_request_record):
    current_job_root = Path(current_job_root)
    rectify_setting_record = current_request_record['floor_rectify']
    grid_extraction_enabled = rectify_setting_record == FLOOR_GRID_RECTIFY_SETTINGS
    if not grid_extraction_enabled and (not isinstance(rectify_setting_record,dict) or set(rectify_setting_record)!={'version','output_size'} or rectify_setting_record['version']!=1 or type(rectify_setting_record['output_size']) is not int or rectify_setting_record['output_size'] not in (512,768,1024)):
        raise ValueError('바닥 원근 보정 설정 오류')
    original_image_path = current_job_root/'result.png'
    rectify_record_path = current_job_root/'square-crop.json'
    try:
        logging.info('floor-detect/start source=%s',original_image_path)
        original_image_value = cv2.imread(str(original_image_path),cv2.IMREAD_COLOR)
        if original_image_value is None: raise ValueError('바닥 생성 원본 이미지를 읽을 수 없습니다.')
        extraction_record_value = None
        working_image_value = original_image_value
        detected_image_value = original_image_value.copy()
        if grid_extraction_enabled:
            working_image_value,detected_image_value,extraction_record_value = extract_center_tile(original_image_value)
            if not cv2.imwrite(str(current_job_root/'center-tile.png'),working_image_value): raise OSError('중앙 타일 저장 실패')
        ordered_corner_values = detect_floor_quadrilateral(working_image_value)
        display_corner_values = ordered_corner_values.copy()
        if extraction_record_value:
            display_corner_values += np.array(extraction_record_value['crop_box'][:2],dtype='float32')
        cv2.polylines(detected_image_value,[display_corner_values.astype('int32')],True,(0,255,255),3)
        for corner_index_value,corner_point_value in enumerate(display_corner_values):
            cv2.putText(detected_image_value,str(corner_index_value+1),tuple(corner_point_value.astype(int)),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)
        output_size_value = int(np.floor(min(np.linalg.norm(ordered_corner_values[(corner_index_value+1)%4]-ordered_corner_values[corner_index_value]) for corner_index_value in range(4)))) if grid_extraction_enabled else rectify_setting_record['output_size']
        destination_corner_values = np.array([[0,0],[output_size_value-1,0],[output_size_value-1,output_size_value-1],[0,output_size_value-1]],dtype='float32')
        perspective_matrix_value = cv2.getPerspectiveTransform(ordered_corner_values,destination_corner_values)
        logging.info('floor-rectify/start corners=%s output_size=%s',ordered_corner_values.tolist(),output_size_value)
        corrected_image_value = cv2.warpPerspective(working_image_value,perspective_matrix_value,(output_size_value,output_size_value),flags=cv2.INTER_CUBIC)
        for output_file_name,output_image_value in (('quadrilateral.png',detected_image_value),('square-crop.png',corrected_image_value)):
            if not cv2.imwrite(str(current_job_root/output_file_name),output_image_value): raise OSError('바닥 보정 이미지 저장 실패')
        crop_result_record = {'status':'completed','version':rectify_setting_record['version'],'extraction':extraction_record_value,'source':'result.png','output':'square-crop.png','corners':ordered_corner_values.tolist(),'perspective_matrix':perspective_matrix_value.tolist(),'output_size':[output_size_value,output_size_value],'background_threshold':FLOOR_BACKGROUND_THRESHOLD,'source_sha256':hashlib.sha256(original_image_path.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((current_job_root/'square-crop.png').read_bytes()).hexdigest()}
        if extraction_record_value:
            crop_result_record['corner_coordinate_space']='center-tile.png'
            crop_result_record['extracted_sha256']=hashlib.sha256((current_job_root/'center-tile.png').read_bytes()).hexdigest()
        rectify_record_path.write_text(json.dumps(crop_result_record,ensure_ascii=False,indent=2)+'\n')
        generation_result_path = current_job_root/'result.json'
        generation_result_record = json.loads(generation_result_path.read_text())
        generation_result_record.update(floor_rectify=crop_result_record,outputs={'original':'result.png','detection':'quadrilateral.png','rectified':'square-crop.png'})
        if extraction_record_value: generation_result_record['outputs']['extracted']='center-tile.png'
        generation_result_path.write_text(json.dumps(generation_result_record,ensure_ascii=False,indent=2)+'\n')
        logging.info('floor-rectify/completed output=%s',current_job_root/'square-crop.png')
    except Exception as rectify_failure_value:
        (current_job_root/'square-crop.png').unlink(missing_ok=True)
        rectify_record_path.write_text(json.dumps({'status':'failed','error':str(rectify_failure_value)},ensure_ascii=False)+'\n')
        raise
