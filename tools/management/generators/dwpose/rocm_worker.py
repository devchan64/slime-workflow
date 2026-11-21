"""DWPose 작업을 ROCm 공유 라이브러리 경로와 함께 실행한다."""
import importlib.util
import os
from pathlib import Path
import sys

current_workspace_root = Path(__file__).resolve().parents[4]
current_library_paths = []
for current_module_name, current_library_directory in (('onnxruntime', 'capi'), ('migraphx_libs', '')):
    current_module_spec = importlib.util.find_spec(current_module_name)
    if not current_module_spec or not current_module_spec.submodule_search_locations:
        raise RuntimeError(f'DWPose ROCm 실행 의존성 누락: {current_module_name}. 모델 관리에서 Wan Fun Control을 준비하세요.')
    current_library_paths.append(str(Path(next(iter(current_module_spec.submodule_search_locations))) / current_library_directory))
if os.environ.get('LD_LIBRARY_PATH'):
    current_library_paths.append(os.environ['LD_LIBRARY_PATH'])
os.chdir(current_workspace_root)
os.execve(sys.executable, [sys.executable, '-m', 'generators.dwpose.worker', *sys.argv[1:]],
          dict(os.environ, LD_LIBRARY_PATH=os.pathsep.join(current_library_paths)))
