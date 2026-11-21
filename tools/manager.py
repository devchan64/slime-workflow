"""통합 관리 게이트웨이의 CLI 진입점."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cli.__main__ import main


if __name__ == '__main__':
    sys.exit(main())
