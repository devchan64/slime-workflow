"""과거 Fun Control SOMA 작업 재개를 위한 호환 진입점."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from generators.kimodo.dwpose_runtime import *

if __name__ == '__main__':
    import runpy
    runpy.run_module('generators.kimodo.dwpose_runtime', run_name='__main__')
