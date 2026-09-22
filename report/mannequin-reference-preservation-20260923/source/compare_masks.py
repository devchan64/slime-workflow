from pathlib import Path
from PIL import Image
import numpy as np,json,shutil
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
REFERENCE_INPUT_ROOT=EXPERIMENT_OUTPUT_ROOT.parent/'2026-09-23_01-02-22'
comparison_metric_values={}
for view_name_value,reference_name_value in [('front','front'),('side','left'),('back','back')]:
 shutil.copy2(REFERENCE_INPUT_ROOT/f'{reference_name_value}.png',EXPERIMENT_OUTPUT_ROOT/f'reference-{view_name_value}.png')
 shutil.copy2(REFERENCE_INPUT_ROOT/f'{reference_name_value}-preview.png',EXPERIMENT_OUTPUT_ROOT/f'reference-{view_name_value}-preview.png')
 reference_mask_values=np.array(Image.open(EXPERIMENT_OUTPUT_ROOT/f'compare-accepted-{view_name_value}.png'))[:,:,3]>127
 comparison_metric_values[view_name_value]={}
 for model_name_value in ['accepted','previous','revised']:
  source_image_value=Image.open(EXPERIMENT_OUTPUT_ROOT/f'compare-{model_name_value}-{view_name_value}.png').convert('RGBA')
  current_mask_values=np.array(source_image_value)[:,:,3]>127
  comparison_metric_values[view_name_value][model_name_value]=float(np.logical_and(reference_mask_values,current_mask_values).sum()/np.logical_or(reference_mask_values,current_mask_values).sum())
  occupied_bound_values=source_image_value.getchannel('A').getbbox()
  cropped_image_value=source_image_value.crop(occupied_bound_values)
  target_width_value=round(cropped_image_value.width*900/cropped_image_value.height)
  cropped_image_value=cropped_image_value.resize((target_width_value,900),Image.Resampling.LANCZOS)
  aligned_image_value=Image.new('RGBA',(1024,1024),(255,255,255,0));aligned_image_value.alpha_composite(cropped_image_value,((1024-target_width_value)//2,64))
  aligned_image_value.save(EXPERIMENT_OUTPUT_ROOT/f'aligned-{model_name_value}-{view_name_value}.png')
(EXPERIMENT_OUTPUT_ROOT/'silhouette-comparison.json').write_text(json.dumps({'metric':'동일 카메라 alpha 실루엣 IoU','baseline':'사용자가 채택한 3방향 생성 모델, 레퍼런스 그림의 일치도 점수가 아님','views':comparison_metric_values},ensure_ascii=False,indent=2))
print(comparison_metric_values)
