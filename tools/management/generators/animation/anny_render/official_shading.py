"""VNCCS의 흰색 환경광·윤곽 셰이딩을 Cycles에서 재현한다.

공식 keepOriginalLighting=true의 무텍스처 흰색 Phong 재질에 한정한다.
직접광이 없어 specular/shininess 항은 기여하지 않는다. WebGL의 보간
노멀·래스터 AA와 Cycles의 정규화 노멀·샘플링 차이는 남는다.
"""
import math

OFFICIAL_SHADING_VERSION = 'vnccs-white-ambient-rim-cycles-v1'
OFFICIAL_SOURCE_REVISION = 'eedaed79a7c42d2570d832cc5d2e0a2da5ab022d'
OFFICIAL_RIM_EXPONENT = 3.0
OFFICIAL_RIM_STRENGTH = 0.4
OFFICIAL_BASE_SRGB = 1.055 * (1.0 / math.pi) ** (1.0 / 2.4) - 0.055


def apply_official_shading(current_render_scene, current_body_object):
    """포즈·카메라·알파는 유지하고 재질과 색 관리만 고정한다."""
    import bpy

    current_render_scene.view_settings.view_transform = 'Standard'
    current_render_scene.view_settings.look = 'None'
    current_render_scene.view_settings.exposure = 0
    current_render_scene.view_settings.gamma = 1
    current_render_scene.view_settings.use_curve_mapping = False
    current_render_scene.display_settings.display_device = 'sRGB'
    current_render_scene.world.use_nodes = True
    current_render_scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0
    current_material_record = bpy.data.materials.new(OFFICIAL_SHADING_VERSION)
    current_material_record.use_nodes = True
    current_shader_nodes = current_material_record.node_tree.nodes
    current_shader_links = current_material_record.node_tree.links
    current_shader_nodes.clear()

    def append_scalar_operation(current_operation_name, current_input_socket, current_constant_value=0, constant_first_input=False):
        current_math_node = current_shader_nodes.new('ShaderNodeMath')
        current_math_node.operation = current_operation_name
        current_math_node.inputs[0 if constant_first_input else 1].default_value = current_constant_value
        current_shader_links.new(current_input_socket, current_math_node.inputs[1 if constant_first_input else 0])
        return current_math_node.outputs[0]

    current_geometry_node = current_shader_nodes.new('ShaderNodeNewGeometry')
    current_transform_node = current_shader_nodes.new('ShaderNodeVectorTransform')
    current_transform_node.vector_type = 'NORMAL'
    current_transform_node.convert_from = 'WORLD'
    current_transform_node.convert_to = 'CAMERA'
    current_shader_links.new(current_geometry_node.outputs['Normal'], current_transform_node.inputs[0])
    current_separate_node = current_shader_nodes.new('ShaderNodeSeparateXYZ')
    current_shader_links.new(current_transform_node.outputs[0], current_separate_node.inputs[0])
    current_scalar_socket = append_scalar_operation('ABSOLUTE', current_separate_node.outputs['Z'])
    current_scalar_socket = append_scalar_operation('SUBTRACT', current_scalar_socket, 1, True)
    current_scalar_socket = append_scalar_operation('POWER', current_scalar_socket, OFFICIAL_RIM_EXPONENT)
    current_scalar_socket = append_scalar_operation('MULTIPLY', current_scalar_socket, OFFICIAL_RIM_STRENGTH)
    current_scalar_socket = append_scalar_operation('SUBTRACT', current_scalar_socket, 1, True)
    current_scalar_socket = append_scalar_operation('MULTIPLY', current_scalar_socket, OFFICIAL_BASE_SRGB)
    # 공식 shader는 sRGB 출력 변환 후 rim을 곱한다. 역변환해 Emission에 입력한다.
    # 출력 범위 0.36~0.60이므로 sRGB의 선형 저휘도 분기는 필요하지 않다.
    current_scalar_socket = append_scalar_operation('ADD', current_scalar_socket, 0.055)
    current_scalar_socket = append_scalar_operation('DIVIDE', current_scalar_socket, 1.055)
    current_scalar_socket = append_scalar_operation('POWER', current_scalar_socket, 2.4)
    current_emission_node = current_shader_nodes.new('ShaderNodeEmission')
    current_shader_links.new(current_scalar_socket, current_emission_node.inputs['Color'])
    current_output_node = current_shader_nodes.new('ShaderNodeOutputMaterial')
    current_shader_links.new(current_emission_node.outputs[0], current_output_node.inputs['Surface'])
    current_body_object.data.materials.clear()
    current_body_object.data.materials.append(current_material_record)
    for current_mesh_polygon in current_body_object.data.polygons:
        current_mesh_polygon.material_index = 0
    return {'profile': OFFICIAL_SHADING_VERSION, 'source_revision': OFFICIAL_SOURCE_REVISION,
            'lighting': 'white-ambient-1', 'rim_strength': OFFICIAL_RIM_STRENGTH,
            'rim_exponent': OFFICIAL_RIM_EXPONENT, 'color_transform': 'sRGB',
            'implementation': 'Cycles emission; normalized camera-space normal',
            'pixel_equivalence': False}
