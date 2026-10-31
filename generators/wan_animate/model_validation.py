"""ONNX 그래프와 외부 가중치의 경로·크기를 검사한다. GPU 연산은 하지 않는다."""
from pathlib import Path
import sys


def validate_external_tensor_files(current_model_path,current_external_records):
    current_model_root=current_model_path.parent.resolve()
    for current_external_record in current_external_records:
        current_location_text=current_external_record.get('location')
        if not current_location_text:
            raise ValueError('ONNX 외부 가중치 location 누락')
        current_tensor_path=(current_model_root/current_location_text).resolve()
        if not current_tensor_path.is_relative_to(current_model_root) or not current_tensor_path.is_file():
            raise ValueError(f'ONNX 외부 가중치 누락 또는 경로 오류: {current_tensor_path}')
        current_tensor_offset=int(current_external_record.get('offset','0'))
        current_tensor_length=int(current_external_record.get('length','0'))
        if current_tensor_offset<0 or current_tensor_length<0 or current_tensor_path.stat().st_size<=0 or current_tensor_path.stat().st_size<current_tensor_offset+current_tensor_length:
            raise ValueError(f'ONNX 외부 가중치 크기 오류: {current_tensor_path}')


def validate_onnx_model_bundle(current_bundle_path):
    import onnx
    from onnx.external_data_helper import _get_all_tensors
    current_model_path=current_bundle_path/'end2end.onnx' if current_bundle_path.is_dir() else current_bundle_path
    if not current_model_path.is_file():
        raise ValueError(f'ONNX 그래프 누락: {current_model_path}')
    current_model_graph=onnx.load(str(current_model_path),load_external_data=False)
    current_external_records=[{current_entry_value.key:current_entry_value.value for current_entry_value in current_tensor_value.external_data} for current_tensor_value in _get_all_tensors(current_model_graph) if current_tensor_value.data_location==onnx.TensorProto.EXTERNAL]
    validate_external_tensor_files(current_model_path,current_external_records)
    print(f'ONNX 준비 확인: {current_model_path} · 외부 텐서 {len(current_external_records)}개',flush=True)


if __name__=='__main__':
    validate_onnx_model_bundle(Path(sys.argv[1]))
