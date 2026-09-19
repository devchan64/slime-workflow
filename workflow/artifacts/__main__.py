"""파일/sidecar 공통 계약 검사 CLI. 원본이나 공개 팩을 쓰지 않는다."""
import argparse
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
import traceback
from .sidecar import validate_pair
from .registry import register


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--sidecar', type=Path, required=True)
    parser.add_argument('--registry', type=Path, help='검증 후 등록할 로컬 registry DB (선택)')
    parser.add_argument('--log', type=Path, default=Path('.local/logs/artifact-validate.log'))
    args = parser.parse_args()
    if args.log.resolve().is_relative_to(args.root.resolve()):
        parser.error('검증 로그는 원본 보존을 위해 산출물 루트 밖에 지정해야 합니다.')
    if args.registry is not None and args.registry.resolve() == args.log.resolve():
        parser.error('registry와 로그는 다른 파일이어야 합니다.')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    def log(stage, message):
        line = f'{datetime.now().astimezone().isoformat(timespec="seconds")}/artifact-validate/{stage} {message}'
        print(line, flush=True)
        with args.log.open('a', encoding='utf-8') as target:
            target.write(line + '\n')
    stopped = Event()
    def heartbeat():
        while not stopped.wait(5):
            log('heartbeat', '파일·메타데이터·해시 검증 진행 중')
    thread = Thread(target=heartbeat, daemon=True)
    log('start', f'검증 시작, 로그={args.log}')
    thread.start()
    try:
        data = validate_pair(args.root, args.sidecar)
        if args.registry is not None:
            register(args.registry, args.root, args.sidecar)
            log('registered', f"등록 확인: {data['artifactId']}@{data['version']}")
        for warning in data['quality']['quality_warnings']:
            log('WARN', warning)
        log('complete', f"공통 계약 통과: {data['artifactId']}@{data['version']} (공개 승인 아님)")
    except Exception:
        log('failure', traceback.format_exc())
        raise SystemExit(1)
    finally:
        stopped.set()
        thread.join()


if __name__ == '__main__':
    main()
