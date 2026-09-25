"""이전 import·실행 경로 호환용. 구현은 domains/character_animation/character_animation.py에 있다."""
import sys
from pathlib import Path
from importlib import import_module
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
if __name__=='__main__':
    import runpy
    runpy.run_module('tools.review.domains.character_animation.character_animation',run_name='__main__')
else:
    sys.modules[__name__]=import_module('tools.review.domains.character_animation.character_animation')
