"""통합 관리 게이트웨이의 CLI 진입점."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.review.common.management_gateway import execute_gateway_cli


if __name__ == '__main__':
    try:
        sys.exit(execute_gateway_cli())
    except (ValueError, OSError) as management_command_error:
        print(str(management_command_error), file=sys.stderr)
        sys.exit(1)
