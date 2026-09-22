"""원본 시트의 세 방향을 재생성 없이 분리·정렬한다."""
from pathlib import Path
import cv2,numpy as np,json,hashlib,time,traceback
from scipy.ndimage import binary_fill_holes
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
INPUT_REFERENCE_PATH=EXPERIMENT_OUTPUT_ROOT/'reference-sheet.png'
VIEW_CROP_REGIONS={'front':(140,88,441,942),'left':(922,89,1115,941),'back':(617,89,922,944)}
OUTPUT_CANVAS_SIZE=1024
TARGET_OBJECT_HEIGHT=900
TARGET_FOOT_BASELINE=964

def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/multiview-input/{stage_name_value} {message_text_value}',flush=True)
def execute_reference_preparation():
 source_image_array=cv2.imread(str(INPUT_REFERENCE_PATH),cv2.IMREAD_COLOR)
 if source_image_array is None:raise ValueError('원본 이미지 로드 실패')
 view_input_records={}
 for view_name_value,crop_rectangle_value in VIEW_CROP_REGIONS.items():
  write_trace_message('segment',view_name_value)
  crop_left_value,crop_top_value,crop_right_value,crop_bottom_value=crop_rectangle_value
  cropped_image_array=source_image_array[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value].copy()
  image_hsv_values=cv2.cvtColor(cropped_image_array,cv2.COLOR_BGR2HSV)
  image_lab_values=cv2.cvtColor(cropped_image_array,cv2.COLOR_BGR2LAB)
  color_warm_values=image_lab_values[:,:,2].astype(float)-128
  initial_mask_array=np.full(cropped_image_array.shape[:2],cv2.GC_PR_BGD,dtype=np.uint8)
  probable_foreground_mask=(color_warm_values>5)&(image_hsv_values[:,:,2]>90)
  certain_foreground_mask=(color_warm_values>12)&(image_hsv_values[:,:,2]>145)
  initial_mask_array[probable_foreground_mask]=cv2.GC_PR_FGD
  initial_mask_array[certain_foreground_mask]=cv2.GC_FGD
  # 어두운 관절 틈이 배경으로 빠지지 않도록 원본 내부에 전경 시드를 둔다.
  foreground_seed_paths={
   'front':[[(233,153),(231,171),(232,192)],[(297,294),(297,510)],[(229,330),(202,443),(171,540),(164,582)],[(366,330),(387,443),(420,540),(426,582)],[(250,514),(250,695),(246,875),(239,920)],[(338,514),(338,695),(338,875),(340,920)]],
   'back':[[(769,292),(769,518)],[(703,330),(678,440),(650,543),(640,585)],[(835,330),(860,440),(890,543),(904,585)],[(724,512),(728,695),(728,872),(727,920)],[(811,512),(810,695),(811,872),(811,920)]],
   'left':[[(1013,283),(1005,513)],[(1035,326),(1034,435),(1020,533),(1016,590)],[(1010,515),(1021,695),(1023,873),(995,914)]]}
  for seed_path_values in foreground_seed_paths[view_name_value]:
   seed_point_values=np.array([[point_x_value-crop_left_value,point_y_value-crop_top_value] for point_x_value,point_y_value in seed_path_values],dtype=np.int32)
   cv2.polylines(initial_mask_array,[seed_point_values],False,cv2.GC_FGD,3)
  head_seed_values={'front':((297,185),(57,79)),'back':((769,185),(59,79)),'left':((1010,185),(49,76))}
  head_center_values,head_radius_values=head_seed_values[view_name_value]
  cv2.ellipse(initial_mask_array,(head_center_values[0]-crop_left_value,head_center_values[1]-crop_top_value),head_radius_values,0,0,360,cv2.GC_FGD,-1)
  initial_mask_array[:2]=cv2.GC_BGD;initial_mask_array[-2:]=cv2.GC_BGD;initial_mask_array[:,:2]=cv2.GC_BGD;initial_mask_array[:,-2:]=cv2.GC_BGD
  background_model_array=np.zeros((1,65),np.float64);foreground_model_array=np.zeros((1,65),np.float64)
  cv2.grabCut(cropped_image_array,initial_mask_array,None,background_model_array,foreground_model_array,5,cv2.GC_INIT_WITH_MASK)
  segmented_mask_array=np.uint8((initial_mask_array==cv2.GC_FGD)|(initial_mask_array==cv2.GC_PR_FGD))
  component_total_count,component_label_array,component_stat_values,component_center_values=cv2.connectedComponentsWithStats(segmented_mask_array,8)
  retained_component_mask=np.zeros_like(segmented_mask_array)
  for component_index_value in range(1,component_total_count):
   if component_stat_values[component_index_value,cv2.CC_STAT_AREA]>=100:retained_component_mask[component_label_array==component_index_value]=1
  retained_component_mask=cv2.morphologyEx(retained_component_mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
  retained_component_mask=np.uint8(binary_fill_holes(retained_component_mask))*255
  occupied_row_indices,occupied_column_indices=np.nonzero(retained_component_mask)
  if len(occupied_row_indices)<10000:raise ValueError(f'{view_name_value} 전경 분리 픽셀 부족')
  foreground_bounds_values=[int(occupied_column_indices.min()),int(occupied_row_indices.min()),int(occupied_column_indices.max()+1),int(occupied_row_indices.max()+1)]
  cv2.imwrite(str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}-crop.png'),cropped_image_array)
  cv2.imwrite(str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}-mask.png'),retained_component_mask)
  view_input_records[view_name_value]={'crop':crop_rectangle_value,'foreground_bbox':foreground_bounds_values,'image':cropped_image_array,'mask':retained_component_mask}
 for view_name_value,view_record_value in view_input_records.items():
  bound_left_value,bound_top_value,bound_right_value,bound_bottom_value=view_record_value['foreground_bbox']
  foreground_height_value=bound_bottom_value-bound_top_value;foreground_width_value=bound_right_value-bound_left_value
  foreground_scale_value=TARGET_OBJECT_HEIGHT/foreground_height_value
  target_width_value=int(round(foreground_width_value*foreground_scale_value))
  resized_image_array=cv2.resize(view_record_value['image'][bound_top_value:bound_bottom_value,bound_left_value:bound_right_value],(target_width_value,TARGET_OBJECT_HEIGHT),interpolation=cv2.INTER_LANCZOS4)
  resized_alpha_array=cv2.resize(view_record_value['mask'][bound_top_value:bound_bottom_value,bound_left_value:bound_right_value],(target_width_value,TARGET_OBJECT_HEIGHT),interpolation=cv2.INTER_LINEAR)
  output_image_array=np.full((OUTPUT_CANVAS_SIZE,OUTPUT_CANVAS_SIZE,4),255,dtype=np.uint8);output_image_array[:,:,3]=0
  paste_left_value=(OUTPUT_CANVAS_SIZE-target_width_value)//2;paste_top_value=TARGET_FOOT_BASELINE-TARGET_OBJECT_HEIGHT
  output_image_array[paste_top_value:TARGET_FOOT_BASELINE,paste_left_value:paste_left_value+target_width_value,:3]=resized_image_array
  output_image_array[paste_top_value:TARGET_FOOT_BASELINE,paste_left_value:paste_left_value+target_width_value,3]=resized_alpha_array
  cv2.imwrite(str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}.png'),output_image_array)
  preview_alpha_values=output_image_array[:,:,3:4].astype(float)/255
  preview_image_values=(output_image_array[:,:,:3]*preview_alpha_values+255*(1-preview_alpha_values)).astype(np.uint8)
  cv2.imwrite(str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}-preview.png'),preview_image_values)
  output_record_value={'source_crop':view_record_value['crop'],'foreground_bbox':view_record_value['foreground_bbox'],'target_height':TARGET_OBJECT_HEIGHT,'foot_baseline':TARGET_FOOT_BASELINE,'scale':foreground_scale_value,'sha256':hashlib.sha256((EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}.png').read_bytes()).hexdigest()}
  view_input_records[view_name_value]=output_record_value
 result_record_value={'status':'prepared','method':'원본 픽셀 크롭 + OpenCV GrabCut 색상 분리 + 등방성 크기 정렬','source_sha256':hashlib.sha256(INPUT_REFERENCE_PATH.read_bytes()).hexdigest(),'view_orientation':'공식 left.png 예시와 동일하게 코가 화면 왼쪽을 향하는 측면 사용','views':view_input_records}
 (EXPERIMENT_OUTPUT_ROOT/'input-preparation.json').write_text(json.dumps(result_record_value,ensure_ascii=False,indent=2));write_trace_message('complete',str(result_record_value))
try:execute_reference_preparation()
except Exception:write_trace_message('failure',traceback.format_exc());raise
