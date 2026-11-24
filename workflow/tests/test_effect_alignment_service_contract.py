"""콘텐츠 서비스와 GUI의 정렬 좌표 판정을 비교한다."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


class EffectAlignmentServiceContractTests(unittest.TestCase):
    def test_ui_bounds_match_content_service_for_normalized_values(self):
        root = Path(__file__).resolve().parents[2]
        service = root.parent / 'slime-backend' / 'app' / 'content_effect_assets.py'
        if not service.is_file():
            self.skipTest('콘텐츠 서비스 소스가 없습니다.')
        try:
            spec = importlib.util.spec_from_file_location('isolated_effect_assets', service)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except ModuleNotFoundError as error:
            self.skipTest(f'콘텐츠 서비스 의존성이 없습니다: {error.name}')
        row = [0, 0, 1, 1]
        valid = {'texture':'moths','key':'swarm','alpha':0.5,'target':row,'frames':[row[:] for _ in range(8)]}
        samples = [valid, {**valid,'target':[0,0,0,1]}, {**valid,'target':[-0.01,0,1,1]},
                   {**valid,'frames':valid['frames'][:7]}, {**valid,'frames':[[0,0,0,1]]+valid['frames'][1:]}]
        backend = []
        for sample in samples:
            try:
                module.validate_effect_alignment_values(sample,8)
                backend.append(True)
            except ValueError:
                backend.append(False)
        script = """import {effectAlignmentBoundsError as error} from './gui/effectAlignmentBounds.mjs';
          const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
          process.stdout.write(JSON.stringify(JSON.parse(Buffer.concat(chunks)).map(value=>!error(value))));"""
        result = subprocess.check_output(['node','--input-type=module','-e',script], cwd=root, input=json.dumps(samples), text=True)
        self.assertEqual(json.loads(result), backend)
        self.assertEqual(backend, [True,False,False,False,False])


if __name__ == '__main__':
    unittest.main()
