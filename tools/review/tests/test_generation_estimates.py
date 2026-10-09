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
