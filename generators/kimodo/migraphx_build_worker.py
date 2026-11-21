"""공용 GPU 대기열에서 DWPose MIGraphX 빌드를 실행한다."""
import importlib.util
import os
from pathlib import Path
import sys

current_workspace_root = Path(__file__).resolve().parents[2]
current_library_paths = []
for current_module_name, current_library_directory in (('onnxruntime', 'capi'), ('migraphx_libs', '')):
    current_module_spec = importlib.util.find_spec(current_module_name)
    if current_module_spec and current_module_spec.submodule_search_locations:
        current_library_paths.append(str(Path(next(iter(current_module_spec.submodule_search_locations)))/current_library_directory))
if os.environ.get('LD_LIBRARY_PATH'):
    current_library_paths.append(os.environ['LD_LIBRARY_PATH'])
current_process_environment = dict(os.environ, LD_LIBRARY_PATH=os.pathsep.join(current_library_paths))
os.chdir(current_workspace_root)
os.execve(sys.executable, [sys.executable, '-m', 'generators.kimodo.migraphx_build', *sys.argv[1:]], current_process_environment)
