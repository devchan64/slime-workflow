"""계약 버전 고정·호환 타입·과거 registry 확장과 모든 송신 경계를 검사한다."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import yaml
import test_sidecar as fixtures
from workflow.artifacts.contracts import read_definition, register_contract, resolve_contract
from workflow.artifacts.registry import archive_register, register, resolve
from workflow.artifacts.reviews import current_review, record_review
from workflow.artifacts.exporter import export_asset


class ContractTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write

    def db(self):
        return self.root.parent / 'registry.sqlite'

    def test_contract_is_pinned_independent_of_source_changes(self):
        expected = read_definition(self.contract_source)
        with ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(lambda _: register_contract(self.db(), self.contract_source), range(8)))
        self.assertTrue(all(x == entries[0] for x in entries))
        self.contract_source.write_text(yaml.safe_dump(dict(expected, description='수정된 설명')))
        with self.assertRaisesRegex(ValueError, '새 버전'): register_contract(self.db(), self.contract_source)
        self.contract_source.unlink()
        self.assertEqual(resolve_contract(self.db(), 'terrain', '1'), expected)

    def test_strict_yaml_shape_duplicates_and_types(self):
        data = read_definition(self.contract_source)
        for bad in [dict(data, extra=True), dict(data, schemaVersion=True), dict(data, version=1),
                    dict(data, artifactTypes=[]), dict(data, artifactTypes=['TERRAIN_TILE']*2),
                    dict(data, artifactTypes=['UNKNOWN']), dict(data, artifactTypes=[True]),
                    dict(data, managementId=''), dict(data, description='')]:
            with self.subTest(bad=bad):
                self.contract_source.write_text(yaml.safe_dump(bad))
                with self.assertRaises(ValueError): read_definition(self.contract_source)
        self.contract_source.write_text(yaml.safe_dump(data)+'version: 2\n')
        with self.assertRaisesRegex(ValueError, '중복'): read_definition(self.contract_source)

    def test_new_version_needs_distinct_management_id(self):
        data = read_definition(self.contract_source)
        data['version'] = '2'
        self.contract_source.write_text(yaml.safe_dump(data))
        with self.assertRaisesRegex(ValueError, '관리 ID'): register_contract(self.db(), self.contract_source)
        data['managementId'] = 'contract.terrain.v2'
        self.contract_source.write_text(yaml.safe_dump(data))
        register_contract(self.db(), self.contract_source)
        self.assertEqual(resolve_contract(self.db(), 'terrain', '1')['version'], '1')
        self.assertEqual(resolve_contract(self.db(), 'terrain', '2')['version'], '2')

    def test_missing_version_or_incompatible_type_blocks_registration_and_archive(self):
        original = deepcopy(self.data)
        for changes in [dict(contractRefs=[dict(contractId='terrain',version='99')]),
                        dict(contractRefs=[dict(contractId='missing',version='1')]),
                        dict(artifactType='UI_ICON')]:
            self.data = dict(original, **changes); self.write()
            for action in (register, archive_register):
                with self.subTest(changes=changes, action=action), self.assertRaises(ValueError):
                    action(self.db(), self.root, self.sidecar)
        with sqlite3.connect(self.db()) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM artifacts').fetchone()[0], 0)
        self.assertFalse(self.db().with_suffix('.artifacts').exists())

    def test_database_rejects_contract_updates_and_deletion(self):
        with sqlite3.connect(self.db()) as connection:
            for statement in ('DELETE FROM contracts', "UPDATE contracts SET definition_hash='changed'"):
                with self.assertRaises(sqlite3.IntegrityError): connection.execute(statement)
        self.assertEqual(resolve_contract(self.db(), 'terrain', '1')['contractId'], 'terrain')

    def test_legacy_v2_lookup_requires_explicit_contract_registration(self):
        self.data['license'].update(licenseId='CC-BY-4.0', modificationAllowed=True, redistributionAllowed=True)
        self.write()
        entry = archive_register(self.db(), self.root, self.sidecar)
        review = dict(review_id='test.review', decision='APPROVED', reviewer='test', evidence_ref='test',
                      content_hash=entry['content_hash'], metadata_hash=entry['metadata_hash'])
        record_review(self.db(), 'terrain.test', '1.0.0', **review)
        with sqlite3.connect(self.db()) as connection:
            before = connection.execute('SELECT * FROM artifacts').fetchall()
            connection.execute('DROP TABLE contracts')
            connection.execute('PRAGMA user_version=2')
        for action in [lambda: resolve(self.db(),'terrain.test','1.0.0'),
                       lambda: current_review(self.db(),'terrain.test','1.0.0'),
                       lambda: record_review(self.db(),'terrain.test','1.0.0',**review),
                       lambda: export_asset(self.db(),'terrain.test','1.0.0',self.root.parent/'releases')]:
            with self.assertRaisesRegex(ValueError, '등록 계약'): action()
        # export의 쓰기 트랜잭션에서 시도한 스키마 확장도 실패와 함께 롤백한다.
        with sqlite3.connect(self.db()) as connection:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 2)
        register_contract(self.db(), self.contract_source)
        self.assertEqual(resolve(self.db(),'terrain.test','1.0.0'), self.data)
        self.assertEqual(current_review(self.db(),'terrain.test','1.0.0')['review_id'], 'test.review')
        export_asset(self.db(),'terrain.test','1.0.0',self.root.parent/'releases')
        with sqlite3.connect(self.db()) as connection:
            self.assertEqual(connection.execute('SELECT * FROM artifacts').fetchall(), before)
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 3)

    def test_contract_hash_tampering_is_detected(self):
        with sqlite3.connect(self.db()) as connection:
            connection.execute('DROP TRIGGER contracts_no_update')
            definition = read_definition(self.contract_source)
            definition['description'] = '변조'
            connection.execute('UPDATE contracts SET definition=?', (json.dumps(definition),))
        with self.assertRaisesRegex(ValueError, '해시'): resolve_contract(self.db(), 'terrain', '1')

    def test_cli_registration_and_source_log_protection(self):
        target = self.root.parent/'fresh.sqlite'
        args = [sys.executable, '-m', 'workflow.artifacts.contract_cli', '--registry',str(target),
                '--contract',str(self.contract_source),'--log']
        log = self.root.parent/'contract.log'
        result = subprocess.run(args+[str(log)], capture_output=True, text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('/artifact-contract/complete', log.read_text())
        self.assertEqual(resolve_contract(target,'terrain','1')['contractId'], 'terrain')
        before = self.contract_source.read_bytes()
        result = subprocess.run(args+[str(self.contract_source)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.contract_source.read_bytes(),before)
