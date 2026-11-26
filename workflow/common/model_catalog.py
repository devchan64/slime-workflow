"""Versioned model declarations joined with explicitly separate observations."""
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import stat

CATALOG = Path(__file__).resolve().parents[1] / 'catalog' / 'models.json'
DEFAULT_MODEL_ROOT = Path(__file__).resolve().parents[2] / '.model'
SURVEY_DIR = DEFAULT_MODEL_ROOT.parent / '.local/model-catalog/surveys'
DUPLICATE_SURVEY = DEFAULT_MODEL_ROOT.parent / '.local/model-catalog/duplicate-observations.json'
IDENTIFIER = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
SERVICE_IDENTIFIER = re.compile(r'^[a-z0-9]+(?:[.-][a-z0-9]+)*$')
KINDS = {'model', 'shared', 'cache', 'collection'}


def validate_catalog(value):
    if not isinstance(value, dict) or value.get('schema_version') != 1 or not isinstance(value.get('components'), list):
        raise ValueError('지원하지 않는 카탈로그 형식입니다.')
    ids, paths = set(), set()
    for component in value['components']:
        if not isinstance(component, dict):
            raise ValueError('구성요소 형식이 올바르지 않습니다.')
        identifier, label, path = component.get('id'), component.get('label'), component.get('path')
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) or identifier in ids:
            raise ValueError('구성요소 ID가 올바르지 않거나 중복됩니다.')
        if not isinstance(label, str) or not label.strip() or component.get('kind') not in KINDS:
            raise ValueError('구성요소 이름 또는 종류가 올바르지 않습니다.')
        if not isinstance(path, str) or not path or '\\' in path or '\x00' in path:
            raise ValueError('구성요소 경로가 올바르지 않습니다.')
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or '..' in normalized.parts or normalized.as_posix() != path or path == '.' or path in paths:
            raise ValueError('구성요소 경로가 올바르지 않거나 중복됩니다.')
        services = component.get('services')
        if not isinstance(services, list) or any(not isinstance(s, str) or not SERVICE_IDENTIFIER.fullmatch(s) for s in services) or len(set(services)) != len(services):
            raise ValueError('서비스 관계가 올바르지 않습니다.')
        optional = component.get('optional_services', [])
        if not isinstance(optional, list) or any(not isinstance(s, str) or s not in services for s in optional) or len(set(optional)) != len(optional):
            raise ValueError('선택적 서비스 관계가 올바르지 않습니다.')
        if any(component.get(key) is not None and (not isinstance(component[key], str) or not component[key].strip()) for key in ('source', 'revision')):
            raise ValueError('출처 또는 리비전이 올바르지 않습니다.')
        if component.get('usage_note') is not None and (not isinstance(component['usage_note'], str) or not component['usage_note'].strip()):
            raise ValueError('사용 설명이 올바르지 않습니다.')
        ids.add(identifier)
        paths.add(path)
    return value


def read_catalog(path=CATALOG):
    with Path(path).open(encoding='utf-8') as stream:
        return validate_catalog(json.load(stream))


def declared_version(component):
    """Expose only explicitly declared revisions; presence is not verification."""
    if not component.get('source') or not component.get('revision'):
        return None
    return {'id': f"{component['id']}@{component['source']}@{component['revision']}",
            'source': component['source'], 'revision': component['revision'],
            'origin': 'catalog_declaration', 'installation_match': 'unknown'}


