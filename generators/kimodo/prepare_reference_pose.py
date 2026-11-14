"""Kimodo 참조 포즈용 공식 Wan2.2 코드와 고정 가중치를 준비한다."""
import hashlib
import subprocess
from pathlib import Path
from huggingface_hub import HfApi
from tools.review.common.model_huggingface_download import tracked_snapshot_download as snapshot_download
from tools.review.common.generation_records import write_record_atomically

REFERENCE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_SOURCE_ROOT = REFERENCE_WORKSPACE_ROOT/'.local/wan-reference-source'
REFERENCE_MODEL_ROOT = REFERENCE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess'
REFERENCE_SOURCE_REVISION = '1ea34ff48f87168174e12956e200b1d908b1c5ff'
REFERENCE_MODEL_REVISION = 'cb93a225fbaf1ca100f54e79da8f994995b689b3'
REFERENCE_MODEL_REPOSITORY = 'Wan-AI/Wan2.2-Animate-14B'
REFERENCE_FILE_PATTERNS = ['process_checkpoint/det/yolov10m.onnx','process_checkpoint/pose2d/vitpose_h_wholebody.onnx/*']


def prepare_reference_pose_assets():
    if not REFERENCE_SOURCE_ROOT.exists():
        subprocess.run(['git','clone','--filter=blob:none','--no-checkout','https://github.com/Wan-Video/Wan2.2.git',str(REFERENCE_SOURCE_ROOT)],check=True)
        subprocess.run(['git','-C',str(REFERENCE_SOURCE_ROOT),'checkout','--detach',REFERENCE_SOURCE_REVISION],check=True)
    current_revision_text=subprocess.check_output(['git','-C',str(REFERENCE_SOURCE_ROOT),'rev-parse','HEAD'],text=True).strip()
    if current_revision_text != REFERENCE_SOURCE_REVISION:
        raise ValueError('Wan2.2 참조 포즈 소스 리비전이 일치하지 않습니다.')
    snapshot_download(REFERENCE_MODEL_REPOSITORY,revision=REFERENCE_MODEL_REVISION,allow_patterns=REFERENCE_FILE_PATTERNS,local_dir=REFERENCE_MODEL_ROOT,token=False,max_workers=8)
    current_model_info=HfApi().model_info(REFERENCE_MODEL_REPOSITORY,revision=REFERENCE_MODEL_REVISION,files_metadata=True,token=False)
    current_model_files=[current_file_record for current_file_record in current_model_info.siblings if current_file_record.rfilename=='process_checkpoint/det/yolov10m.onnx' or current_file_record.rfilename.startswith('process_checkpoint/pose2d/vitpose_h_wholebody.onnx/')]
    if not current_model_files:
        raise ValueError('참조 포즈 파일 목록이 비어 있습니다.')
    for current_file_record in current_model_files:
        current_file_path=REFERENCE_MODEL_ROOT/current_file_record.rfilename
        if not current_file_record.lfs or not current_file_path.is_file() or current_file_path.stat().st_size!=current_file_record.size:
            raise ValueError(f'참조 포즈 가중치 누락 또는 크기 불일치: {current_file_path}')
        with current_file_path.open('rb') as current_file_stream:
            if hashlib.file_digest(current_file_stream,'sha256').hexdigest()!=current_file_record.lfs.sha256:
                raise ValueError(f'참조 포즈 가중치 해시 불일치: {current_file_path}')
    from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON
    current_graph_directory=REFERENCE_MODEL_ROOT/'process_checkpoint/pose2d/vitpose_h_wholebody.onnx'
    subprocess.run([str(KIMODO_ENVIRONMENT_PYTHON), '-m', 'generators.kimodo.prepare_reference_pose', '--fixed-graph', str(current_graph_directory)],cwd=REFERENCE_WORKSPACE_ROOT,check=True)
    write_record_atomically(REFERENCE_MODEL_ROOT/'prepared-reference.json', {'revision':REFERENCE_MODEL_REVISION,'files':{current_file_record.rfilename:{'size':current_file_record.size,'sha256':current_file_record.lfs.sha256} for current_file_record in current_model_files}})
    print(f'참조 포즈 가중치 {len(current_model_files)}개 검증 완료',flush=True)


def prepare_fixed_reference_graph(current_graph_directory):
    import onnx
    current_model_graph=onnx.load(str(current_graph_directory/'end2end.onnx'),load_external_data=False)
    current_model_graph.graph.input[0].type.tensor_type.shape.dim[0].dim_value=1
    current_model_graph.graph.output[0].type.tensor_type.shape.dim[0].dim_value=1
    onnx.save(current_model_graph,str(current_graph_directory/'end2end-rocm.onnx'))


if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--fixed-graph':
        prepare_fixed_reference_graph(Path(sys.argv[2]))
    elif len(sys.argv)==1:
        prepare_reference_pose_assets()
    else:
        raise SystemExit('지원하지 않는 인자')
