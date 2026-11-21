"""기존 GUI 서버 경로의 호환 진입점."""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    runpy.run_module('gui.serve', run_name='__main__')
else:
    from gui import serve
    sys.modules[__name__] = serve
