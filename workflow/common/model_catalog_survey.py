"""Read-only survey of model storage; never follows links or hashes weights."""
from collections import defaultdict
from datetime import datetime, timezone
import os
from pathlib import Path
import stat


def survey_model_root(root, service_paths=None, nested_roots=()):
    root = Path(root).resolve(strict=True)
    nested_roots = tuple(nested_roots)
    if not root.is_dir():
        raise ValueError('모델 경로가 디렉터리가 아닙니다.')
    started = datetime.now(timezone.utc).isoformat()
    errors, links, entries, changed = [], [], {}, []
    inode_paths = defaultdict(list)

    def record_error(path, error):
        errors.append({'path': str(path), 'error': str(error)})

    try:
        children = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError as error:
        raise ValueError('모델 경로를 읽을 수 없습니다.') from error
    for child in children:
        name = child.name
        result = {'path': name, 'files': 0, 'logical_bytes': 0, 'allocated_bytes': 0,
                  'links': 0, 'errors': 0, 'services': [], 'kind': 'unknown', 'metadata_files': [],
                  'partial_files': 0, 'partial_allocated_bytes': 0}
        entries[name] = result

        def observe(path):
            relative = path.relative_to(root).as_posix()
            try:
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    target = os.readlink(path)
                    try:
                        resolved = path.resolve(strict=True)
                        status = 'present' if resolved.is_relative_to(root) else 'outside'
                    except FileNotFoundError:
                        status = 'missing'
                    except (OSError, RuntimeError):
                        status = 'unknown'
                    links.append({'path': relative, 'target': target, 'status': status})
                    result['links'] += 1
                elif stat.S_ISREG(info.st_mode):
                    result['files'] += 1
                    result['logical_bytes'] += info.st_size
                    result['allocated_bytes'] += info.st_blocks * 512
                    if path.name.endswith(('.incomplete', '.partial')):
                        result['partial_files'] += 1
                        result['partial_allocated_bytes'] += info.st_blocks * 512
                    if path.name in ('manifest.json', 'verified-manifest.json', 'prepared.json', 'PINNED_REVISION'):
                        result['metadata_files'].append(relative)
                    if info.st_nlink > 1:
                        inode_paths[(info.st_dev, info.st_ino)].append(relative)
                    after = path.lstat()
                    if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                        changed.append(relative)
                return info
            except OSError as error:
                result['errors'] += 1
                record_error(relative, error)
                return None

        info = observe(child)
        if info is None:
            continue
        result['kind'] = 'symlink' if stat.S_ISLNK(info.st_mode) else 'directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) else 'other'
        if not stat.S_ISDIR(info.st_mode):
            continue
        directories = {}
        def onerror(error):
            result['errors'] += 1
            record_error(error.filename or name, error)
        for directory, dirnames, filenames in os.walk(child, followlinks=False, onerror=onerror):
            directory = Path(directory)
            try:
                before = directory.lstat()
                directories[directory] = (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns)
            except OSError as error:
                result['errors'] += 1
                record_error(directory.relative_to(root).as_posix(), error)
            for filename in filenames:
                observe(directory / filename)
            for dirname in list(dirnames):
                path = directory / dirname
                details = observe(path)
                if details is None or not stat.S_ISDIR(details.st_mode):
                    dirnames.remove(dirname)
        for directory, before in directories.items():
            try:
                after = directory.lstat()
                if before != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns):
                    changed.append(directory.relative_to(root).as_posix())
            except OSError as error:
                result['errors'] += 1
                record_error(directory.relative_to(root).as_posix(), error)

    mapping_errors = []
    for service, paths in (service_paths or {}).items():
        for path in paths:
            try:
                path = Path(path)
                if not path.is_absolute():
                    path = root / path
                relative = path.relative_to(root)
                if relative.parts and relative.parts[0] in entries:
                    record = entries[relative.parts[0]]
                    if service not in record['services']:
                        record['services'].append(service)
            except (OSError, ValueError, TypeError) as error:
                mapping_errors.append({'service': service, 'path': str(path), 'error': str(error)})
    for item in entries.values():
        item['services'].sort()
    for nested_name in nested_roots:
        if (not isinstance(nested_name, str) or not nested_name or '\\' in nested_name
                or any(part in ('', '.', '..') for part in nested_name.split('/'))
                or Path(nested_name).is_absolute()):
            raise ValueError('중첩 조사 경로는 모델 루트 안의 상대 디렉터리여야 합니다.')
        nested_root = root
        for part in nested_name.split('/'):
            nested_root = nested_root / part
            if nested_root.is_symlink():
                raise ValueError('중첩 조사 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if not nested_root.is_dir():
            raise ValueError('중첩 조사 디렉터리를 확인할 수 없습니다.')
        nested = survey_model_root(nested_root)
        for entry in nested['entries']:
            entry['path'] = f"{nested_name}/{entry['path']}"
            entry['metadata_files'] = [f'{nested_name}/{path}' for path in entry['metadata_files']]
            entries[entry['path']] = entry
        changed.extend(f'{nested_name}/{path}' for path in nested['changed_paths'])
        errors.extend({'path': f"{nested_name}/{error['path']}", 'error': error['error']} for error in nested['errors'])
    return {'version': 1, 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
            'root': str(root), 'surveyed_roots': list(nested_roots), 'entries': list(entries.values()), 'links': links,
            'hardlinks': [paths for paths in inode_paths.values() if len(paths) > 1],
            'errors': errors, 'mapping_errors': mapping_errors, 'changed_paths': sorted(set(changed)),
            'note': '링크 대상의 존재 여부를 확인했으며 파일 내용은 읽지 않았습니다. 스캔 중 일부 변경을 감지하지만 완전한 일관성은 보장하지 않습니다. 할당량은 하드링크를 중복 계산할 수 있습니다. 서비스 매핑이 없어도 미사용을 뜻하지 않습니다.'}


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='모델 디렉터리')
    parser.add_argument('--services', action='store_true', help='등록된 서비스 경로와 연결')
    parser.add_argument('--nested', action='append', default=[], help='최상위 디렉터리의 구성요소별 관측 추가')
    args = parser.parse_args()
    service_paths = None
    if args.services:
        from workflow.common.model_file_inventory import resolve_model_inventory_paths
        service_paths = resolve_model_inventory_paths()
    print(json.dumps(survey_model_root(args.root, service_paths, args.nested), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
