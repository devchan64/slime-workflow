"""중앙점과 저채도 몰딩 직선·바깥 어두운 경계로 중앙 타일을 분리한다."""
import cv2
import numpy as np

SATURATION_MAXIMUM_VALUE = 90
BRIGHTNESS_MAXIMUM_VALUE = 190
CLOSING_KERNEL_SIZE = 3
DARK_SEAM_THRESHOLD = 16
MAXIMUM_BORDER_SEARCH_RATIO = 0.025


def extract_molding_center(source_image_value):
    if source_image_value is None or source_image_value.shape != (1024,1024,3):
        raise ValueError('중앙 몰딩 검출은 1024×1024 RGB 원본만 지원합니다.')
    image_height_value,image_width_value=source_image_value.shape[:2]
    image_hsv_values=cv2.cvtColor(source_image_value,cv2.COLOR_BGR2HSV)
    border_mask_value=((image_hsv_values[:,:,1]<SATURATION_MAXIMUM_VALUE)&(image_hsv_values[:,:,2]<BRIGHTNESS_MAXIMUM_VALUE)).astype('uint8')*255
    border_mask_value=cv2.morphologyEx(border_mask_value,cv2.MORPH_CLOSE,np.ones((CLOSING_KERNEL_SIZE,CLOSING_KERNEL_SIZE),dtype='uint8'))
    contour_candidate_values,contour_hierarchy_values=cv2.findContours(border_mask_value,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    center_contour_values=[current_contour_value for current_contour_index,current_contour_value in enumerate(contour_candidate_values) if contour_hierarchy_values[0,current_contour_index,3]>=0 and .05*image_width_value*image_height_value<cv2.contourArea(current_contour_value)<.16*image_width_value*image_height_value and cv2.pointPolygonTest(current_contour_value,(image_width_value/2,image_height_value/2),False)>0]
    if len(center_contour_values)!=1: raise ValueError(f'중앙 블록 경계 후보가 하나가 아닙니다: {len(center_contour_values)}')
    # 중앙 블록 주변의 긴 직선으로 몰딩 안쪽을 찾고 바깥 첫 어두운 골을 추적한다.
    source_gray_value=cv2.cvtColor(source_image_value,cv2.COLOR_BGR2GRAY)
    raw_border_mask_value=((image_hsv_values[:,:,1]<SATURATION_MAXIMUM_VALUE)&(image_hsv_values[:,:,2]<BRIGHTNESS_MAXIMUM_VALUE)).astype('uint8')*255
    search_start_value=round(image_width_value*.30)
    search_end_value=round(image_width_value*.70)
    center_edge_values=cv2.Canny(raw_border_mask_value,50,150)[search_start_value:search_end_value,search_start_value:search_end_value]
    line_candidate_values=cv2.HoughLinesP(center_edge_values,1,np.pi/180,90,minLineLength=round(image_width_value*.175),maxLineGap=25)
    if line_candidate_values is None: raise ValueError('몰딩 직선을 검출하지 못했습니다.')
    line_candidate_values += search_start_value
    horizontal_line_values=[]
    vertical_line_values=[]
    for first_x_value,first_y_value,last_x_value,last_y_value in line_candidate_values.reshape(-1,4):
        if not all(.30*image_width_value<current_axis_value<.70*image_width_value for current_axis_value in (first_x_value,first_y_value,last_x_value,last_y_value)): continue
        if abs(last_y_value-first_y_value)<=3: horizontal_line_values.append(round((first_y_value+last_y_value)/2))
        if abs(last_x_value-first_x_value)<=3: vertical_line_values.append(round((first_x_value+last_x_value)/2))
    central_point_value=image_width_value//2
    if any(not any((current_line_value<central_point_value) == select_lower_side for current_line_value in current_line_values) for current_line_values in (horizontal_line_values,vertical_line_values) for select_lower_side in (True,False)):
        raise ValueError('중앙 몰딩의 네 방향 직선을 모두 검출하지 못했습니다.')
    inner_boundary_values={'left':max(current_line_value for current_line_value in vertical_line_values if current_line_value<central_point_value),'right':min(current_line_value for current_line_value in vertical_line_values if current_line_value>central_point_value),'top':max(current_line_value for current_line_value in horizontal_line_values if current_line_value<central_point_value),'bottom':min(current_line_value for current_line_value in horizontal_line_values if current_line_value>central_point_value)}
    profile_start_value=round(image_width_value*.40)
    profile_end_value=round(image_width_value*.60)
    horizontal_gray_profile=np.median(source_gray_value[profile_start_value:profile_end_value,:],axis=0)
    vertical_gray_profile=np.median(source_gray_value[:,profile_start_value:profile_end_value],axis=1)
    outer_boundary_values={}
    for current_side_name,current_inner_value in inner_boundary_values.items():
        current_gray_profile=horizontal_gray_profile if current_side_name in ('left','right') else vertical_gray_profile
        outward_step_value=-1 if current_side_name in ('left','top') else 1
        dark_seam_indices=[]
        for outward_offset_value in range(1,round(image_width_value*MAXIMUM_BORDER_SEARCH_RATIO)+1):
            current_pixel_index=current_inner_value+outward_step_value*outward_offset_value
            if current_gray_profile[current_pixel_index]<DARK_SEAM_THRESHOLD: dark_seam_indices.append(current_pixel_index)
            elif dark_seam_indices: break
        if not dark_seam_indices: raise ValueError('몰딩 바깥 경계 검출 실패: '+current_side_name)
        outer_boundary_values[current_side_name]=int(min(dark_seam_indices,key=lambda current_pixel_index:current_gray_profile[current_pixel_index]))
    crop_left_value=outer_boundary_values['left']
    crop_top_value=outer_boundary_values['top']
    crop_width_value=outer_boundary_values['right']-crop_left_value+1
    crop_height_value=outer_boundary_values['bottom']-crop_top_value+1
    if abs(crop_width_value-crop_height_value)>image_width_value*.02: raise ValueError('중앙 블록의 가로세로 비율 불일치')
    crop_box_values=[crop_left_value,crop_top_value,crop_left_value+crop_width_value,crop_top_value+crop_height_value]
    center_crop_value=source_image_value[crop_top_value:crop_top_value+crop_height_value,crop_left_value:crop_left_value+crop_width_value].copy()
    detected_image_value = source_image_value.copy()
    cv2.rectangle(detected_image_value,(crop_left_value,crop_top_value),(crop_left_value+crop_width_value-1,crop_top_value+crop_height_value-1),(0,0,255),3)
    return center_crop_value, detected_image_value, {'method':'central-molding-lines-nearest-exterior-dark-seam','version':1,'crop_box':crop_box_values,'crop_size':[crop_width_value,crop_height_value],'inner_lines':inner_boundary_values,'outer_seams':outer_boundary_values,'parameters':{'saturation_max':SATURATION_MAXIMUM_VALUE,'brightness_max':BRIGHTNESS_MAXIMUM_VALUE,'closing_kernel':CLOSING_KERNEL_SIZE,'dark_seam_threshold':DARK_SEAM_THRESHOLD,'search_ratio':MAXIMUM_BORDER_SEARCH_RATIO}}
