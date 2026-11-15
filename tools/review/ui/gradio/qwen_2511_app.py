"""기존 관리 화면 import 및 실행 호환 경로."""
import importlib
import runpy
import sys
from pathlib import Path

current_workspace_root = Path(__file__).resolve().parents[4]
if str(current_workspace_root) not in sys.path:
    sys.path.insert(0, str(current_workspace_root))

if __name__ == "__main__":
    runpy.run_module("tools.review.ui.shared.qwen_generator_page", run_name="__main__")
else:
    sys.modules[__name__] = importlib.import_module("tools.review.ui.shared.qwen_generator_page")
