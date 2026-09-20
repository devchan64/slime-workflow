"""등록된 입력 출처의 누락·해시·변조·순환 검증."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import unittest
import test_sidecar as fixtures
from workflow.artifacts import registry


class ReferenceTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write

    def db(self):
        return self.root.parent / 'registry.sqlite'

    def reference(self, name):
        return dict(artifactId=name, version='1.0.0', sha256=self.data['sha256'])

    def test_registered_provenance_chain_is_preserved(self):
        registry.archive_register(self.db(), self.root, self.sidecar)
        self.data['artifactId'] = 'terrain.derived'
        self.data['sourceArtifacts'] = [self.reference('terrain.test')]
        self.write()
        registry.archive_register(self.db(), self.root, self.sidecar)
        self.assertEqual(registry.resolve(self.db(), 'terrain.derived', '1.0.0'), self.data)

    def test_missing_or_wrong_hash_input_is_not_registered(self):
        registry.archive_register(self.db(), self.root, self.sidecar)
        self.data['artifactId'] = 'terrain.derived'
        for source in [self.reference('unknown'), dict(self.reference('terrain.test'), sha256='0'*64)]:
            with self.subTest(source=source):
                self.data['sourceArtifacts'] = [source]; self.write()
                with self.assertRaises(ValueError): registry.archive_register(self.db(), self.root, self.sidecar)
                with self.assertRaises(ValueError): registry.registered_entry(self.db(), 'terrain.derived', '1.0.0')

    def test_input_archive_tampering_invalidates_derived_lookup(self):
        first = registry.archive_register(self.db(), self.root, self.sidecar)
        self.data['artifactId'] = 'terrain.derived'
        self.data['sourceArtifacts'] = [self.reference('terrain.test')]; self.write()
        registry.archive_register(self.db(), self.root, self.sidecar)
        source = Path(first['root']) / 'tile.png'
        source.chmod(0o644); source.write_bytes(b'changed-input')
        with self.assertRaises(ValueError): registry.resolve(self.db(), 'terrain.derived', '1.0.0')

    def test_self_reference_fails_before_creating_database(self):
        self.db().unlink()
        self.data['sourceArtifacts'] = [self.reference('terrain.test')]; self.write()
        with self.assertRaisesRegex(ValueError, '순환'): registry.archive_register(self.db(), self.root, self.sidecar)
        self.assertFalse(self.db().exists())

    def test_legacy_cycle_and_shared_input_graph(self):
        root = deepcopy(self.data)
        root['sourceArtifacts'] = [self.reference('a'), self.reference('b')]
        nodes = {}
        for key in ['a', 'b', 'shared']:
            nodes[key] = dict(deepcopy(self.data), artifactId=key,
                              sourceArtifacts=[] if key == 'shared' else [self.reference('shared')])
        with patch.object(registry, '_resolve_pair', side_effect=lambda _, name, version: nodes[name]) as lookup:
            registry.validate_references(self.db(), root)
            self.assertEqual(lookup.call_count, 3)
        nodes['shared']['sourceArtifacts'] = [self.reference('a')]
        with patch.object(registry, '_resolve_pair', side_effect=lambda _, name, version: nodes[name]):
            with self.assertRaisesRegex(ValueError, '순환'): registry.validate_references(self.db(), root)
