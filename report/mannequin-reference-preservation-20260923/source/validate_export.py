"""내보낸 GLB의 스킨 가중치·본·애니메이션 계약을 검증한다."""
from pathlib import Path
import json,struct,numpy as np,hashlib
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
GLTF_COMPONENT_TYPES={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}
GLTF_ELEMENT_COUNTS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
source_binary_bytes=(EXPERIMENT_OUTPUT_ROOT/'rigged-mannequin.glb').read_bytes()
header_magic_value,header_version_value,header_length_value=struct.unpack_from('<4sII',source_binary_bytes)
assert header_magic_value==b'glTF' and header_version_value==2 and header_length_value==len(source_binary_bytes)
json_chunk_length,json_chunk_type=struct.unpack_from('<II',source_binary_bytes,12)
gltf_document_record=json.loads(source_binary_bytes[20:20+json_chunk_length])
binary_chunk_offset=20+json_chunk_length
binary_chunk_length,binary_chunk_type=struct.unpack_from('<II',source_binary_bytes,binary_chunk_offset)
binary_payload_bytes=source_binary_bytes[binary_chunk_offset+8:binary_chunk_offset+8+binary_chunk_length]

def read_accessor_values(accessor_index_value):
 accessor_record_value=gltf_document_record['accessors'][accessor_index_value]
 buffer_view_record=gltf_document_record['bufferViews'][accessor_record_value['bufferView']]
 element_type_value=np.dtype(GLTF_COMPONENT_TYPES[accessor_record_value['componentType']]);element_width_value=GLTF_ELEMENT_COUNTS[accessor_record_value['type']]
 byte_offset_value=buffer_view_record.get('byteOffset',0)+accessor_record_value.get('byteOffset',0)
 stride_byte_count=buffer_view_record.get('byteStride',element_type_value.itemsize*element_width_value)
 return np.ndarray((accessor_record_value['count'],element_width_value),dtype=element_type_value,buffer=binary_payload_bytes,offset=byte_offset_value,strides=(stride_byte_count,element_type_value.itemsize)).copy()

skinned_primitive_count=0;triangle_total_count=0
for mesh_record_value in gltf_document_record['meshes']:
 for primitive_record_value in mesh_record_value['primitives']:
  attribute_record_values=primitive_record_value['attributes']
  weight_accessor_values=read_accessor_values(attribute_record_values['WEIGHTS_0'])
  assert np.allclose(weight_accessor_values.sum(axis=1),1) and np.all((weight_accessor_values>1e-6).sum(axis=1)<=2)
  assert np.isfinite(read_accessor_values(attribute_record_values['POSITION'])).all()
  triangle_total_count+=len(read_accessor_values(primitive_record_value['indices']))//3
  skinned_primitive_count+=1
animation_record_values=gltf_document_record['animations'];assert animation_record_values
animation_duration_values=[]
for animation_record_value in animation_record_values:
 channel_end_times=[]
 for sampler_record_value in animation_record_value['samplers']:
  key_time_values=read_accessor_values(sampler_record_value['input']).ravel()
  assert np.all(np.diff(key_time_values)>0)
  assert np.isfinite(read_accessor_values(sampler_record_value['output'])).all()
  channel_end_times.append(float(key_time_values[-1]-key_time_values[0]))
 animation_duration_values.append(max(channel_end_times))
assert all(abs(duration_scalar_value-1.2)<1e-5 for duration_scalar_value in animation_duration_values)
export_validation_record={'status':'passed','meshes':len(gltf_document_record['meshes']),'skinned_primitives':skinned_primitive_count,'skin_joint_counts':[len(skin_record_value['joints']) for skin_record_value in gltf_document_record['skins']],'triangles':triangle_total_count,'animation_durations':animation_duration_values,'max_bones_per_vertex':2,'sha256':hashlib.sha256(source_binary_bytes).hexdigest()}
(EXPERIMENT_OUTPUT_ROOT/'export-validation.json').write_text(json.dumps(export_validation_record,indent=2))
print(export_validation_record)
