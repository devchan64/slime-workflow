"""YAML 계약 설명자를 ID/버전으로 고정하고 산출물 타입 호환성을 검사한다."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from .registry import database, metadata_hash
from .sidecar import TYPES, fields, identifier, text


def validate_definition(data):
    fields(data, {'managementId', 'schemaVersion', 'contractId', 'version', 'artifactTypes', 'description'}, '계약')
    if type(data['schemaVersion']) is not int or data['schemaVersion'] != 1:
        raise ValueError('지원하지 않는 계약 schemaVersion입니다.')
    for key in ('managementId', 'contractId', 'version'):
        identifier(data[key], key)
    text(data['description'], 'description')
    types = data['artifactTypes']
    if (type(types) is not list or not types or any(type(t) is not str or t not in TYPES for t in types)
            or len(set(types)) != len(types)):
        raise ValueError('artifactTypes는 중복 없는 지원 산출물 타입 목록이어야 합니다.')
    return data


def read_definition(path):
    # YAML 등록에만 PyYAML이 필요하며 기존 조회/검수/export는 표준 라이브러리만 쓴다.
    import yaml
    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            result = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if type(key) is not str or key in result:
                    raise ValueError('계약 YAML 키는 중복 없는 문자열이어야 합니다.')
                result[key] = self.construct_object(value_node, deep=deep)
            return result
    path = Path(path)
    if path.suffix != '.yaml' or any(p.is_symlink() for p in (path.absolute(), *path.absolute().parents)):
        raise ValueError('계약 원본에는 심볼릭 링크가 아닌 .yaml 파일이 필요합니다.')
    try:
        return validate_definition(yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader))
    except yaml.YAMLError as exc:
        raise ValueError(f'계약 YAML 구문 오류: {path}: {exc}') from exc


def register_contract(registry, source):
    data = read_definition(source)
    entry = dict(contract_id=data['contractId'], version=data['version'], management_id=data['managementId'],
                 definition=json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')),
                 definition_hash=metadata_hash(data))
    with database(registry, Path(source).resolve().parent) as connection:
        old = connection.execute('SELECT * FROM contracts WHERE contract_id=? AND version=?',
                                 (data['contractId'], data['version'])).fetchone()
        if old is not None:
            if dict(old) != entry:
                raise ValueError('등록된 계약 ID/버전의 내용을 바꿀 수 없습니다. 새 버전을 등록하세요.')
            return entry
        if connection.execute('SELECT 1 FROM contracts WHERE management_id=?', (data['managementId'],)).fetchone():
            raise ValueError('계약 관리 ID가 중복되었습니다.')
        connection.execute('INSERT INTO contracts VALUES (:contract_id,:version,:management_id,:definition,:definition_hash)', entry)
    return entry


def resolve_contract(registry, contract_id, version):
    identifier(contract_id, 'contractId'); identifier(version, 'version')
    path = Path(registry).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        schema = connection.execute('PRAGMA user_version').fetchone()[0]
        if schema in (1, 2):
            raise ValueError('이 registry에는 등록 계약이 없습니다. YAML 계약을 먼저 등록하세요.')
        if schema != 3:
            raise ValueError('지원하지 않는 산출물 registry DB입니다.')
        row = connection.execute('SELECT * FROM contracts WHERE contract_id=? AND version=?',
                                 (contract_id, version)).fetchone()
    if row is None:
        raise ValueError(f'등록되지 않은 계약 ID/버전입니다: {contract_id}@{version}')
    data = validate_definition(json.loads(row['definition']))
    if (data['contractId'] != contract_id or data['version'] != version
            or data['managementId'] != row['management_id'] or metadata_hash(data) != row['definition_hash']):
        raise ValueError('등록된 계약의 내용과 해시가 일치하지 않습니다.')
    return data


def validate_contract_references(registry, artifact):
    for reference in artifact['contractRefs']:
        definition = resolve_contract(registry, reference['contractId'], reference['version'])
        if artifact['artifactType'] not in definition['artifactTypes']:
            raise ValueError(f"계약이 산출물 타입 {artifact['artifactType']}을 허용하지 않습니다: {reference['contractId']}")
