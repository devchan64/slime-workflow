"""공유 목록을 YAML 별칭 없이 저장하는 계약을 검증한다."""
import unittest
import yaml
from tools.review.maintenance.sync_billboard_catalog import serialize_billboard_catalog


class BillboardSerializationTest(unittest.TestCase):
    def test_shared_lists_preserve_values_without_aliases(self):
        current_shared_uses = ['석영맥 강조', '낙석 군집']
        current_catalog_record = {'family': {'uses': current_shared_uses},
                                  'modeling': {'recommended_uses': current_shared_uses}}
        current_yaml_text = serialize_billboard_catalog(current_catalog_record)
        self.assertEqual(yaml.safe_load(current_yaml_text), current_catalog_record)
        self.assertFalse(any(isinstance(current_yaml_event, yaml.events.AliasEvent)
                             for current_yaml_event in yaml.parse(current_yaml_text)))
