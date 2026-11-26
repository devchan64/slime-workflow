"""Normalize existing model manifests without treating declarations as proof."""
import json
from pathlib import Path
import re

from workflow.common.model_backup_service import read_model_source, read_backup_roots, latest_model_snapshot
from workflow.common.model_file_inventory import resolve_model_inventory_paths
from workflow.common.model_backup_targets import target_path

SHA256 = re.compile(r'^[0-9a-fA-F]{64}$')


def model_metadata(model, *, config_path=None, service_paths=None):
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    source, _ = read_model_source(config_path)
    folder = target_path(source, model)
    origin = 'local'
    if folder.is_symlink():
        raise ValueError('모델 디렉터리를 찾을 수 없습니다.')
    if not folder.is_dir():
        _, backup, _ = read_backup_roots(config_path)
        snapshot = latest_model_snapshot(backup, model)
        if snapshot is None:
            folder = target_path(backup, model, layout_root=source)
            if folder.is_symlink() or not folder.is_dir():
                raise ValueError('모델과 백업을 찾을 수 없습니다.')
            origin = 'backup_directory'
        else:
            try:
                manifest = json.loads((snapshot / '.snapshot.json').read_text(encoding='utf-8'))
                saved = manifest.get('model_metadata')
                if not isinstance(saved, dict):
                    saved = {}
                result = {'version': 1, 'model': model, 'origin': 'backup_snapshot', 'snapshot_id': snapshot.name,
                          'manifest_state': saved.get('manifest_state', 'unavailable'),
                          'services': saved.get('services', []), 'declared_sources': saved.get('declared_sources', []),
                          'declared_files': saved.get('declared_files', []),
                          'note': '백업 시 저장한 선언값입니다. 현재 파일 검증 결과가 아닙니다.'}
                if any(not isinstance(result[name], list) for name in ('services', 'declared_sources', 'declared_files')):
                    raise ValueError('스냅샷 메타정보 형식 오류')
                return result
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise ValueError('백업 메타정보를 읽을 수 없습니다.') from error
    services = []
    paths = resolve_model_inventory_paths() if service_paths is None else service_paths
    for service, roots in paths.items():
        for path in roots:
            try:
                path = Path(path).resolve()
                if path == folder or path.is_relative_to(folder) or folder.is_relative_to(path):
                    services.append(service)
                    break
            except (OSError, ValueError):
                continue
    result = {'version': 1, 'model': model, 'origin': origin, 'services': sorted(services),
              'manifest_state': 'missing', 'declared_sources': [], 'declared_files': []}
    manifest = folder / 'manifest.json'
    preparation_record = False
    if not manifest.exists():
        manifest = folder / 'verified-manifest.json'
        if not manifest.exists():
            prepared = folder / 'prepared.json'
            if prepared.exists() or prepared.is_symlink():
                manifest = prepared
                preparation_record = True
            else:
                manifest = None
        if manifest is None:
            if model == 'qwen3vl-32b-minimax-h3-int8-convrot':
                from generators.minimax_h3.assets import FILES
                path, _, digest = FILES[1]
                result['manifest_state'] = 'code_pinned'
                result['declared_files'] = [{'path': Path(path).name, 'sha256': digest,
                                             'hash_origin': 'application_pinned',
                                             'repository': None, 'revision': None}]
                return result
            if model == 'umt5-xxl-tokenizer-vace':
                import yaml
                from generators.wan_vace.official_prepare import VACE_OFFICIAL_MANIFEST_PATH, VACE_ENCODER_IDENTIFIER, VACE_ENCODER_REVISION
                manifest_data = yaml.safe_load(VACE_OFFICIAL_MANIFEST_PATH.read_text())
                result['manifest_state'] = 'code_pinned'
                result['declared_sources'] = [{'repository': VACE_ENCODER_IDENTIFIER, 'revision': VACE_ENCODER_REVISION}]
                result['declared_files'] = [{'path': path, 'sha256': digest, 'hash_origin': 'application_pinned',
                                             'repository': VACE_ENCODER_IDENTIFIER, 'revision': VACE_ENCODER_REVISION}
                                            for path, digest in sorted(manifest_data['tokenizer_files'].items())]
                return result
            if model == 'umt5-xxl-encoder-bf16':
                from generators.wan_vace.contracts import VACE_MODEL_FILES, VACE_ENCODER_IDENTIFIER, VACE_ENCODER_REVISION
                path, _, digest = VACE_MODEL_FILES['encoder']
                result['manifest_state'] = 'code_pinned'
                result['declared_sources'] = [{'repository': VACE_ENCODER_IDENTIFIER, 'revision': VACE_ENCODER_REVISION}]
                result['declared_files'] = [{'path': Path(path).name, 'sha256': digest,
                                             'hash_origin': 'application_pinned',
                                             'repository': VACE_ENCODER_IDENTIFIER, 'revision': VACE_ENCODER_REVISION}]
                return result
            if model in ('yolov10m-animate', 'vitpose-h-wholebody-animate'):
                prefix = ('process_checkpoint/det/' if model == 'yolov10m-animate'
                          else 'process_checkpoint/pose2d/vitpose_h_wholebody.onnx/')
                record = source/'wan22-animate-preprocess'/'prepared-reference.json'
                try:
                    if record.parent.is_symlink() or record.is_symlink() or not record.is_file() or record.stat().st_size > 4 * 1024 * 1024:
                        raise ValueError('준비 기록을 확인할 수 없습니다.')
                    value = json.loads(record.read_text(encoding='utf-8'))
                    revision, files = value['revision'], value['files']
                    if not isinstance(revision, str) or not isinstance(files, dict):
                        raise ValueError('준비 기록 형식 오류')
                    for name, entry in files.items():
                        if not isinstance(name, str) or not name.startswith(prefix) or not isinstance(entry, dict):
                            continue
                        path, digest = Path(name[len(prefix):]), entry.get('sha256')
                        if (not path.parts or path.is_absolute() or '..' in path.parts
                                or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
                            raise ValueError('준비 기록 파일 형식 오류')
                        result['declared_files'].append({'path': path.as_posix(), 'sha256': digest.lower(),
                                                         'hash_origin': 'local_preparation_record',
                                                         'repository': None, 'revision': revision})
                    if not result['declared_files']:
                        raise ValueError('해당 모델의 준비 기록이 없습니다.')
                    result['manifest_state'] = 'prepared_record'
                except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError):
                    result['declared_files'] = []
                    result['manifest_state'] = 'unavailable'
                return result
            if model == 'wan22-lightning-i2v-seko-v1':
                from generators.wan_i2v.assets import FILES
                entries = [entry for entry in FILES if entry[0].startswith('lightning/')]
                result['manifest_state'] = 'code_pinned'
                result['declared_sources'] = [{'repository': repo, 'revision': revision}
                                              for repo, revision in sorted({(entry[1], entry[2]) for entry in entries})]
                result['declared_files'] = [{'path': Path(relative).name, 'sha256': digest,
                                             'hash_origin': 'application_pinned',
                                             'repository': repo, 'revision': revision}
                                            for relative, repo, revision, _, _, digest in entries]
                return result
            if model in ('wan22-fighting-lora-high', 'wan22-lightning-t2v-v11'):
                if model == 'wan22-fighting-lora-high':
                    from generators.wan_vace.fighting_lora import SHA256 as FIGHTING_SHA256, PATH
                    repository, revision = 'r4tn4/Bubble', '338e12cb179abf0573b61c310db6163018effdde'
                    hashes = {PATH.name: FIGHTING_SHA256}
                else:
                    from generators.wan_vace.lightning_lora import FILES, REVISION
                    repository, revision = 'lightx2v/Wan2.2-Lightning', REVISION
                    hashes = {record[0]: record[2] for record in FILES.values()}
                result['manifest_state'] = 'code_pinned'
                result['declared_sources'] = [{'repository': repository, 'revision': revision}]
                result['declared_files'] = [{'path': path, 'sha256': digest, 'hash_origin': 'application_pinned',
                                             'repository': repository, 'revision': revision}
                                            for path, digest in sorted(hashes.items())]
                return result
            if model in ('umt5-xxl-fp16', 'catalog-wan-umt5-fp16', 'wan-2.1-vae', 'catalog-wan-21-vae'):
                from generators.wan_fun.prepare import FUN_SHARED_MODEL_SOURCES
                component = 'encoder' if model in ('umt5-xxl-fp16', 'catalog-wan-umt5-fp16') else 'vae'
                repository, revision, remote, digest = FUN_SHARED_MODEL_SOURCES[component]
                result['manifest_state'] = 'code_pinned'
                result['declared_sources'] = [{'repository': repository, 'revision': revision}]
                result['declared_files'] = [{'path': Path(remote).name, 'sha256': digest,
                                             'hash_origin': 'application_pinned',
                                             'repository': repository, 'revision': revision}]
                return result
            if model in ('flan-t5-base', 'animationgpt-author'):
                from workflow.common.animationgpt_model_download import (AUTHOR_WEIGHT_SHA256, FILENAME,
                    T5_REVISION, author_t5_required_files)
                if model == 'flan-t5-base':
                    repository, revision = 'google/flan-t5-base', T5_REVISION
                    hashes = author_t5_required_files()
                    result['declared_sources'] = [{'repository': repository, 'revision': revision}]
                else:
                    repository, revision = None, None
                    hashes = {FILENAME: AUTHOR_WEIGHT_SHA256}
                result['manifest_state'] = 'code_pinned'
                result['declared_files'] = [{'path': path, 'sha256': digest, 'hash_origin': 'application_pinned',
                                             'repository': repository, 'revision': revision}
                                            for path, digest in sorted(hashes.items())]
                return result
            if model in ('hermes-agent', 'hermes-coding', 'qwen3.8-27b-iq4-xs', 'catalog-hermes-coding'):
                from workflow.common.hermes_model_download import HERMES_MODEL_FILENAME
                ready = folder / 'ready.sha256'
                try:
                    if not ready.exists() and not ready.is_symlink():
                        return result
                    if ready.is_symlink() or not ready.is_file() or ready.stat().st_size > 4096:
                        raise ValueError('준비 기록을 읽을 수 없습니다.')
                    record = json.loads(ready.read_text(encoding='utf-8'))
                    digest = record.get('sha256')
                    if (not isinstance(digest, str) or not SHA256.fullmatch(digest)
                            or type(record.get('size')) is not int or record['size'] < 0
                            or type(record.get('mtime_ns')) is not int):
                        raise ValueError('준비 기록 형식 오류')
                    result['manifest_state'] = 'ready_record'
                    result['declared_files'] = [{'path': HERMES_MODEL_FILENAME, 'sha256': digest.lower(),
                                                 'hash_origin': 'local_ready_record', 'repository': None,
                                                 'revision': None}]
                except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
                    result['manifest_state'] = 'unavailable'
            return result
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 4 * 1024 * 1024:
        result['manifest_state'] = 'unavailable'
        return result
    try:
        value = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        result['manifest_state'] = 'unavailable'
        return result
    result['manifest_state'] = 'prepared_record' if preparation_record else 'read'

    def add_file(path, digest, repo=None, revision=None):
        if not isinstance(path, str) or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            return
        item_path = Path(path)
        if item_path.is_absolute() or '..' in item_path.parts:
            return
        # Some existing manifests use paths relative to .model instead of the model directory.
        if item_path.parts[:2] == ('.model', model):
            item_path = Path(*item_path.parts[2:])
        if not item_path.parts or item_path.parts[0] == '.model':
            return
        result['declared_files'].append({'path': item_path.as_posix(), 'sha256': digest.lower(),
                                         'hash_origin': 'local_preparation_record' if preparation_record else 'local_manifest', 'repository': repo, 'revision': revision})

    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                repo, revision = entry.get('repo'), entry.get('revision')
                add_file(entry.get('path'), entry.get('sha256'), repo, revision)
                if isinstance(repo, str) and isinstance(revision, str):
                    source_record = {'repository': repo, 'revision': revision}
                    if source_record not in result['declared_sources']:
                        result['declared_sources'].append(source_record)
    elif isinstance(value, dict):
        repo = value.get('repo') or value.get('repository') or value.get('model_id')
        revision = value.get('revision')
        if isinstance(repo, str) and isinstance(revision, str):
            result['declared_sources'].append({'repository': repo, 'revision': revision})
        if preparation_record:
            sources = value.get('sources', value.get('revisions', []))
            if isinstance(sources, list):
                for entry in sources:
                    if isinstance(entry, list) and len(entry) >= 2 and all(isinstance(part, str) for part in entry[:2]):
                        source_record = {'repository': entry[0], 'revision': entry[1]}
                        if source_record not in result['declared_sources']:
                            result['declared_sources'].append(source_record)
        hashes = value.get('sha256') or value.get('files')
        if isinstance(hashes, dict):
            for path, digest in hashes.items():
                add_file(path, digest, repo, revision)
        elif isinstance(hashes, list):
            for item in hashes:
                if isinstance(item, dict):
                    add_file(item.get('path'), item.get('sha256'), repo, revision)
    return result
