"""기존 게이트웨이 경로를 위한 호환 진입점."""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    runpy.run_module('gateway.server', run_name='__main__')
else:
    from gateway import server
    sys.modules[__name__] = server
