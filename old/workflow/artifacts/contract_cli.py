"""명시적 YAML 계약을 로컬 registry에 등록한다. 승인이나 에셋 제작을 수행하지 않는다."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from threading import Event, Thread
import traceback
from .contracts import register_contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    if args.log.resolve() == args.registry.resolve():
        parser.error('로그와 registry는 다른 파일이어야 합니다.')
    if args.log.resolve().is_relative_to(args.contract.resolve().parent):
        parser.error('로그는 계약 원본 디렉터리 밖에 지정해야 합니다.')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    def log(stage, message):
        line = f'{datetime.now().astimezone().isoformat(timespec="seconds")}/artifact-contract/{stage} {message}'
        print(line, flush=True)
        with args.log.open('a', encoding='utf-8') as output:
            output.write(line + '\n')
    stopped = Event()
    def heartbeat():
        while not stopped.wait(5):
            log('heartbeat', '계약 YAML 검증·불변 버전 등록 처리 중')
    thread = Thread(target=heartbeat, daemon=True)
    log('start', str(args.contract))
    thread.start()
    try:
        entry = register_contract(args.registry, args.contract)
        log('complete', json.dumps({k: entry[k] for k in ('contract_id','version','management_id','definition_hash')}, ensure_ascii=False))
    except Exception:
        log('failure', traceback.format_exc())
        raise SystemExit(1)
    finally:
        stopped.set(); thread.join()


if __name__ == '__main__':
    main()
