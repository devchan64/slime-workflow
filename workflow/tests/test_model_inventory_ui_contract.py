"""격리 파일 목록과 공통 UI 검증의 연결을 확인한다."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from workflow.common.model_file_inventory import list_model_inventory_files


class ModelInventoryUiContractTests(unittest.TestCase):
    def test_inventory_responses_match_ui_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / '.model' / 'sample'
            model.mkdir(parents=True)
            (model / 'one').write_bytes(b'12')
            (model / 'two').write_bytes(b'345')
            paths = {'sample': [model], 'empty': [root / '.model' / 'missing']}
            records = list_model_inventory_files(paths, root)
            with patch('workflow.common.model_file_inventory.MODEL_INVENTORY_LIMIT', 1):
                truncated = list_model_inventory_files(paths, root)['sample']
            def failed_walk(path, *, followlinks, onerror):
                onerror(OSError('isolated failure'))
                return []
            with patch('workflow.common.model_file_inventory.os.walk', side_effect=failed_walk):
                incomplete = list_model_inventory_files(paths, root)['sample']
            self.assertTrue(truncated['truncated'])
            self.assertTrue(incomplete['incomplete'])
            cases = [[records['sample'], True], [records['empty'], True], [truncated, True],
                     [incomplete, True], [{**records['sample'], 'total_bytes': 1}, False]]
            script = """
              import assert from 'node:assert/strict';
              import {validModelInventory} from './gui/modelInventoryValidation.mjs';
              let data=''; for await (const part of process.stdin) data+=part;
              for (const [inventory,expected] of JSON.parse(data))
                assert.equal(validModelInventory(inventory),expected);
            """
            subprocess.run(['node', '--input-type=module', '-e', script],
                           input=json.dumps(cases), text=True, check=True,
                           cwd=Path(__file__).resolve().parents[2], capture_output=True)


if __name__ == '__main__':
    unittest.main()
