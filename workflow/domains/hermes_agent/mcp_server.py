"""이전 Hermes MCP 경로의 호환 진입점."""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'mcp'))
if __name__ == '__main__':
    runpy.run_module('hermes_server', run_name='__main__')
else:
    import hermes_server
    sys.modules[__name__] = hermes_server
