"""MakeHuman 고정 가중치 스키닝과 CUDA 포즈 렌더 단계."""
from pathlib import Path
import sys
import json
import runpy
import time
import bpy
import numpy as np

CURRENT_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(CURRENT_REPOSITORY_ROOT))
from generators.hy_motion.makehuman_retarget import retarget_makehuman_motion

current_stage_record = json.loads(Path(sys.argv[2]).read_text())
current_output_directory = Path(current_stage_record['export_directory'])
current_asset_path = Path(current_stage_record['asset_path'])
with np.load(current_asset_path, allow_pickle=False) as current_asset_archive:
    current_asset_arrays = {current_field_name: current_asset_archive[current_field_name] for current_field_name in current_asset_archive.files}
with np.load(current_stage_record['motion_path'], allow_pickle=False) as current_motion_archive:
    current_frame_rotations, current_frame_positions, current_quality_record = retarget_makehuman_motion(current_motion_archive['world_joints'], current_motion_archive['root_rotations_mat'], current_asset_arrays['bone_names'].tolist(), current_asset_arrays['parent_indices'], current_asset_arrays['rest_heads'], current_asset_arrays['rest_tails'])
np.savez_compressed(current_output_directory / 'makehuman-motion.npz', rotations=current_frame_rotations, positions=current_frame_positions, rest_heads=current_asset_arrays['rest_heads'], rest_tails=current_asset_arrays['rest_tails'], bone_names=current_asset_arrays['bone_names'])
(current_output_directory / 'retarget-quality.json').write_text(json.dumps(current_quality_record, ensure_ascii=False, indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
current_mesh_data = bpy.data.meshes.new('MakeHumanMesh')
current_mesh_data.from_pydata(current_asset_arrays['vertices'].tolist(), [], current_asset_arrays['triangles'].tolist())
current_body_object = bpy.data.objects.new('MakeHumanBody', current_mesh_data)
bpy.context.collection.objects.link(current_body_object)
for current_mesh_polygon in current_mesh_data.polygons:
    current_mesh_polygon.use_smooth = True
current_body_material = bpy.data.materials.new('MakeHumanDummy')
current_body_material.diffuse_color = (.65, .65, .65, 1)
current_mesh_data.materials.append(current_body_material)
current_body_object.shape_key_add(name='Basis')
current_request_record = current_stage_record['request']
current_sample_frames = range(current_request_record['start_frame'], current_request_record['end_frame'] + 1, current_request_record['frame_step'])
current_skin_indices = current_asset_arrays['skin_indices']
current_skin_weights = current_asset_arrays['skin_weights']
if not np.allclose(current_skin_weights.sum(1), 1, atol=1e-5):
    raise ValueError('MakeHuman 스킨 가중치 합 오류')
for current_frame_number in current_sample_frames:
    current_frame_index = current_frame_number - 1
    current_deformed_vertices = np.zeros_like(current_asset_arrays['vertices'])
    for current_weight_slot in range(4):
        current_bone_indices = current_skin_indices[:, current_weight_slot]
        current_local_vertices = current_asset_arrays['vertices'] - current_asset_arrays['rest_heads'][current_bone_indices]
        current_world_vertices = np.einsum('nij,nj->ni', current_frame_rotations[current_frame_index, current_bone_indices], current_local_vertices) + current_frame_positions[current_frame_index, current_bone_indices]
        current_deformed_vertices += current_world_vertices * current_skin_weights[:, current_weight_slot, None]
    current_shape_key = current_body_object.shape_key_add(name=f'frame-{current_frame_number}')
    current_shape_key.data.foreach_set('co', current_deformed_vertices.ravel())
    for current_key_frame, current_key_value in ((current_frame_number - 1, 0.), (current_frame_number, 1.), (current_frame_number + 1, 0.)):
        current_shape_key.value = current_key_value
        current_shape_key.keyframe_insert('value', frame=current_key_frame)
    print(f'{time.strftime("%FT%T")}/makehuman/skin frame={current_frame_number}', flush=True)
bpy.ops.object.camera_add()
bpy.context.scene.camera = bpy.context.object
bpy.context.scene.world = bpy.data.worlds.new('MakeHumanWorld')
runpy.run_path(str(Path(__file__).parent / 'vnccs_render.py'), init_globals={'export_stage_request': current_stage_record, 'prepared_body_object': current_body_object}, run_name='__main__')
