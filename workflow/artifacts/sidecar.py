"""파일과 sidecar 쌍의 공통 v1 계약. 공개 승인이나 이미지 품질을 판정하지 않는다."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re

TYPES = {'CONCEPT_IMAGE', 'CHARACTER_REFERENCE', 'STYLE_REFERENCE', 'RIG_PART',
         'POSE_IMAGE', 'DEPTH_MAP', 'SEGMENTATION_MASK', 'FLAT_RENDER', 'STYLED_FRAME',
         'SPRITE_SHEET', 'TERRAIN_TILE', 'PROP', 'UI_ICON', 'AUDIO', 'MIDI', 'VALIDATION_IMAGE'}
FIELDS = {'schemaVersion', 'artifactId', 'version', 'artifactType', 'sourcePath', 'sha256',
          'createdBy', 'createdAt', 'runId', 'sourceArtifacts', 'contractRefs', 'generation', 'license', 'quality'}


def fields(value, names, label):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError(f'{label}: 필드가 누락되었거나 알 수 없는 필드가 있습니다.')


def text(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(f'{label}: 비어 있지 않은 문자열이 필요합니다.')


def identifier(value, label):
    text(value, label)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value):
        raise ValueError(f'{label}: 관리 식별자 형식이 올바르지 않습니다.')


def digest(value):
    if type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('sha256: 소문자 SHA-256이 필요합니다.')


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'sidecar 중복 JSON 키: {key}')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(f'유한하지 않은 JSON 값: {value}')


def validate_metadata(data):
    fields(data, FIELDS, 'sidecar')
    if type(data['schemaVersion']) is not int or data['schemaVersion'] != 1:
        raise ValueError('지원하지 않는 sidecar schemaVersion입니다.')
    for key in ('artifactId', 'version', 'runId'):
        identifier(data[key], key)
    if type(data['artifactType']) is not str or data['artifactType'] not in TYPES:
        raise ValueError('지원하지 않는 artifactType입니다.')
    for key in ('sourcePath', 'createdBy', 'createdAt'):
        text(data[key], key)
    digest(data['sha256'])
    created = datetime.fromisoformat(data['createdAt'])
    if created.tzinfo is None:
        raise ValueError('createdAt에는 시간대가 필요합니다.')
    for name, keys, id_key in [('sourceArtifacts', {'artifactId', 'version', 'sha256'}, 'artifactId'),
                               ('contractRefs', {'contractId', 'version'}, 'contractId')]:
        if type(data[name]) is not list:
            raise ValueError(f'{name}: 목록이 필요합니다.')
        seen = set()
        for entry in data[name]:
            fields(entry, keys, name)
            identifier(entry[id_key], id_key)
            identifier(entry['version'], 'version')
            pair = (entry[id_key], entry['version'])
            if pair in seen:
                raise ValueError(f'{name}: 중복 ID/버전입니다.')
            seen.add(pair)
            if 'sha256' in entry:
                digest(entry['sha256'])
    if not data['contractRefs']:
        raise ValueError('contractRefs: 하나 이상의 계약 참조가 필요합니다.')
    generation = data['generation']
    fields(generation, {'profileId', 'profileVersion', 'pipelineVersion', 'seed', 'modelPreparationRef'}, 'generation')
    for key in ('profileId', 'profileVersion', 'pipelineVersion', 'modelPreparationRef'):
        text(generation[key], key)
    if type(generation['seed']) is not int or generation['seed'] < 0:
        raise ValueError('generation.seed: 비음수 정수가 필요합니다.')
    license = data['license']
    fields(license, {'source', 'licenseId', 'rightsHolder', 'evidenceRef', 'modificationAllowed',
                     'redistributionAllowed', 'attribution'}, 'license')
    for key in ('source', 'licenseId', 'rightsHolder', 'evidenceRef', 'attribution'):
        text(license[key], 'license.' + key)
    for key in ('modificationAllowed', 'redistributionAllowed'):
        if type(license[key]) is not bool:
            raise ValueError(f'license.{key}: 참/거짓 값이 필요합니다.')
    quality = data['quality']
    fields(quality, {'quality_warnings', 'reviewRequired', 'reviewRecordRef'}, 'quality')
    if type(quality['quality_warnings']) is not list or type(quality['reviewRequired']) is not bool:
        raise ValueError('quality: 경고 목록과 검수 필요 여부가 올바르지 않습니다.')
    for warning in quality['quality_warnings']:
        text(warning, 'quality_warnings')
    if quality['reviewRecordRef'] is not None:
        text(quality['reviewRecordRef'], 'reviewRecordRef')
    return data


def validate_pair(root, sidecar):
    root, sidecar = Path(root).resolve(strict=True), Path(sidecar)
    if sidecar.is_symlink():
        raise ValueError('sidecar 심볼릭 링크는 허용하지 않습니다.')
    sidecar = sidecar.resolve(strict=True)
    if not sidecar.is_relative_to(root) or sidecar.suffix != '.json':
        raise ValueError('sidecar는 산출물 루트 안의 JSON이어야 합니다.')
    data = validate_metadata(json.loads(sidecar.read_text(encoding='utf-8'),
                                       object_pairs_hook=unique_pairs, parse_constant=invalid_constant))
    source = PurePosixPath(data['sourcePath'])
    if source.is_absolute() or '..' in source.parts or '\\' in data['sourcePath'] or str(source) != data['sourcePath']:
        raise ValueError('sourcePath는 정규화된 상대 경로여야 합니다.')
    path = root.joinpath(*source.parts)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('산출물 경로의 심볼릭 링크는 허용하지 않습니다.')
    path = path.resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path == sidecar:
        raise ValueError('원본 산출물 파일이 올바르지 않습니다.')
    if path.with_suffix('.json') != sidecar:
        raise ValueError('산출물과 sidecar의 디렉터리·basename이 다릅니다.')
    allowed = {'.wav', '.mp3'} if data['artifactType'] == 'AUDIO' else {'.mid', '.midi'} if data['artifactType'] == 'MIDI' else {'.png'}
    if path.suffix not in allowed:
        raise ValueError('산출물 타입과 파일 확장자가 다릅니다.')
    hasher = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    if hasher.hexdigest() != data['sha256']:
        raise ValueError('산출물 내용과 sidecar SHA-256이 다릅니다.')
    return data
