"""ANNY 공식 COCO 회귀점을 변형된 표면과 동일 카메라로 투영한다."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

GENERATION_JOB_PATH=Path(sys.argv[-1])
WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]
FACE_REGRESSION_RECORD=json.loads((WORKFLOW_ROOT_DIRECTORY/'generators/momask/config/face_keypoints.json').read_text())
projection_source_record=json.loads((GENERATION_JOB_PATH/'result/anny/openpose-keypoints.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(GENERATION_JOB_PATH/'result/anny/mannequin.blend'))
current_scene_value=bpy.context.scene
current_rig_object=bpy.data.objects['AnnyAttributesRig']
current_body_object=bpy.data.objects['AnnyAttributesBody']
if len(current_body_object.data.vertices)!=FACE_REGRESSION_RECORD['vertex_count']:raise ValueError('얼굴 회귀 데이터와 ANNY 정점 수 불일치')
direction_camera_points={'down_left':(26**.5,-26**.5,3),'down_right':(-26**.5,-26**.5,3),'up_left':(26**.5,26**.5,3),'up_right':(-26**.5,26**.5,3)}
face_projection_records={}
current_scene_value.camera.data.ortho_scale=2.
for direction_name_value in projection_source_record['frames']:
    face_projection_records[direction_name_value]=[]
    for source_frame_number in projection_source_record['source_frames']:
        current_scene_value.frame_set(source_frame_number)
        bpy.context.view_layer.update()
        camera_follow_position=current_rig_object.location.copy();camera_follow_position.z=0
        camera_target_position=camera_follow_position+Vector((0,0,.8))
        current_scene_value.camera.location=camera_follow_position+Vector(direction_camera_points[direction_name_value])
        current_scene_value.camera.rotation_euler=(camera_target_position-current_scene_value.camera.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        evaluated_body_object=current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
        current_face_points=[]
        for point_weight_values in FACE_REGRESSION_RECORD['points'].values():
            local_point_position=sum((evaluated_body_object.data.vertices[vertex_index_value].co*vertex_weight_value for vertex_index_value,vertex_weight_value in point_weight_values),Vector())
            world_point_position=evaluated_body_object.matrix_world@local_point_position
            projected_point_value=world_to_camera_view(current_scene_value,current_scene_value.camera,world_point_position)
            # 동일 정사영 광선에서 다른 표면이 앞에 있으면 가려진 점이다.
            camera_ray_direction=current_scene_value.camera.matrix_world.to_quaternion()@Vector((0,0,1))
            local_ray_origin=evaluated_body_object.matrix_world.inverted()@(world_point_position+camera_ray_direction*10)
            local_ray_direction=evaluated_body_object.matrix_world.inverted().to_3x3()@(-camera_ray_direction)
            ray_hit_found,ray_hit_position,_,_=evaluated_body_object.ray_cast(local_ray_origin,local_ray_direction)
            visible_point_value=ray_hit_found and (evaluated_body_object.matrix_world@ray_hit_position-world_point_position).length<.015 and 0<=projected_point_value.x<=1 and 0<=projected_point_value.y<=1
            current_face_points.append([projected_point_value.x*512,(1-projected_point_value.y)*512,1] if visible_point_value else [0,0,0])
        face_projection_records[direction_name_value].append(current_face_points)
(GENERATION_JOB_PATH/'result/anny/face-keypoints.json').write_text(json.dumps({'source':FACE_REGRESSION_RECORD['source'],'regressor_sha256':FACE_REGRESSION_RECORD['sha256'],'frames':face_projection_records}))
print('ANNY 얼굴 5점 투영 완료',flush=True)