def read_retained_copy_record(directory, component_id):
    """Expose the recorded copy check, never a current equality decision."""
    path = Path(directory) / 'transaction.json'
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            return None
        record = json.loads(path.read_text(encoding='utf-8'))
        if (component_id == 'trellis-dinov2'
                and record.get('source') == '.model/trellis-dinov2'
                and record.get('retained') == '.local/model-catalog/retained/trellis-dinov2/original'
                and record.get('active') == '.model/models/trellis-dinov2/dinov2_vitl14_reg4_pretrain.pth'
                and isinstance(record.get('sha256'), str) and re.fullmatch(r'[a-f0-9]{64}', record['sha256'])):
            return {'kind': 'recorded_fixed_sha256', 'sha256': record['sha256']}
        if (record.get('verification') != 'source-copy-sha256'
                or record.get('source') != f'.model/{component_id}'
                or record.get('active') != f'.model/models/{component_id}'
                or record.get('retained') != f'.local/model-catalog/retained/{component_id}/original'
                or type(record.get('file_count')) is not int or record['file_count'] <= 0):
            return None
        return {'kind': 'recorded_source_copy_sha256', 'file_count': record['file_count']}
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def read_survey_report(path=None, root=DEFAULT_MODEL_ROOT):
    """Read an optional previous inventory; never infer current disk usage."""
    try:
        if path is None:
            candidates = sorted(SURVEY_DIR.glob('????-??-??-*.json'), key=lambda value: value.stat().st_mtime_ns)
            if not candidates:
                return None
            path = candidates[-1]
        with Path(path).open(encoding='utf-8') as stream:
            report = json.load(stream)
        if (report.get('version') != 1 or Path(report.get('root', '')) != Path(root)
                or not isinstance(report.get('entries'), list)):
            return None
        entries = {}
        for entry in report['entries']:
            if not (isinstance(entry, dict) and isinstance(entry.get('path'), str)
                    and entry['path'] and entry['path'] not in entries
                    and all(type(entry.get(k)) is int and entry[k] >= 0
                            for k in ('files', 'logical_bytes', 'allocated_bytes', 'links', 'errors'))):
                return None
            entries[entry['path']] = {k: entry[k] for k in
                                      ('files', 'logical_bytes', 'allocated_bytes', 'links', 'errors')}
            partial_keys = ('partial_files', 'partial_allocated_bytes')
            if any(k in entry for k in partial_keys) and not all(type(entry.get(k)) is int and entry[k] >= 0 for k in partial_keys):
                return None
            if all(k in entry for k in partial_keys):
                entries[entry['path']].update({k: entry[k] for k in ('partial_files', 'partial_allocated_bytes')})
        changed_paths = report.get('changed_paths', [])
        if not isinstance(changed_paths, list) or any(not isinstance(path, str) or not path for path in changed_paths):
            return None
        for path, observation in entries.items():
            observation['changed'] = any(changed == path or changed.startswith(path + '/') for changed in changed_paths)
        links = []
        for link in report.get('links', []):
            if not isinstance(link, dict) or not isinstance(link.get('path'), str) or not isinstance(link.get('target'), str):
                continue
            link_path, target = link['path'], link['target']
            if target.startswith('/'):
                resolved = target
            else:
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(link_path), target))
            status = link.get('status')
            if status not in ('present', 'missing', 'outside', 'unknown'):
                status = 'unknown'
            if (target.startswith('/') or resolved == '..' or resolved.startswith('../')) and status == 'present':
                status = 'unknown'
            links.append({'path': link_path, 'target': target, 'resolved': resolved, 'status': status})
        surveyed_roots = report.get('surveyed_roots', [])
        if not isinstance(surveyed_roots, list):
            surveyed_roots = []
        return {'finished_at': report.get('finished_at'), 'entries': entries, 'links': links,
                'surveyed_roots': [path for path in surveyed_roots if isinstance(path, str)],
                'changed': bool(report.get('changed_paths')), 'errors': bool(report.get('errors'))}
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def read_duplicate_survey(path=DUPLICATE_SURVEY, root=DEFAULT_MODEL_ROOT):
    """Expose a bounded historical report without turning it into a deletion decision."""
    try:
        path = Path(path)
        if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            return None
        record = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(record, dict) or record.get('version') != 1 or record.get('root') != str(root)
                or not isinstance(record.get('observed_at'), str) or not isinstance(record.get('groups'), list)
                or not isinstance(record.get('errors'), list)):
            return None
        groups = []
        for group in record['groups']:
            if (not isinstance(group, dict) or type(group.get('size')) is not int or group['size'] < 0
                    or not isinstance(group.get('paths'), list) or len(group['paths']) < 2):
                return None
            paths = []
            inodes = set()
            seen_paths = set()
            can_estimate = True
            for item in group['paths']:
                if (not isinstance(item, dict) or not isinstance(item.get('path'), str) or not item['path']
                        or item['path'].startswith('/') or '\\' in item['path'] or '\x00' in item['path']
                        or any(part in ('', '.', '..') for part in item['path'].split('/'))
                        or item['path'] in seen_paths
                        or item.get('state') not in ('matches', 'different', 'unavailable')
                        or (item.get('via_link') is not None and type(item['via_link']) is not bool)):
                    return None
                seen_paths.add(item['path'])
                paths.append({'path': item['path'], 'state': item['state'], 'via_link': item.get('via_link')})
                if item['state'] != 'matches' or type(item.get('device')) is not int or type(item.get('inode')) is not int:
                    can_estimate = False
                else:
                    inodes.add((item['device'], item['inode']))
            groups.append({'size': group['size'], 'paths': paths,
                           'distinct_files': len(inodes) if can_estimate else None,
                           'duplicate_logical_bytes': group['size'] * max(0, len(inodes) - 1) if can_estimate else None})
        return {'observed_at': record['observed_at'], 'groups': groups, 'error_count': len(record['errors'])}
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def reconcile_catalog(catalog, survey):
    """Join top-level observations without inferring verification or deletion safety."""
    validate_catalog(catalog)
    if not isinstance(survey, dict) or survey.get('version') != 1 or not isinstance(survey.get('entries'), list):
        raise ValueError('조사 결과 형식이 올바르지 않습니다.')
    observed = {entry['path']: entry for entry in survey['entries'] if isinstance(entry, dict) and isinstance(entry.get('path'), str)}
    declared_paths = {PurePosixPath(item['path']).parts[0] for item in catalog['components']}
    return {'schema_version': 1, 'observed_at': survey.get('finished_at'),
            'components': [{'declaration': item, 'observation': observed.get(item['path'])}
                           for item in catalog['components']],
            'unclassified': [entry for name, entry in observed.items() if name not in declared_paths],
            'survey_errors': survey.get('errors', []),
            'note': '관측은 파일 검증이나 서비스 의존성 전체 확인을 뜻하지 않습니다.'}


