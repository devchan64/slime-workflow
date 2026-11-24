"""격리된 실제 이력 관측 결과와 공통 UI 페이지 계약을 연결한다."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from workflow.common.generation_records import observe_generation_history_records


class GeneratorHistoryUiContractTests(unittest.TestCase):
    def test_observed_pages_are_accepted_and_corrupt_next_offset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history, jobs = root / 'history', root / 'jobs'
            history.mkdir()
            jobs.mkdir()
            for index in range(3):
                job = jobs / f'2026-11-18_12-0{index}-00-{index:08x}'
                job.mkdir()
                (job / 'request.json').write_text(json.dumps({'prompt': 'isolated'}))
                (job / 'status.json').write_text(json.dumps({'status': 'completed'}))
            first = observe_generation_history_records(history, jobs, {'limit': 2})
            last = observe_generation_history_records(history, jobs, {
                'limit': 2, 'offset': first['next_offset'], 'snapshot': first['snapshot']})
            empty = observe_generation_history_records(history, jobs, {'limit': 2, 'query': 'missing'})
            cases = [[first, 0, 2, None, True], [last, 2, 2, first['snapshot'], True],
                     [empty, 0, 2, None, True], [{**first, 'next_offset': 3}, 0, 2, None, False]]
            script = """
              import assert from 'node:assert/strict';
              import {validGeneratorHistoryPage} from './gui/generatorHistoryPage.mjs';
              let data=''; for await (const part of process.stdin) data+=part;
              for (const [page,offset,limit,snapshot,expected] of JSON.parse(data))
                assert.equal(validGeneratorHistoryPage(page,offset,limit,snapshot),expected);
            """
            subprocess.run(['node', '--input-type=module', '-e', script],
                           input=json.dumps(cases), text=True, check=True,
                           cwd=Path(__file__).resolve().parents[2], capture_output=True)


if __name__ == '__main__':
    unittest.main()
