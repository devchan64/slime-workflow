"""공식 VNCCS v2 팩의 고정 기본 체형을 재현 가능한 제작 자산으로 추출한다."""
import gzip
import hashlib
import json
import struct
from pathlib import Path
import shutil
import sys
import numpy as np
import yaml


def import_makehuman_asset(source_pack_path, target_asset_directory):
    source_pack_path = Path(source_pack_path)
    target_asset_directory = Path(target_asset_directory)
    source_binary_data = gzip.decompress(source_pack_path.read_bytes())
    if source_binary_data[:8] != b'VNMHJS02':
        raise ValueError('지원하지 않는 VNCCS 팩')
    source_header_length = struct.unpack_from('<I', source_binary_data, 8)[0]
    source_header_record = json.loads(source_binary_data[12:12 + source_header_length])
    if source_header_record['version'] != 2:
        raise ValueError('VNCCS v2 팩이 필요합니다')
    source_data_offset = (12 + source_header_length + 3) // 4 * 4
    source_array_values = {}
    for source_field_name, source_field_dtype in {'base_vertices': '<f4', 'base_indices': '<u4', 'skin_indices': '<u2', 'skin_weights': '<f4'}.items():
        source_field_record = source_header_record[source_field_name]
        source_array_values[source_field_name] = np.frombuffer(source_binary_data, dtype=source_field_dtype, count=source_field_record['length'], offset=source_data_offset + source_field_record['offset']).copy()
    source_mesh_vertices = source_array_values['base_vertices'].reshape(-1, 3) * .1
    source_mesh_vertices[:, 1] -= source_mesh_vertices[:, 1].min()
    target_axis_matrix = np.array(((1., 0., 0.), (0., 0., -1.), (0., 1., 0.)))
    target_mesh_vertices = source_mesh_vertices @ target_axis_matrix.T
    target_bone_names = [current_bone_record['name'] for current_bone_record in source_header_record['bones']]
    target_bone_heads = np.array([target_mesh_vertices[source_header_record['joints'][current_bone_record['head_joint']]].mean(0) for current_bone_record in source_header_record['bones']])
    target_bone_tails = np.array([target_mesh_vertices[source_header_record['joints'][current_bone_record['tail_joint']]].mean(0) for current_bone_record in source_header_record['bones']])
    target_parent_indices = np.array([target_bone_names.index(current_bone_record['parent']) if current_bone_record['parent'] is not None else -1 for current_bone_record in source_header_record['bones']])
    if not np.isfinite(target_mesh_vertices).all() or source_array_values['base_indices'].max() >= len(target_mesh_vertices):
        raise ValueError('MakeHuman 메쉬 오류')
    target_asset_directory.mkdir(parents=True, exist_ok=False)
    target_bundle_path = target_asset_directory / 'rig.npz'
    np.savez_compressed(target_bundle_path, vertices=target_mesh_vertices, triangles=source_array_values['base_indices'].reshape(-1, 3), skin_indices=source_array_values['skin_indices'].reshape(-1, 4), skin_weights=source_array_values['skin_weights'].reshape(-1, 4), bone_names=np.array(target_bone_names), parent_indices=target_parent_indices, rest_heads=target_bone_heads, rest_tails=target_bone_tails)
    shutil.copy2(source_pack_path.with_name('pose_studio_makehuman.v2.CC0-1.0.md'), target_asset_directory / 'LICENSE.md')
    target_manifest_record = {'schema_version': 1, 'id': 'vnccs-makehuman-base', 'version': 1, 'source': 'https://github.com/AHEKOT/ComfyUI_VNCCS_Utils', 'revision': 'eedaed79a7c42d2570d832cc5d2e0a2da5ab022d', 'source_sha256': hashlib.sha256(source_pack_path.read_bytes()).hexdigest(), 'sha256': hashlib.sha256(target_bundle_path.read_bytes()).hexdigest(), 'license': 'CC0-1.0', 'units': 'meter', 'coordinate_system': 'right-handed Z-up', 'shape': 'base vertices, no morph targets applied', 'status': 'retarget-candidate-not-quality-approved'}
    (target_asset_directory / 'manifest.yaml').write_text(yaml.safe_dump(target_manifest_record, allow_unicode=True, sort_keys=False))
    print('MakeHuman 자산 추출 완료:', target_asset_directory)


if __name__ == '__main__':
    import_makehuman_asset(sys.argv[1], sys.argv[2])
