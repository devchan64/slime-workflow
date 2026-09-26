"""ANNY 카메라 투영점을 COCO18 신체 맵으로 변환한다. 얼굴은 ANNY 공식 COCO 회귀점을 선택적으로 투영한다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import json, math, subprocess, time
from PIL import Image, ImageDraw

COCO_BODY_COLORS=((255,0,85),(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),(85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),(0,170,255),(0,85,255),(0,0,255))
COCO_BODY_CONNECTIONS=((1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13))
def generate_openpose_maps(job_directory_path, include_face_points=False):
    if type(include_face_points) is not bool:raise ValueError("얼굴 옵션은 ON/OFF여야 합니다.")
    projection_record_values=json.loads((job_directory_path/'result/anny/openpose-keypoints.json').read_text())
    result_record_values=json.loads((job_directory_path/'result.json').read_text())
    face_projection_record=None
    if include_face_points:
        workflow_root_directory=Path(__file__).resolve().parents[4]
        face_record_path=job_directory_path/'result/anny/face-keypoints.json'
        if not face_record_path.exists():
            subprocess.run([str(workflow_root_directory/'.local/blender-runtime/bin/python'),str(workflow_root_directory/'generators/momask/templates/run_stage.py'),str(workflow_root_directory/'generators/momask/project_face_points.py'),str(job_directory_path)],check=True)
        face_projection_record=json.loads(face_record_path.read_text())
    output_root_path=job_directory_path/'result/openpose-map'
    output_keypoint_records={}
    for direction_label_value in result_record_values['directions']:
        projected_frame_values=projection_record_values['frames'][direction_label_value]
        if len(projected_frame_values)!=result_record_values['frames']:raise ValueError('투영 프레임 수 불일치')
        output_keypoint_records[direction_label_value]=[]
        for frame_index_value,projected_point_values in enumerate(projected_frame_values,1):
            if len(projected_point_values)!=14 or any(len(point_value)!=2 or any(not math.isfinite(axis_value) or not 0<=axis_value<=512 for axis_value in point_value) for point_value in projected_point_values):raise ValueError('ANNY 투영점 형식 오류')
            # 인덱스 0은 머리 중심이므로 코로 사용하지 않는다. 눈·귀도 결측 처리한다.
            pose_keypoint_values=[[0,0,0] for unused_joint_index in range(18)]
            for body_joint_index in range(1,14):pose_keypoint_values[body_joint_index]=[*projected_point_values[body_joint_index],1]
            if face_projection_record:
                for face_joint_index,face_point_value in zip((0,14,15,16,17),face_projection_record['frames'][direction_label_value][frame_index_value-1]):pose_keypoint_values[face_joint_index]=face_point_value
            output_image_value=Image.new('RGB',(512,512),'black');image_draw_context=ImageDraw.Draw(output_image_value)
            for start_joint_index,end_joint_index in COCO_BODY_CONNECTIONS:
                image_draw_context.line([tuple(pose_keypoint_values[start_joint_index][:2]),tuple(pose_keypoint_values[end_joint_index][:2])],fill=COCO_BODY_COLORS[start_joint_index],width=4)
            for body_joint_index in range(1,14):
                point_x_value,point_y_value,_=pose_keypoint_values[body_joint_index]
                image_draw_context.ellipse((point_x_value-4,point_y_value-4,point_x_value+4,point_y_value+4),fill=COCO_BODY_COLORS[body_joint_index])
            if include_face_points:
                for face_start_index,face_end_index in ((1,0),(0,14),(14,16),(0,15),(15,17)):
                    if pose_keypoint_values[face_start_index][2] and pose_keypoint_values[face_end_index][2]:image_draw_context.line([tuple(pose_keypoint_values[face_start_index][:2]),tuple(pose_keypoint_values[face_end_index][:2])],fill=(255,255,255),width=2)
                for face_joint_index in (0,14,15,16,17):
                    point_x_value,point_y_value,point_visible_value=pose_keypoint_values[face_joint_index]
                    if point_visible_value:image_draw_context.ellipse((point_x_value-2,point_y_value-2,point_x_value+2,point_y_value+2),fill=(255,255,255))
            destination_frame_path=output_root_path/direction_label_value/f'openpose-map-{frame_index_value:04d}.png';destination_frame_path.parent.mkdir(parents=True,exist_ok=True);output_image_value.save(destination_frame_path)
            output_keypoint_records[direction_label_value].append({'pose_keypoints_2d':[component_value for keypoint_value in pose_keypoint_values for component_value in keypoint_value]})
    (output_root_path/'keypoints.json').write_text(json.dumps({'format':'COCO18','source':'MoMask motion retargeted to ANNY; same render camera projection','face_enabled':include_face_points,'missing_joints':[] if include_face_points else [0,14,15,16,17],'confidence_note':'1은 투영점 존재 여부이며 검출 확률이 아님','frames':output_keypoint_records},ensure_ascii=False))
    result_record_values['openpose_face_enabled']=include_face_points
    result_record_values['openpose_map_revision']=time.time_ns()
    result_record_values['openpose_map_frames']=result_record_values['frames']
    result_temporary_path=job_directory_path/'result.pending.json';result_temporary_path.write_text(json.dumps(result_record_values,ensure_ascii=False,indent=2));result_temporary_path.replace(job_directory_path/'result.json')
    return {'frames':result_record_values['frames'],'directions':result_record_values['directions']}
