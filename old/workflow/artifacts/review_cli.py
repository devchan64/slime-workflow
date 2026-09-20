"""신뢰된 로컬 검수자의 선언을 조회·기록한다. 승인·권리 근거를 자동 생성하지 않는다."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from threading import Event, Thread
import traceback
from .registry import registered_entry
from .exporter import export_asset
from .reviews import current_review, record_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--artifact-id', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--log', type=Path, default=Path('.local/logs/artifact-review.log'))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('show', help='현재 검수와 대상 해시 조회')
    export = commands.add_parser('export', help='승인·권리 조건을 검사하고 로컬 공개 ZIP 생성')
    export.add_argument('--release-root', type=Path, required=True)
    record = commands.add_parser('record', help='명시적인 검수 결정 기록')
    for name in ('review-id', 'reviewer', 'evidence-ref', 'content-hash', 'metadata-hash'):
        record.add_argument('--' + name, required=True)
    record.add_argument('--decision', choices=('APPROVED', 'REJECTED'), required=True)
    record.add_argument('--previous-review-id')
    args = parser.parse_args()
    # 로그가 registry나 검수 대상 파일을 훼손하지 않도록 쓰기 전에 확인한다.
    if args.log.resolve() == args.registry.resolve():
        parser.error('검수 로그와 registry는 다른 파일이어야 합니다.')
    try:
        entry = registered_entry(args.registry, args.artifact_id, args.version)
    except Exception as exc:
        parser.error(str(exc))
    if args.log.resolve().is_relative_to(Path(entry['root']).resolve()):
        parser.error('검수 로그는 등록된 산출물 루트 밖에 지정해야 합니다.')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    def log(stage, message):
        line = f'{datetime.now().astimezone().isoformat(timespec="seconds")}/artifact-review/{stage} {message}'
        print(line, flush=True)
        with args.log.open('a', encoding='utf-8') as target:
            target.write(line + '\n')
    stopped = Event()
    def heartbeat():
        while not stopped.wait(5):
            log('heartbeat', '등록 대상 재검증·검수 기록 처리 중')
    thread = Thread(target=heartbeat, daemon=True)
    log('start', f'{args.command}: {args.artifact_id}@{args.version}')
    thread.start()
    try:
        if args.command == 'show':
            result = dict(artifactId=args.artifact_id, version=args.version,
                          contentHash=entry['content_hash'], metadataHash=entry['metadata_hash'],
                          review=current_review(args.registry, args.artifact_id, args.version))
        elif args.command == 'export':
            result = export_asset(args.registry, args.artifact_id, args.version, args.release_root)
        else:
            result = record_review(args.registry, args.artifact_id, args.version,
                review_id=args.review_id, decision=args.decision, reviewer=args.reviewer,
                evidence_ref=args.evidence_ref, content_hash=args.content_hash,
                metadata_hash=args.metadata_hash, previous_review_id=args.previous_review_id)
        log('complete', json.dumps(result, ensure_ascii=False, sort_keys=True))
    except Exception:
        log('failure', traceback.format_exc())
        raise SystemExit(1)
    finally:
        stopped.set()
        thread.join()


if __name__ == '__main__':
    main()
