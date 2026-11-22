"""보관된 생성 입력은 기록 그대로 조회하며 새 작업을 만들 수 없다."""
import json
from pathlib import Path
import subprocess
import unittest

from workflow.common.management_gateway import ARCHIVED_QWEN_IMAGE_SERVICES, resolve_management_command


class ArchiveInputTests(unittest.TestCase):
    def test_archive_reads_original_request_and_denies_generation(self):
        script = """
            import {readArchiveJob} from './readArchiveJob.mjs';
            import assert from 'node:assert/strict';
            const [service, request] = JSON.parse(process.argv[1]);
            async function command(name, operation, payload) {
                assert.deepEqual([name, operation, payload], [service, 'history', {}]);
                return {records:[{id:'other',request:{}},{id:'saved',request}]};
            }
            assert.deepEqual(await readArchiveJob(command, service, 'missing'), {});
            process.stdout.write(JSON.stringify((await readArchiveJob(command, service, 'saved')).request));
        """
        gui = Path(__file__).resolve().parents[2] / 'gui'
        for service in ARCHIVED_QWEN_IMAGE_SERVICES:
            for seed in (0, 42):
                with self.subTest(service=service, seed=seed):
                    request = dict(seed=seed, prompt='saved', user_prompt='', width=768,
                                   height=512, steps=30, tag='원본', references=['b.png', 'a.png'],
                                   circular_vae=dict(boundary_radius=24, baseline_decode=False),
                                   soft_shading=False, pattern_view=True,
                                   expression=dict(id='removed-preset'),
                                   seamless_tile=dict(user_prompt='grass'))
                    output = subprocess.check_output(
                        ['node', '--input-type=module', '-e', script, json.dumps([service, request])],
                        cwd=gui, text=True)
                    self.assertEqual(json.loads(output), request)
                    with self.assertRaisesRegex(ValueError, '폐기'):
                        resolve_management_command(service, 'generate', request)
