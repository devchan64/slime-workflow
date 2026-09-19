"""승인된 원본을 공개 ZIP과 별도 비공개 릴리스 기록으로 만든다. 업로드는 하지 않는다."""
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4
from zipfile import ZipFile, ZipInfo, ZIP_STORED
from .registry import database, registered_entry, resolve
from .reviews import current_review
from .sidecar import identifier

LICENSES = {'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def export_asset(registry, artifact_id, version, release_root):
    """기존 단일 에셋 manifest 계약을 유지한다."""
    return _export(registry, [(artifact_id, version)], release_root)


def export_pack(registry, pack_id, version, assets, release_root):
    """명시적으로 지정한 에셋만 묶는다. 제작 입력을 공개 의존성으로 추정하지 않는다."""
    identifier(pack_id, 'packId')
    identifier(version, 'version')
    return _export(registry, assets, release_root, pack=(pack_id, version))


def selected_assets(assets):
    if not isinstance(assets, (list, tuple)) or not assets:
        raise ValueError('공개 팩에는 하나 이상의 에셋 ID/버전이 필요합니다.')
    selected = []
    for item in assets:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError('에셋 선택은 ID와 버전의 쌍이어야 합니다.')
        artifact_id, version = item
        identifier(artifact_id, 'artifactId')
        identifier(version, 'version')
        selected.append((artifact_id, version))
    if len(set(selected)) != len(selected):
        raise ValueError('공개 팩의 에셋 ID/버전이 중복되었습니다.')
    return sorted(selected)


def _export(registry, assets, release_root, pack=None):
    selected = selected_assets(assets)
    entries = [registered_entry(registry, *key) for key in selected]
    release_path = Path(release_root).absolute()
    if any(p.is_symlink() for p in (release_path, *release_path.parents)):
        raise ValueError('릴리스 경로의 심볼릭 링크는 허용하지 않습니다.')
    release_root = release_path.resolve()
    if any(release_root.is_relative_to(Path(entry['root'])) for entry in entries):
        raise ValueError('릴리스 저장소는 모든 원본 보관 루트 밖에 있어야 합니다.')
    # 모든 검수 포인터와 export 승인을 한 트랜잭션으로 직렬화한다.
    with database(registry, entries[0]['root']):
        approved = []
        for (artifact_id, version), entry in zip(selected, entries):
            data = resolve(registry, artifact_id, version)
            review = current_review(registry, artifact_id, version)
            if review is None or review['decision'] != 'APPROVED':
                raise ValueError('최신 검수에서 승인된 산출물만 내보낼 수 있습니다.')
            license = data['license']
            if (not license['modificationAllowed'] or not license['redistributionAllowed']
                    or license['licenseId'] not in LICENSES):
                raise ValueError('지원하는 공개 라이선스와 수정·재배포 허용이 필요합니다.')
            source = Path(entry['root']) / data['sourcePath']
            filename = data['sha256'] + source.suffix
            public = dict(assetId=artifact_id, version=version, assetType=data['artifactType'],
                files=[filename], hashes={filename: data['sha256']}, licenseId=license['licenseId'],
                attribution=license['attribution'], compatibleSchemaVersion=1)
            private = dict(artifactId=artifact_id, version=version, reviewId=review['review_id'],
                           contentHash=entry['content_hash'], metadataHash=entry['metadata_hash'])
            approved.append((data, source, filename, public, private))
        manifest = (approved[0][3] if pack is None else
                    dict(packId=pack[0], version=pack[1], compatibleSchemaVersion=1,
                         assets=[item[3] for item in approved]))
        public_json = encoded(manifest)
        release_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.pending-', dir=release_root) as temporary:
            staging = Path(temporary) / 'release'
            staging.mkdir()
            archive = staging / 'pack.zip'
            with ZipFile(archive, 'w', compression=ZIP_STORED) as target:
                written = set()
                for data, source, filename, _, _ in approved:
                    # 동일 바이트를 공유하는 에셋도 각각 원본을 확인한다.
                    digest = sha256()
                    with source.open('rb') as stream:
                        if filename in written:
                            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                                digest.update(chunk)
                        else:
                            with target.open(ZipInfo(filename), 'w') as output:
                                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                                    digest.update(chunk); output.write(chunk)
                            written.add(filename)
                    if digest.hexdigest() != data['sha256']:
                        raise ValueError('내보내는 동안 원본 파일 내용이 변경되었습니다.')
                target.writestr(ZipInfo('manifest.json'), public_json)
                licenses = sorted({item[0]['license']['licenseId'] for item in approved})
                target.writestr(ZipInfo('LICENSE.txt'), ''.join(
                    f"{key}\n{LICENSES[key]}\n" for key in licenses).encode())
                attributions = [item[0]['license']['attribution'] for item in approved]
                target.writestr(ZipInfo('ATTRIBUTION.txt'), ('\n'.join(attributions) + '\n').encode())
            for key in selected:
                resolve(registry, *key)
            pack_hash = sha256()
            with archive.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    pack_hash.update(chunk)
            pack_name = pack_hash.hexdigest() + '.zip'
            archive.rename(staging / pack_name)
            receipt = (approved[0][4] if pack is None else
                       dict(packId=pack[0], version=pack[1], assets=[item[4] for item in approved]))
            receipt.update(manifestHash=sha256(public_json).hexdigest(), packHash=pack_hash.hexdigest())
            (staging / 'private-release.json').write_bytes(encoded(receipt))
            for file in staging.iterdir():
                with file.open('rb') as stream:
                    os.fsync(stream.fileno())
                file.chmod(0o444)
            destination = release_root / str(uuid4())
            os.rename(staging, destination)
    return dict(archive=str(destination / pack_name), privateRecord=str(destination / 'private-release.json'), manifest=manifest)
