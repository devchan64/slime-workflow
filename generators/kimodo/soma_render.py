"""공식 SOMASkin 메시를 선택 방향의 단일 인체 영상으로 렌더링한다."""
import importlib.util
import math
import os
from pathlib import Path

SOMA_RENDER_WIDTH = 832
SOMA_RENDER_HEIGHT = 480
SOMA_RENDER_FPS = 30
SOMA_CAMERA_NEAR_PLANE = 0.01
SOMA_CAMERA_FAR_PLANE = 100.0


def build_soma_camera_rotation(current_direction_angle, current_elevation_angle):
    """양의 고도는 대상 위쪽에서 내려다보는 카메라다."""
    import numpy as np
    current_yaw_angle = math.radians(current_direction_angle)
    current_pitch_angle = math.radians(current_elevation_angle)
    current_yaw_matrix = np.array([[math.cos(current_yaw_angle),0,-math.sin(current_yaw_angle)],[0,1,0],[math.sin(current_yaw_angle),0,math.cos(current_yaw_angle)]])
    current_pitch_matrix = np.array([[1,0,0],[0,math.cos(current_pitch_angle),-math.sin(current_pitch_angle)],[0,math.sin(current_pitch_angle),math.cos(current_pitch_angle)]])
    return current_pitch_matrix @ current_yaw_matrix




def convert_orthographic_render_depth(current_render_depth,current_near_plane,current_far_plane):
    """pyrender 원근 역변환값을 직교 카메라의 선형 깊이로 복원한다."""
    import numpy as np
    current_depth_values=np.asarray(current_render_depth,dtype=float)
    if not np.isfinite(current_depth_values).all() or np.any(current_depth_values<0) or type(current_near_plane) not in (int,float) or type(current_far_plane) not in (int,float) or not np.isfinite([current_near_plane,current_far_plane]).all() or not 0<current_near_plane<current_far_plane:
        raise ValueError('직교 카메라 깊이 또는 근·원 평면 오류')
    current_visible_mask=current_depth_values>0
    current_output_depth=np.zeros_like(current_depth_values)
    current_output_depth[current_visible_mask]=current_near_plane+current_far_plane-current_near_plane*current_far_plane/current_depth_values[current_visible_mask]
    if np.any(current_output_depth[current_visible_mask]<current_near_plane-1e-3) or np.any(current_output_depth[current_visible_mask]>current_far_plane+1e-3):
        raise ValueError('직교 카메라 복원 깊이가 근·원 평면을 벗어났습니다.')
    return current_output_depth

def measure_face_anchor_depth(current_anchor_positions,current_camera_record,current_depth_image):
    """투영된 얼굴 앵커와 가장 가까운 렌더 표면의 깊이를 기록한다."""
    import numpy as np
    from generators.kimodo.soma_pose import project_recorded_camera_points
    current_anchor_positions=np.asarray(current_anchor_positions,dtype=float)
    current_depth_image=np.asarray(current_depth_image,dtype=float)
    current_width=current_camera_record['width'];current_height=current_camera_record['height']
    if current_anchor_positions.shape!=(5,3) or not np.isfinite(current_anchor_positions).all() or current_depth_image.shape!=(current_height,current_width) or not np.isfinite(current_depth_image).all() or np.any(current_depth_image<0):
        raise ValueError('얼굴 앵커 또는 깊이 영상 형식 오류')
    current_pixels=project_recorded_camera_points(current_anchor_positions,current_camera_record)
    current_rotation=np.asarray(current_camera_record['rotation_matrix'],dtype=float)
    current_center=np.asarray(current_camera_record['center_position'],dtype=float)
    current_anchor_depth=current_center[2]+6.-(current_anchor_positions@current_rotation.T)[:,2]
    if np.any(current_anchor_depth<=0) or not np.isfinite(current_anchor_depth).all():
        raise ValueError('얼굴 앵커의 카메라 깊이가 유효하지 않습니다.')
    current_records=[]
    for current_index,current_joint in enumerate((0,14,15,16,17)):
        current_x,current_y=np.rint(current_pixels[current_index]).astype(int)
        current_surface=None
        if 0<=current_x<current_width and 0<=current_y<current_height:
            current_sample=float(current_depth_image[current_y,current_x])
            if current_sample>0:
                current_surface=current_sample
        current_records.append({'joint':current_joint,'pixel_xy':current_pixels[current_index].tolist(),'anchor_depth':float(current_anchor_depth[current_index]),'surface_depth':current_surface,'depth_gap':float(current_anchor_depth[current_index]-current_surface) if current_surface is not None else None})
    return current_records

