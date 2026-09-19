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

LICENSES = {'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def export_asset(registry, artifact_id, version, release_root):
    entry = registered_entry(registry, artifact_id, version)
    release_path = Path(release_root).absolute()
    if any(p.is_symlink() for p in (release_path, *release_path.parents)):
        raise ValueError('릴리스 경로의 심볼릭 링크는 허용하지 않습니다.')
    release_root = release_path.resolve()
    if release_root.is_relative_to(Path(entry['root'])):
        raise ValueError('릴리스 저장소는 원본 보관 루트 밖에 있어야 합니다.')
    # 검수 포인터 변경과 export 승인을 직렬화한다.
    with database(registry, entry['root']):
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
        manifest = dict(assetId=artifact_id, version=version, assetType=data['artifactType'],
                        files=[filename], hashes={filename: data['sha256']},
                        licenseId=license['licenseId'], attribution=license['attribution'], compatibleSchemaVersion=1)
        public_json = encoded(manifest)
        release_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.pending-', dir=release_root) as temporary:
            staging = Path(temporary) / 'release'
            staging.mkdir()
            archive = staging / 'pack.zip'
            with ZipFile(archive, 'w', compression=ZIP_STORED) as target:
                digest = sha256()
                with source.open('rb') as stream, target.open(ZipInfo(filename), 'w') as output:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk); output.write(chunk)
                if digest.hexdigest() != data['sha256']:
                    raise ValueError('내보내는 동안 원본 파일 내용이 변경되었습니다.')
                target.writestr(ZipInfo('manifest.json'), public_json)
                target.writestr(ZipInfo('LICENSE.txt'),
                    f"{license['licenseId']}\n{LICENSES[license['licenseId']]}\n".encode())
                target.writestr(ZipInfo('ATTRIBUTION.txt'), (license['attribution'] + '\n').encode())
            # 복사 이후에도 메타데이터·보관본이 검수 대상과 같은지 확인한다.
            resolve(registry, artifact_id, version)
            pack_hash = sha256()
            with archive.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    pack_hash.update(chunk)
            pack_name = pack_hash.hexdigest() + '.zip'
            archive.rename(staging / pack_name)
            receipt = dict(artifactId=artifact_id, version=version, reviewId=review['review_id'],
                           contentHash=entry['content_hash'], metadataHash=entry['metadata_hash'],
                           manifestHash=sha256(public_json).hexdigest(), packHash=pack_hash.hexdigest())
            (staging / 'private-release.json').write_bytes(encoded(receipt))
            for file in staging.iterdir():
                with file.open('rb') as stream:
                    os.fsync(stream.fileno())
                file.chmod(0o444)
            destination = release_root / str(uuid4())
            os.rename(staging, destination)
    return dict(archive=str(destination / pack_name), privateRecord=str(destination / 'private-release.json'), manifest=manifest)
