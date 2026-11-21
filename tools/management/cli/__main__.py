"""통합 관리 게이트웨이 CLI."""
import sys

from tools.management.common.management_gateway import execute_gateway_cli


def main():
    try:
        return execute_gateway_cli()
    except (ValueError, OSError) as management_command_error:
        print(str(management_command_error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
