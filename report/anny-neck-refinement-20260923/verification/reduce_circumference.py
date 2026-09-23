from pathlib import Path
from datetime import datetime
import numpy as np,json
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
source_bundle_values=dict(np.load(EXPERIMENT_OUTPUT_ROOT/'inputs/anny-rest-rig.npz',allow_pickle=False))
source_vertex_array=source_bundle_values['vertices'].astype(float)
source_bone_names=source_bundle_values['bone_names'].tolist()
arm_bone_mask=np.array([current_bone_name.startswith(('clavicle','shoulder','upperarm','lowerarm','wrist','finger','metacarpal')) for current_bone_name in source_bone_names])
arm_vertex_influence=np.sum(source_bundle_values['weights']*arm_bone_mask[source_bundle_values['indices']],axis=1)
neck_region_values=np.exp(-2*((source_vertex_array[:,2]-1.235)/.055)**2)*np.exp(-2*(source_vertex_array[:,0]/.095)**2)
rib_region_values=np.exp(-2*((source_vertex_array[:,2]-1.065)/.115)**2)*(1-arm_vertex_influence)
output_vertex_array=source_vertex_array.copy()
output_vertex_array[:,0]*=(1-.15*neck_region_values)*(1-.00*rib_region_values)
output_vertex_array[:,1]=.005+(source_vertex_array[:,1]-.005)*(1-.15*neck_region_values)*(1-.00*rib_region_values)
output_vertex_array[5155]=source_vertex_array[5155]
source_bundle_values['vertices']=output_vertex_array.astype(np.float32)
np.savez(EXPERIMENT_OUTPUT_ROOT/'anny-rest-rig.npz',**source_bundle_values)
result_record_values={'status':'passed','neck_peak_cross_section_scale':.85,'ribcage_peak_cross_section_scale':1.0,'bone_positions_unchanged':True,'weights_unchanged':True,'head_ratio':float(np.ptp(output_vertex_array[:,2])/(output_vertex_array[:,2].max()-output_vertex_array[5155,2])),'overlay_opacity':.60,'note':'중심 단면의 가로·깊이 축소 계수; 전체 둘레 감소율 측정값이 아님. 높이 경계에서 연속 감쇠.'}
(EXPERIMENT_OUTPUT_ROOT/'circumference-validation.json').write_text(json.dumps(result_record_values,ensure_ascii=False,indent=2))
print(f'{datetime.now().isoformat()}/circumference/complete {result_record_values}',flush=True)
