"""이전 import·실행 경로 호환용. 구현은 domains/image/image_generation.py에 있다."""
import sys
from pathlib import Path
from importlib import import_module
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __name__=='__main__':
    import runpy
    runpy.run_module('workflow.domains.image.image_generation',run_name='__main__')
else:
    sys.modules[__name__]=import_module('workflow.domains.image.image_generation')
