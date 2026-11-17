"""공용 포즈 가중치만 독립적으로 준비한다."""
import subprocess
from generators.dwpose.contracts import DWPOSE_WORKSPACE_ROOT, validate_fun_pose_assets
from generators.wan_fun.contracts import FUN_PYTHON_EXECUTABLE
from tools.review.common.management_setup import hold_shared_environment_reservation


def prepare_dwpose_model_files():
    if not FUN_PYTHON_EXECUTABLE.is_file():
        raise ValueError('DWPose ROCm 환경이 없습니다. workflow.sh setup --scope wan-fun-runtime을 먼저 실행하세요.')
    with hold_shared_environment_reservation():
        try:
            validate_fun_pose_assets()
        except (OSError, ValueError):
            subprocess.run([str(FUN_PYTHON_EXECUTABLE), '-m', 'generators.wan_fun.prepare_pose'], cwd=DWPOSE_WORKSPACE_ROOT, check=True)
            validate_fun_pose_assets()
