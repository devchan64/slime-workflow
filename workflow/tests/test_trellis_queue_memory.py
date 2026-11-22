"""A tiny prior probe must not lower the unmeasured TRELLIS model reservation."""
import unittest
from unittest.mock import patch

from workflow.common import gpu_memory_history as memory
from workflow.common import gpu_job_queue as queue


class TrellisQueueMemoryTest(unittest.TestCase):
    def test_probe_observation_does_not_reduce_floor(self):
        summary = {"peak_memory_mib": 198, "usable_runs": 1, "retained_runs": 1}
        with patch.object(memory, "load_recent_observations", return_value=[("probe", {})]), patch.object(memory, "summarize_memory_observations", return_value=summary):
            result = memory.estimate_required_memory("trellis-experiment", 32768, "queue_probe.py")
        self.assertEqual(result["required_memory_mib"], 32768)
        self.assertIn("trellis-experiment", queue.GPU_EXCLUSIVE_SERVICES)


if __name__ == "__main__":
    unittest.main()
