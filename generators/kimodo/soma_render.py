"""공식 SOMASkin 메시를 선택 방향의 단일 인체 영상으로 렌더링한다."""
import importlib.util
import math
import os
from pathlib import Path

SOMA_RENDER_WIDTH = 832
SOMA_RENDER_HEIGHT = 480
SOMA_RENDER_FPS = 30


def render_soma_motion(current_attempt_root, current_direction_angles, current_scale_percent=85.0):
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
    try:
        for current_direction_name, current_direction_angle in current_direction_angles.items():
            current_rotation_angle = math.radians(current_direction_angle)
            current_rotation_matrix = np.array([[math.cos(current_rotation_angle), 0, -math.sin(current_rotation_angle)], [0, 1, 0], [math.sin(current_rotation_angle), 0, math.cos(current_rotation_angle)]])
            current_rotated_vertices = current_mesh_frames @ current_rotation_matrix.T
            current_minimum_bounds = current_rotated_vertices.min(axis=(0, 1))
            current_maximum_bounds = current_rotated_vertices.max(axis=(0, 1))
            current_center_position = (current_minimum_bounds+current_maximum_bounds)/2
            current_half_height = max((current_maximum_bounds-current_minimum_bounds)[1]/2, (current_maximum_bounds-current_minimum_bounds)[0]/2*SOMA_RENDER_HEIGHT/SOMA_RENDER_WIDTH)/(current_scale_percent/100)
            current_render_scene = pyrender.Scene(bg_color=[255, 255, 255, 255], ambient_light=[0.45, 0.45, 0.45])
            current_camera_pose = np.eye(4)
            current_camera_pose[:3, 3] = current_center_position+[0, 0, 6]
            current_render_scene.add(pyrender.OrthographicCamera(xmag=current_half_height*SOMA_RENDER_WIDTH/SOMA_RENDER_HEIGHT, ymag=current_half_height, znear=0.01, zfar=100), pose=current_camera_pose)
            current_render_scene.add(pyrender.DirectionalLight(color=np.ones(3), intensity=2.0), pose=current_camera_pose)
            current_mesh_material = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.65, 0.55, 0.45, 1], metallicFactor=0, roughnessFactor=0.85)
            current_output_path = current_attempt_root/f'soma-render-{current_direction_name}.mp4'
            with imageio.get_writer(str(current_output_path), fps=SOMA_RENDER_FPS, codec='libx264', quality=8, macro_block_size=1) as current_video_writer:
                for current_frame_vertices in current_rotated_vertices:
                    current_mesh_object = trimesh.Trimesh(vertices=current_frame_vertices, faces=current_face_indices, process=False)
                    current_mesh_node = current_render_scene.add(pyrender.Mesh.from_trimesh(current_mesh_object, material=current_mesh_material, smooth=True))
                    current_color_image, _ = current_video_renderer.render(current_render_scene)
                    current_video_writer.append_data(current_color_image)
                    current_render_scene.remove_node(current_mesh_node)
            current_output_records[current_direction_name] = current_output_path.name
    finally:
        current_video_renderer.delete()
    write_record_atomically(current_attempt_root/'soma-render.json', {'source': current_motion_path.name, 'skinning': 'Kimodo SOMASkin', 'source_revision': KIMODO_ASSET_CONFIG['source_revision'], 'renderer': current_renderer_name, 'fps': SOMA_RENDER_FPS, 'width': SOMA_RENDER_WIDTH, 'height': SOMA_RENDER_HEIGHT, 'scale_percent': current_scale_percent, 'videos': current_output_records})
    return current_output_records
