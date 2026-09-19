"""명시적으로 선택한 승인 에셋을 로컬 공개 ZIP으로 묶는다. 외부 업로드는 하지 않는다."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from threading import Event, Thread
import traceback
from .exporter import export_pack, selected_assets
from .registry import registered_entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--pack-id', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--asset', action='append', nargs=2, metavar=('ID', 'VERSION'), required=True)
    parser.add_argument('--release-root', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    try:
        selected = selected_assets(args.asset)
        entries = [registered_entry(args.registry, *key) for key in selected]
        if args.log.resolve() == args.registry.resolve():
            raise ValueError('로그와 registry는 다른 파일이어야 합니다.')
        if any(args.log.resolve().is_relative_to(Path(entry['root']).resolve()) for entry in entries):
            raise ValueError('로그는 모든 산출물 루트 밖에 지정해야 합니다.')
    except Exception as exc:
        parser.error(str(exc))
    args.log.parent.mkdir(parents=True, exist_ok=True)
    def log(stage, message):
        line = f'{datetime.now().astimezone().isoformat(timespec="seconds")}/artifact-pack/{stage} {message}'
        print(line, flush=True)
        with args.log.open('a', encoding='utf-8') as output:
            output.write(line + '\n')
    stopped = Event()
    def heartbeat():
        while not stopped.wait(5):
            log('heartbeat', f'{len(selected)}개 에셋의 승인·원본 재검증 및 ZIP 생성 중')
    thread = Thread(target=heartbeat, daemon=True)
    log('start', f'{args.pack_id}@{args.version}: {len(selected)}개 에셋')
    thread.start()
    try:
        result = export_pack(args.registry, args.pack_id, args.version, selected, args.release_root)
        log('complete', json.dumps(result, ensure_ascii=False, sort_keys=True))
    except Exception:
        log('failure', traceback.format_exc())
        raise SystemExit(1)
    finally:
        stopped.set(); thread.join()


if __name__ == '__main__':
    main()