def catalog_overview(catalog=None, listing=None, *, include_manifests=True):
    """Read declarations and top-level presence; no weight reads or writes."""
    if catalog is None:
        catalog = read_catalog()
    validate_catalog(catalog)
    survey_root = None
    if listing is None:
        from workflow.common.model_backup_service import list_backup_models, read_model_source
        try:
            listing = list_backup_models()
            survey_root, _ = read_model_source()
        except ValueError:
            # A missing or invalid local backup configuration must not hide the
            # catalog. Never infer backup absence from this fallback.
            try:
                models = [{'name': path.name, 'local_present': True,
                           'backup_present': None, 'snapshot_present': None}
                          for path in DEFAULT_MODEL_ROOT.iterdir()
                          if path.is_dir() and not path.is_symlink()]
                from workflow.common.model_backup_targets import CATALOG_TARGETS, target_path
                for name in CATALOG_TARGETS:
                    try:
                        if target_path(DEFAULT_MODEL_ROOT, name).is_dir():
                            models.append({'name': name, 'local_present': True,
                                           'backup_present': None, 'snapshot_present': None})
                    except (OSError, ValueError):
                        continue
            except OSError as error:
                raise ValueError('기본 모델 경로를 읽을 수 없습니다.') from error
            listing = {'models': models, 'backup_error': '백업 설정 또는 경로를 확인할 수 없습니다. 기본 모델 경로를 표시합니다.'}
            survey_root = DEFAULT_MODEL_ROOT
    if not isinstance(listing, dict) or not isinstance(listing.get('models'), list):
        raise ValueError('모델 목록 형식이 올바르지 않습니다.')
    observed = {item['name']: item for item in listing['models']
                if isinstance(item, dict) and isinstance(item.get('name'), str)}
    declared_paths = {item['path'] for item in catalog['components']}
    survey = read_survey_report(root=survey_root) if survey_root is not None else None
    components = []
    partial_roots = set()
    from workflow.common.model_restore_history import read_restore_record
    restore_cache = {}

    def observed_restore(name):
        if survey_root != DEFAULT_MODEL_ROOT:
            return None
        if name in restore_cache:
            return restore_cache[name]
        record = read_restore_record(name)
        if record is not None:
            match = None
            if observed.get(name, {}).get('snapshot_present') is True:
                try:
                    from workflow.common.model_backup_service import latest_model_snapshot, read_backup_roots
                    _, backup_root, _ = read_backup_roots()
                    latest = latest_model_snapshot(backup_root, name)
                    if latest is not None:
                        match = latest.name == record['snapshot_id']
                except (OSError, ValueError):
                    pass
            record = {**record, 'latest_snapshot_match': match}
        restore_cache[name] = record
        return record
    for item in catalog['components']:
        state = observed.get(item['path'])
        if state is None and survey_root is not None and item['path'].startswith('audio/'):
            from workflow.common.model_backup_targets import target_path
            try:
                nested_path = target_path(survey_root, tuple(item['path'].split('/')))
                try:
                    local_present = stat.S_ISDIR(nested_path.lstat().st_mode)
                except FileNotFoundError:
                    local_present = False
                state = {'name': item['path'], 'local_present': local_present,
                         'backup_present': None, 'snapshot_present': None}
            except (OSError, ValueError):
                state = {'name': item['path'], 'local_present': None,
                         'backup_present': None, 'snapshot_present': None}
        install = None
        if include_manifests and state and state.get('local_present') is True and '/' not in item['path']:
            try:
                from workflow.common.model_backup_metadata import model_metadata
                metadata = model_metadata(item['path'], service_paths={})
                install = {'origin': metadata['origin'], 'manifest_state': metadata['manifest_state'],
                           'declared_sources': metadata['declared_sources'],
                           'declared_file_count': len(metadata['declared_files'])}
            except (OSError, ValueError, TypeError, KeyError):
                install = {'origin': 'local', 'manifest_state': 'unavailable',
                           'declared_sources': [], 'declared_file_count': None}
        alternate = []
        from workflow.common.model_backup_targets import CATALOG_TARGETS
        target_name = 'catalog-' + item['id']
        if target_name in CATALOG_TARGETS:
            target_state = observed.get(target_name)
            if target_state is not None:
                path = target_state.get('relative_path') or '/'.join(CATALOG_TARGETS[target_name])
                if target_state.get('local_present') is True:
                    partial_roots.add(path.split('/')[0])
                alternate_metadata = None
                if include_manifests and target_state.get('local_present') is True:
                    try:
                        from workflow.common.model_backup_metadata import model_metadata
                        metadata = model_metadata(target_name, service_paths={})
                        alternate_metadata = {'origin': metadata['origin'], 'manifest_state': metadata['manifest_state'],
                                              'declared_sources': metadata['declared_sources'],
                                              'declared_file_count': len(metadata['declared_files'])}
                    except (OSError, ValueError, TypeError, KeyError):
                        alternate_metadata = {'origin': 'local', 'manifest_state': 'unavailable',
                                              'declared_sources': [], 'declared_file_count': None}
                alternate.append({'path': path, 'backup_target': target_name,
                                  'local_present': target_state.get('local_present'),
                                  'backup_present': target_state.get('backup_present'),
                                  'legacy_backup_present': target_state.get('legacy_backup_present'),
                                  'snapshot_present': target_state.get('snapshot_present'),
                                  'installation_metadata': alternate_metadata,
                                  'restore_record': observed_restore(target_name),
                                  'storage_observation': survey['entries'].get(path) if survey else None})
                # The direct directory and catalog alias keep separate snapshot
                # histories even when they point to the same installation.
                direct = observed.get(path) if '/' not in path and path != item['path'] else None
                if direct is not None:
                    alternate.append({'path': path, 'backup_target': path,
                                      'local_present': direct.get('local_present'),
                                      'backup_present': direct.get('backup_present'),
                                      'snapshot_present': direct.get('snapshot_present'),
                                      'installation_metadata': alternate_metadata,
                                      'restore_record': observed_restore(path),
                                      'storage_observation': survey['entries'].get(path) if survey else None})
        if item['id'] in ('trellis-dinov2', 'flux-report-vision', 'trellis-image-large') and survey_root == DEFAULT_MODEL_ROOT:
            retained_path = f".local/model-catalog/retained/{item['id']}/original"
            retained = DEFAULT_MODEL_ROOT.parent / retained_path
            if retained.is_dir() and not retained.is_symlink():
                retained_observation = None
                try:
                    from workflow.common.model_catalog_survey import survey_model_root
                    report = survey_model_root(retained.parent)
                    retained_observation = next((entry for entry in report['entries'] if entry['path'] == 'original'), None)
                    if retained_observation is not None:
                        retained_observation = {**retained_observation, 'observed_at': report['finished_at'],
                                                'changed': bool(report['changed_paths']),
                                                'errors': len(report['errors'])}
                except (OSError, ValueError):
                    pass
                alternate.append({'path': retained_path,
                                  'local_present': True, 'backup_present': None, 'snapshot_present': None,
                                  'retained_original': True, 'storage_observation': retained_observation,
                                  'copy_record': read_retained_copy_record(retained.parent, item['id'])})
        if item['id'] == 'minimax-hf-cache' and survey_root == DEFAULT_MODEL_ROOT:
            external = DEFAULT_MODEL_ROOT.parent / '.cache/huggingface'
            if external.is_dir() and not external.is_symlink() and not external.parent.is_symlink():
                alternate.append({'path': '.cache/huggingface', 'local_present': True,
                                  'backup_present': None, 'snapshot_present': None,
                                  'external_cache': True})
        link_roots = [item['path'], *(entry['path'] for entry in alternate if not entry.get('retained_original'))]
        components.append({'declaration': item, 'declared_version': declared_version(item),
                           'presence': state, 'installation_metadata': install,
                           'restore_record': observed_restore(item['path']) if '/' not in item['path'] else None,
                           'storage_observation': survey['entries'].get(item['path']) if survey else None,
                           'observed_links': [link for link in survey['links']
                                              if any(link['path'] == path or link['path'].startswith(path + '/')
                                                     or link['resolved'] == path or link['resolved'].startswith(path + '/')
                                                     for path in link_roots)]
                                             if survey else [],
                           'alternate_installations': alternate})
    from workflow.common.model_backup_targets import CATALOG_TARGETS
    nested_unclassified = []
    if survey:
        registered = {item['path'] for item in catalog['components']}
        registered.update('/'.join(parts) for parts in CATALOG_TARGETS.values())
        for path, observation in survey['entries'].items():
            if not path.startswith('models/'):
                continue
            if any(path == known or path.startswith(known + '/') or known.startswith(path + '/') for known in registered):
                continue
            nested_unclassified.append({'path': path, 'storage_observation': observation})
    activity = None
    if survey_root == DEFAULT_MODEL_ROOT:
        try:
            from workflow.domains.hermes_agent.management_observer import read_hermes_queue_snapshot, read_hermes_gpu_reservation_snapshot
            activity = {'queue': read_hermes_queue_snapshot(), 'reservations': read_hermes_gpu_reservation_snapshot()}
        except (OSError, ValueError, TypeError, RuntimeError):
            activity = {'queue': {'status': 'unavailable'}, 'reservations': {'status': 'unavailable'}}
    installed_top_level = {state.get('relative_path') for name, state in observed.items()
                           if name in CATALOG_TARGETS and state.get('local_present') is True
                           and isinstance(state.get('relative_path'), str) and '/' not in state['relative_path']}
    duplicates = read_duplicate_survey(root=survey_root) if survey_root is not None else None
    if duplicates:
        for group in duplicates['groups']:
            for path in group['paths']:
                root = path['path'].split('/')[0]
                services = set()
                for component in components:
                    declaration = component['declaration']
                    locations = [declaration['path'], *(alt['path'] for alt in component['alternate_installations']
                                                       if not alt.get('retained_original') and not alt.get('external_cache'))]
                    if root in locations:
                        services.update(declaration['services'])
                path['services'] = sorted(services)
                path['snapshot_present'] = observed.get(root, {}).get('snapshot_present')
                path['restore_record'] = observed_restore(root)
    return {'schema_version': 1,
            'components': components,
            'surveyed_model_children': [{'path': path, 'storage_observation': observation}
                                        for path, observation in sorted((survey or {}).get('entries', {}).items())
                                        if '/' in path and path.split('/')[0] in (survey or {}).get('surveyed_roots', [])
                                        and path.split('/')[0] != 'models'],
            'surveyed_model_roots': [path for path in (survey or {}).get('surveyed_roots', [])
                                     if '/' not in path and path != 'models'],
            'unclassified': [{**item, 'partially_classified': name in partial_roots}
                             for name, item in observed.items()
                             if name not in declared_paths and name not in CATALOG_TARGETS and name not in installed_top_level],
            'unclassified_nested': nested_unclassified,
            'nested_survey_available': bool(survey and ('models' in survey.get('surveyed_roots', [])
                                                       or any(path.startswith('models/') for path in survey['entries']))),
            'backup_error': listing.get('backup_error'),
            'activity': activity,
            'duplicate_survey': duplicates,
            'storage_survey': {key: survey[key] for key in ('finished_at', 'changed', 'errors')} if survey else None,
            'note': '카탈로그와 설치 매니페스트는 각각의 선언값입니다. 존재 여부는 파일 검증이나 모든 서비스 의존성의 확인을 뜻하지 않습니다.'}
