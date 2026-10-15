"""공용 예상 시간의 무표본·진행·지연·종료 계약."""
from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo
from tools.review.common.generation_estimates import calculate_generation_estimate


class GenerationEstimateTests(unittest.TestCase):
    def test_estimate_lifecycle_states(self):
        current_status_record = {'status': 'running', 'started_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}
        self.assertIsNone(calculate_generation_estimate(current_status_record, [], '계산 중', '전체')['remaining'])
        current_estimate_record = calculate_generation_estimate(current_status_record, [60, 80], '이력', '전체')
        self.assertEqual(current_estimate_record['total_seconds'], 70)
        self.assertEqual(current_estimate_record['sample_count'], 2)
        self.assertGreater(current_estimate_record['remaining'], 0)
        current_status_record['started_at'] = (datetime.now(ZoneInfo('Asia/Seoul')) - timedelta(seconds=100)).isoformat()
        self.assertIn('지연', calculate_generation_estimate(current_status_record, [60], '이력', '전체')['basis'])
        for current_status_name in ('queued', 'completed', 'failed', 'cancelled'):
            current_status_record['status'] = current_status_name
            self.assertIsNone(calculate_generation_estimate(current_status_record, [60], '이력', '전체')['completion'])

    def test_running_estimate_never_rounds_to_completed_progress(self):
        from unittest.mock import patch
        current_fixed_clock = datetime(2026, 10, 15, 12, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        for current_elapsed_seconds in (99.94, 99.96, 99.999, 100, 101):
            with self.subTest(elapsed=current_elapsed_seconds):
                current_status_record = {'status': 'running', 'started_at': (current_fixed_clock - timedelta(seconds=current_elapsed_seconds)).isoformat()}
                with patch('tools.review.common.generation_estimates.datetime') as current_datetime_mock:
                    current_datetime_mock.now.return_value = current_fixed_clock
                    current_datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
                    current_estimate_record = calculate_generation_estimate(current_status_record, [100], '같은 설정 이력', '전체')
                if current_elapsed_seconds < 100:
                    self.assertLess(current_estimate_record['estimated_progress'], 100)
                    self.assertGreater(current_estimate_record['remaining'], 0)
                else:
                    self.assertIsNone(current_estimate_record['estimated_progress'])
                    self.assertIsNone(current_estimate_record['remaining'])
                    self.assertIn('지연', current_estimate_record['basis'])
