"""Read-only comparison of restored audio components with backup observations."""
import argparse
import json
import sys
import time

from workflow.common.model_backup_service import compare_backup_model, verify_snapshot_manifest

COMPONENTS = {
    'sfx-dasheng-audiogen': ('dasheng-audiogen', 'flan-t5-large', 'dasheng-tokenizer'),
    'music-heartmula': ('heartmula-oss-3b', 'heartcodec-oss', 'demucs'),
}
REQUIRED = {
    'sfx-dasheng-audiogen': {
        'dasheng-audiogen': ('config.json', 'model.safetensors', 'configuration_dasheng_audiogen.py', 'modeling_dasheng_audiogen.py'),
        'flan-t5-large': ('config.json', 'model.safetensors', 'spiece.model', 'tokenizer_config.json'),
        'dasheng-tokenizer': ('config.json', 'model.safetensors', 'configuration_dasheng_tokenizer.py', 'modeling_dasheng_tokenizer.py'),
    },
    'music-heartmula': {
        'heartmula-oss-3b': ('config.json', 'model.safetensors.index.json', 'generation/tokenizer.json', 'generation/gen_config.json',
                             *(f'model-{index:05d}-of-00004.safetensors' for index in range(1, 5))),
        'heartcodec-oss': ('config.json', 'model.safetensors.index.json',
                           *(f'model-{index:05d}-of-00002.safetensors' for index in range(1, 3))),
        'demucs': ('955717e8-8726e21a.th',),
    },
}


def check_restored_audio(service, config_path=None, *, progress=None):
    """Compare each installed tree and its latest snapshot without writing either.

    This establishes agreement with recorded backup hashes, not origin or runtime readiness.
    """
    if service not in COMPONENTS:
        raise ValueError('지원하지 않는 오디오 서비스입니다.')
    components = []
    for model in COMPONENTS[service]:
        try:
            report = (lambda phase, path, done, total: progress(model, phase, path, done, total)) if progress else None
            snapshot = verify_snapshot_manifest(model, config_path, progress=report)
            local = compare_backup_model(model, config_path, hash_content=True, target='latest_snapshot', progress=report)
            same_snapshot = snapshot['snapshot_id'] == local['snapshot_id']
            snapshot_files, local_files = snapshot['files'], local['files']
            valid = (snapshot['complete'] and local['complete'] and same_snapshot
                     and bool(snapshot_files) and bool(local_files)
                     and all(item['status'] == 'verified' for item in snapshot_files)
                     and all(item['status'] == 'verified' for item in local_files))
            partials = [item['path'] for item in local_files if item['path'].endswith(('.partial', '.incomplete'))]
            local_paths = {item['path'] for item in local_files if item['status'] == 'verified'
                           and isinstance(item.get('source'), dict) and item['source'].get('size', 0) > 0}
            missing_required = [name for name in REQUIRED.get(service, {}).get(model, ()) if name not in local_paths]
            differences = [{'stage': stage, 'path': item['path'], 'status': item['status']}
                           for stage, items in (('snapshot', snapshot_files), ('local', local_files))
                           for item in items if item['status'] != 'verified']
            components.append({'model': model, 'snapshot_id': snapshot['snapshot_id'], 'matches': valid,
                               'files': len(local_files), 'partial_files': len(partials),
                               'missing_required': missing_required,
                               'difference_count': len(differences), 'differences': differences[:20],
                               'comparison_complete': snapshot['complete'] and local['complete'],
                               'same_snapshot': same_snapshot,
                               'local_comparison_snapshot_id': local['snapshot_id'],
                               'inventory_errors': [{'stage': stage, 'path': error.get('path'), 'reason': error.get('reason')}
                                                    for stage, result in (('snapshot', snapshot), ('local', local))
                                                    for key in ('source_errors', 'backup_errors')
                                                    for error in result.get(key, [])][:20]})
        except (OSError, ValueError, KeyError, TypeError) as error:
            components.append({'model': model, 'matches': None, 'error': str(error)})
    return {'service': service, 'components': components,
            'matches': all(item['matches'] is True and item['partial_files'] == 0 and not item['missing_required'] for item in components),
            'note': '백업 당시 관측한 해시 기준입니다. 공급처 원본 인증 및 서비스 준비·추론 성공은 별도입니다.'}


def main():
    parser = argparse.ArgumentParser(description='복원된 오디오 모델과 완료 스냅샷을 읽기 전용 SHA-256 비교')
    parser.add_argument('service', choices=COMPONENTS)
    args = parser.parse_args()
    last_report = 0.0
    last_phase = None
    def report(model, phase, path, done, total):
        nonlocal last_report, last_phase
        now = time.monotonic()
        if (model, phase) != last_phase or now - last_report >= 5:
            print(f'{model} · {phase} · {path} · {done}/{total} 바이트', file=sys.stderr, flush=True)
            last_report, last_phase = now, (model, phase)
    result = check_restored_audio(args.service, progress=report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['matches'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