def render_soma_motion(current_attempt_root, current_direction_angles, current_scale_percent=85.0, current_elevation_angle=0, current_face_calibration_record=None):
    # EGL은 별도 작업 프로세스에서만 초기화한다.
    os.environ['PYOPENGL_PLATFORM'] = 'egl'
    import imageio.v2 as imageio
    import numpy as np
    import pyrender
    import torch
    import trimesh
    from OpenGL.GL import glGetString, GL_RENDERER
    from kimodo.skeleton import SOMASkeleton77
    from generators.kimodo.contracts import KIMODO_SOURCE_ROOT, KIMODO_ASSET_CONFIG
    from tools.review.common.generation_records import write_record_atomically

    if not torch.cuda.is_available():
        raise RuntimeError('SOMA 스키닝에 CUDA가 필요합니다.')
    current_skin_source = KIMODO_SOURCE_ROOT/'kimodo/viz/soma_skin.py'
    current_module_spec = importlib.util.spec_from_file_location('kimodo_official_soma_skin', current_skin_source)
    current_skin_module = importlib.util.module_from_spec(current_module_spec)
    current_module_spec.loader.exec_module(current_skin_module)
    current_skin_model = current_skin_module.SOMASkin(SOMASkeleton77().to('cuda'))
    current_motion_path = current_attempt_root/'motion-in-place.npz'
    if not current_motion_path.is_file():
        current_motion_path = current_attempt_root/'motion.npz'
    with np.load(current_motion_path, allow_pickle=False) as current_motion_data:
        current_joint_positions = np.asarray(current_motion_data['posed_joints'])
        current_joint_rotations = np.asarray(current_motion_data['global_rot_mats'])
    if current_joint_positions.shape[1:] != (77, 3) or current_joint_rotations.shape != (*current_joint_positions.shape[:2], 3, 3):
        raise ValueError('SOMA 렌더 입력 관절·회전 형식 오류')
    current_face_anchor_positions = None
    if current_face_calibration_record is not None:
        import json
        from generators.kimodo.multiview_face_anchor_experiment import validate_face_anchor_calibration
        current_names=json.loads((current_attempt_root/'skeleton.json').read_text())['joint_names']
        current_reference=json.loads((current_attempt_root/'reference-proportions.json').read_text())
        current_offsets=validate_face_anchor_calibration(current_face_calibration_record,current_reference['weighted_body_face_candidate'],current_names)
        current_head_index=current_names.index('Head')
        current_face_anchor_positions=current_joint_positions[:,current_head_index,None,:]+np.einsum('fij,kj->fki',current_joint_rotations[:,current_head_index],current_offsets)
    current_mesh_frames = []
    with torch.inference_mode():
        for current_frame_index in range(len(current_joint_positions)):
            current_mesh_vertices = current_skin_model.skin(
                torch.as_tensor(current_joint_rotations[current_frame_index:current_frame_index+1], device='cuda', dtype=torch.float32),
                torch.as_tensor(current_joint_positions[current_frame_index:current_frame_index+1], device='cuda', dtype=torch.float32),
                rot_is_global=True).cpu().numpy()[0]
            if not np.isfinite(current_mesh_vertices).all():
                raise ValueError('SOMA 메시 비유한 좌표')
            current_mesh_frames.append(current_mesh_vertices)
    current_mesh_frames = np.asarray(current_mesh_frames)
    current_face_indices = current_skin_model.faces.cpu().numpy()
    current_video_renderer = pyrender.OffscreenRenderer(SOMA_RENDER_WIDTH, SOMA_RENDER_HEIGHT)
    current_renderer_name = glGetString(GL_RENDERER).decode()
    if any(current_software_name in current_renderer_name.lower() for current_software_name in ('llvmpipe', 'softpipe', 'software')):
        current_video_renderer.delete()
        raise RuntimeError(f'GPU 렌더러 필요: {current_renderer_name}')
    current_output_records = {}
    current_camera_records = {}
    current_face_depth_records = {}
    try:
        for current_direction_name, current_direction_angle in current_direction_angles.items():
            current_rotation_matrix = build_soma_camera_rotation(current_direction_angle,current_elevation_angle)
            current_rotated_vertices = current_mesh_frames @ current_rotation_matrix.T
            current_minimum_bounds = current_rotated_vertices.min(axis=(0, 1))
            current_maximum_bounds = current_rotated_vertices.max(axis=(0, 1))
            current_center_position = (current_minimum_bounds+current_maximum_bounds)/2
            current_half_height = max((current_maximum_bounds-current_minimum_bounds)[1]/2, (current_maximum_bounds-current_minimum_bounds)[0]/2*SOMA_RENDER_HEIGHT/SOMA_RENDER_WIDTH)/(current_scale_percent/100)
            current_camera_records[current_direction_name] = {'rotation_matrix': current_rotation_matrix.tolist(), 'center_position': current_center_position.tolist(), 'half_height': float(current_half_height), 'width': SOMA_RENDER_WIDTH, 'height': SOMA_RENDER_HEIGHT, 'elevation_degrees':current_elevation_angle}
            current_render_scene = pyrender.Scene(bg_color=[255, 255, 255, 255], ambient_light=[0.45, 0.45, 0.45])
            current_camera_pose = np.eye(4)
            current_camera_pose[:3, 3] = current_center_position+[0, 0, 6]
            current_render_scene.add(pyrender.OrthographicCamera(xmag=current_half_height*SOMA_RENDER_WIDTH/SOMA_RENDER_HEIGHT, ymag=current_half_height, znear=SOMA_CAMERA_NEAR_PLANE, zfar=SOMA_CAMERA_FAR_PLANE), pose=current_camera_pose)
            current_render_scene.add(pyrender.DirectionalLight(color=np.ones(3), intensity=2.0), pose=current_camera_pose)
            current_mesh_material = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.65, 0.55, 0.45, 1], metallicFactor=0, roughnessFactor=0.85)
            current_output_path = current_attempt_root/f'soma-render-{current_direction_name}.mp4'
            current_direction_depth=[]
            with imageio.get_writer(str(current_output_path), fps=SOMA_RENDER_FPS, codec='libx264', quality=8, macro_block_size=1) as current_video_writer:
                for current_frame_index,current_frame_vertices in enumerate(current_rotated_vertices):
                    current_mesh_object = trimesh.Trimesh(vertices=current_frame_vertices, faces=current_face_indices, process=False)
                    current_mesh_node = current_render_scene.add(pyrender.Mesh.from_trimesh(current_mesh_object, material=current_mesh_material, smooth=True))
                    current_color_image,current_depth_image = current_video_renderer.render(current_render_scene)
                    if current_face_anchor_positions is not None:
                        current_linear_depth=convert_orthographic_render_depth(current_depth_image,SOMA_CAMERA_NEAR_PLANE,SOMA_CAMERA_FAR_PLANE)
                        current_direction_depth.append(measure_face_anchor_depth(current_face_anchor_positions[current_frame_index],current_camera_records[current_direction_name],current_linear_depth))
                    current_video_writer.append_data(current_color_image)
                    current_render_scene.remove_node(current_mesh_node)
            current_output_records[current_direction_name] = current_output_path.name
            if current_face_anchor_positions is not None:
                current_face_depth_records[current_direction_name]=current_direction_depth
    finally:
        current_video_renderer.delete()
    if current_face_anchor_positions is not None:
        write_record_atomically(current_attempt_root/'soma-face-anchor-depth.json',{'schema':'kimodo-face-anchor-depth-v2','depth_conversion':'pyrender 원근 역변환을 역산한 직교 선형 깊이','near_plane':SOMA_CAMERA_NEAR_PLANE,'far_plane':SOMA_CAMERA_FAR_PLANE,'fps':SOMA_RENDER_FPS,'unit':'SOMA 좌표 단위','face_anchor_binding':current_face_calibration_record['binding_sha256'],'directions':current_face_depth_records,'limitations':['깊이 차이는 앵커가 실제 표면에 놓였다는 보장이 없어 가림 판정이 아님','한 픽셀 표면 깊이로 경계·자체 가림과 외부 가림을 분리할 수 없음','0 또는 화면 밖은 표면 미측정으로 기록']})
    write_record_atomically(current_attempt_root/'soma-render.json', {'source': current_motion_path.name, 'skinning': 'Kimodo SOMASkin', 'source_revision': KIMODO_ASSET_CONFIG['source_revision'], 'renderer': current_renderer_name, 'fps': SOMA_RENDER_FPS, 'width': SOMA_RENDER_WIDTH, 'height': SOMA_RENDER_HEIGHT, 'scale_percent': current_scale_percent, 'videos': current_output_records, 'cameras': current_camera_records})
    return current_output_records
