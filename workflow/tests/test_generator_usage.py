import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common.generator_usage import GENERATOR_USAGE_PATHS, read_generator_usage

class GeneratorUsageTests(unittest.TestCase):
    def test_domain_documents_are_distinct_and_unknown_rejected(self):
        self.assertIn("전진", read_generator_usage("wan22-vace"))
        self.assertIn("Kimodo", read_generator_usage("kimodo"))
        with self.assertRaises(ValueError):
            read_generator_usage("../kimodo")

    def test_missing_document_is_reported(self):
        with patch.dict(GENERATOR_USAGE_PATHS, {"kimodo": Path("/nonexistent/README.md")}):
            with self.assertRaisesRegex(OSError, "사용설명을 읽을 수 없습니다"):
                read_generator_usage("kimodo")
