"""합성 검수 기록의 멱등성·경쟁·과거 결정 보존."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import unittest
import test_sidecar as fixtures
from workflow.artifacts.registry import archive_register, resolve
from workflow.artifacts.reviews import record_review, current_review


class ReviewTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write

    def prepare(self):
        self.db = self.root.parent / 'registry.sqlite'
        entry = archive_register(self.db, self.root, self.sidecar)
        return dict(review_id='review.1', decision='APPROVED', reviewer='synthetic-reviewer',
                    evidence_ref='synthetic-evidence', content_hash=entry['content_hash'],
                    metadata_hash=entry['metadata_hash'])

    def record(self, **record):
        return record_review(self.db, 'terrain.test', '1.0.0', **record)

    def test_no_implicit_approval_and_idempotent_history(self):
        record = self.prepare()
        self.assertIsNone(current_review(self.db, 'terrain.test', '1.0.0'))
        first = self.record(**record)
        self.assertEqual(self.record(**record), first)
        rejected = self.record(**dict(record, review_id='review.2', decision='REJECTED', previous_review_id='review.1'))
        self.assertEqual(self.record(**record), first)
        self.assertEqual(current_review(self.db, 'terrain.test', '1.0.0'), rejected)
        self.assertEqual(resolve(self.db, 'terrain.test', '1.0.0'), self.data)

    def test_different_review_content_cannot_reuse_id(self):
        record = self.prepare(); self.record(**record)
        with self.assertRaises(ValueError): self.record(**dict(record, decision='REJECTED'))

    def test_stale_decisions_cannot_replace_latest_head(self):
        record = self.prepare(); self.record(**record)
        with self.assertRaises(ValueError): self.record(**dict(record, review_id='review.2'))
        self.assertEqual(current_review(self.db, 'terrain.test', '1.0.0')['review_id'], 'review.1')

    def test_concurrent_different_first_reviews_have_one_winner(self):
        record = self.prepare()
        def submit(index):
            try:
                return self.record(**dict(record, review_id=f'review.{index}'))
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, [1, 2]))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_review_hash_and_required_evidence(self):
        record = self.prepare()
        for changes in [dict(content_hash='0'*64), dict(metadata_hash='0'*64), dict(evidence_ref=''), dict(decision=True)]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError): self.record(**dict(record, **changes))
        self.assertIsNone(current_review(self.db, 'terrain.test', '1.0.0'))

    def test_history_update_and_delete_are_rejected_by_database(self):
        record = self.prepare(); self.record(**record)
        with sqlite3.connect(self.db) as connection:
            for statement in ["DELETE FROM reviews", "UPDATE reviews SET decision='REJECTED'"]:
                with self.assertRaises(sqlite3.IntegrityError): connection.execute(statement)
        self.assertEqual(current_review(self.db, 'terrain.test', '1.0.0')['decision'], 'APPROVED')

    def test_existing_v1_registry_expands_without_changing_artifact(self):
        record = self.prepare()
        with sqlite3.connect(self.db) as connection:
            connection.execute('DROP TABLE contracts')
            connection.execute('DROP TABLE review_heads')
            connection.execute('DROP TABLE reviews')
            connection.execute('PRAGMA user_version=1')
        with self.assertRaisesRegex(ValueError, '등록 계약'):
            current_review(self.db, 'terrain.test', '1.0.0')
        from workflow.artifacts.contracts import register_contract
        register_contract(self.db, self.contract_source)
        self.assertIsNone(current_review(self.db, 'terrain.test', '1.0.0'))
        self.record(**record)
        self.assertEqual(resolve(self.db, 'terrain.test', '1.0.0'), self.data)
