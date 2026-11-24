"""Verify that a configured SMB destination still refers to its share."""
from pathlib import Path
import re
import socket
from urllib.parse import unquote, urlsplit


def _unescape_mount(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match.group(1), 8)), value)


def _same_host(left, right):
    if left.casefold().rstrip('.') == right.casefold().rstrip('.'):
        return True
    try:
        left_addresses = {entry[4][0] for entry in socket.getaddrinfo(left, None)}
        right_addresses = {entry[4][0] for entry in socket.getaddrinfo(right, None)}
        return bool(left_addresses & right_addresses)
    except OSError:
        return False


def verify_smb_mount(path, uri, *, mountinfo_path='/proc/self/mountinfo'):
    """Reject an unmounted directory, different share or different subdirectory."""
    if uri is None:
        return
    if not isinstance(uri, str):
        raise ValueError('Samba 주소 형식이 올바르지 않습니다.')
    address = urlsplit(uri)
    parts = [unquote(part) for part in address.path.split('/') if part]
    if address.scheme.lower() != 'smb' or not address.hostname or address.username or address.password or not parts:
        raise ValueError('Samba 주소 형식이 올바르지 않습니다.')
    if any(part in ('.', '..') or '/' in part or '\\' in part for part in parts):
        raise ValueError('Samba 공유 경로 형식이 올바르지 않습니다.')
    destination = Path(path).resolve(strict=True)
    mounts = []
    with open(mountinfo_path, encoding='utf-8') as stream:
        for line in stream:
            before, separator, after = line.partition(' - ')
            fields, details = before.split(), after.split()
            if not separator or len(fields) < 5 or len(details) < 2:
                continue
            mountpoint = Path(_unescape_mount(fields[4]))
            if destination == mountpoint or mountpoint in destination.parents:
                mounts.append((len(mountpoint.parts), mountpoint, details[0], _unescape_mount(details[1])))
    if not mounts:
        raise ValueError('백업 마운트를 확인할 수 없습니다.')
    _, mountpoint, filesystem, source = max(mounts, key=lambda item: item[0])
    relative = destination.relative_to(mountpoint).parts
    expected_share, expected_tail = parts[0], tuple(parts[1:])
    if filesystem == 'fuse.gvfsd-fuse':
        if not relative or not relative[0].startswith('smb-share:'):
            raise ValueError('GVFS Samba 공유 경로를 확인할 수 없습니다.')
        attributes = {key: unquote(value) for key, value in
                      (item.split('=', 1) for item in relative[0][len('smb-share:'):].split(',') if '=' in item)}
        host, share, tail = attributes.get('server', ''), attributes.get('share', ''), relative[1:]
    elif filesystem in ('cifs', 'smb3'):
        source_parts = source.removeprefix('//').split('/')
        if not source.startswith('//') or len(source_parts) < 2:
            raise ValueError('CIFS 공유 정보를 확인할 수 없습니다.')
        host, share, tail = source_parts[0], source_parts[1], tuple(source_parts[2:]) + relative
    else:
        raise ValueError('설정된 Samba 공유가 마운트되어 있지 않습니다.')
    if share.casefold() != expected_share.casefold() or tuple(tail) != expected_tail or not _same_host(host, address.hostname):
        raise ValueError('마운트된 공유가 설정된 Samba 주소와 일치하지 않습니다.')
